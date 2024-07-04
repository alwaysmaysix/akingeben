import os
import subprocess
import logging
import time
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv
from pyrogram import Client, errors

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')

# Telegram Bot API credentials
bot_token = os.getenv('TELEGRAM_BOT_API_KEY')

# Function to create input file
def create_input_file(url):
    with open('input.txt', 'w') as f:
        f.write(url)

# Function to delete input file
def delete_input_file():
    if os.path.exists('input.txt'):
        os.remove('input.txt')

# Command handler for /dl
def dl(update: Update, context: CallbackContext):
    url = ' '.join(context.args)
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
                            # Use the user bot to send the video file
                            with open(video_file, 'rb') as video:
                                update.message.reply_video(
                                    video=video,
                                    caption=f'Downloaded video from {url}'  # Optional caption
                                )
                            os.remove(video_file)  # Optionally delete the video file after sending
                        except errors.FloodWait as e:
                            logger.error(f"FloodWait error: {e}")
                            time.sleep(e.x)  # Wait before retrying
                        except Exception as e:
                            logger.error(f"Failed to send video: {e}")
                            update.message.reply_text(f'Failed to send video: {e}')
                else:
                    update.message.reply_text(f'No videos found after downloading from {url}.')
            else:
                update.message.reply_text(f'Failed to download videos from {url}: {result.stderr}')
        except Exception as e:
            update.message.reply_text(f'Failed to download videos from {url}: {e}')
        finally:
            delete_input_file()  # Delete input.txt after processing
    else:
        update.message.reply_text('Please provide a URL.')

# Function to start the bot and handle commands
def start_bot():
    updater = Updater(bot_token)
    dp = updater.dispatcher

    # Add command handlers
    dp.add_handler(CommandHandler("dl", dl))

    # Start the bot
    updater.start_polling()
    logger.info("Bot started polling.")
    updater.idle()
    logger.info("Bot stopped gracefully.")

# Function to start the Telegram API server
def start_telegram_api():
    # Run Telegram API server
    server_process = subprocess.Popen(['./telegram-bot-api/bin/telegram-bot-api', 
                                       '--api-id', api_id,
                                       '--api-hash', api_hash])
    logger.info("Telegram API server started.")

    # Wait for the server process to finish
    server_process.wait()
    logger.info("Telegram API server stopped.")

if __name__ == "__main__":
    # Start Telegram API server in a separate thread or process
    api_server_process = subprocess.Popen(['python', '-c', 'from __main__ import start_telegram_api; start_telegram_api()'])

    # Start the bot
    start_bot()

    # Clean up and terminate the Telegram API server
    api_server_process.terminate()
    api_server_process.wait()
