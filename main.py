import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check which workflow is running
WORKFLOW_NAME = os.environ.get('WORKFLOW_NAME', '')
logger.info(f"Running in workflow: {WORKFLOW_NAME}")

# Special handling for bot_app workflow
if WORKFLOW_NAME == 'bot_app':
    logger.info("Starting bot-only workflow")
    try:
        import bot_only
        sys.exit(0)  # Exit after bot is started
    except Exception as e:
        logger.error(f"Failed to start bot in workflow: {e}")
        sys.exit(1)
else:
    # Regular web application mode
    logger.info("Starting in web application mode")
    from app import app
    
    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=5000, debug=True)