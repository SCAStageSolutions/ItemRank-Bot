import logging
import os
import sys
import telegram
from telegram.ext import Updater

# Configure logging (if not already configured)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the bot token directly from environment variable
if 'TELEGRAM_TOKEN' not in os.environ:
    logger.error("TELEGRAM_TOKEN not set in environment variables")
    sys.exit(1)

TOKEN = os.environ.get('TELEGRAM_TOKEN')

def main():
    """Start the bot in direct polling mode without importing app.py."""
    # Set the workflow name environment variable
    os.environ["WORKFLOW_NAME"] = "bot_app"
    
    # Ensure we don't start the Flask server in this mode
    os.environ["BOT_ONLY_MODE"] = "1"
    
    logger.info("Starting the Telegram bot in standalone polling mode...")
    
    try:
        # Import here to avoid circular imports
        from bot_handlers_spanish import setup_bot
        
        # Setup the bot directly using the configured function
        updater = setup_bot()
        
        # Start polling
        updater.start_polling()
        
        # Run the bot until the user presses Ctrl-C
        logger.info("Bot started successfully. Press Ctrl+C to stop.")
        updater.idle()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()