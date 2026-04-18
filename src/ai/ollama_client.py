import httpx #hacerlo asíncrono

def check_llm(url: str = 'http://localhost:11434/'):
    try:
        response = httpx.get(url)
        if response.status_code == 200:
            return True 
        return False
    except httpx.RequestError:
        return False 
    
def get_command(user_input: str) -> str:
    instructions = " .You are a Linux Shell expert. Return ONLY the command to comply with the client's request without format neither explanations nor greetings"
    prompt = user_input + instructions
    req = {
        "model": "qwen2.5-coder:1.5b",
        "prompt": prompt,
        "stream": False
    }
    response = httpx.post("http://localhost:11434/api/generate", json=req)
    data = response.json()
    return data["response"].replace("```bash", "").replace("```", "").strip()
    
    
    