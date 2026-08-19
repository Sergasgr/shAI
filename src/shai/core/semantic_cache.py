import threading
import uuid
from pathlib import Path
from shai.ai.ollama_client import OLLAMA_BASE_URL
from shai.core.config import EMBEDDINGS_MODEL, SIMILARITY_THRESHOLD
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

CACHE_DIR = Path.home() / ".local" / "share" / "shai" / "cache_db"
MAX_CACHE_SIZE = 500
vector_store_instance = None
lock = threading.Lock()

def get_vector_store() -> Chroma | None:
    global vector_store_instance
    if vector_store_instance is None:
        with lock:
            if vector_store_instance is None:
                try:
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    embedder = OllamaEmbeddings(
                        model=EMBEDDINGS_MODEL, 
                        base_url=OLLAMA_BASE_URL
                    )
                    vector_store_instance = Chroma(
                        collection_name="semantic_cache",
                        embedding_function=embedder,
                        persist_directory=str(CACHE_DIR)
                    )
                except Exception:
                    return None
    return vector_store_instance

def check_cache(prompt: str) -> str | None:
    try:
        db = get_vector_store()
        if not db: 
            return None
            
        results = db.similarity_search_with_score(prompt, k=1)
        if results:
            doc, score = results[0]
            if score < SIMILARITY_THRESHOLD: 
                return doc.metadata.get("command")
    except Exception:
        pass
    
    return None

def save_to_cache(prompt: str, command: str) -> None:
    try:
        db = get_vector_store()
        if db:
            db.add_texts(
                texts=[prompt],
                metadatas=[{"command": command}],
                ids=[str(uuid.uuid4())]
            )
         
            all_data = db.get()
            count = len(all_data["ids"])
            if count > MAX_CACHE_SIZE:
                excess = count - MAX_CACHE_SIZE
                ids_to_delete = all_data["ids"][:excess]
                db.delete(ids=ids_to_delete)
    except Exception:
        pass