# src/chain_builder.py

import os
from typing import Optional, Dict, Any

from langchain.schema import HumanMessage
try:
    from langchain_community.chat_models import ChatOpenAI as OpenAI
except ImportError:
    from langchain.chat_models import ChatOpenAI as OpenAI

# Импортируем всё необходимое из tenacity
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import RateLimitError, APIError

def build_chain(
    vectordb,
    prompt_template: Optional[str] = None,
    k: int = 5,
    temperature: float = 0.2,
):
    """
    Простая RAG-цепочка «вручную».
    По умолчанию использует модель из env OPENAI_MODEL_NAME или gpt-3.5-turbo.
    """

    if not hasattr(vectordb, "as_retriever"):
        raise TypeError("Vectorstore must support .as_retriever()")

    # читаем модель из переменной окружения, fallback на gpt-3.5-turbo
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4")

    llm = OpenAI(model_name=model_name, temperature=temperature)

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((RateLimitError, APIError))
    )
    def run_llm_with_retry(messages):
        return llm(messages)

    def run(inputs: Dict[str, Any]) -> Dict[str, Any]:
        query = inputs.get("task_description", "")
        retr = vectordb.as_retriever(search_kwargs = {"k": k},where = {"pattern": query})
        docs = retr.get_relevant_documents(query)
        joined = "\n---\n".join(getattr(d, "page_content", "") for d in docs)

        if prompt_template:
            prompt_text = prompt_template.format(
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

        # Используем нашу "усиленную" функцию
        response = run_llm_with_retry(messages)

        answer = response.content if hasattr(response, "content") else str(response)

        return {"result": answer, "source_documents": docs}

    run.combine_documents_chain = True
    return run