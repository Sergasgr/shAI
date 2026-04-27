import json
import time
from ai.ollama_client import get_command

mock_context = {
    "os": "Ubuntu",
    "shell": "bash",
    "language": "en_US.UTF-8" 
}

avg_time = 0
hit = 0
n_examples = 0

with open('/home/sergas/shai/evals/ground_truth.json', 'r') as f:
    data = json.load(f)
    n_examples = len(data)
    for example in data:
        t1 = time.time()
        y_hat = get_command(example['prompt'], mock_context)
        t2 = time.time()
        avg_time += t2 - t1
        if y_hat == example['expected']:
            hit += 1

print(f"Precision: {hit/n_examples*100:.2f}%. Average latency: {avg_time/n_examples*1000:.2f}ms")
