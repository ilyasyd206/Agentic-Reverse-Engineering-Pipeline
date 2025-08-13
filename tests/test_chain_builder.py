from unittest.mock import patch, MagicMock
from src.chain_builder import build_chain

class DummyVectorStore:
    def as_retriever(self, **kwargs):
        return "dummy_retriever"

# Определяем класс мока, который будет имитировать Runnable
class MockLLM(MagicMock):
    # Эти методы нужны для Runnable интерфейса
    def invoke(self, *args, **kwargs):
        return "Mocked response"

    # Добавляем все свойства, которые проверяет LangChain для типа Runnable
    @property
    def lc_serializable(self):
        return True

    @property
    def lc_runnable(self):
        return True

@patch("src.chain_builder.OpenAI")
def test_build_chain_happy_path(mock_openai):
    # Создаём мок, соответствующий интерфейсу Runnable
    mock_llm = MockLLM()
    mock_openai.return_value = mock_llm

    # Патчим дополнительно RetrievalQA, чтобы не проверял тип llm
    with patch("langchain.chains.RetrievalQA.from_chain_type") as mock_retrieval:
        mock_chain = MagicMock()
        mock_chain.combine_documents_chain = "mock_combine_chain"
        mock_retrieval.return_value = mock_chain

        vectordb = DummyVectorStore()
        chain = build_chain(vectordb, prompt_template=None)   # prompt не важен для теста

        # удостоверяемся, что всё вызвалось
        mock_openai.assert_called_once()
        assert hasattr(chain, "combine_documents_chain")