import os
import subprocess
import logging
import time
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv
from pyrogram import Client, errors
from pyngrok import ngrok
import threading
from flask import Flask, request, send_file
from telethon import TelegramClient, events

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

# Define the user bot globally
userbot = None

app = Flask(__name__)

@app.route('/')
def home():
    return "Server is running"

@app.route('/download/<file_id>')
def download_file(file_id):
    try:
        async def download():
            async with TelegramClient('anon', api_id, api_hash) as client:
                message = await client.get_messages(dummy_channel_id, ids=int(file_id))
                if message and message.media:
                    path = await message.download_media()
                    return path
        file_path = download()
        if file_path:
            return send_file(file_path, as_attachment=True)
        else:
            return "File not found", 404
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return "Error downloading file", 500

def run_flask_app():
    app.run(port=3000)

def create_input_file(url):
    with open('input.txt', 'w') as f:
        f.write(url)

def delete_input_file():
    if os.path.exists('input.txt'):
        os.remove('input.txt')

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
                            # Use the user bot to send the video file to the dummy channel
                            with open(video_file, 'rb') as video:
                                message = userbot.send_document(dummy_channel_id, video)
                                message_id = message.message_id

                                # Provide the user with a link to download the file
                                public_url = ngrok.connect(3000)
                                download_link = f"{public_url}/download/{message_id}"
                                update.message.reply_text(f'Download your video from {download_link}')
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

def main():
    global userbot

    # Prompt the user to choose between using an existing session or creating a new one
    use_existing_session = input("Do you want to use an existing Pyrogram session? (yes/no): ").strip().lower()

    if use_existing_session == 'yes':
        userbot_session_string = input("Please enter the session string: ").strip()
    else:
        userbot_session_string = None

    # Initialize the user bot (Client)
    if userbot_session_string:
        userbot = Client("userbot", api_id=api_id, api_hash=api_hash, session_string=userbot_session_string)
    else:
        userbot = Client("userbot", api_id=api_id, api_hash=api_hash)

    userbot.start()

    # Initialize the updater and dispatcher
    updater = Updater(bot_token)
    
    # Log bot start
    logger.info('Starting the bot...')
    
    dp = updater.dispatcher

    # Add the /dl command handler
    dp.add_handler(CommandHandler('dl', dl))

    # Start the bot
    updater.start_polling()
    updater.idle()

    userbot.stop()  # Ensure the user bot is stopped when the main program exits

if __name__ == '__main__':
    # Start Flask server in a separate thread
    threading.Thread(target=run_flask_app).start()
    
    # Start the ngrok tunnel after the Flask server is up and running
    public_url = ngrok.connect(3000)
    print(f'Public URL: {public_url}')
    
    main()
