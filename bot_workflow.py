"""
Bot launcher for the bot_app workflow.
This script is designed to be used by the bot_app workflow ONLY.
It ensures that the bot runs in standalone mode without Flask.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables to force bot-only mode
os.environ["BOT_ONLY_MODE"] = "1"
os.environ["WORKFLOW_NAME"] = "bot_app"

# Check if the token exists
if 'TELEGRAM_TOKEN' not in os.environ:
    logger.error("TELEGRAM_TOKEN environment variable is not set")
    sys.exit(1)

# Run the bot directly from bot_only.py
try:
    logger.info("Starting bot from workflow using bot_only.py...")
    import bot_only
except Exception as e:
    logger.error(f"Failed to start bot in workflow: {e}")
    sys.exit(1)