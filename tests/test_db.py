import os
from src.data_loader import build_vectorstore

print("🚀 Починаємо примусову побудову бази (це може зайняти хвилину-дві, бо книги великі)...")

# Вказуємо шлях до папки docs
docs_path = os.path.join(os.getcwd(), "docs")

# Примусово БУДУЄМО базу
db = build_vectorstore(docs_path)

# Перевіряємо результат
count = db._collection.count()
print(f"✅ Готово! В базі зараз: {count} чанків тексту.")

# Робимо тестовий пошук
print("\n🔍 Шукаємо: 'Single Responsibility Principle'...")
docs = db.similarity_search("Single Responsibility Principle", k=3)

for i, doc in enumerate(docs):
    source = doc.metadata.get('source', 'Невідомо')
    print(f"\n--- Результат {i+1} ---")
    print(f"📄 Джерело: {source}")
    print(f"📝 Текст: {doc.page_content[:150]}...")