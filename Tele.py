import os
import subprocess
import logging
import asyncio
from moviepy.editor import VideoFileClip
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo
from pyrogram.errors import FloodWait
from dotenv import load_dotenv
from datetime import datetime
from PIL import Image

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

class BotTimes:
    task_start = None

class MSG:
    sent_msg = None

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

def generate_thumbnail(video_path):
    try:
        clip = VideoFileClip(video_path)
        thumbnail_path = f"{os.path.splitext(video_path)[0]}.jpg"
        clip.save_frame(thumbnail_path, t=(clip.duration / 2))
        clip.close()
        return thumbnail_path
    except Exception as e:
        logger.error(f"Error generating thumbnail for {video_path}: {e}")
        return None

async def progress_bar(current, total):
    upload_speed = 4 * 1024 * 1024
    elapsed_time_seconds = (datetime.now() - BotTimes.task_start).seconds
    if current > 0 and elapsed_time_seconds > 0:
        upload_speed = current / elapsed_time_seconds
    eta = (total - current) / upload_speed
    percentage = (current / total) * 100
    print(f"Upload Progress: {percentage:.2f}% | Speed: {upload_speed:.2f} B/s | ETA: {eta:.2f} s")

async def upload_file(client, chat_id, file_path, caption, f_type):
    BotTimes.task_start = datetime.now()

    try:
        if f_type == "video":
            duration, width, height = get_video_attributes(file_path)
            if not duration or not width or not height:
                raise ValueError("Invalid video attributes")
            thumbnail_path = generate_thumbnail(file_path)
            MSG.sent_msg = await client.send_video(
                chat_id=chat_id,
                video=file_path,
                supports_streaming=True,
                width=width,
                height=height,
                caption=caption,
                thumb=thumbnail_path,
                duration=duration,
                progress=progress_bar
            )

        elif f_type == "audio":
            thumbnail_path = None if not os.path.exists("thumb.jpg") else "thumb.jpg"
            MSG.sent_msg = await client.send_audio(
                chat_id=chat_id,
                audio=file_path,
                caption=caption,
                thumb=thumbnail_path,
                progress=progress_bar
            )

        elif f_type == "document":
            thumbnail_path = "thumb.jpg" if os.path.exists("thumb.jpg") else None
            MSG.sent_msg = await client.send_document(
                chat_id=chat_id,
                document=file_path,
                caption=caption,
                thumb=thumbnail_path,
                progress=progress_bar
            )

        elif f_type == "photo":
            MSG.sent_msg = await client.send_photo(
                chat_id=chat_id,
                photo=file_path,
                caption=caption,
                progress=progress_bar
            )

    except FloodWait as e:
        await asyncio.sleep(e.value)
        await upload_file(client, chat_id, file_path, caption, f_type)
    except Exception as e:
        logging.error(f"Error When Uploading : {e}")

async def send_media_files(client, message, media_type, folder_path):
    if not os.path.exists(folder_path):
        await message.reply_text(f'No media files found in {folder_path}.')
        return

    files = os.listdir(folder_path)
    if not files:
        await message.reply_text(f'No media files found in {folder_path}.')
        return

    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        caption = f"Downloaded {media_type.lower()} file: {file_name}"

        if media_type == 'Pics':
            await upload_file(client, message.chat.id, file_path, caption, 'photo')
        elif media_type == 'Vids':
            await upload_file(client, message.chat.id, file_path, caption, 'video')

        os.remove(file_path)  # Optionally delete the file after sending

@app.on_message(filters.command("cscraper"))
async def cscraper(client, message):
    url = ' '.join(message.command[1:])
    if not url:
        await message.reply_text('Please provide a URL.')
        return

    await message.reply_text('Running cscraper...')
    subprocess.run(['python', 'cscraper.py', url, './', 'yes'])
    await message.reply_text('cscraper completed.')
    await send_media_files(client, message, 'Vids', './Vids')
    delete_already_dl_file()

@app.on_message(filters.command("sb_scraper"))
async def sb_scraper(client, message):
    url = ' '.join(message.command[1:])
    if not url:
        await message.reply_text('Please provide a URL.')
        return

    create_input_file(url)
    await message.reply_text('Running sb_scraper...')

    try:
        result = subprocess.run(['python', 'sb_scraper.py'], capture_output=True, text=True)
        if result.returncode == 0:
            video_files = [file for file in os.listdir() if file.endswith('.mp4')]
            if video_files:
                for video_file in video_files:
                    try:
                        await upload_file(client, message.chat.id, video_file, f'Downloaded video from {url}', 'video')
                        os.remove(video_file)  # Optionally delete the video file after sending
                    except FloodWait as e:
                        logger.warning(f"Flood wait exception: waiting for {e.value} seconds.")
                        await asyncio.sleep(e.value)
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
        delete_input_file()
        delete_already_dl_file()

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text('Hi! Use /cscraper <URL> or /sb_scraper <URL> to start the download process.')

if __name__ == '__main__':
    app.run()
