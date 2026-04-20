import httpx

def check_llm(url: str = 'http://localhost:11434/'):
    try:
        response = httpx.get(url)
        if response.status_code == 200:
            return True 
        return False
    except httpx.RequestError:
        return False 
    
def get_command(user_input: str, context: dict) -> str:
    instructions = f"You are a Linux Shell expert. Return ONLY the command to comply with the client's request without format neither explanations nor greetings. Take into account that the user is using the operative system {context['os']}, in the shell {context['shell']} and his preferred language {context['language']}"
    req = {
        "model": "qwen2.5-coder:1.5b",
        "prompt": user_input,
        "system": instructions,
        "stream": False
    }
    response = httpx.post("http://localhost:11434/api/generate", json=req)
    data = response.json()
    return data["response"].replace("```bash", "").replace("```", "").replace("`", "").strip().split("\n")[0]
    
    
def get_explanation(command: str, context: dict) -> str:
    instructions = f"You are a Linux Shell expert. Return a briefly explanation of the command {command} in the language {context['language']}. Be concise and direct."
    req = {
        "model": "qwen2.5-coder:1.5b",
        "prompt": instructions,
        "stream": False 
    }
    response = httpx.post("http://localhost:11434/api/generate", json=req)
    data = response.json()
    return data["response"].replace("`","'")