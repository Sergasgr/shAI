import httpx
from shai.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from shai.core.rag_engine import search_knowledge

def check_llm():
    try:
        response = httpx.get(OLLAMA_BASE_URL)
        if response.status_code == 200:
            return True 
        return False
    except httpx.RequestError:
        return False 
    
def get_command(user_input: str, context: dict) -> str:
    rag_context = search_knowledge(user_input)
    instructions = f"You are a Linux Shell expert. Return ONLY the command to comply with the client's request without format neither explanations nor greetings. Take into account that the user is using the operative system {context['os']}, in the shell {context['shell']} and his preferred language {context['language']}. Additionally, the user has internal documentation. If it is relevant for the request use EXCLUSIVELY this information for generate the command: {rag_context}"
    req = {
        "model": OLLAMA_MODEL,
        "prompt": user_input,
        "system": instructions,
        "stream": False
    }
    response = httpx.post(OLLAMA_BASE_URL+"api/generate", json=req)
    data = response.json()
    return data["response"].replace("```bash", "").replace("```", "").replace("`", "").strip().split("\n")[0]
    
    
def get_explanation(command: str, context: dict) -> str:
    instructions = f"You are a Linux Shell expert. Return a briefly explanation of the command {command} in the language {context['language']}. Be concise and direct."
    req = {
        "model": OLLAMA_MODEL,
        "prompt": instructions,
        "stream": False 
    }
    response = httpx.post(OLLAMA_BASE_URL+"api/generate", json=req)
    data = response.json()
    return data["response"].replace("`","'")