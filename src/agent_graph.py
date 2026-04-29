import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from src.prompt_template import (
    TEXT_DOC_PROMPT,
    TEXT_REVIEWER_PROMPT,
    CLASS_DIAGRAM_PROMPT,
    CLASS_REVIEWER_PROMPT,
    SEQUENCE_DIAGRAM_PROMPT,
    SEQUENCE_REVIEWER_PROMPT,
    WEIGHTED_GRAPH_PROMPT,
    GRAPH_REVIEWER_PROMPT,
)

google_api_key = os.getenv("GOOGLE_API_KEY")

llm_generator = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    google_api_key=google_api_key,
    temperature=0.2,
    transport="rest",
    timeout=60
)

llm_reviewer = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    google_api_key=google_api_key,
    temperature=0.0,
    transport="rest",
    timeout=60
)


# --- 1. State ---
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    context_code: str
    query: str

    doc_text: str
    diagram_class: str
    diagram_sequence: str
    diagram_weighted_graph: str

    text_critique: str
    text_iteration: int
    class_critique: str
    class_iteration: int
    seq_critique: str
    seq_iteration: int
    graph_critique: str
    graph_iteration: int


# --- POMOCNÉ FUNKCIE ---

def llm_call_with_backoff(llm, messages: list, max_retries: int = 4, call_timeout: int = 90) -> object:
    """
    Volá LLM s exponenciálnym backoff pri rate limit chybách: 5→10→20→40s.
    Hard timeout cez ThreadPoolExecutor — funguje aj na Windows.
    Ak SDK visí bez exception, po call_timeout sekundách vyhodí TimeoutError.
    """
    delay = 5
    for attempt in range(max_retries):
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(llm.invoke, messages)
                try:
                    return future.result(timeout=call_timeout)
                except FuturesTimeoutError:
                    print(f"⏱️ LLM call timeout po {call_timeout}s (pokus {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2
                        continue
                    raise RuntimeError(f"LLM nedostupný — timeout {call_timeout}s po {max_retries} pokusoch")
        except RuntimeError:
            raise
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = any(k in error_str for k in [
                "429", "quota", "rate limit", "resource exhausted"
            ])
            is_network_error = any(k in error_str for k in [
                "connection aborted", "remotedisconnected", "connectionerror",
                "connection reset", "broken pipe", "network", "remote end closed",
                "connection refused", "timeout", "timed out"
            ])
            should_retry = (is_rate_limit or is_network_error) and attempt < max_retries - 1
            if should_retry:
                reason = "Rate limit" if is_rate_limit else "Sieťová chyba"
                print(f"⚠️ {reason} (pokus {attempt + 1}/{max_retries}), čakám {delay}s... [{type(e).__name__}]")
                time.sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError("LLM nedostupný po všetkých pokusoch")


def build_enriched_query(state: AgentState) -> str:
    """DRY helper: chat history + aktuálna požiadavka."""
    chat_history = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content}"
        for m in state["messages"][-4:]
    )
    return f"Kontext rozhovoru:\n{chat_history}\n\nAktuálna požiadavka: {state['query']}"


def check_verdict(critique_json: str) -> bool:
    """Parsuje JSON od Reviewera a kontroluje verdict == APPROVE."""
    if not critique_json:
        return False
    try:
        clean_json = critique_json.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        return data.get("verdict", "").upper() == "APPROVE"
    except json.JSONDecodeError:
        print(f"⚠️ Chyba parsovania JSON: {critique_json[:100]}")
        return "APPROVE" in critique_json.upper()


# --- 2. UZLY ---

# --- TEXT DOC LOOP ---
def text_doc_node(state: AgentState):
    iteration = state.get("text_iteration", 0)
    print(f"--- PIPELINE: GENERÁCIA TEXTOVEJ DOKUMENTÁCIE (Iterácia {iteration + 1}/3) ---")
    enriched_query = build_enriched_query(state)
    prompt_text = TEXT_DOC_PROMPT.format(
        query=enriched_query,
        critique=state.get("text_critique", ""),   # ✅ critique sa predáva generátoru
        context_code=state["context_code"][:5000]
    )
    response = llm_call_with_backoff(llm_generator, [HumanMessage(content=prompt_text)])
    return {"doc_text": response.content, "text_iteration": iteration + 1}


