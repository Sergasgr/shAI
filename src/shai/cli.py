import json
import os
import shutil
import subprocess
import warnings
from pathlib import Path
from typing import Annotated

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TQDM_DISABLE"] = "1"
os.environ["HF_HUB_VERBOSITY"] = "error"

import typer
from rich import print
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from shai.ai.engine import check_forbidden, run_static_analysis, build_sandbox_command
from shai.ai.ollama_analyzer import get_risk_summary
from shai.ai.ollama_client import check_llm, get_bash_script, get_command, get_explanation, get_script_explanation
from shai.ai.security_detector import is_prompt_injection
from shai.core.dashboard import ShaiDashboard
from shai.core.download_llama_cpp import fetch_llama_cpp
from shai.core.env_detector import create_alias, get_system_context
from shai.core.mlops import export_telemetry_to_chatml
from shai.core.orchestrator import AgentOrchestrator
from shai.core.rag_engine import build_vector_db, rm_chromadb
from shai.core.semantic_cache import check_cache, save_to_cache
from shai.core.telemetry import init_db, log_cloud_telemetry, log_execution, rm_db
from shai.core.utils import save_to_file

console = Console()

t = typer.Typer(
    rich_markup_mode="rich",
    help="[bold cyan]shAI[/bold cyan] - Your AI-powered local terminal assistant."
)

@t.callback()
def help_callback():
    """
    [bold green]shAI v2.0[/bold green] translates natural language into Linux commands, generates bash scripts, 
    and acts as an autonomous local AI agent protecting your system.
    
    [bold yellow]Core Features:[/bold yellow]
    - [bold cyan]Agentic Auto-Healing:[/bold cyan] Breaks down complex tasks and automatically recovers from execution errors.
    - [bold cyan]Zero-Trust DevSecOps:[/bold cyan] Validates syntax with Shellcheck and safely executes commands inside Docker sandboxes.
    - [bold cyan]Hybrid RAG & Semantic Cache:[/bold cyan] Learns your docs with zero-latency responses and exact-keyword matching.
    - [bold cyan]End-to-End MLOps:[/bold cyan] Continuously learns from your telemetry to dynamically fine-tune your local AI models.
    - [bold cyan]Cloud Observability & TUI:[/bold cyan] Launch the interactive terminal dashboard to manage your data lifecycle.
    """
    pass

@t.command()
def ask(
    prompt: str, 
    explanation: Annotated[bool, typer.Option(..., "--explain", "-e", help="Briefly explanation of the command in natural language.")] = False,
    bash: Annotated[bool, typer.Option(..., "--bash", "-b", help="Generates a bash script based on the prompt.")] = False,
    save: Annotated[str | None, typer.Option("--save", "-s", help="Path to save the generated output (overwrites by default).")] = None,
    append: Annotated[bool, typer.Option("--append", "-ap", help="If --save is used, append to the file instead of overwriting.")] = False,
    alias: Annotated[str | None, typer.Option("--alias", "-a", help="Save the generated command as a permanent shell alias.")] = None,
    yes: Annotated[bool, typer.Option(..., "--yes", "-y", help="Execute the generated command or script automatically without confirmation.")] = False,
    agent: Annotated[bool, typer.Option(..., "--agent", "-ag", help="Enable autonomous agent mode to break down complex tasks and auto-heal execution errors.")] = False,
    sandbox: Annotated[bool, typer.Option("--sandbox", "-sb", help="Execute the generated command safely inside an isolated Docker container.")] = False # le llamo sandbox o safe??
    ):
    """
    [bold cyan]Generate[/bold cyan] Linux commands or bash scripts from natural language.
    
    This is the core engine of shAI. It uses a local LLM to understand your request
    and generate the exact command you need. You can ask for explanations, save the 
    output, or create permanent aliases.
    """ 
    
    if agent and any([bash, save, alias, sandbox]):
        print("[bold red]Error:[/bold red] The [cyan]--agent[/cyan] mode is an autonomous orchestrator and is mutually exclusive.")
        print("Please do not combine [cyan]--agent[/cyan] with [yellow]--bash, --save, --alias, or --sandbox[/yellow].")
        raise typer.Exit(code=1)
    
    final_output = ""
    expl_text = "NULL"
    latency = 0.0
    tps = 0.0
    
    if not check_llm():
        print("[bold red]Ollama is not running or could not be connected. Please make sure the service is active.[/bold red]")
        raise typer.Exit(code=1)
    
    sys_context = get_system_context()
    
    if agent:
        orchestrator = AgentOrchestrator(sys_context)
        orchestrator.run(prompt)
        raise typer.Exit(code=0)
    
    if bash: 
        if alias:
            print(f"[yellow]The option --alias is ignored when generating bash scripts")
        with console.status("Generating script...", spinner='dots'):
            script = get_bash_script(prompt, sys_context) 
            
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
        cached_command = check_cache(prompt)
        if cached_command:
            command = cached_command
        else:
            command, latency, tps = get_command(prompt, sys_context)
            save_to_cache(prompt, command)
    
    final_output += command
    print(Panel.fit(f"[green]{command}", border_style="green"))
    
    if not run_static_analysis(command):
        if not typer.confirm("\n⚠️ Linter found potential syntax issues. Do you want to proceed anyway?"):
            print("[yellow]Action aborted by the user.[/yellow]")
            raise typer.Exit(code=1)
    
    if explanation:
        with console.status("Generating explanation...", spinner='material'):
            expl_text = get_explanation(command, sys_context) 
    
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
    
    if check_forbidden(command):
        with console.status("Auditing command safety...", spinner='material'):
            risk_msg = get_risk_summary(command)
        print(Panel.fit(f"[bold red]{risk_msg}[/bold red]", border_style="red", title="Safety Auditor"))
        confirmation = typer.confirm("Do you want to execute it despite the risks?")
        if not confirmation:
            print("[yellow]Action aborted by the user.[/yellow]")
            raise typer.Exit(code=1)
        
    if sandbox:
        if not shutil.which("docker"):
            print("[bold red]Error: Docker is not installed or not running. Sandbox mode requires Docker.[/bold red]")
            raise typer.Exit(code=1)
        print(Panel.fit("🛡️ Executing command inside an isolated Ubuntu Sandbox...", border_style="blue"))
        result = subprocess.run(build_sandbox_command(command))
    else:
        result = subprocess.run(command, shell=True)
                
    log_execution(prompt, command, expl_text, sys_context['os'], result.returncode)
    log_cloud_telemetry(prompt, command, sys_context['os'], result.returncode, latency, tps)
   
