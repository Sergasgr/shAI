import json
import time
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from shai.ai.ollama_client import get_command

mock_context = {
    "os": "Ubuntu",
    "shell": "bash",
    "language": "en_US.UTF-8" 
}

total_latency = 0
hits = 0
path = os.path.expanduser("~/shai/evals/ground_truth.json")

try:
    with open(path, 'r') as f:
        data = json.load(f)
        n_examples = len(data)
        for example in data:
            start = time.time()
            y_hat = get_command(example['prompt'], mock_context)
            end = time.time()
            total_latency += (end - start)
            if y_hat == example['expected'].strip():
                hits += 1
            else:
                print(f"[FAILED] Expected: {example['expected'].strip()} | Predicted: {y_hat}")
        print(f"Precision: {(hits / n_examples) * 100:.2f}%. Average latency: {(total_latency / n_examples) * 1000:.2f}ms")
except FileNotFoundError:
    print("'ground_truth.json' not found")