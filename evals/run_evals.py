import time
import json
from rich import print
from shai.ai.ollama_client import get_command, send_ollama_request
from shai.core.config import OLLAMA_BASE_URL
from evals.evals_config import PROMPT_JUDGE, LLM_JUDGE
from evals.prompts import EVAL_PROMPTS

def evaluate_semantic_success(prompt: str, generated_command: str) -> int:
    user_content = f"<intent>:\n```\n{prompt}\n```\n<generated_command>:\n```\n{generated_command}\n```\nResponse:"
    req = {
        "model": LLM_JUDGE,
        "messages": [
            {"role": "system", "content": PROMPT_JUDGE},
            {"role": "user", "content": user_content}
        ],
        "options": {"temperature": 0.0},
        "stream": False,
        "format": "json" 
    }
    
    try:
        llm_analysis = send_ollama_request(OLLAMA_BASE_URL + "api/chat", req)
        result = json.loads(llm_analysis["message"]["content"])
        return int(result.get("evaluation", 0))
    except Exception as e:
        print(f"[yellow][ERROR][/yellow] LLM Judge output format error: {e}")
        return 0

if __name__ == "__main__":
    mock_context = {
        "os": "Ubuntu",
        "shell": "bash",
        "language": "en_US.UTF-8" 
    }
    
    total_latency = 0
    hits = 0
    n_examples = len(EVAL_PROMPTS)

    print(f"Starting LLM-as-a-Judge evaluation for {n_examples} commands...")
    
    for prompt in EVAL_PROMPTS:
        start = time.time()
        y_hat, _, _ = get_command(prompt, mock_context)
        total_latency += (time.time() - start)
        success = evaluate_semantic_success(prompt, y_hat)
        if success == 1:
            hits += 1
        else:
            print(f"[bold red][FAILED][/bold red] Intent: {prompt}")
            print(f"  > Predicted: {y_hat}\n")
    
    if n_examples > 0:
        print(f"Precision (Success Rate): {(hits / n_examples) * 100:.2f}%. Average latency: {(total_latency / n_examples) * 1000:.2f}ms")