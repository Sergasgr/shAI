import shutil
import subprocess
from pathlib import Path
from rich import print
from rich.panel import Panel
from shai.core.config import FORBIDDEN_COMMANDS, CRITICAL_PATHS

def run_static_analysis(command: str) -> bool:
    if not shutil.which("shellcheck"):
        print("[yellow]⚠️ Shellcheck not installed. Skipping static analysis...[/yellow]")
        return True

    linter_analysis = subprocess.run(
        ["shellcheck", "-s", "bash", "-"], 
        input=command, 
        text=True, 
        capture_output=True
    )
    
    if linter_analysis.returncode != 0:
        print(Panel.fit(
            f"{linter_analysis.stdout}", 
            border_style="red", 
            title="Static Analysis Warnings (Shellcheck)"
        ))
        return False
        
    return True

def check_forbidden(bash_content: str):
    commands = bash_content.split()
    return any(
        any(cmd.startswith(forbidden) for forbidden in FORBIDDEN_COMMANDS)
        for cmd in commands
    )

def is_critical(path_str: str) -> bool: 
    target_path = Path(path_str).expanduser().resolve()
    return any(
        target_path == crit_path or target_path.is_relative_to(crit_path)
        for crit_path in CRITICAL_PATHS
    )
    
def build_sandbox_command(command: str) -> list[str]:
    return [
        "docker", 
        "run", 
        "--rm", 
        "-i", 
        "-v", f"{Path.cwd()}:/workspace", 
        "-w", "/workspace", 
        "ubuntu", 
        "bash", 
        "-c", 
        command
    ]