import os
import subprocess
import logging
import asyncio
from moviepy.editor import VideoFileClip
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo
from pyrogram.errors import FloodWait
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load API credentials from environment variables
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def create_input_file(url):
    with open('input.txt', 'w') as f:
        f.write(url)

def delete_input_file():
    if os.path.exists('input.txt'):
        os.remove('input.txt')

def delete_already_dl_file():
    if os.path.exists('already_dl.txt'):
        os.remove('already_dl.txt')

def get_video_attributes(video_path):
    try:
        clip = VideoFileClip(video_path)
        duration = int(clip.duration)
        width, height = clip.size
        clip.close()
        return duration, width, height
    except Exception as e:
        logger.error(f"Error getting video attributes for {video_path}: {e}")
        return None, None, None

async def send_media_files(client, message, media_type, folder_path):
    # Check if the directory exists
    if not os.path.exists(folder_path):
        await message.reply_text(f'No media files found in {folder_path}.')
        return

    files = os.listdir(folder_path)

    if not files:
        await message.reply_text(f'No media files found in {folder_path}.')
        return

    media_files = []
    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        if media_type == 'Pics':
            media_files.append(InputMediaPhoto(file_path))
        elif media_type == 'Vids':
            duration, width, height = get_video_attributes(file_path)
            if duration and width and height:
                media_files.append(
                    InputMediaVideo(
                        media=file_path,
                        duration=duration,
                        width=width,
                        height=height,
                        supports_streaming=True
                    )
                )

    if media_files:
        for i in range(0, len(media_files), 10):
            try:
                await client.send_media_group(chat_id=message.chat.id, media=media_files[i:i + 10])
                await asyncio.sleep(2)  # Introduce a small delay between batches
            except FloodWait as e:
                logger.warning(f"Flood wait exception: waiting for {e.value} seconds.")
                await asyncio.sleep(e.value)  # Wait for the specified time before continuing
            except Exception as e:
                logger.error(f"Failed to send media group: {e}")
                await message.reply_text(f"Failed to send media group: {e}")

    # Remove files after sending
    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        os.remove(file_path)

@app.on_message(filters.command("cscraper"))
async def cscraper(client, message):
    url = ' '.join(message.command[1:])

    # Check if URL is provided
    if not url:
        await message.reply_text('Please provide a URL.')
        return

    await message.reply_text('Running cscraper...')
    # Call cscraper.py with parameters
    subprocess.run(['python', 'cscraper.py', url, './', 'yes'])
    await message.reply_text('cscraper completed.')
    # Send media files
   
    await send_media_files(client, message, 'Vids', './Vids')
    # Delete already_dl.txt file
    delete_already_dl_file()

@app.on_message(filters.command("sb_scraper"))
async def sb_scraper(client, message):
    url = ' '.join(message.command[1:])
    if not url:
        await message.reply_text('Please provide a URL.')
        return

    # Create input.txt with the URL
    create_input_file(url)
    await message.reply_text('Running sb_scraper...')

    try:
        # Call sb_scraper.py as a separate process
        result = subprocess.run(['python', 'sb_scraper.py'], capture_output=True, text=True)

        if result.returncode == 0:
            # Assume videos are downloaded to the current directory by sb_scraper.py
            video_files = [file for file in os.listdir() if file.endswith('.mp4')]

            if video_files:
                for video_file in video_files:
                    try:
                        # Get video attributes
                        duration, width, height = get_video_attributes(video_file)
                        if duration and width and height:
                            # Send the video file using the bot
                            await client.send_video(
                                chat_id=message.chat.id,
                                video=video_file,
                                caption=f'Downloaded video from {url}',  # Optional caption
                                supports_streaming=True,
                                duration=duration,
                                width=width,
                                height=height
                            )
                            os.remove(video_file)  # Optionally delete the video file after sending
                    except FloodWait as e:
                        logger.warning(f"Flood wait exception: waiting for {e.value} seconds.")
                        await asyncio.sleep(e.value)  # Wait for the specified time before continuing
                    except Exception as e:
                        logger.error(f"Failed to send video: {e}")
                        await message.reply_text(f'Failed to send video: {e}')
            else:
                await message.reply_text(f'No videos found after downloading from {url}.')
        else:
            await message.reply_text(f'Failed to download videos from {url}: {result.stderr}')
    except Exception as e:
        await message.reply_text(f'Failed to download videos from {url}: {e}')
    finally:
        delete_input_file()  # Delete input.txt after processing
        delete_already_dl_file()  # Delete already_dl.txt after processing

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text('Hi! Use /cscraper <URL> or /sb_scraper <URL> to start the download process.')

if __name__ == '__main__':
    app.run()
