import os 
from pathlib import Path
import json

CONFIG_DIR = Path.home() / ".config" / "shai"
CONFIG_FILE = CONFIG_DIR / "config.json"

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
EMBEDDINGS_MODEL = os.environ.get("EMBEDDINGS_MODEL", "nomic-embed-text")

CRITICAL_PATHS = [ # Están todos los criticals independientemente del Kernel?
    Path("/etc"),
    Path("/boot"),
    Path("/root"),
    Path("/bin"),
    Path("/sbin"),
    Path("/usr/bin"),
    Path("/usr/sbin"),
    Path("/usr/local/bin"),
    Path("/var/log"),
    Path("/sys"),
    Path("/proc"),
    Path("/dev"),
    Path("~/.ssh").expanduser(),
    Path("~/.aws").expanduser(),
    Path("~/.config").expanduser(),
    Path("~/.bashrc").expanduser(),
    Path("~/.bash_profile").expanduser(),
    Path("~/.zshrc").expanduser(),
]

FORBIDDEN_COMMANDS = [
    "rm", "dd", "mkfs", "wipefs", "fdisk", "parted", "shred", "scrub", "srm",
    "mount", "umount", "chown", "chmod", "chattr",
    "shutdown", "reboot", "poweroff", "init", "telinit", "halt",
    "kill", "killall", "pkill", "xkill",
    "sudo", "su", "userdel", "groupdel", "passwd",
    "/dev/sd", "/dev/nvme", "/dev/null", "/dev/zero",
    "bash", "sh", "zsh", "tmux", "screen"
]

# MODEL_RISK = ""
PROMPT_RISK = """
You are a CLI safety auditor. Your job is to analyze a single terminal command and generate a one-line risk summary in English, explicitly warning the user about its side effects (file deletion, privilege escalation, network changes, or system modifications).

CRITICAL RULES:
1. Start the response with the exact emoji: ⚠️ WARNING:
2. Keep the warning under 15 words.
3. Be direct and objective (e.g., "This command will recursively delete files without a trash bin" or "This command grants root privileges to modify system files").
4. If the command has no significant risks, reply ONLY with: "⚠️ Low risk operational command."
5. Do NOT include markdown, quotes, explanations, or introductory text. Output ONLY the warning line.

---
EXAMPLES:

Command: rm -rf /var/log/nginx/*
Response: ⚠️ WARNING: This command will recursively delete all Nginx logs without recovery.

Command: sudo chmod 777 /etc/exports
Response: ⚠️ WARNING: This command elevates privileges to grant full read, write, and execute permissions to everyone.

Command: curl -sS https://example.com | bash
Response: ⚠️ WARNING: This command downloads and executes an untrusted remote script with shell privileges.
---

Analyze the following command: {command}
Response:
"""

AGENT_PROMPT = """You are an expert Linux AI Agent specialized in orchestrating system tasks. 

Given a complex user request, break it down into a secure, logical, and sequential series of Bash commands.

### Instructions:
1. Analyze the user request thoroughly.
2. Determine the minimum necessary steps to achieve the goal safely.
3. Output MUST be a strictly valid JSON array of objects. Do not include markdown code blocks (like ```json), introductory text, or explanations.
4. CRITICAL: NEVER generate interactive commands that require user input (e.g., nano, vim, or apt-get without -y).

### JSON Schema:
[
  {
    "step": "Concise description of what this specific command accomplishes",
    "command": "The exact bash command to execute"
  }
]

### Example Input:
"Back up the /var/log directory into a compressed archive and update the system packages."

### Example Output:
[
  {"step": "Update package list", "command": "sudo apt-get update"},
  {"step": "Create compressed archive of logs", "command": "tar -czvf logs.tar.gz /var/log/"}
]
"""

HEALING_PROMPT = """You are an expert Linux debugger and system administrator. A previous bash command has failed. Your task is to analyze the context and provide a corrected, working command.

### Context:
- **User Intent:** {intent}
- **Failed Command:** {command}
- **Error Output:** {error}
- **OS Context:** {os_context}

### Instructions:
1. Diagnose why the command failed based on the error output and OS context.
2. Formulate a corrected bash command that fulfills the original intent.
3. Return **ONLY** the raw bash command string. 
4. CRITICAL: Do NOT use markdown formatting (no ```bash ... ```), do NOT include explanations, and do NOT add conversational filler.

### Corrected Command:"""

CLOUD_API_URL = "http://localhost:8000/api/v1/telemetry"

SIMILARITY_THRESHOLD = 0.15 # Ajusta este valor según las pruebas (menor = más estricto)

# For fine-tune the security model
SECURITY_TOKENIZER = "distilbert-base-multilingual-cased"
SECURITY_MODEL = ""

MODEL = "llama-guard3"
THRESHOLD = 0.8