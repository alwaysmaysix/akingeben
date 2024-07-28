import os
import subprocess
import logging
from telegram import Update
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

def dl(update: Update, context: CallbackContext):
    url = ' '.join(context.args)
    
    # Check if URL is provided
    if not url:
        update.message.reply_text('Please provide a URL.')
        return

    # Create input file
    create_input_file(url)

    # Prompt user to choose scraper
    update.message.reply_text('Choose scraper: /cscraper or /sb_scraper')

    # Define command handlers for cscraper and sb_scraper
    def cscraper(update: Update, context: CallbackContext):
        update.message.reply_text('Running cscraper...')
        # Call cscraper.py with parameters
        subprocess.run(['python', 'cscraper.py', url, './', 'yes'])
        update.message.reply_text('cscraper completed.')

    def sb_scraper(update: Update, context: CallbackContext):
        update.message.reply_text('Running sb_scraper...')
        # Call sb_scraper.py with parameters (assuming it also accepts similar parameters)
        subprocess.run(['python', 'sb_scraper.py', url, './', 'yes'])
        update.message.reply_text('sb_scraper completed.')

    # Add command handlers to dispatcher
    dispatcher = context.dispatcher
    dispatcher.add_handler(CommandHandler('cscraper', cscraper))
    dispatcher.add_handler(CommandHandler('sb_scraper', sb_scraper))

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hi! Use /dl <URL> to start the download process.')

def main() -> None:
    updater = Updater(bot_token)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('dl', dl))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
