import os 
import json

CONFIG_DIR = os.path.expanduser("~/.shai")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

SHAI_OLLAMA_MODEL = "qwen2.5-coder"

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            SHAI_OLLAMA_MODEL = config_data.get('model', "qwen2.5-coder")
    except Exception:
        pass
    
OLLAMA_BASE_URL = os.environ.get("SHAI_OLLAMA_URL", "http://localhost:11434/")
OLLAMA_MODEL = os.environ.get("SHAI_OLLAMA_MODEL", SHAI_OLLAMA_MODEL)