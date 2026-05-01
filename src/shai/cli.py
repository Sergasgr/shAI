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
import shutil
import json
import sys
from rich import print
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown
from typing import Annotated
from shai.ai.ollama_client import check_llm, get_command, get_explanation, get_bash_script, get_script_explanation
from shai.core.env_detector import get_system_context
from shai.core.rag_engine import build_vector_db
from shai.core.telemetry import init_db, log_execution, db_path

t = typer.Typer(
    rich_markup_mode="rich",
    help="[bold cyan]shAI[/bold cyan] - Your AI-powered local terminal assistant."
)

@t.callback()
def help_callback():
    """
    [bold green]shAI[/bold green] translates natural language into Linux commands, generates bash scripts, 
    and remembers your corporate documentation using local LLMs.
    
    [bold yellow]Core Features:[/bold yellow]
    - Generate executable commands instantly.
    - Explain complex bash syntax.
    - Ingest local files for context-aware generation (RAG).
    """
    pass 

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
    clean_shell = shell_name.split('/')[-1]
    shell_path = os.path.expanduser(f'~/.{clean_shell}rc')
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
            if lines and not lines[-1].endswith("\n"):
                f.write("\n")
            f.write(content)
            print(f"[bold green]✓ Alias successfully created[/bold green]. Run 'source ~/.{clean_shell}rc' or open a new terminal to use it.")
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
    [bold cyan]Generate[/bold cyan] Linux commands or bash scripts from natural language.
    
    This is the core engine of shAI. It uses a local LLM to understand your request
    and generate the exact command you need. You can ask for explanations, save the 
    output, or create permanent aliases.
    """
    
    final_output = ""
    expl_text = "NULL"
    
    if not check_llm():
        print("[bold red]Ollama is not running or could not be connected. Please make sure the service is active.[/bold red]")
        raise typer.Exit(code=1)
    sys_context = get_system_context()
    
    if bash:
        if alias:
            print(f"[yellow]The option --alias is ignored when generating bash scripts")
        with console.status("Generating script...", spinner='dots'):
            script = get_bash_script(prompt, sys_context) 
            
        if script.startswith("ERROR_OLLAMA_API:"):
            print(f"[bold red]Ollama API Error:[/bold red] {script.split(':', 1)[1].strip()}")
            print("[yellow]Tip: Check if the configured model is installed by running 'ollama list'.[/yellow]")
            raise typer.Exit(code=1)
            
        syntax_block = Syntax(script, "bash", theme="ansi_dark", background_color="default", word_wrap=True)
        console.print(syntax_block)
        final_output += script 
        if save: 
            save_to_file(final_output, save, 'w' if not append else 'a')  
        
        if explanation:
            with console.status("Generating explanation...", spinner='material'):
                script_expl = get_script_explanation(script, sys_context)
            final_output += f"\n# Explanation: {script_expl}"
            print(Panel.fit(Markdown(script_expl), border_style="cyan", title="Explanation"))
                        
        raise typer.Exit(code=0)
  
    with console.status("", spinner='dots'):
        command = get_command(prompt, sys_context)
    
    if command.startswith("ERROR_OLLAMA_API:"):
        print(f"[bold red]Ollama API Error:[/bold red] {command.split(':', 1)[1].strip()}")
        print("[yellow]Tip: Check if the configured model is installed by running 'ollama list'.[/yellow]")
        raise typer.Exit(code=1)
    
    final_output += command
    print(Panel.fit(f"[green]{command}", border_style="green"))
    
    if explanation:
        with console.status("Generating explanation...", spinner='material'):
            expl_text = get_explanation(command, sys_context)  #Aqui no haria falta el error porque ya hubiera raiseado antes no?
      
        final_output += f"\n# Explanation: {expl_text}"
        print(Panel.fit(Markdown(expl_text), border_style="cyan", title="Explanation"))
        
    if save:
        save_to_file(final_output, save, 'w' if not append else 'a') 
        
    if alias:
        create_alias(command, alias, sys_context['shell'])
    
    if not yes:
        ex = typer.confirm("Do you want to execute it?")
        if not ex:
            raise typer.Exit(code=1)

    result = subprocess.run(command, shell=True)
    log_execution(prompt, command, expl_text, sys_context['os'], result.returncode)
   
@t.command()
def learn(file_path: str):
    """
    [bold cyan]Ingest[/bold cyan] local documentation into the vector database (RAG).
    
    Reads a text file, splits it into chunks, and saves it mathematically in ChromaDB.
    shAI will automatically prioritize this knowledge for future commands.
    """
    with console.status("Learning content..", spinner='dots'):
        flag = build_vector_db(file_path)
        
    if not flag:
        print("Invalid or non-existing file_path")
        raise typer.Exit(code=1)    
    print("[green]The content has been learnt succesfully")

@t.command()
def setup(model: str = typer.Option("-m", help="Specify the model to use")):
    """
    [bold cyan]Initialize[/bold cyan] the shAI environment.
    
    Verifies Ollama installation, selects the AI engine, creates the local configuration, 
    and downloads the necessary embedding models for the RAG engine.
    """
    init_db()
    
    if not shutil.which("ollama"):
        print("[bold red]Ollama is not installed![/bold red]")
        print("Please install it from https://ollama.com before running setup.")
        raise typer.Exit(code=1)
    
    output = subprocess.check_output(["ollama", "list"], text=True).strip().split('\n')
    available_models = [line.split()[0] for line in output[1:] if line]

    valid_models = [m for m in available_models if "embed" not in m]

    if not valid_models:
        print("[bold red]No text-generation models found in Ollama.[/bold red]")
        print("Please pull a model first: 'ollama pull qwen2.5-coder'")
        raise typer.Exit(code=1)
    
    if model:
        matching_models = [m for m in available_models if model in m]
        if not matching_models:
            print(f"[bold red]Model '{model}' is not installed in your Ollama![/bold red]")
            raise typer.Exit(code=1)
        selected_model = matching_models[0]
    else:
        matching_defaults = [m for m in valid_models if "qwen2.5-coder" in m]
        selected_model = matching_defaults[0] if matching_defaults else valid_models[0]
        
    CONFIG_DIR = os.path.expanduser("~/.shai")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(os.path.join(CONFIG_DIR, 'config.json'), 'w', encoding='utf-8') as f:
        json.dump({'model': selected_model}, f, indent=4)
    
    print(f"[bold cyan]Selected Engine:[/bold cyan] {selected_model}")    
        
    with console.status("Downloading embedding models for RAG (this may take a few minutes)...", spinner='bouncingBar'):
        subprocess.run("ollama pull nomic-embed-text", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    print("[bold green]✓ Environment successfully initialized.[/bold green]")
    disclaimer = """[bold red]Disclaimer:[/bold red] shAI generates system commands using Artificial Intelligence. 
