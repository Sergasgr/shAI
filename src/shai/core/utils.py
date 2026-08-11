from rich import print
import typer
from pathlib import Path
from shai.core.config import CRITICAL_PATHS

def save_to_file(content: str, path: str, mode: str):
    target_path = Path(path).expanduser().resolve()
    
    is_critical = any(
        target_path == crit_path or target_path.is_relative_to(crit_path) 
        for crit_path in CRITICAL_PATHS
    )
    
    if is_critical:
        confirmation = typer.confirm(f"⚠️ WARNING: You are attempting to save in a critical system path: {target_path}. Are you absolutely sure?")
        if not confirmation:
            print("[yellow]Action aborted by the user.[/yellow]")
            raise typer.Exit(code=1)
            
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, mode) as f:
            f.write(content)
        print(f"[bold green]✓ Content successfully saved to {target_path}[/bold green]")
    except Exception as e:
        print(f"[bold red]Error saving file: {e}[/bold red]")
        raise typer.Exit(code=1)