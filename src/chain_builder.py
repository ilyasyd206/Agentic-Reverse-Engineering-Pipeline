# src/chain_builder.py

import os
from typing import Optional, Dict, Any

# --- ВИПРАВЛЕНО ІМПОРТ ---
from langchain_core.messages import HumanMessage
# -------------------------

from langchain_google_genai import ChatGoogleGenerativeAI


def build_chain(
        vectordb,
        prompt_template: Optional[str] = None,
        k: int = 5,
        temperature: float = 0.2,
):
    """
    RAG-ланцюжок на базі Google Gemini.
    """

    if not hasattr(vectordb, "as_retriever"):
        raise TypeError("Vectorstore must support .as_retriever()")

    # Отримуємо ключ зі змінних середовища
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set. Please set the environment variable.")

    # Ініціалізація Gemini
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=api_key,
        temperature=temperature,
        convert_system_message_to_human=True,
        transport="rest"  # <--- ДОДАЙ ЦЕЙ ПАРАМЕТР
    )

    def run(inputs: Dict[str, Any]) -> Dict[str, Any]:
        query = inputs.get("task_description", "")

        # Пошук документів (оновлений метод invoke)
        retr = vectordb.as_retriever(search_kwargs={"k": k})
        docs = retr.invoke(query)

        # Об'єднання знайденого коду
        joined = "\n---\n".join(getattr(d, "page_content", "") for d in docs)

        # Формування промпта
        if prompt_template:
            # Якщо prompt_template це об'єкт PromptTemplate, використовуємо format
            if hasattr(prompt_template, "format"):
                prompt_text = prompt_template.format(
                    use_case=inputs.get("use_case", ""),
                    context=inputs.get("context", ""),
                    task_description=inputs.get("task_description", ""),
                    docs=joined,
                )
            # Якщо це просто рядок (хоча у тебе в коді це об'єкт)
            else:
                prompt_text = str(prompt_template).format(
                    use_case=inputs.get("use_case", ""),
                    context=inputs.get("context", ""),
                    task_description=inputs.get("task_description", ""),
                    docs=joined,
                )
        else:
            prompt_text = (
                f"{inputs.get('context', '')}\n{joined}\n{inputs.get('task_description', '')}"
            )

        messages = [HumanMessage(content=prompt_text)]

        # Виклик Gemini (оновлений метод invoke)
        response = llm.invoke(messages)

        answer = response.content if hasattr(response, "content") else str(response)

        return {"result": answer, "source_documents": docs}

    return run