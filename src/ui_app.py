import os
import sys
import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from openai import RateLimitError,  APIError
from src.data_loader     import build_vectorstore, load_vectorstore
from src.prompt_template import prompt
from src.chain_builder   import build_chain
from src.postprocess     import prepare_output

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

# Sidebar
st.sidebar.header("Nastavenia RAG/LLM")
k = st.sidebar.slider("k (počet dokumentov)", 1, 10, 5)
temperature = st.sidebar.slider("Teplota LLM", 0.0, 1.0, 0.2)

if st.sidebar.button("Prebudovať vektorovú databázu"):
    with st.spinner("Opätovne budujeme vektorovú databázu z docs/..."):
        vectordb = reset_vectorstore()
    st.sidebar.success("Hotovo")
else:
    vectordb = get_vectorstore()

# Main UI
st.title("AI-asistent pre analýzu a vizualizáciu SW")

use_case  = st.selectbox(
    "Scenár použitia",
    ["UC1: Architektúra", "UC2: Dokumentácia", "UC3: Refaktorovanie", "UC4: Hľadanie UML-vzorov"]
)
context   = st.text_area(
    "Kontext (dopln. informácie)",
    placeholder="Kontext (dopln. informácie)...",
    height=120
)
task_desc = st.text_area(
    "Popis úlohy",
    placeholder="Popis úlohy...",
    height=120
)

if st.button("Spustiť analýzu"):
    chain = build_chain(vectordb, prompt, k=k, temperature=temperature)

    with st.spinner("LLM generuje odpoveď…"):
        try:
            raw = chain({
                "use_case":         use_case,
                "context":          context,
                "task_description": task_desc
            })
        except RateLimitError:
            st.error(
                "Prekročený limit požiadaviek na OpenAI. "
                "Skontrolujte svoj zostatok a plán na platform.openai.com"
            )
            st.stop()
        except APIError as e:
            st.error(f"Sieťová chyba OpenAI API: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Chyba pri vykonávaní reťazca: {e}")
            st.stop()

    out = prepare_output(raw)

    st.subheader("Odpoveď LLM")
    st.write(out.get("text", ""))

    if out.get("uml"):
        st.subheader("PlantUML")
        for block in out["uml"]:
            st.code(block, language="plantuml")

    if out.get("source_documents"):
        st.subheader("Zdroje (source_documents)")
        # Собираем уникальные пути в порядке появления
        seen = set()
        for sd in out["source_documents"]:
            src = sd.metadata.get("source") or getattr(sd, "source", None)
            if src and src not in seen:
                seen.add(src)
                st.write(f"- {src}")
