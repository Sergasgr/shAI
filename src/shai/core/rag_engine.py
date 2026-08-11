import threading
import shutil
import pickle 
import hashlib
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from shai.core.config import OLLAMA_BASE_URL, EMBEDDINGS_MODEL
from shai.ai.security_detector import is_prompt_injection

DB_DIR = Path.home() / ".local" / "share" / "shai" / "shai_db"
CHUNKS_FILE = DB_DIR / "chunks.pkl"
vector_store_instance = None
lock = threading.Lock()

def get_vector_store():
    global vector_store_instance
    if vector_store_instance is None:
        with lock:
            if vector_store_instance is None:
                try:
                    embedder = OllamaEmbeddings(
                        model=EMBEDDINGS_MODEL, 
                        base_url=OLLAMA_BASE_URL
                    )
                    vector_store_instance = Chroma(
                        embedding_function=embedder,
                        persist_directory=str(DB_DIR)
                    )
                except Exception:
                    return None
    return vector_store_instance

def build_vector_db(file_path: str) -> bool:
    try:
        loader = TextLoader(file_path)
        documents = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=200, 
            chunk_overlap=20, 
            separators=["\n\n", "\n"]
        )
        chunks = splitter.split_documents(documents)     
        
        embedder = OllamaEmbeddings(
            model=EMBEDDINGS_MODEL, 
            base_url=OLLAMA_BASE_URL
        )
        
        DB_DIR.mkdir(parents=True, exist_ok=True)
        
        if any(is_prompt_injection(str(chunk)) for chunk in chunks):
            return False
        
        with open(CHUNKS_FILE, "wb") as f:
            pickle.dump(chunks, f)
  
        unique_ids = [hashlib.sha256(chunk.page_content.encode('utf-8')).hexdigest() for chunk in chunks]
        
        Chroma.from_documents(
            documents=chunks,
            embedding=embedder, 
            ids=unique_ids, 
            persist_directory=str(DB_DIR)
        )
        
        global vector_store_instance
        vector_store_instance = None
        return True # Inyectamos los IDs únicos aquí
    
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"Error in build_vector_db: {e}")
        return False

def search_knowledge(query: str) -> str:
    if not CHUNKS_FILE.exists():
        return ""
        
    global vector_store_instance
    vector_store = get_vector_store()
    
    if not vector_store:
        return ""
    
    try:
        with open(CHUNKS_FILE, "rb") as f:
            chunks = pickle.load(f)
            
        bm25_retriever = BM25Retriever.from_documents(chunks)
        bm25_retriever.k = 2
        
        vector_retriever = vector_store.as_retriever(search_kwargs={"k": 2})
        
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever], 
            weights=[0.5, 0.5]
        )
        
        results = ensemble_retriever.invoke(query)
        text = [doc.page_content for doc in results]
        return "\n".join(text)
    except Exception:
        return ""
    
def rm_chromadb():
    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)