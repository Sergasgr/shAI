import typer 
from ai.ollama_client import check_llm, get_command

t = typer.Typer() 

@t.command()
def principalCommand(prompt: str):
    if not check_llm():
        typer.echo("LLM not on")
        raise typer.Exit(code=1)
    print(get_command(prompt))
    
if __name__ == "__main__":
    t()
