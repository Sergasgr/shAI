import sqlite3
import os
import json
from shai.core.env_detector import get_system_context
from shai.core.telemetry import init_db

init_db()

db_dir = os.path.expanduser("~/shai/data/")
db_path = os.path.join(db_dir, "feedback.db")
json_path = os.path.join(db_dir, "dataset.jsonl")
ground_truth_path = os.path.expanduser("~/shai/evals/ground_truth.json")

os.makedirs(db_dir, exist_ok=True)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

os_context = get_system_context()
mock_os = os_context['os']


with open(json_path, 'w', encoding='utf-8') as f:
    cur.execute("SELECT prompt, command, os_context FROM executions WHERE exit_code = 0")
    for row in cur:
        chatml_dict = {
            "messages": [
                {
                    "role": "system", 
                    "content": f"You are a strict Linux Shell executor. Return ONLY the raw bash code starting exactly with #!/bin/bash. NO explanations, NO markdown formatting, NO conversational text before or after. OS: {row['os_context']}."
                },
                {
                    "role": "user", 
                    "content": row["prompt"]
                },
                {
                    "role": "assistant", 
                    "content": row["command"]
                }
            ]
        }
        f.write(json.dumps(chatml_dict, ensure_ascii=False) + "\n")

    cur.execute("SELECT command, explanation, os_context FROM executions WHERE explanation != 'NULL' AND explanation != ''")
    for row in cur:
        chatml_dict = {
            "messages": [
                {
                    "role": "system", 
                    "content": f"You are a Linux Shell expert. Return a briefly explanation of the given command. Be concise and direct. OS: {row['os_context']}."
                },
                {
                    "role": "user", 
                    "content": row["command"]
                },
                {
                    "role": "assistant", 
                    "content": row["explanation"]
                }
            ]
        }
        f.write(json.dumps(chatml_dict, ensure_ascii=False) + "\n")
        
    if os.path.exists(ground_truth_path):
        with open(ground_truth_path, 'r', encoding='utf-8') as gt_file:
            ground_truth = json.load(gt_file)
            for sample in ground_truth:
                chatml_dict = {
                    "messages": [
                        {
                            "role": "system", 
                            "content": f"You are a strict Linux Shell executor. Return ONLY the raw bash code starting exactly with #!/bin/bash. NO explanations, NO markdown formatting, NO conversational text before or after. OS: {mock_os}."
                        },
                        {
                            "role": "user", 
                            "content": sample["prompt"]
                        },
                        {
                            "role": "assistant", 
                            "content": sample["expected"]
                        }
                    ]
                }
                f.write(json.dumps(chatml_dict, ensure_ascii=False) + "\n")
conn.close()