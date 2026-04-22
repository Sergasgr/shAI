import os 
# By default is used Ollama and Qwen 2.5
OLLAMA_BASE_URL = os.environ.get("SHAI_OLLAMA_URL", "http://localhost:11434/")
OLLAMA_MODEL = os.environ.get("SHAI_OLLAMA_MODEL", "qwen2.5-coder:1.5b")
