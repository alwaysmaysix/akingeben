import os
import subprocess
import logging
import time
import asyncio
import sys
from pyrogram import Client, errors
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

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
chat_id = os.getenv('TELEGRAM_CHAT_ID')  # The chat ID of the group or channel
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
dummy_channel_id = os.getenv('DUMMY_CHANNEL_ID')

# Custom API server configuration
custom_api_base = "http://localhost:8081"  # Use Docker's mapped port for the Telegram Bot API

# Define the user bot globally
userbot = None

def create_input_file(url):
    with open('input.txt', 'w') as f:
        f.write(url)

def delete_input_file():
    if os.path.exists('input.txt'):
        os.remove('input.txt')

async def dl(message: Message):
    url = message.get_args()
    if url:
        try:
            # Create input.txt with the URL
            create_input_file(url)

            # Call sb_scraper.py as a separate process
            result = subprocess.run(['python', 'sb_scraper.py'], capture_output=True, text=True)

            if result.returncode == 0:
                # Assume videos are downloaded to the current directory by sb_scraper.py
                video_files = [file for file in os.listdir() if file.endswith('.mp4')]

                if video_files:
                    for video_file in video_files:
                        try:
                            # Use the user bot to send the video file to the dummy channel
                            async with Client("userbot", api_id, api_hash) as userbot:
                                message = await userbot.send_document(dummy_channel_id, video_file)
                                message_id = message.message_id

                                # Provide the user with a link to download the file
                                download_link = f"http://localhost:8081/download/{message_id}"
                                await message.answer(f'Download your video from {download_link}')
                            os.remove(video_file)  # Optionally delete the video file after sending
                        except errors.FloodWait as e:
                            logger.error(f"FloodWait error: {e}")
                            time.sleep(e.x)  # Wait before retrying
                        except Exception as e:
                            logger.error(f"Failed to send video: {e}")
                            await message.answer(f'Failed to send video: {e}')
                else:
                    await message.answer(f'No videos found after downloading from {url}.')
            else:
                await message.answer(f'Failed to download videos from {url}: {result.stderr}')
        except Exception as e:
            await message.answer(f'Failed to download videos from {url}: {e}')
        finally:
            delete_input_file()  # Delete input.txt after processing
    else:
        await message.answer('Please provide a URL.')

async def main() -> None:
    global userbot

    # Initialize the user bot (Client)
    userbot = Client("userbot", api_id=api_id, api_hash=api_hash)
    await userbot.start()

    # Initialize the custom API server
    custom_api_server = TelegramAPIServer.from_base(custom_api_base)

    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=bot_token, session=AiohttpSession(api=custom_api_server), default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Create dispatcher
    dp = Dispatcher()

    # Register command handlers
    @dp.message(CommandStart())
    async def command_start_handler(message: Message) -> None:
        await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")

    @dp.message(Command("dl"))
    async def dl_command_handler(message: Message) -> None:
        await dl(message)

    @dp.message()
    async def echo_handler(message: Message) -> None:
        try:
            await message.send_copy(chat_id=message.chat.id)
        except TypeError:
            await message.answer("Nice try!")

    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # Run the udocker command to pull the image and run the container
    !pip install udocker > /dev/null
    !udocker --allow-root install > /dev/null
    !useradd -m user > /dev/null
    
    # Pull the Telegram Bot API image
    udocker("pull aiogram/telegram-bot-api:latest")
    
    # Use environment variables in the Docker run command
    udocker(f"run -d -p 8081:8081 --name=telegram-bot-api --restart=always -v telegram-bot-api-data:/var/lib/telegram-bot-api -e TELEGRAM_API_ID={api_id} -e TELEGRAM_API_HASH={api_hash} aiogram/telegram-bot-api:latest")
    
    # Start the main function
    asyncio.run(main())
