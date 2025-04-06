"""
Script especializado para ejecutar el bot de Telegram.
Este script está diseñado para ser utilizado por el workflow "bot_app".
"""
import os
import sys
import subprocess
import time
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Establecer variables de entorno
    os.environ["BOT_ONLY_MODE"] = "1"
    os.environ["WORKFLOW_NAME"] = "bot_app"
    
    # Verificar si el token existe
    if 'TELEGRAM_TOKEN' not in os.environ:
        logger.error("No se ha configurado TELEGRAM_TOKEN en las variables de entorno")
        sys.exit(1)
    
    logger.info("Iniciando bot de Telegram desde workflow...")
    
    try:
        # Ejecutar el bot como un proceso separado para evitar conflictos
        bot_process = subprocess.Popen([sys.executable, 'bot_only.py'])
        
        # Mantener el script principal en ejecución
        logger.info("Bot iniciado correctamente. Este script seguirá ejecutándose para mantener el workflow activo.")
        
        # Bucle para mantener el script principal en ejecución
        while True:
            # Verificar si el proceso del bot sigue en ejecución
            if bot_process.poll() is not None:
                logger.error("El proceso del bot ha terminado inesperadamente. Reiniciando...")
                bot_process = subprocess.Popen([sys.executable, 'bot_only.py'])
            
            time.sleep(30)  # Comprobar cada 30 segundos
            
    except KeyboardInterrupt:
        logger.info("Deteniendo el bot...")
        if 'bot_process' in locals() and bot_process.poll() is None:
            bot_process.terminate()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error al ejecutar el bot: {e}")
        if 'bot_process' in locals() and bot_process.poll() is None:
            bot_process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()