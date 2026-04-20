import typer 
import subprocess
from rich import print
from rich.console import Console
from typing import Annotated
from ai.ollama_client import check_llm, get_command, get_explanation
from shai.core.env_detector import get_system_context

t = typer.Typer() 
console = Console()

@t.command()
def principalCommand(prompt: str, explanation: Annotated[bool, typer.Option(..., "--explain", "-e", help="Briefly explanation of the command in natural language")] = False):
    if not check_llm():
        typer.echo("LLM not on")
        raise typer.Exit(code=1)
    sys_context = get_system_context()
    
    with console.status("", spinner='dots'):
        command = get_command(prompt, sys_context)
    
    print(f"[italic red]{command}") #typer.secho(f"{command}\n", fg=typer.colors.RED)
    
    if explanation:
        with console.status("Generating explanation...", spinner='material'):
            expl = get_explanation(command, sys_context)    
        print(f"[italic cyan]{expl}")
        
    ex = typer.confirm("Do you want to execute it?")
    if not ex:
        raise typer.Exit(code=1)
    subprocess.run(command, shell=True)
    
if __name__ == "__main__":
    t()
