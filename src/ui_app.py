import os
import sys
import shutil
import subprocess
import streamlit as st
from plantuml import PlantUML
from langchain_core.messages import HumanMessage, AIMessage

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.agent_graph import build_graph
from src.data_loader import build_vectorstore, load_vectorstore
from src.utils import remove_readonly  # ✅ Jeden zdrojový súbor, žiadna duplikácia

st.set_page_config(page_title="AI-asistent SW analýzy", layout="wide")
DOCS_PATH = os.path.join(PROJECT_ROOT, "docs")
REPOS_DIR = os.path.join(DOCS_PATH, "repos")
os.makedirs(REPOS_DIR, exist_ok=True)

plantuml_server = PlantUML(url='http://www.plantuml.com/plantuml/svg/')


# ==========================================
# ✅ render_puml na úrovni modulu (nie vnútri if bloku)
# ==========================================
def render_puml(puml_code: str, tab, diagram_id: str):
    """Renderuje PlantUML kód ako SVG v danom Streamlit tabe."""
    with tab:
        try:
            clean_code = puml_code.replace("```plantuml", "").replace("```", "").strip()
            svg_bytes = plantuml_server.processes(clean_code)
            svg_string = svg_bytes.decode('utf-8')

            st.markdown(
                f"<div style='text-align: center;'>{svg_string}</div>",
                unsafe_allow_html=True
            )
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


@st.cache_resource(show_spinner=False)
def get_vectorstore():
    try:
        return load_vectorstore()
    except FileNotFoundError:
        return build_vectorstore(DOCS_PATH)


def get_active_vectorstore():
    """
    ✅ Vracia aktuálnu vektorovú databázu.
    Po Clone & Build RAG používa novú DB zo session_state,
    nie starú načítanú z disku cez load_vectorstore().
    """
    if "_current_vectordb" in st.session_state:
        return st.session_state["_current_vectordb"]
    return get_vectorstore()


def reset_vectorstore():
    get_vectorstore.clear()
    if "_current_vectordb" in st.session_state:
        del st.session_state["_current_vectordb"]


# --- Inicializácia stavu ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "graph_app" not in st.session_state:
    st.session_state.graph_app = build_graph()
if "repo_ready" not in st.session_state:
    st.session_state.repo_ready = False

# --- Rozhranie ---
st.title("🧠 AI Architecture Analyzer (IEEE Pipeline)")

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.header("Nastavenia RAG")
k = st.sidebar.slider("Počet kontextových dokumentov (k)", 1, 10, 5)
if st.sidebar.button("Prebudovať databázu"):
    with st.spinner("Budujeme vektorovú databázu..."):
        reset_vectorstore()
    st.sidebar.success("Hotovo!")

st.sidebar.markdown("---")

st.sidebar.subheader("📦 Repo Setup")
repo_url = st.sidebar.text_input("GitHub repo URL", placeholder="https://github.com/psf/requests")

if st.sidebar.button("🔄 Clone & Build RAG"):
    if not repo_url:
        st.sidebar.warning("⚠️ Zadaj najprv GitHub URL.")
    else:
        with st.spinner("Klonujem repozitár a budujem databázu..."):
            repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
            CLONE_DIR = os.path.join(REPOS_DIR, repo_name)

            for item in os.listdir(REPOS_DIR):
                item_path = os.path.join(REPOS_DIR, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, onerror=remove_readonly)
                else:
                    os.remove(item_path)

            try:
                subprocess.run(
                    ["git", "clone", repo_url, CLONE_DIR],
                    capture_output=True, text=True, check=True,
                    timeout=120  # ✅ Timeout aby sa nezaseklo navždy
                )
                st.sidebar.success(f"✅ Repozitár '{repo_name}' úspešne naklonovaný!")
                st.session_state.repo_ready = True

                # ✅ Explicitne buildujeme DB priamo z naklonovaného repozitára
                # reset_vectorstore() volá load_vectorstore() → načíta STARÚ DB z disku!
                get_vectorstore.clear()
                built_db = build_vectorstore(CLONE_DIR)
                st.session_state["_current_vectordb"] = built_db
                st.sidebar.success(f"✅ Vektorová databáza zostavená z repozitára '{repo_name}'!")

            except subprocess.TimeoutExpired:
                st.sidebar.error("❌ Klonovanie trvalo príliš dlho (timeout 120s).")
            except subprocess.CalledProcessError as e:
                st.sidebar.error(f"❌ Chyba pri klonovaní: {e.stderr}")
            except FileNotFoundError:
                st.sidebar.error("❌ Git nie je nainštalovaný alebo nie je v PATH.")

# ==========================================
# CHAT
# ==========================================
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        st.chat_message("user").write(msg.content)
    elif isinstance(msg, AIMessage):
        st.chat_message("assistant").write(msg.content)

user_input = st.chat_input("Zadajte požiadavku (napr. 'Generate documentation for auth module')...")

if user_input:
    st.chat_message("user").write(user_input)
    st.session_state.messages.append(HumanMessage(content=user_input))

    vectordb = get_active_vectorstore()  # ✅ vždy používa aktuálnu DB
    docs = vectordb.as_retriever(search_kwargs={"k": k}).invoke(user_input)
    context_code = "\n---\n".join([d.page_content for d in docs])

    with st.spinner("AI analyzuje a generuje dokumentáciu..."):
        initial_state = {
            "messages": st.session_state.messages,
            "context_code": context_code,
            "query": user_input
        }
        final_state = st.session_state.graph_app.invoke(initial_state)
        st.session_state.messages = final_state["messages"]

        with st.chat_message("assistant"):
            if "doc_text" in final_state and final_state["doc_text"]:
                st.write("✅ Generovanie dokončené! Tu sú výsledky:")

                tab1, tab2, tab3, tab4 = st.tabs(
                    ["📄 IEEE Text", "🧱 Class Diagram", "🔄 Sequence Diagram", "🕸️ Weighted Graph"]
                )
                with tab1:
                    st.markdown(final_state["doc_text"])

                # ✅ render_puml volané zvonku if bloku — čisté a predvídateľné
                render_puml(final_state["diagram_class"], tab2, "class_diagram")
                render_puml(final_state["diagram_sequence"], tab3, "sequence_diagram")
                render_puml(final_state["diagram_weighted_graph"], tab4, "weighted_graph")
            else:
                st.write(final_state["messages"][-1].content)