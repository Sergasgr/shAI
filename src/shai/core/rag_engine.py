from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import os 

def build_vector_db():
    loader = TextLoader("docs/mis_trucos.txt")
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=200, 
        chunk_overlap=20, 
        separators=["\n\n", "\n"]
    )
    chunks = splitter.split_documents(documents)
    hf = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )
    directory = "./shai_db"
    os.makedirs(directory, exist_ok=True)
    Chroma.from_documents(documents=chunks, embedding=hf, persist_directory=directory)

def search_knowledge(query: str) -> str:
    vector_store = Chroma(
        embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
        persist_directory="./shai_db"
    )
    results = vector_store.similarity_search(
        query,
        k=2
    )
    text = []
    for doc in results:
        text.append(doc.page_content)
    return "\n".join(text)

if __name__ == "__main__":
    build_vector_db()