import os
import subprocess
import logging
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv
from pyrogram import Client

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

def create_input_file(url):
    with open('input.txt', 'w') as f:
        f.write(url)

def delete_input_file():
    if os.path.exists('input.txt'):
        os.remove('input.txt')

def download_progress_hook(stream, chunk, bytes_remaining):
    """Update download progress"""
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    print(f"Download progress: {percentage:.2f}%")

def upload_progress_callback(current, total, context, message_id):
    """Update upload progress"""
    percentage = (current / total) * 100
    context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=f"Uploading: {percentage:.2f}%"
    )

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
                        # Send initial message for progress tracking
                        progress_message = context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="Uploading: 0.00%"
                        )
                        message_id = progress_message.message_id
                        
                        # Use the user bot to send the video file
                        with open(video_file, 'rb') as video:
                            userbot.send_video(
                                chat_id=chat_id,
                                video=video,
                                supports_streaming=True,  # Enable streaming support for large files
                                progress=upload_progress_callback,
                                progress_args=(context, message_id)
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
    main()
