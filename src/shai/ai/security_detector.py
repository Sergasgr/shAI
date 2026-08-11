import threading
import torch
from pathlib import Path
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from peft import PeftModel
from shai.core.config import SECURITY_TOKENIZER, SECURITY_MODEL

class SecurityEngine:
    instance = None
    lock = threading.Lock()
    
    def __new__(cls):
        with cls.lock:
            if cls.instance is None:
                cls.instance = super(SecurityEngine, cls).__new__(cls)
                cls.instance.tokenizer = None
                cls.instance.model = None
        return cls.instance
    
    def load(self):
        with self.lock:
            if self.model is None:
                lora_path = Path.home() / ".local" / "share" / "shai" / "models" / "security_lora"
                
                self.tokenizer = AutoTokenizer.from_pretrained(SECURITY_TOKENIZER)
                base_model = AutoModelForSequenceClassification.from_pretrained(SECURITY_MODEL, num_labels=2)
                
                if lora_path.exists():
                    self.model = PeftModel.from_pretrained(base_model, str(lora_path))
                else:
                    self.model = base_model
                    
                self.model.eval()

def is_prompt_injection(text: str) -> bool:
    engine = SecurityEngine()
    engine.load()
    
    inputs = engine.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    
    with torch.no_grad():
        outputs = engine.model(**inputs)
        logits = outputs.logits
        prediction = torch.argmax(logits, dim=-1).item()
        
    return prediction == 1