@t.command()
def learn(file_path: str):
    """
    [bold cyan]Ingest[/bold cyan] local documentation into the vector database (RAG).
    
    Reads a text file, splits it into chunks, and saves it mathematically in ChromaDB.
    shAI will automatically prioritize this knowledge for future commands.
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        print(f"[bold red]Error:[/bold red] File '{file_path}' does not exist.")
        raise typer.Exit(code=1)
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"[bold red]Error reading file:[/bold red] {e}")
        raise typer.Exit(code=1)

    is_malicious = False
    with console.status("Scanning document with ML security classifier...", spinner='dots'):
        is_malicious = is_prompt_injection(content)
        
    if is_malicious:
        security_confirmation = typer.confirm(f"\n⚠️ WARNING: Potential prompt injection detected in '{file_path}'. Are you absolutely sure you want to ingest this into the RAG memory?")
        if not security_confirmation:
            print("[yellow]Action aborted by the user.[/yellow]")
            raise typer.Exit(code=1)
    
    with console.status("Learning content...", spinner='dots'):
        flag = build_vector_db(file_path)
        
    if not flag:
        print("[bold red]Invalid or non-existing file_path.[/bold red]")
        raise typer.Exit(code=1)    
        
    print("[bold green]✓ The content has been learnt successfully.[/bold green]")

@t.command()
def setup(model: Annotated[str | None, typer.Option("--model", "-m", help="Specify the model to use")] = None):
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
        expert_models = [m for m in valid_models if "shai-expert" in m]
        qwen_models = [m for m in valid_models if "qwen2.5-coder" in m]
        if expert_models:
            selected_model = expert_models[0]
        elif qwen_models:
            selected_model = qwen_models[0]
        else:
            selected_model = valid_models[0]
    
    CONFIG_DIR = Path.home() / ".config" / "shai"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    config_file = CONFIG_DIR / "config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump({'model': selected_model}, f, indent=4)
    
    print(f"[bold cyan]Selected Engine:[/bold cyan] {selected_model}")    
        
    with console.status("Downloading embedding models for RAG (this may take a few minutes)...", spinner='bouncingBar'):
        subprocess.run("ollama pull nomic-embed-text", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    print("[bold green]✓ Environment successfully initialized.[/bold green]")
    disclaimer = """[bold red]Disclaimer:[/bold red] shAI generates system commands using Artificial Intelligence. The user is strictly responsible for reviewing all commands before execution. The creator assumes no liability for any system damage or data loss."""
    
    print(Panel.fit(disclaimer, border_style="yellow", title="⚠️ WARNING"))
    
@t.command()
def train():
    """
    [bold cyan]Export[/bold cyan] telemetry data to a ChatML dataset for Fine-Tuning.
    
    Analyzes your local execution history (successful commands and explanations) 
    and exports them to ~/.local/share/shai/dataset.jsonl ready for HuggingFace.
    """
    with console.status("Compiling ChatML dataset from telemetry...", spinner='dots'):
        try:
            count, json_path = export_telemetry_to_chatml()
        except Exception as e:
            print(f"[bold red]Error generating dataset:[/bold red] {e}")
            raise typer.Exit(code=1)
            
    if count == 0:
        print("[yellow]No successful executions found in telemetry to export.[/yellow]")
        raise typer.Exit(code=0)
        
    print(f"[bold green]✓ {count} records successfully exported to {json_path}[/bold green]")
    print("\n[bold cyan]Next Steps for Fine-Tuning (shai-expert):[/bold cyan]")
    print("1. Use HuggingFace TRL to train your LoRA adapter using the exported dataset.")
    print("2. Merge the LoRA weights back into the base model to produce native .safetensors.")
    
    with console.status("Fetching precompiled llama.cpp binaries...", spinner='dots'):
        try:
            success, msg = fetch_llama_cpp()
            if success:
                print(f"3. Use the binaries downloaded at [green]{msg}[/green] to convert the model to GGUF.")
            else:
                print(f"3. Convert the merged model to GGUF format using llama.cpp (Auto-download failed).")
        except Exception:
            print("3. Convert the merged model to GGUF format using llama.cpp.")
            
    print("4. Import it to Ollama: [yellow]ollama create shai-expert -f Modelfile[/yellow]")
    
@t.command()
def clean():
    """
    [bold cyan]Clean[/bold cyan] local data to free up disk space.
    """
    telemetry_confirmation = typer.confirm("Do you want to clear telemetry?")
    if telemetry_confirmation:
        rm_db()
        print("[bold green]✓ Telemetry database cleared successfully.[/bold green]")
    
    chroma_confirmation = typer.confirm("Do you want to clear RAG memory?")
    if chroma_confirmation:
        rm_chromadb() 
        print("[bold green]✓ RAG memory (ChromaDB) cleared successfully.[/bold green]")
        
@t.command()
def privacy(): 
    """
    [bold cyan]View[/bold cyan] the shAI data privacy and retention manifesto.
    """
    manifesto = """
    # 🛡️ shAI Privacy Manifesto

    At shAI, your data privacy is the absolute priority. This tool operates within your machine's boundaries and respects your local environment.

    ### 1. Local Storage Only 🏠
    All your telemetry data is stored **strictly locally** in a SQLite database located at `~/.local/share/shai/feedback.db`. **No data ever leaves your computer** or is sent to external servers.

    ### 2. Data Collected 📊
    We only record the essential telemetry needed to improve your local AI model (Continuous Learning/Fine-Tuning):
    * Your natural language **prompts**.
    * The **commands** generated by the AI.
    * The AI's **explanations**.
    * The execution success status (**exit_code**).

    ### 3. Strict Retention Policy ⏳
    To prevent infinite disk growth and ensure data relevance, shAI applies a strict retention policy. **Only the last 500 interactions** are kept in the database. Older records are automatically purged silently in the background.

    ### 4. The Right to be Forgotten 🗑️
    You have absolute control over your data. You can completely wipe your telemetry history and the RAG (Vector Database) memory at any time by simply running:

    `shai clean`
    """
    print(Panel.fit(Markdown(manifesto), border_style="cyan", title="Data Ethics & Privacy"))
    
@t.command()
def dashboard():
    """
    [bold cyan]Launch[/bold cyan] the shAI Terminal User Interface (TUI).
    
    Explore your execution history, monitor telemetry metrics, and manage your RAG vector database visually without leaving the terminal.
    """  
    ShaiDashboard().run()
    
@t.command(name="ci-review")
def ci_review(file_path: str):
    """
    [bold cyan]Review[/bold cyan] a bash script for security and syntax issues (CI/CD integration).
    
    Reads a local .sh file and runs DevSecOps static analysis over it. 
    Returns exit code 0 if safe, or 1 if vulnerabilities are found.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"[bold red]Error:[/bold red] File '{file_path}' not found.")
        raise typer.Exit(code=1)
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    print(f"[cyan]Analyzing {file_path} with shAI DevSecOps...[/cyan]")
    is_safe = run_static_analysis(content)
    
    if not is_safe:
        print("\n[bold red]✗ Security or syntax issues found! Halting pipeline.[/bold red]")
        raise typer.Exit(code=1)
        
    print("\n[bold green]✓ Script passed static analysis![/bold green]")
    raise typer.Exit(code=0)
    
if __name__ == "__main__":
    init_db()
    t()