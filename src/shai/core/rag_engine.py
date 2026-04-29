from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from shai.core.config import OLLAMA_BASE_URL
import os 

DB_DIR = os.path.expanduser("~/shai/data/shai_db")

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
        embedder = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_BASE_URL)
        os.makedirs(DB_DIR, exist_ok=True)
        Chroma.from_documents(documents=chunks, embedding=embedder, persist_directory=DB_DIR)
        return True
    except FileNotFoundError:
        return False

def search_knowledge(query: str) -> str:
    vector_store = Chroma(
        embedding_function = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_BASE_URL),
        persist_directory=DB_DIR
    )
    results = vector_store.similarity_search(
        query,
        k=2
    )
    text = []
    for doc in results:
        text.append(doc.page_content)
    return "\n".join(text)