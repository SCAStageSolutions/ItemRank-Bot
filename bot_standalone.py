"""
Standalone bot script that avoids importing Flask.
This is a specialized launcher for the workflow "bot_app".
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables for bot mode
os.environ["BOT_ONLY_MODE"] = "1"
os.environ["WORKFLOW_NAME"] = "bot_app"

def main():
    """Start the bot directly without importing app.py"""
    # Verify token exists
    if 'TELEGRAM_TOKEN' not in os.environ:
        logger.error("TELEGRAM_TOKEN environment variable is not set")
        sys.exit(1)
        
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