import json
import subprocess
from rich import print
from shai.core.config import AGENT_PROMPT, HEALING_PROMPT
from shai.ai.ollama_client import send_ollama_request, OLLAMA_MODEL, OLLAMA_BASE_URL

# Modo --agent (Opt-in): Ejerce de Ingeniero Autónomo. Es lento, consume recursos y es arriesgado, pero es capaz de resolver problemas complejos de múltiples pasos por ti. 
# HACERLO MÁS SEGURO? ESTUDIAR SU COMPORTAMIENTO

class AgentOrchestrator:
    def __init__(self, sys_context: dict, max_retries: int = 3): 
        self.sys_context = sys_context
        self.max_retries = max_retries
        
    def generate_plan(self, prompt: str) -> list[dict]: 
        req = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": AGENT_PROMPT},
                {"role": "user", "content": f"OS: {self.sys_context.get('os', 'Linux')}. Task: {prompt}"}
            ],
            "stream": False,
            "format": "json"
        }
            
        data = send_ollama_request(OLLAMA_BASE_URL+"api/chat", req)
        try:
            raw_content = data.get("message", {}).get("content", "[]")
            parsed = json.loads(raw_content.replace("```json", "").replace("```", "").strip())
        
            if isinstance(parsed, dict):
                if "plan" in parsed and isinstance(parsed["plan"], list):
                    return parsed["plan"]
                elif "steps" in parsed and isinstance(parsed["steps"], list):
                    return parsed["steps"]
                return [parsed]
                
            elif isinstance(parsed, list):
                return parsed
                
            else:
                print("[yellow]Warning: Unrecognized JSON structure from LLM.[/yellow]")
                return []
                
        except json.JSONDecodeError:
            print("[bold red]Failed to parse agent plan.[/bold red]")
            return []
        
    def fix_command(self, step_intent: str, command: str, error_msg: str) -> str:
        prompt = HEALING_PROMPT.format(
            intent=step_intent, 
            command=command, 
            error=error_msg, 
            os_context=self.sys_context.get('os', 'Linux')
        )
        req = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        response = send_ollama_request(OLLAMA_BASE_URL+"api/chat", req)
        return response.get("message", {}).get("content", "").strip().replace("```bash", "").replace("```", "")
    
    def execute_with_healing(self, step_intent: str, initial_command: str) -> bool:
        current_command = initial_command
        retries = self.max_retries
        
        while retries > 0:
            print(f"[cyan]Executing:[/cyan] {current_command}")
            try: 
                result = subprocess.run(current_command, shell=True, check=True, capture_output=True, text=True, timeout=30)
                if result.stdout:
                    print(result.stdout.strip())
                print("[bold green]✓ Step completed successfully.[/bold green]")
                return True
                
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.strip() if e.stderr else str(e)
                print(f"[yellow]Command failed. Auto-healing attempt {self.max_retries - retries + 1}/{self.max_retries}...[/yellow]")
                print(f"[red]Error caught:[/red] {error_msg}")
                
                current_command = self.fix_command(step_intent, current_command, error_msg)
                retries -= 1
            
            except subprocess.TimeoutExpired as e:
                print(f"[yellow]Command failed. Auto-healing attempt {self.max_retries - retries + 1}/{self.max_retries}...[/yellow]")
                print("[red]Command timed out. Did it require interactive input? Use non-interactive flags[/red]")
                
                current_command = self.fix_command(step_intent, current_command, "Command timed out. Remove interactive prompts or use non-interactive flags.")
                retries -= 1 
                
        print("[bold red]✗ Step failed after maximum retries. Halting plan.[/bold red]")
        return False
    
    def run(self, prompt: str):
        print(f"[bold magenta]Agent analyzing complex task:[/bold magenta] {prompt}")
        plan = self.generate_plan(prompt)
        
        if not plan:
            print("[yellow]Could not generate a valid plan for this task.[/yellow]")
            return
            
        print(f"[bold blue]Plan generated with {len(plan)} steps.[/bold blue]")
        
        for i, step in enumerate(plan, 1):
            if isinstance(step, dict):
                step_intent = str(step.get('step', f"Task {i}"))
                initial_command = str(step.get('command', ""))
            else:
                step_intent = f"Execute step {i}"
                initial_command = str(step)
                
            print(f"\n[bold]Step {i}:[/bold] {step_intent}")
            
            if not initial_command or initial_command == "None":
                print("[yellow]⚠️ Warning: No valid command generated for this step. Skipping.[/yellow]")
                continue
   
            success = self.execute_with_healing(step_intent, initial_command) 
            if not success:
                print("[bold red]Aborting remaining steps due to critical failure.[/bold red]")
                break