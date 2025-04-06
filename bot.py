import logging
import os
from bot_handlers_new import setup_bot

# Configure logging (if not already configured)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Start the bot in polling mode."""
    # Set the workflow name environment variable
    os.environ["WORKFLOW_NAME"] = "bot_app"
    
    # Ensure we don't start the Flask server in this mode
    os.environ["BOT_ONLY_MODE"] = "1"
    
    # Set a different port for Flask in case it gets initialized anyway
    os.environ["FLASK_RUN_PORT"] = "5001"
    
    logger.info("Starting the Telegram bot in standalone polling mode...")
    
    try:
        # Set up and start the bot
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