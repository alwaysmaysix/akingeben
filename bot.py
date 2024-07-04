import os
import subprocess
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv
from pyrogram import Client, errors

# Initialize Flask app
app = Flask(__name__)

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
chat_id = os.getenv('TELEGRAM_CHAT_ID')  # The chat ID of the group or channel

# Function to create input.txt with URL
def create_input_file(url):
    with open('input.txt', 'w') as f:
        f.write(url)

# Function to delete input.txt
def delete_input_file():
    if os.path.exists('input.txt'):
        os.remove('input.txt')

# Command handler for /dl command
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
                                context.bot.send_video(
                                    chat_id=update.effective_chat.id,
                                    video=video,
                                    caption=f'Downloaded video from {url}'  # Optional caption
                                )
                            os.remove(video_file)  # Optionally delete the video file after sending
                        except errors.FloodWait as e:
                            logger.error(f"FloodWait error: {e}")
                            time.sleep(e.x)  # Wait before retrying
                        except Exception as e:
                            logger.error(f"Failed to send video: {e}")
                            context.bot.send_message(chat_id=update.effective_chat.id,
                                                     text=f'Failed to send video: {e}')
                else:
                    context.bot.send_message(chat_id=update.effective_chat.id,
                                             text=f'No videos found after downloading from {url}.')
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f'Failed to download videos from {url}: {result.stderr}')
        except Exception as e:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f'Failed to download videos from {url}: {e}')
        finally:
            delete_input_file()  # Delete input.txt after processing
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Please provide a URL.')

# Telegram webhook handler for receiving updates
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return 'ok'

def main():
    global bot

    # Initialize the updater and dispatcher
    updater = Updater(bot_token)
    bot = updater.bot
    dp = updater.dispatcher

    # Add the /dl command handler
    dp.add_handler(CommandHandler('dl', dl))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
