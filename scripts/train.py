import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from datasets import load_dataset
from trl import SFTTrainer
from peft import LoraModel, LoraConfig
import os 

dataset_path = os.path.expanduser("~/shai/data/dataset.jsonl")
dataset = load_dataset("json", data_files=dataset_path, split="train")
model_name = "Qwen/Qwen2.5-Coder-7B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token
bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
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