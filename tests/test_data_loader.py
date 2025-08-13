import pickle
import tempfile
from pathlib import Path
import pytest

from src.data_loader import load_vectorstore

class DummyVectorStore:
    def as_retriever(self, **kwargs):  # type: ignore
        return lambda *a, **kw: "ok"

def test_load_vectorstore_ok(monkeypatch):
    # создаём временный файл с валидным объектом
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "vect.pkl"
        with p.open("wb") as f:
            pickle.dump(DummyVectorStore(), f)

        # загружаем
        vect = load_vectorstore(path=str(p))
        assert hasattr(vect, "as_retriever")

def test_load_vectorstore_wrong_type(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "vect.pkl"
        with p.open("wb") as f:
            pickle.dump({"bad": "object"}, f)

        with pytest.raises(TypeError):
            load_vectorstore(path=str(p))