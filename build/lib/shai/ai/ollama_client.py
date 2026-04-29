import httpx
from core.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from core.rag_engine import search_knowledge

def check_llm():
    try:
        response = httpx.get(OLLAMA_BASE_URL, timeout=None)
        if response.status_code == 200:
            return True     
        return False
    except httpx.RequestError:
        return False 
    
def get_command(user_input: str, context: dict) -> str:
    rag_context = search_knowledge(user_input)
    instructions = f"You are a Linux Shell expert. Return ONLY the command to comply with the client's request without format neither explanations nor greetings. OS: {context['os']}. Shell: {context['shell']}."
    
    if context.get('language') != 'en':
        instructions += f" Consider the user's language is {context['language']}."
    if rag_context:
        instructions += f" Use EXCLUSIVELY this internal documentation if relevant: {rag_context}"
        
    req = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": user_input}
        ],
        "stream": False
    }
    
    response = httpx.post(OLLAMA_BASE_URL+"api/chat", json=req, timeout=None)
    data = response.json()
    
    data_content = data["message"]["content"].replace("```bash", "").replace("```", "").replace("`", "")
    lines = data_content.split("\n")
    
    for line in lines:
        if len(line.strip()) > 1:
            return line.strip()
            
    return data_content.strip() 
    
def get_explanation(command: str, context: dict) -> str:
    instructions = f"You are a Linux Shell expert. Return a briefly explanation of the given command. Be concise and direct. OS: {context['os']}. Language: {context['language']}."
    
    req = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": command}
        ],
        "stream": False 
    }
    
    response = httpx.post(OLLAMA_BASE_URL+"api/chat", json=req, timeout=None)
    data = response.json()
    return data["message"]["content"].replace("`","'")

def get_bash_script(user_input: str, context: dict) -> str:
    rag_context = search_knowledge(user_input)
    instructions = f"You are a Linux Shell expert. Return ONLY the raw bash code starting exactly with #!/bin/bash. No markdown formatting. OS: {context['os']}. Shell: {context['shell']}."
    
    if rag_context:
        instructions += f" Strict documentation to follow: {rag_context}"
        
    req = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": user_input}
        ],
        "stream": False
    }
    
    response = httpx.post(OLLAMA_BASE_URL+"api/chat", json=req, timeout=None)
    data = response.json()
    return data["message"]["content"].replace("```bash", "").replace("```", "").strip()