# test_db.py
import os
from langchain_community.vectorstores import Chroma
from sentence_transformers import SentenceTransformer

# 1. Налаштування шляху (має збігатися з твоїм config.py)
CHROMA_DB_DIR = "db/"


# 2. Оскільки Chroma потребує функцію ембеддінгів для ініціалізації,
# ми дублюємо твій клас LocalEmbeddings тут
class LocalEmbeddings:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode([text], convert_to_numpy=True)[0].tolist()


def inspect_database():
    if not os.path.exists(CHROMA_DB_DIR):
        print(f"❌ Помилка: Директорія бази '{CHROMA_DB_DIR}' не знайдена.")
        return

    print(f"🔍 Підключення до бази за адресою: {CHROMA_DB_DIR}...")

    try:
        # Завантажуємо базу
        vectordb = Chroma(
            persist_directory=CHROMA_DB_DIR,
            embedding_function=LocalEmbeddings()
        )

        # Отримуємо всі метадані
        # ми не беремо самі тексти (documents), щоб не забивати консоль
        db_data = vectordb.get(include=["metadatas"])
        metadatas = db_data.get("metadatas", [])

        if not metadatas:
            print("⚠️ База знайдена, але вона порожня.")
            return

        # Словник для підрахунку чанків на файл
        file_stats = {}

        for meta in metadatas:
            source = meta.get("source", "Unknown")
            # Очищуємо шлях, щоб було видно тільки назву файлу
            file_name = os.path.basename(source)
            file_stats[file_name] = file_stats.get(file_name, 0) + 1

        print("\n--- 📂 СПИСОК ФАЙЛІВ У БАЗІ ---")
        total_chunks = 0
        for i, (fname, count) in enumerate(sorted(file_stats.items()), 1):
            print(f"{i}. 📄 {fname} — ({count} чанків)")
            total_chunks += count

        print("------------------------------")
        print(f"✅ Всього унікальних файлів: {len(file_stats)}")
        print(f"✅ Загальна кількість чанків: {total_chunks}")

    except Exception as e:
        print(f"❌ Сталася помилка при читанні бази: {e}")


if __name__ == "__main__":
    inspect_database()