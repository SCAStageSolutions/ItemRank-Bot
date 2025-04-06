"""
Script dedicado para ejecutar el bot en modo independiente, 
específicamente para el workflow "bot_app".
Este script evita cualquier conflicto con Flask.
"""
import os
import sys
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Establecer variables de entorno específicas para el modo bot
os.environ["BOT_ONLY_MODE"] = "1"
os.environ["WORKFLOW_NAME"] = "bot_app"

# Verificar si el token existe
if 'TELEGRAM_TOKEN' not in os.environ:
    logger.error("TELEGRAM_TOKEN no está configurado en las variables de entorno")
    sys.exit(1)

# Iniciar el bot directamente sin Flask
try:
    # Importar el módulo del bot en español
    from bot_handlers_spanish import setup_bot
    
    logger.info("Iniciando bot de Telegram en modo independiente...")
    updater = setup_bot()
    
    # Iniciar polling
    updater.start_polling()
    
    # Mantener el bot ejecutándose hasta que se interrumpa manualmente
    logger.info("Bot iniciado correctamente. Presione Ctrl+C para detener.")
    updater.idle()
except Exception as e:
    logger.error(f"Error al iniciar el bot: {e}")
    sys.exit(1)