The user is strictly responsible for reviewing all commands before execution. 
The creator assumes no liability for any system damage or data loss."""
    
    print(Panel.fit(disclaimer, border_style="yellow", title="⚠️ WARNING"))
    
@t.command()
def train():
    """
    [bold cyan]Export[/bold cyan] telemetry data to a ChatML dataset for Fine-Tuning.
    
    Analyzes your local execution history (successful commands and explanations) 
    and exports them to ~/shai/data/dataset.jsonl ready for HuggingFace.
    """
    export_script = os.path.expanduser("~/shai/scripts/export_dataset.py")
    
    if not os.path.exists(export_script):
        print("[bold red]Export script not found![/bold red]")
        print(f"Expected to find it at: {export_script}")
        raise typer.Exit(code=1)

    with console.status("Compiling ChatML dataset from telemetry and ground truth...", spinner='dots'):
        result = subprocess.run([sys.executable, export_script], capture_output=True, text=True)
        
    if result.returncode != 0:
        print("[bold red]Error generating dataset:[/bold red]")
        print(result.stderr)
        raise typer.Exit(code=1)
        
    json_path = os.path.expanduser("~/shai/data/dataset.jsonl")
    
    print(f"[bold green]✓ Dataset successfully exported to {json_path}[/bold green]")
    print("\n[bold cyan]Next Steps for Fine-Tuning (shai-expert):[/bold cyan]")
    print("1. Run the HuggingFace training:   [yellow]python ~/shai/scripts/train.py[/yellow]")
    print("2. Merge the LoRA adapter:         [yellow]python ~/shai/scripts/merge.py[/yellow]")
    print("3. Clone llama.cpp repository:     [yellow]git clone https://github.com/ggerganov/llama.cpp[/yellow]")
    print("4. Convert to Ollama format:       [yellow]python llama.cpp/convert_hf_to_gguf.py models/shai-merged --outfile shai-expert.gguf[/yellow]")
    print("5. Create the Ollama model:        [yellow]ollama create shai-expert -f Modelfile[/yellow] (Ensure Modelfile points to the .gguf)")
    print("6. Update your CLI to use it:      [yellow]shai setup -m shai-expert[/yellow]")
    
if __name__ == "__main__":
    init_db()
    t()