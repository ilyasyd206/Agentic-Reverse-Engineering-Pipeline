import os
import pickle
import shutil
import stat
import gc  # ДОДАНО: Для примусового очищення пам'яті та зняття блокувань файлів

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .config import CHROMA_DB_DIR


class LocalEmbeddings:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode([text], convert_to_numpy=True)[0].tolist()


def remove_readonly(func, path, _):
    """Допоміжна функція для Windows, щоб видаляти заблоковані/read-only файли"""
    os.chmod(path, stat.S_IWRITE)
    try:
        func(path)
    except Exception:
        pass


def build_vectorstore(docs_path):
    # 1. ПРИМУСОВО відпускаємо базу даних з пам'яті, щоб Windows дозволив її видалити
    gc.collect()

    # 2. Жорстко видаляємо стару базу
    if os.path.exists(CHROMA_DB_DIR):
        try:
            shutil.rmtree(CHROMA_DB_DIR, onerror=remove_readonly)
            print(f"✅ Deleted old DB at {CHROMA_DB_DIR}")
        except Exception as e:
            print(f"❌ Error deleting old DB: {e}")

    all_docs = []
    # общий loader
    for glob in ["**/*.md", "**/*.txt", "**/*.py", "**/*.pdf"]:
        loader = DirectoryLoader(docs_path, glob=glob, show_progress=True, use_multithreading=True,
                                 loader_cls=TextLoader)
        try:
            docs = loader.load()
        except Exception as e:
            print(f"Error loading {glob}: {e}")
            docs = []
            # Fallback для PDF якщо TextLoader падає
            for root, _, files in os.walk(docs_path):
                for f in files:
                    if f.endswith(".pdf"):
                        docs.extend(PyPDFLoader(os.path.join(root, f)).load())
        for d in docs:
            ext = os.path.splitext(d.metadata["source"])[1].lstrip(".")
            d.metadata["type"] = ext
        all_docs.extend(docs)

    # зберігаємо
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    split_docs = text_splitter.split_documents(all_docs)

    # будуємо нову базу
    vectordb = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=LocalEmbeddings())
    vectordb.add_documents(split_docs)
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
            raise TypeError("Loaded object is not a retriever-compatible vectorstore")
        return vectordb

    vectordb = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=LocalEmbeddings())
    return vectordb