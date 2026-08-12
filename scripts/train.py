import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from datasets import load_dataset
from trl import SFTTrainer
from peft import LoraConfig
from pathlib import Path
from shai.core.config import HF_BASE_MODEL

dataset_path = Path.home() / ".local" / "share" / "shai" / "dataset.jsonl"
dataset = load_dataset("json", data_files=str(dataset_path), split="train")

tokenizer = AutoTokenizer.from_pretrained(HF_BASE_MODEL)
tokenizer.pad_token = tokenizer.eos_token
bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)

model = AutoModelForCausalLM.from_pretrained(
    HF_BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto" 
)

config = LoraConfig(
    task_type="CAUSAL_LM",
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
)

training_args = TrainingArguments(
    per_device_train_batch_size=2, 
    gradient_accumulation_steps=4, 
    learning_rate=2e-4, 
    num_train_epochs=3,
    output_dir="models/checkpoints" 
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    peft_config=config,
    processing_class=tokenizer,
    args=training_args
)

trainer.train()
trainer.model.save_pretrained("models/shai-bash-adapter")