def review_text_node(state: AgentState):
    print("--- REVIEWER: KONTROLA TEXTOVEJ DOKUMENTÁCIE ---")
    prompt = TEXT_REVIEWER_PROMPT.format(doc_text=state["doc_text"])
    response = llm_call_with_backoff(llm_reviewer, [HumanMessage(content=prompt)])
    print(f"Text Verdict: {response.content[:100]}...")
    return {"text_critique": response.content}


# --- CLASS DIAGRAM LOOP ---
def class_diagram_node(state: AgentState):
    iteration = state.get("class_iteration", 0)
    print(f"--- PIPELINE: GENERÁCIA CLASS DIAGRAM (Iterácia {iteration + 1}/3) ---")
    enriched_query = build_enriched_query(state)
    prompt_text = CLASS_DIAGRAM_PROMPT.format(
        query=enriched_query,
        critique=state.get("class_critique", ""),
        context_code=state["context_code"][:5000]
    )
    response = llm_call_with_backoff(llm_generator, [HumanMessage(content=prompt_text)])
    return {"diagram_class": response.content, "class_iteration": iteration + 1}


def review_class_node(state: AgentState):
    print("--- REVIEWER: KONTROLA CLASS DIAGRAMU ---")
    prompt = CLASS_REVIEWER_PROMPT.format(uml_code=state["diagram_class"])   # ✅ окремий reviewer
    response = llm_call_with_backoff(llm_reviewer, [HumanMessage(content=prompt)])
    print(f"Verdict: {response.content[:80]}...")
    return {"class_critique": response.content}


# --- SEQUENCE DIAGRAM LOOP ---
def sequence_diagram_node(state: AgentState):
    iteration = state.get("seq_iteration", 0)
    print(f"--- PIPELINE: GENERÁCIA SEQUENCE DIAGRAM (Iterácia {iteration + 1}/3) ---")
    enriched_query = build_enriched_query(state)
    prompt_text = SEQUENCE_DIAGRAM_PROMPT.format(
        query=enriched_query,
        critique=state.get("seq_critique", ""),
        context_code=state["context_code"][:5000]
    )
    response = llm_call_with_backoff(llm_generator, [HumanMessage(content=prompt_text)])
    return {"diagram_sequence": response.content, "seq_iteration": iteration + 1}


def review_sequence_node(state: AgentState):
    print("--- REVIEWER: KONTROLA SEQUENCE DIAGRAMU ---")
    prompt = SEQUENCE_REVIEWER_PROMPT.format(uml_code=state["diagram_sequence"])  # ✅ окремий reviewer
    response = llm_call_with_backoff(llm_reviewer, [HumanMessage(content=prompt)])
    print(f"Verdict: {response.content[:80]}...")
    return {"seq_critique": response.content}


# --- WEIGHTED GRAPH LOOP ---
def weighted_graph_node(state: AgentState):
    iteration = state.get("graph_iteration", 0)
    print(f"--- PIPELINE: GENERÁCIA VÁŽENÉHO GRAFU (Iterácia {iteration + 1}/3) ---")
    enriched_query = build_enriched_query(state)
    prompt_text = WEIGHTED_GRAPH_PROMPT.format(
        query=enriched_query,
        critique=state.get("graph_critique", ""),
        context_code=state["context_code"][:5000]
    )
    response = llm_call_with_backoff(llm_generator, [HumanMessage(content=prompt_text)])
    return {"diagram_weighted_graph": response.content, "graph_iteration": iteration + 1}


def review_graph_node(state: AgentState):
    print("--- REVIEWER: KONTROLA VÁŽENÉHO GRAFU ---")
    prompt = GRAPH_REVIEWER_PROMPT.format(uml_code=state["diagram_weighted_graph"])  # ✅ окремий reviewer
    response = llm_call_with_backoff(llm_reviewer, [HumanMessage(content=prompt)])
    print(f"Verdict: {response.content[:80]}...")
    return {"graph_critique": response.content}


