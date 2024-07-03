import os
import subprocess
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import logging
from dotenv import load_dotenv
from pyrogram import Client
import getpass

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

def get_userbot_session():
    choice = input("Do you want to use an existing Pyrogram session (yes/no)? ").strip().lower()
    if choice == 'yes':
        session_string = os.getenv('USERBOT_SESSION_STRING')
        if not session_string:
            raise ValueError("USERBOT_SESSION_STRING is not set in the environment variables.")
        return Client("userbot", api_id=api_id, api_hash=api_hash, session_string=session_string)
    else:
        phone_number = input("Enter your phone number: ").strip()
        return Client("userbot", api_id=api_id, api_hash=api_hash, phone_number=phone_number)

# Initialize the user bot (Client)
userbot = get_userbot_session()
userbot.start()

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
                        # Use the user bot to send the video file
                        userbot.send_video(
                            chat_id=chat_id,
                            video=video_file,
                            supports_streaming=True  # Enable streaming support for large files
                        )
                        os.remove(video_file)  # Optionally delete the video file after sending
                    update.message.reply_text(f'Downloaded videos from {url} sent to group/channel.')
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

if __name__ == '__main__':
    main()
    userbot.stop()  # Ensure the user bot is stopped when the main program exits
