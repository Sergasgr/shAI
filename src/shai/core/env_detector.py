import os
import typer
import re
from pathlib import Path

def get_system_context() -> dict: 
    shell = os.environ.get('SHELL', '/bin/bash')
    lang = os.environ.get('LANG', 'en_US.UTF-8') 
    
    try:
        with open("/etc/os-release", 'r') as f:
            for line in f:
                if line.startswith("PRETTY_NAME"):
                    os_ = line.replace("PRETTY_NAME=", "").strip('"\n')
                    break       
    except FileNotFoundError:
        os_ = 'Linux/Unix'
        
    return {'os': os_, 'shell': shell, 'language': lang}          

def alias_configuration(shell_name: str) -> Path:
    if "zsh" in shell_name:
        return Path("~/.zshrc").expanduser()
    elif "bash" in shell_name:
        return Path("~/.bashrc").expanduser()
    elif "fish" in shell_name:
        return Path("~/.config/fish/config.fish").expanduser()
    print("[bold red]Error:[/bold red] Your shell is not supported for automatic alias creation.")
    raise typer.Exit(code=1) 
    
def create_alias(command: str, alias_name: str, shell_name: str): 
    shell_path = alias_configuration(shell_name)
    content = f"alias {alias_name}='{command}'\n"
    try:
        if shell_path.exists():
            with open(shell_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            lines = []
            
        pattern = rf"^alias\s+{re.escape(alias_name)}="
        exists = any(re.match(pattern, line.lstrip()) for line in lines)
        if exists:
            print("[yellow]The alias is already created.[/yellow]")
            return
        
        with open(shell_path, 'a', encoding='utf-8') as f:
            if lines and not lines[-1].endswith("\n"):
                f.write("\n")
            f.write(content)   
             
        print(f"[bold green]✓ Alias successfully created[/bold green]. Run 'source {shell_path}' or open a new terminal to use it.")
    except Exception as e:
        print(f"[bold red]Error saving alias: {e}[/bold red]")
        raise typer.Exit(code=1)