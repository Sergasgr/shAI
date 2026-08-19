import sqlite3
import json
from pathlib import Path
from datasets import load_dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model
from shai.core.config import SECURITY_TOKENIZER, SECURITY_MODEL

def export_telemetry_to_chatml() -> tuple[int, str]:
    db_path = Path.home() / ".local" / "share" / "shai" / "feedback.db"
    out_path = Path.home() / ".local" / "share" / "shai" / "dataset.jsonl"
    ground_truth_path = Path(__file__).resolve().parent.parent.parent.parent / "evals" / "ground_truth.json"
    
    if not db_path.exists():
        raise FileNotFoundError("Telemetry database not found. Run some commands first!")
        
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    
    with open(out_path, 'w', encoding='utf-8') as f:
        cur.execute("SELECT prompt, command, os_context FROM executions WHERE exit_code = 0")
        for row in cur:
            chatml_entry = {
                "messages": [
                    {"role": "system", "content": f"You are a Linux Shell expert. Return ONLY the command to comply with the client's request without format neither explanations nor greetings. OS: {row['os_context']}."},
                    {"role": "user", "content": row["prompt"]},
                    {"role": "assistant", "content": row["command"]}
                ]
            }
            f.write(json.dumps(chatml_entry, ensure_ascii=False) + '\n')
            count += 1
        
        cur.execute("SELECT command, explanation, os_context FROM executions WHERE explanation != 'NULL' AND explanation != ''")
        for row in cur:
            chatml_entry = {
                "messages": [
                    {"role": "system", "content": f"You are a Linux Shell expert. Return a briefly explanation of the given command. Be concise and direct. OS: {row['os_context']}."},
                    {"role": "user", "content": row["command"]},
                    {"role": "assistant", "content": row["explanation"]}
                ]
            }
            f.write(json.dumps(chatml_entry, ensure_ascii=False) + '\n')
            count += 1

    con.close()

    if ground_truth_path.exists():
        with open(out_path, 'a', encoding='utf-8') as f:
            with open(ground_truth_path, 'r', encoding='utf-8') as gt_file:
                ground_truth = json.load(gt_file)
                for sample in ground_truth:
                    chatml_entry = {
                        "messages": [
                            {"role": "system", "content": "You are a Linux Shell expert. Return ONLY the command to comply with the client's request without format neither explanations nor greetings."},
                            {"role": "user", "content": sample["prompt"]},
                            {"role": "assistant", "content": sample["expected"]}
                        ]
                    }
                    f.write(json.dumps(chatml_entry, ensure_ascii=False) + '\n')
                    count += 1
    
    return count, str(out_path)

def train_security_model():
    dataset_path = Path(__file__).parent.parent / "data" / "security_dataset.jsonl"
    output_dir = Path.home() / ".local" / "share" / "shai" / "models" / "security_lora"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ds = load_dataset("json", data_files=str(dataset_path))
    tokenizer = AutoTokenizer.from_pretrained(SECURITY_TOKENIZER)
    
    def tokenization(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)
    
    tokenized_ds = ds.map(tokenization, batched=True)
    tokenized_ds = tokenized_ds.rename_column("label", "labels")
    tokenized_ds.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
    
    base_model = AutoModelForSequenceClassification.from_pretrained(SECURITY_MODEL, num_labels=2)
    lora_config = LoraConfig(task_type="SEQ_CLS", r=8, lora_alpha=16)
    ft_model = get_peft_model(base_model, lora_config)
    
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        learning_rate=2e-4,
        per_device_train_batch_size=8,
        num_train_epochs=3,
        weight_decay=0.01,
        remove_unused_columns=False,
        logging_steps=5
    )
    
    trainer = Trainer(
        model=ft_model,
        args=training_args,
        train_dataset=tokenized_ds["train"],
    )
    
    print("[cyan]Starting security layer fine-tuning...[/cyan]")
    trainer.train()
    
    ft_model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    
    return str(output_dir)