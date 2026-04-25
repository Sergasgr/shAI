import os
import warnings

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TQDM_DISABLE"] = "1"
os.environ["HF_HUB_VERBOSITY"] = "error"

import typer 
import re
import os.path
import subprocess
from rich import print
from rich.console import Console
from typing import Annotated
from ai.ollama_client import check_llm, get_command, get_explanation, get_bash_script
from shai.core.env_detector import get_system_context
from shai.core.rag_engine import build_vector_db

t = typer.Typer() 
console = Console()

def save_to_file(content: str, path: str, mode: str):
    try:
        with open(path, mode) as f:
            f.write(content)
        print(f"[bold green]✓ Content successfully saved to {path}[/bold green]")
    except Exception as e:
        print(f"[bold red]Error saving file: {e}[/bold red]")
        raise typer.Exit(code=1)
    
def create_alias(command: str, alias_name: str, shell_name: str):
    shell_path = os.path.expanduser(f'~/.{shell_name}rc')
    if not os.path.exists(shell_path):
        shell_path = os.path.expanduser("~/.bashrc") 
        
    content = f"alias {alias_name}='{command}'\n"
    
    try:
        if os.path.exists(shell_path):
            with open(shell_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            lines = []
        pattern = rf"^alias\s+{re.escape(alias_name)}="
        exists = any(re.match(pattern, line.lstrip()) for line in lines)
        if exists:
            print("The alias is already created")
            return
        with open(shell_path, 'a', encoding='utf-8') as f:
            if alias_name not in f.readlines():
                if lines and not lines[-1].endswith("\n"):
                    f.write("\n")
                f.write(content)
                print(f"[bold green]✓ Alias successfully created[/bold green]. Run 'source ~/.{shell_name}rc' or open a new terminal to use it.")
            else:
                print("The alias is already created")
    except Exception as e:
        print(f"[bold red]Error saving alias: {e}[/bold red]")
        raise typer.Exit(code=1)

@t.command()
def ask(
    prompt: str, 
    explanation: Annotated[bool, typer.Option(..., "--explain", "-e", help="Briefly explanation of the command in natural language.")] = False,
    bash: Annotated[bool, typer.Option(..., "--bash", "-b", help="Generates a bash script based on the prompt.")] = False,
    save: Annotated[str | None, typer.Option("--save", "-s", help="Path to save the generated output (overwrites by default).")] = None,
    append: Annotated[bool, typer.Option("--append", "-ap", help="If --save is used, append to the file instead of overwriting.")] = False,
    alias: Annotated[str | None, typer.Option("--alias", "-a", help="Save the generated command as a permanent shell alias.")] = None,
    yes: Annotated[bool, typer.Option(..., "--yes", "-y", help="Execute the generated command or script automatically without confirmation.")] = False
    ):
    """
    IMPLEMENTAR EL --help
    """
    
    final_output = ""
    #REVISAR LAS POSIBILIDADES DE COMBINACIONES POSIBLES DE COMANDOS
    
    if not check_llm():
        typer.echo("LLM not on")
        raise typer.Exit(code=1)
    sys_context = get_system_context()
    
    if bash:
        if alias:
            print(f"[yellow]The option --alias is ignored when generating bash scripts")
        with console.status("Generating script...", spinner='dots'):
            script = get_bash_script(prompt, sys_context) 
        print(script)
        final_output += script #FALTA IMPLEMENTACION EXPLANATION CON FINE-TUNE DE COMO QUIERO QUE RESPONDA
        if save: #ANIMACION PARA SALVAR EL CONTENIDO? QUIZAS NO HACE FALTA
            save_to_file(final_output, save, 'w' if not append else 'a')  
        #IMPLEMENTAR EL EXPLANATION PARA QUE TAMBIÉN EXPLIQUE EL FUNCIONAMIENTO DEL SCRIPT (FINE-TUNEAR ESTO)
        """
        if explanation:
            with console.status("Generating explanation...", spinner='material'):
            script_expl = get_script_explanation(script, sys_context)  
        final_output += f"\n# Explanation: {script_expl}"
        print(f"[italic cyan]{script_expl}")
        """
        raise typer.Exit(code=0)
        
    with console.status("", spinner='dots'):
        command = get_command(prompt, sys_context)
    
    final_output += command
    print(f"[italic red]{command}")
    
    if explanation:
        with console.status("Generating explanation...", spinner='material'):
            expl = get_explanation(command, sys_context)  
      
        final_output += f"\n# Explanation: {expl}"
        print(f"[italic cyan]{expl}")
        
    if save:
        save_to_file(final_output, save, 'w' if not append else 'a') 
        
    if alias:
        create_alias(command, alias, sys_context['shell'])
    
    if not yes:
        ex = typer.confirm("Do you want to execute it?")
        if not ex:
            raise typer.Exit(code=1)

    subprocess.run(command, shell=True)
   
@t.command()
def learn(file_path: str):
    """
    IMPLEMENTAR EL --help
    """
    with console.status("Learning content..", spinner='dots'):
        flag = build_vector_db(file_path)
        
    if not flag:
        print("Invalid or non-existing file_path")
        raise typer.Exit(code=1)    
    print("[green]The content has been learnt succesfully")

"""
@t.command()
def setup():
"""    
    
if __name__ == "__main__":
    t()