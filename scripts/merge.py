import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

model_name = "Qwen/Qwen2.5-Coder-7B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    dtype=torch.float16,
    device_map="auto" 
)

peft_model = PeftModel.from_pretrained(model, "models/shai-bash-adapter")
merged_model = peft_model.merge_and_unload()
merged_model.save_pretrained("models/shai-merged")
tokenizer.save_pretrained("models/shai-merged")