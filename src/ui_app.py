import os
import sys
import stat
import shutil
import subprocess  # <-- ДОДАНО ДЛЯ ВИКЛИКУ GIT
import streamlit as st
import streamlit.components.v1 as components
from plantuml import PlantUML
from langchain_core.messages import HumanMessage, AIMessage



# Імпортуємо наш новий граф
from src.agent_graph import build_graph

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.data_loader import build_vectorstore, load_vectorstore

st.set_page_config(page_title="AI-asistent SW analýzy", layout="wide")
DOCS_PATH = os.path.join(PROJECT_ROOT, "docs")


@st.cache_resource(show_spinner=False)
def get_vectorstore():
    try:
        return load_vectorstore()
    except FileNotFoundError:
        return build_vectorstore(DOCS_PATH)


def reset_vectorstore():
    get_vectorstore.clear()
    return get_vectorstore()


# --- Ініціалізація стану ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "graph_app" not in st.session_state:
    st.session_state.graph_app = build_graph()
if "repo_ready" not in st.session_state:
    st.session_state.repo_ready = False

plantuml_server = PlantUML(url='http://www.plantuml.com/plantuml/svg/')

# --- Інтерфейс ---
st.title("🧠 AI Architecture Analyzer (IEEE Pipeline)")

# ==========================================
# SIDEBAR (Бічна панель)
# ==========================================
st.sidebar.header("Nastavenia RAG")
k = st.sidebar.slider("Počet kontextových dokumentov (k)", 1, 10, 5)
if st.sidebar.button("Prebudovať databázu"):
    with st.spinner("Budujeme vektorovú databázu..."):
        reset_vectorstore()
    st.sidebar.success("Hotovo!")

st.sidebar.markdown("---")


def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    try:
        func(path)
    except Exception:
        pass


# --- НОВИЙ БЛОК: REPO SETUP ---
st.sidebar.subheader("📦 Repo Setup")
repo_url = st.sidebar.text_input("GitHub repo URL", placeholder="https://github.com/psf/requests")

# Створюємо ізольовану папку ТІЛЬКИ для репозиторіїв
REPOS_DIR = os.path.join(DOCS_PATH, "repos")
os.makedirs(REPOS_DIR, exist_ok=True)

if st.sidebar.button("🔄 Clone & Build RAG"):
    if not repo_url:
        st.sidebar.warning("⚠️ Zadaj najprv GitHub URL.")
    else:
        with st.spinner("Klonujem repozitár a budujem databázu..."):

            repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
            CLONE_DIR = os.path.join(REPOS_DIR, repo_name)

            # Очищаємо ТІЛЬКИ папку repos (книжки в docs залишаються недоторканими!)
            for item in os.listdir(REPOS_DIR):
                item_path = os.path.join(REPOS_DIR, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, onerror=remove_readonly)
                else:
                    os.remove(item_path)

            try:
                subprocess.run(["git", "clone", repo_url, CLONE_DIR], capture_output=True, text=True, check=True)
                st.sidebar.success(f"✅ Repozitár '{repo_name}' úspešne naklonovaný do {REPOS_DIR}!")
                st.session_state.repo_ready = True

                reset_vectorstore()
                st.sidebar.success("✅ Vektorová databáza bola aktualizovaná!")

            except subprocess.CalledProcessError as e:
                st.sidebar.error(f"❌ Chyba pri klonovaní: {e.stderr}")
            except FileNotFoundError:
                st.sidebar.error("❌ Git nie je nainštalovaný alebo nie je v PATH.")
# ==========================================я

# Відображення історії чату
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        st.chat_message("user").write(msg.content)
    elif isinstance(msg, AIMessage):
        st.chat_message("assistant").write(msg.content)

# Поле вводу
user_input = st.chat_input("Zadajte požiadavku (napr. 'Zgeneruj dokumentaciu pre auth')...")

if user_input:
    # 1. Показуємо повідомлення юзера
    st.chat_message("user").write(user_input)

    # 2. Додаємо в пам'ять
    st.session_state.messages.append(HumanMessage(content=user_input))

    # 3. RAG: Дістаємо контекст (спрощено)
    vectordb = get_vectorstore()
    docs = vectordb.as_retriever(search_kwargs={"k": k}).invoke(user_input)
    context_code = "\n---\n".join([d.page_content for d in docs])

    # 4. Запуск графа
    with st.spinner("AI analyzuje a generuje dokumentáciu..."):
        initial_state = {
            "messages": st.session_state.messages,
            "context_code": context_code,
            "query": user_input
        }

        # Виклик графа (отримуємо фінальний стан)
        final_state = st.session_state.graph_app.invoke(initial_state)

        # Оновлюємо історію чату з результатів графа
        st.session_state.messages = final_state["messages"]

        # 5. Відображення результатів
        with st.chat_message("assistant"):
            # Якщо граф пройшов повний пайплайн (має ключі діаграм)
            if "doc_text" in final_state and final_state["doc_text"]:
                st.write("✅ Generovanie dokončené! Tu sú výsledky:")

                # Створюємо вкладки (Tabs) для 4-х елементів зі скетчу
                tab1, tab2, tab3, tab4 = st.tabs(
                    ["📄 IEEE Text", "🧱 Class Diagram", "🔄 Sequence Diagram", "🕸️ Weighted Graph"])

                with tab1:
                    st.markdown(final_state["doc_text"])


                # Функція для рендеру PlantUML
                def render_puml(puml_code, tab, diagram_id):
                    with tab:
                        try:
                            clean_code = puml_code.replace("```plantuml", "").replace("```", "").strip()
                            svg_bytes = plantuml_server.processes(clean_code)
                            svg_string = svg_bytes.decode('utf-8')

                            st.markdown(f"<div style='text-align: center;'>{svg_string}</div>", unsafe_allow_html=True)

                            st.download_button(
                                label="📥 Stiahnuť PlantUML kód",
                                data=clean_code,
                                file_name=f"{diagram_id}.puml",
                                mime="text/plain",
                                key=f"btn_{diagram_id}"
                            )

                            with st.expander("Zobraziť zdrojový kód diagramu"):
                                st.code(clean_code, language="plantuml")

                        except Exception as e:
                            st.error(f"Chyba pri renderovaní PlantUML: {e}")
                            st.code(puml_code)


                render_puml(final_state["diagram_class"], tab2, "class_diagram")
                render_puml(final_state["diagram_sequence"], tab3, "sequence_diagram")
                render_puml(final_state["diagram_weighted_graph"], tab4, "weighted_graph")

            else:
                # Якщо це була просто відповідь у чаті
                st.write(final_state["messages"][-1].content)