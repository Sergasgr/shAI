import os 
import warnings

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TQDM_DISABLE"] = "1"
os.environ["HF_HUB_VERBOSITY"] = "error"

import typer 
import subprocess
from rich import print
from rich.console import Console
from typing import Annotated
from ai.ollama_client import check_llm, get_command, get_explanation, get_bash_script
from shai.core.env_detector import get_system_context
from shai.core.rag_engine import build_vector_db

t = typer.Typer() 
console = Console()

@t.command()
def ask(
    prompt: str, 
    explanation: Annotated[bool, typer.Option(..., "--explain", "-e", help="Briefly explanation of the command in natural language")] = False,
    bash: Annotated[bool, typer.Option(..., "--bash", "-b", help="Generates a bash script based on the prompt")] = False
    ):
    if not check_llm():
        typer.echo("LLM not on")
        raise typer.Exit(code=1)
    sys_context = get_system_context()
    
    if bash:
        with console.status("Generating script...", spinner='dots'):
            script = get_bash_script(prompt, sys_context) 
        print(script)
        raise typer.Exit()
        
    with console.status("", spinner='dots'):
        command = get_command(prompt, sys_context)
    
    print(f"[italic red]{command}")
    
    if explanation:
        with console.status("Generating explanation...", spinner='material'):
            expl = get_explanation(command, sys_context)    
        print(f"[italic cyan]{expl}")
        
    ex = typer.confirm("Do you want to execute it?")
    if not ex:
        raise typer.Exit(code=1)
    subprocess.run(command, shell=True)

@t.command()
def learn(file_path: str):
    with console.status("Learning content..", spinner='dots'):
        flag = build_vector_db(file_path)
        
    if not flag:
        print("Invalid or non-existing file_path")
        raise typer.Exit(code=1)    
    print("[green]The content has been learnt succesfully")
    
if __name__ == "__main__":
    t()