import os
import json
import logging
from logging.handlers import RotatingFileHandler

DATA_DIR = './data'
LOG_DIR = os.path.join(DATA_DIR, './logs')
CONFIG_DIR = './config'
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
LOG_FILE = os.path.join(LOG_DIR, 'bot.log')
WORD_LIST_FILE = os.path.join(DATA_DIR, 'wordlist.txt')
RESULTS_FILE = os.path.join(DATA_DIR, 'results.txt')
DYNAMIC_DATA_FILE = os.path.join(DATA_DIR, 'dynamic_data.json')

IsInDockerContainer = os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False)

if IsInDockerContainer:
    DATA_DIR = '/app/data'
    CONFIG_DIR = '/app/config'
    CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
    LOG_DIR = os.path.join(DATA_DIR, 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'bot.log')
    WORD_LIST_FILE = os.path.join(DATA_DIR, 'wordlist.txt')
    RESULTS_FILE = os.path.join(DATA_DIR, 'results.txt')
    DYNAMIC_DATA_FILE = os.path.join(DATA_DIR, 'dynamic_data.json')

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

CONFIG = load_config()

# Get SECRET from environment variable
SECRET = os.environ.get('BOT_SECRET')

if not SECRET:
    SECRET = CONFIG["SECRET"]

# Ensure directories exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

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
