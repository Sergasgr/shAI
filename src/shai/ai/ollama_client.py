import httpx
import typer
from rich import print
from shai.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from shai.core.rag_engine import search_knowledge

def send_ollama_request(url: str, req: dict, timeout: int = 60) -> dict:
    try:
        response = httpx.post(url, json=req, timeout=timeout)
        data = response.json()
        
        if "error" in data:
            print(f"[bold red]Ollama Model Error:[/bold red] {data['error']}")
            print("[yellow]Tip: Check if the configured model is installed by running 'ollama list'.[/yellow]")
            raise typer.Exit(code=1)
            
        return data
    except httpx.ConnectError:
        print("[bold red]Network Error:[/bold red] Could not connect to Ollama. Please make sure the service is active.")
        raise typer.Exit(code=1)
    except httpx.ReadTimeout:
        print("[bold red]Timeout Error:[/bold red] The AI took too long to respond (over 60 seconds). Try checking your system resources.")
        raise typer.Exit(code=1)
    except httpx.RequestError as e:
        print(f"[bold red]HTTP Error:[/bold red] An unexpected error occurred: {e}")
        raise typer.Exit(code=1)
    
def check_llm():
    try:
        response = httpx.get(OLLAMA_BASE_URL, timeout=3.0)
        return response.status_code == 200
    except httpx.RequestError:
        return False 
    
def get_command(user_input: str, context: dict) -> tuple[str, float, float]:
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
    
    data = send_ollama_request(OLLAMA_BASE_URL+"api/chat", req)
    
    total_duration_s = data.get("total_duration", 0) / 1e9
    eval_duration_s = data.get("eval_duration", 0) / 1e9
    eval_count = data.get("eval_count", 0)
    
    tps = (eval_count / eval_duration_s) if eval_duration_s > 0 else 0.0
        
    data_content = data["message"]["content"].replace("```bash", "").replace("```", "").replace("`", "")
    lines = data_content.split("\n")
    
    final_cmd = data_content.strip()
    for line in lines:
        if len(line.strip()) > 1:
            final_cmd = line.strip()
            break
        
    return final_cmd, total_duration_s, tps
    
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
    
    data = send_ollama_request(OLLAMA_BASE_URL+"api/chat", req)
    
    return data["message"]["content"].replace("`","'")

def get_bash_script(user_input: str, context: dict) -> str:
    rag_context = search_knowledge(user_input)
    instructions = f"You are a strict Linux Shell executor. Return ONLY the raw bash code starting exactly with #!/bin/bash. NO explanations, NO markdown formatting, NO conversational text before or after. OS: {context['os']}. Shell: {context['shell']}."
    
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
    
    data = send_ollama_request(OLLAMA_BASE_URL+"api/chat", req)
    content = data["message"]["content"]
    
    if "```bash" in content:
        script = content.split("```bash")[1].split("```")[0].strip()
    elif "```" in content:
        script = content.split("```")[1].split("```")[0].strip()
    else:
        script = content.strip()
        
    if "#!/bin/bash" in script:
        script = "#!/bin/bash" + script.split("#!/bin/bash")[1]
    
    return script

def get_script_explanation(script: str, context: dict) -> str:
    instructions = f"You are a Linux Shell expert. Briefly explain what the provided bash script does step by step. OS: {context['os']}. Language: {context['language']}."
    
    req = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": script}
        ],
        "stream": False 
    }
    
    data = send_ollama_request(OLLAMA_BASE_URL+"api/chat", req)
    return data["message"]["content"].replace("`","'").replace("'''", "")