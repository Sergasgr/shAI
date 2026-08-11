from shai.ai.ollama_client import send_ollama_request
from shai.core.config import OLLAMA_BASE_URL
from shai.core.config import FORBIDDEN_COMMANDS, PROMPT_RISK #, MODEL_RISK
from shai.ai.ollama_client import OLLAMA_MODEL

def get_risk_summary(command: str, model: str = OLLAMA_MODEL) -> str:
    formatted_prompt = PROMPT_RISK.replace("{command}", command)
    req = {
        "model": model,
        "messages": [
            {"role": "user", "content": formatted_prompt}
        ],
        "options": {
            "temperature": 0.0
        },
        "stream": False,
    }
    risk_response = send_ollama_request(OLLAMA_BASE_URL+"api/chat", req)
    
    try:
        raw_warning = risk_response["message"]["content"].strip()
        return raw_warning if raw_warning else "⚠️ Warning: Potential risk detected."
    except Exception:
        return "⚠️ Warning: Unable to analyze command safety. Proceed with caution."