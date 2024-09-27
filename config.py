import os
import json
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = '/app/data/logs'
LOG_FILE = os.path.join(LOG_DIR, 'bot.log')

CONFIG_FILE = './config.json'
IsInDockerContainer = os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False)

if IsInDockerContainer:
    CONFIG_FILE = '/app/config/config.json'

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)
    
CONFIG = load_config()

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(level=getattr(logging, CONFIG.get("LOG_LEVEL", "INFO")),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Create a rotating file handler
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Get the root logger and add the file handler
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)

# Create a logger for this module
logger = logging.getLogger(__name__)