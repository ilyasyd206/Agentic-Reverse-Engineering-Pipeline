

# AI-Powered Multi-Agent Reverse Engineering Pipeline 🧠🔍

An advanced automated system for source code analysis and architectural visualization. This project uses a **Multi-Agent** approach to transform undocumented codebases into standardized **IEEE 1016** documentation and **PlantUML** diagrams with a built-in self-correction feedback loop.



## 🚀 Key Features

- **Multi-Agent Orchestration**: Powered by **LangGraph**, the system manages a "Generator" and a "Reviewer" agent to ensure high-fidelity outputs.
- **Self-Correction Loop**: Every generated diagram is scrutinized by an AI Reviewer against strict metrics (Syntax, OOP, Clean Architecture, IEEE standards). If the score is $< 8/10$, the system automatically regenerates the output.
- **Automated Repository Ingestion**: Built-in GitHub integration that clones repositories directly into a **RAG (Retrieval-Augmented Generation)** pipeline.
- **Semantic Code Understanding**: Uses **ChromaDB** and semantic chunking to provide the LLM with deep context, moving beyond simple keyword search.
- **Architectural Artifacts**: Generates:
  - 📄 **IEEE 1016 Standard** Technical Documentation (in Slovak/English).
  - 🧱 **Class Diagrams** (OOP focus).
  - 🔄 **Sequence Diagrams** (Logic flow).
  - 🕸️ **Weighted Dependency Graphs**.

## 🛠️ Tech Stack

- **Core Framework**: [LangGraph](https://www.langchain.com/langgraph), [LangChain](https://www.langchain.com/)
- **LLM**: Google Gemini 1.5 Flash / Flash-Lite
- **Vector Database**: ChromaDB
- **UI**: Streamlit
- **Visualization**: PlantUML Server
- **Language**: Python 3.10+

## ⚙️ Architecture Detail

The pipeline follows a state-machine logic where:
1. **Input**: A GitHub URL is provided.
2. **Ingestion**: Code is cloned, chunked, and embedded into the vector store.
3. **Generation**: The *Generator Agent* creates documentation and UML code based on the retrieved context.
4. **Verification**: The *Reviewer Agent* evaluates the output.
5. **Iteration**: If errors are found (e.g., PlantUML syntax errors or architectural violations), the agent receives feedback and retries.



## 📥 Installation & Setup

1. **Clone this repository**:
   ```bash
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```

4. **Run the Application**:
   ```bash
   streamlit run src/ui_app.py
   ```

## 📖 Usage Guide

1. Open the sidebar and enter a **GitHub Repository URL**.
2. Click **"Clone & Build RAG"**. The system will download the code and prepare the AI's "memory".
3. Enter your request in the chat (e.g., *"Analyze the authentication logic and generate a class diagram"*).
4. View the real-time "thoughts" of the agents and download the final UML artifacts.

## 🎓 Academic Context

This project was developed as a **Bachelor's Thesis** at **Comenius University Bratislava (FMFI UK)**. It aims to bridge the gap between static code analysis and intuitive human understanding through the power of Agentic AI.
