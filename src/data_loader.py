import os
import pickle

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_community.vectorstores import Chroma
from sentence_transformers import SentenceTransformer

from .config import CHROMA_DB_DIR

class LocalEmbeddings:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode([text], convert_to_numpy=True)[0].tolist()

def build_vectorstore(docs_path):
    all_docs = []
    # общий loader
    for glob in ["**/*.md", "**/*.txt", "**/*.py", "**/*.pdf"]:
        loader = DirectoryLoader(docs_path, glob=glob) if glob != "**/*.pdf" else None
        if loader:
            docs = loader.load()
        else:
            # для PDF — пример
            docs = []
            for root, _, files in os.walk(docs_path):
                for f in files:
                    if f.endswith(".pdf"):
                        docs.extend(PyPDFLoader(os.path.join(root, f)).load())
        for d in docs:
            ext = os.path.splitext(d.metadata["source"])[1].lstrip(".")
            d.metadata["type"] = ext
        all_docs.extend(docs)
    # кастомная категория, например паттерны
    patterns_path = os.path.join(docs_path, "patterns")
    for loader in [DirectoryLoader(patterns_path, glob="**/*.md")]:
        docs = loader.load()
        for d in docs:
            name = os.path.splitext(os.path.basename(d.metadata["source"]))[0]
            d.metadata["category"] = name.lower()
        all_docs.extend(docs)
    # сохраняем
    vectordb = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=LocalEmbeddings())
    vectordb.add_documents(all_docs)
    return vectordb


def load_vectorstore(path: str = None):
    """
    Если path указывает на pickle-файл — загружает его (для тестов).
    Иначе пытается открыть ChromaDB по CHROMA_DB_DIR.
    """
    if path and os.path.isfile(path):
        with open(path, "rb") as f:
            vectordb = pickle.load(f)
        if not hasattr(vectordb, "as_retriever"):
            raise TypeError("Loaded object is not a valid VectorStore")
        return vectordb

    dirpath = path or CHROMA_DB_DIR
    if not os.path.isdir(dirpath):
        raise FileNotFoundError(f"Vectorstore directory '{dirpath}' not found")

    embeddings = LocalEmbeddings()
    return Chroma(persist_directory=dirpath, embedding_function=embeddings)
