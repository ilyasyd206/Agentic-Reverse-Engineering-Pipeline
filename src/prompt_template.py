# Поддерживаем оба импорта — под старую и новую структуру LangChain
try:
    from langchain.prompts import PromptTemplate
except ImportError:
    from langchain_core.prompts import PromptTemplate

TEMPLATE = """
You are a software visualization assistant.
When asked for a diagram, output valid PlantUML code, wrapped in triple backticks.
Include class names **and** their public methods (with parentheses).
if asked for alghoritm in text , in valid PlantUML code write this alghoritm. Or in text for some other things, answer them.

Use-case: {use_case}

Context:
{context}

Task:
{task_description}

-- DOCUMENTS BELOW --
{docs}

-- YOUR ANSWER BELOW --
"""

prompt = PromptTemplate(
    input_variables=["use_case", "context", "task_description", "docs"],
    template=TEMPLATE,
)
