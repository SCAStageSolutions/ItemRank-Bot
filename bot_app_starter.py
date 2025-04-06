import logging
import os
import sys

# Configure logging (if not already configured)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables to indicate we're in bot-only mode
os.environ["BOT_ONLY_MODE"] = "1"
os.environ["WORKFLOW_NAME"] = "bot_app"

# Import the bot main function
from bot_main import main

# Run the bot
if __name__ == "__main__":
    try:
        logger.info("Starting the Telegram bot in standalone mode...")
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
