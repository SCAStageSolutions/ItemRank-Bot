import os
import logging
from flask import Flask, request, jsonify
from bot_handlers_spanish import setup_bot

# Configure logging (if not already configured)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback_secret_key_for_development")

# Global variable to store the bot updater
bot_updater = None

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ListRater Bot - Telegram Bot</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        <style>
            body {
                padding: 20px;
            }
            .command-list {
                background-color: var(--bs-dark); 
                padding: 15px;
                border-radius: 5px;
                margin-top: 20px;
            }
            .command-item {
                margin-bottom: 10px;
            }
            .command-name {
                font-weight: bold;
                color: var(--bs-info);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="my-4">Bot de Listas y Valoraciones para Telegram</h1>
            <div class="alert alert-success">
                <strong>Estado:</strong> Bot ejecutándose en modo de consulta
            </div>
            
            <div class="card my-4">
                <div class="card-header">
                    <h2>Acerca de Este Bot</h2>
                </div>
                <div class="card-body">
                    <p>ListRater es un bot de Telegram que te permite crear listas y valorar elementos del 0 al 10.</p>
                    <p>¡Perfecto para hacer seguimiento de tus películas, restaurantes, libros favoritos o cualquier otra cosa que quieras valorar!</p>
                    <h3 class="mt-4">Cómo Usar</h3>
                    <p>Encuentra el bot en Telegram: <a href="https://t.me/item_rank_bot" target="_blank">@item_rank_bot</a></p>
                    <p>Inicia una conversación con el bot y utiliza los comandos a continuación para crear y gestionar tus listas.</p>
                </div>
            </div>

            <div class="card my-4">
                <div class="card-header">
                    <h2>Comandos Disponibles</h2>
                </div>
                <div class="card-body command-list">
                    <div class="command-item">
                        <span class="command-name">/start</span> - Iniciar el bot y recibir un mensaje de bienvenida
                    </div>
                    <div class="command-item">
                        <span class="command-name">/newlist</span> - Crear una nueva lista
                    </div>
                    <div class="command-item">
                        <span class="command-name">/additem</span> - Añadir un elemento a una lista
                    </div>
                    <div class="command-item">
                        <span class="command-name">/lists</span> - Ver todas tus listas
                    </div>
                    <div class="command-item">
                        <span class="command-name">/viewlist</span> - Ver todos los elementos de una lista específica
                    </div>
                    <div class="command-item">
                        <span class="command-name">/rate</span> - Valorar un elemento de una lista (0-10)
                    </div>
                    <div class="command-item">
                        <span class="command-name">/ratings</span> - Ver valoraciones detalladas de los elementos en una lista
                    </div>
                    <div class="command-item">
                        <span class="command-name">/help</span> - Mostrar el mensaje de ayuda con todos los comandos
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook endpoint for Telegram updates.
    This is only used if webhook mode is enabled. Currently using polling mode.
    """
    return "Webhook mode not enabled. Bot is running in polling mode."

@app.route('/status')
def status():
    """Return the status of the bot."""
    global bot_updater
    
    if bot_updater:
        return jsonify({
            "status": "running",
            "mode": "polling"
        })
    else:
        return jsonify({
            "status": "not_running"
        })

# Initialize the bot on startup in a background thread
def start_bot():
    global bot_updater
    
    # If bot is already running, don't start it again
    if bot_updater:
        return
    
    # When running in the bot_app workflow or BOT_ONLY_MODE is set, don't start the bot in a separate thread
    # as it will be managed directly by bot_main.py
    if os.environ.get("WORKFLOW_NAME") == "bot_app" or os.environ.get("BOT_ONLY_MODE") == "1":
        logger.info("Bot is managed by a dedicated process, skipping thread creation")
        return
    
    logger.info("Starting the Telegram bot in polling mode...")
    try:
        # Start the bot in a separate thread
        import threading
        
        def run_bot():
            global bot_updater
            bot_updater = setup_bot()
            logger.info("Bot started successfully")
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

# Function to start the Flask app
def start_web_app():
    app.run(host="0.0.0.0", port=5000, debug=True)

# Register the function to run before the first request
with app.app_context():
    start_bot()

if __name__ == "__main__":
    # Only start the bot if running directly
    start_web_app()
