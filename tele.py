import os
import subprocess
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo
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

async def progress(current, total, message, action, file_name):
    await message.edit_text(f"{action} {file_name}: {current * 100 / total:.1f}%")

async def send_video_files(client, message, folder_path, delay=5):
    if not os.path.exists(folder_path):
        await message.reply_text(f'No media files found in {folder_path}.')
        return

    files = os.listdir(folder_path)
    if not files:
        await message.reply_text(f'No media files found in {folder_path}.')
        return

    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        try:
            status_message = await message.reply_text(f"Uploading {file_name}...")
            await client.send_video(
                chat_id=message.chat.id,
                video=file_path,
                caption=f'Downloaded video from {file_name}',
                file_name=file_name,
                supports_streaming=True,
                progress=progress,
                progress_args=(status_message, 'Uploading', file_name)
            )
            os.remove(file_path)
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Failed to send video {file_name}: {e}")
            await message.reply_text(f'Failed to send video {file_name}: {e}')

@app.on_message(filters.command("cscraper"))
async def cscraper(client, message):
    url = ' '.join(message.command[1:])
    if not url:
        await message.reply_text('Please provide a URL.')
        return

    status_message = await message.reply_text(f"Downloading from {url}...")
    try:
        subprocess.run(['python', 'cscraper.py', url, './', 'yes'])
        await status_message.edit_text('cscraper completed.')
        await send_video_files(client, message, './Pics')
        await send_video_files(client, message, './Vids')
    except Exception as e:
        await status_message.edit_text(f"cscraper failed: {e}")

@app.on_message(filters.command("sb_scraper"))
async def sb_scraper(client, message):
    url = ' '.join(message.command[1:])
    if not url:
        await message.reply_text('Please provide a URL.')
        return

    create_input_file(url)
    status_message = await message.reply_text(f"Downloading from {url}...")

    try:
        result = subprocess.run(['python', 'sb_scraper.py'], capture_output=True, text=True)

        if result.returncode == 0:
            video_files = [file for file in os.listdir() if file.endswith('.mp4')]
            if video_files:
                for video_file in video_files:
                    await send_video_files(client, message, video_file)
            else:
                await status_message.edit_text(f'No videos found after downloading from {url}.')
        else:
            await status_message.edit_text(f'Failed to download videos from {url}: {result.stderr}')
    except Exception as e:
        await status_message.edit_text(f'Failed to download videos from {url}: {e}')
    finally:
        delete_input_file()

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text('Hi! Use /cscraper <URL> or /sb_scraper <URL> to start the download process.')

if __name__ == '__main__':
    app.run()
