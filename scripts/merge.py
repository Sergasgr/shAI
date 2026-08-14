import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from shai.core.config import HF_BASE_MODEL

tokenizer = AutoTokenizer.from_pretrained(HF_BASE_MODEL)

model = AutoModelForCausalLM.from_pretrained(
    HF_BASE_MODEL,
    torch_dtype=torch.float16,
    device_map="cpu",               
    low_cpu_mem_usage=True          
)

peft_model = PeftModel.from_pretrained(model, "models/shai-bash-adapter")
merged_model = peft_model.merge_and_unload()
merged_model.save_pretrained("models/shai-merged")
tokenizer.save_pretrained("models/shai-merged")