def chat_node(state: AgentState):
    print("--- PRÁCA V REŽIME CHATU ---")
    response = llm_call_with_backoff(llm_generator, state["messages"])
    return {"messages": [AIMessage(content=response.content)]}


# --- 3. ROUTERY ---

PIPELINE_TRIGGER_WORDS = [
    # Slovenské
    "dokumentáci", "zgeneruj", "vytvor", "pipeline", "analyzuj", "diagram",
    "vygeneruj", "urob", "spusti",
    # Anglické
    "generate", "create", "analyze", "document", "diagram", "pipeline",
    "produce", "build", "make"
]


def main_router(state: AgentState):
    last_message = state["messages"][-1].content.lower()
    if any(word in last_message for word in PIPELINE_TRIGGER_WORDS):
        print("-> SPUSTENIE ÚPLNÉHO PIPELINU DOKUMENTÁCIE")
        return "text_doc"
    print("-> BEŽNÁ ODPOVEĎ CHATU")
    return "chat"


def route_text(state: AgentState):
    if check_verdict(state.get("text_critique", "")) or state.get("text_iteration", 0) >= 3:
        if not check_verdict(state.get("text_critique", "")):
            print("⚠️ Text nedosiahol APPROVE po 3 iteráciách, pokračujem ďalej.")
        return "class_diagram"
    print("-> CHYBA V TEXTOVEJ DOKUMENTÁCII, REGENERUJEM...")
    return "text_doc"


def route_class(state: AgentState):
    if check_verdict(state.get("class_critique", "")) or state.get("class_iteration", 0) >= 3:
        return "sequence_diagram"
    print("-> CHYBA V CLASS DIAGRAME, GENERUJEM ZNOVA...")
    return "class_diagram"


def route_sequence(state: AgentState):
    if check_verdict(state.get("seq_critique", "")) or state.get("seq_iteration", 0) >= 3:
        return "weighted_graph"
    print("-> CHYBA V SEQUENCE DIAGRAME, GENERUJEM ZNOVA...")
    return "sequence_diagram"


def route_graph(state: AgentState):
    if check_verdict(state.get("graph_critique", "")) or state.get("graph_iteration", 0) >= 3:
        return END
    print("-> CHYBA VO VÁŽENOM GRAFE, GENERUJEM ZNOVA...")
    return "weighted_graph"


# --- 4. ZOSTAVENIE GRAFU ---
def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("text_doc", text_doc_node)
    workflow.add_node("review_text", review_text_node)
    workflow.add_node("class_diagram", class_diagram_node)
    workflow.add_node("review_class", review_class_node)
    workflow.add_node("sequence_diagram", sequence_diagram_node)
    workflow.add_node("review_sequence", review_sequence_node)
    workflow.add_node("weighted_graph", weighted_graph_node)
    workflow.add_node("review_graph", review_graph_node)
    workflow.add_node("chat", chat_node)

    workflow.set_conditional_entry_point(
        main_router, {"text_doc": "text_doc", "chat": "chat"}
    )

    workflow.add_edge("text_doc", "review_text")
    workflow.add_conditional_edges(
        "review_text", route_text,
        {"class_diagram": "class_diagram", "text_doc": "text_doc"}
    )

    workflow.add_edge("class_diagram", "review_class")
    workflow.add_conditional_edges(
        "review_class", route_class,
        {"sequence_diagram": "sequence_diagram", "class_diagram": "class_diagram"}
    )

    workflow.add_edge("sequence_diagram", "review_sequence")
    workflow.add_conditional_edges(
        "review_sequence", route_sequence,
        {"weighted_graph": "weighted_graph", "sequence_diagram": "sequence_diagram"}
    )

    workflow.add_edge("weighted_graph", "review_graph")
    workflow.add_conditional_edges(
        "review_graph", route_graph,
        {END: END, "weighted_graph": "weighted_graph"}
    )

    workflow.add_edge("chat", END)

    return workflow.compile()