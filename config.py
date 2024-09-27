import os
import json

CONFIG_FILE = './config.json'
IsInDockerContainer = os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False)

if IsInDockerContainer:
    CONFIG_FILE = '/app/config/config.json'

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)
    
CONFIG = load_config()