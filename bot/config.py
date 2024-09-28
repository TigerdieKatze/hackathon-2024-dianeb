import os
import json
import logging
from logging.handlers import RotatingFileHandler

# Default Thread count
# WARNING: The Bot uses double the number of threads specified here per instance
THREADCOUNT = 20

DATA_DIR = '../data'
CONFIG_DIR = '../config'
PKL_DIR = './pkls'
LIST_DIR = './lists'


IsInDockerContainer = os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False)
IsFarmBot = os.environ.get('Farm', False)
THREADCOUNT = int(os.environ.get('THREADCOUNT', THREADCOUNT))

if IsInDockerContainer:
    DATA_DIR = '/app/data'
    CONFIG_DIR = '/app/config'
    PKL_DIR = '/app/pkls'
    LIST_DIR = '/app/lists'

LOG_DIR = os.path.join(DATA_DIR, 'logs')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
LOG_FILE = os.path.join(LOG_DIR, 'bot.log')
RESULTS_FILE = os.path.join(DATA_DIR, 'results.txt')
SINGLE_LETTER_FREQ_FILE = os.path.join(PKL_DIR, 'single_letter_freq.pkl')
PAIR_LETTER_FREQ_FILE = os.path.join(PKL_DIR, 'pair_letter_freq.pkl')
OVERALL_LETTER_FREQ_FILE = os.path.join(PKL_DIR, 'overall_letter_freq.pkl')
CLEAN_WORDLIST_FILE = os.path.join(PKL_DIR, 'clean_wordlist.pkl')
CLEAN_WORDLIST_FILE_E = os.path.join(PKL_DIR, 'clean_wordlist_e.pkl')
CLEAN_WORDLIST_FILE_NE = os.path.join(PKL_DIR, 'clean_wordlist_ne.pkl')
WORD_LIST_FILE = os.path.join(LIST_DIR, 'wordlist.txt')

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
