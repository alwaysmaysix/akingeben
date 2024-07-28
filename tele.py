import os
import subprocess
import logging
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Updater, CommandHandler, CallbackContext
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
chat_id = os.getenv('TELEGRAM_CHAT_ID')
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

def create_input_file(url):
    with open('input.txt', 'w') as f:
        f.write(url)

def delete_input_file():
    if os.path.exists('input.txt'):
        os.remove('input.txt')

def send_media_files(update: Update, context: CallbackContext, media_type: str, folder_path: str):
    # Check if the directory exists
    if not os.path.exists(folder_path):
        update.message.reply_text(f'No media files found in {folder_path}.')
        return

    files = os.listdir(folder_path)

    if not files:
        update.message.reply_text(f'No media files found in {folder_path}.')
        return

    media_files = []
    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        if media_type == 'Pics':
            media_files.append(InputMediaPhoto(open(file_path, 'rb')))
        elif media_type == 'Vids':
            media_files.append(InputMediaVideo(open(file_path, 'rb')))

    if media_files:
        for i in range(0, len(media_files), 10):
            update.message.reply_media_group(media_files[i:i + 10])
            os.remove(media_file_path)  # Moved to correct indent level

def cscraper(update: Update, context: CallbackContext):
    url = ' '.join(context.args)
    
    # Check if URL is provided
    if not url:
        update.message.reply_text('Please provide a URL.')
        return

    update.message.reply_text('Running cscraper...')
    # Call cscraper.py with parameters
    subprocess.run(['python', 'cscraper.py', url, './', 'yes'])
    update.message.reply_text('cscraper completed.')
    # Send media files
    send_media_files(update, context, 'Pics', './Pics')
    send_media_files(update, context, 'Vids', './Vids')

def sb_scraper(update: Update, context: CallbackContext):
    url = ' '.join(context.args)
    
    # Check if URL is provided
    if not url:
        update.message.reply_text('Please provide a URL.')
        return

    update.message.reply_text('Running sb_scraper...')
    
    try:
        # Call sb_scraper.py as a separate process
        result = subprocess.run(['python', 'sb_scraper.py', url, './', 'yes'], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Assume videos are downloaded to the current directory by sb_scraper.py
            video_files = [file for file in os.listdir() if file.endswith('.mp4')]
            
            if video_files:
                for video_file in video_files:
                    try:
                        # Send the video file using the bot
                        with open(video_file, 'rb') as video:
                            update.message.reply_video(
                                video=video,
                                caption=f'Downloaded video from {url}'  # Optional caption
                            )
                        os.remove(video_file)  # Optionally delete the video file after sending
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

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hi! Use /cscraper <URL> or /sb_scraper <URL> to start the download process.')

def main() -> None:
    updater = Updater(bot_token)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('cscraper', cscraper))
    dispatcher.add_handler(CommandHandler('sb_scraper', sb_scraper))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
