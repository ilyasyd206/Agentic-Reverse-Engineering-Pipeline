
import json
import os
import time
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from src.prompt_template import (
    TEXT_DOC_PROMPT,
    CLASS_DIAGRAM_PROMPT,
    SEQUENCE_DIAGRAM_PROMPT,
    WEIGHTED_GRAPH_PROMPT,
    REVIEWER_PROMPT
)

google_api_key = os.getenv("GOOGLE_API_KEY")

# --- Ініціалізація Агентів ---
llm_generator = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    google_api_key=google_api_key,
    temperature=0.2,
    transport="rest",
    timeout=60
)

# Рецензент з температурою 0.0 pre maximalnu presnost
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

    # Змінні для циклів Reviewera
    class_critique: str
    class_iteration: int
    seq_critique: str
    seq_iteration: int
    graph_critique: str
    graph_iteration: int


# --- 2. ВУЗЛИ ГЕНЕРАТОРІВ ТА РЕЦЕНЗЕНТІВ ---

def text_doc_node(state: AgentState):
    print("--- PIPELINE: GENERÁCIA TEXTOVEJ DOKUMENTÁCIE ---")
    chat_history = "\n".join(
        [f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" for m in state["messages"][-4:]])
    enriched_query = f"Kontext rozhovoru:\n{chat_history}\n\nAktuálna požiadavka: {state['query']}"

    prompt_text = TEXT_DOC_PROMPT.format(query=enriched_query, context_code=state["context_code"][:5000])
    response = llm_generator.invoke([HumanMessage(content=prompt_text)])

    time.sleep(5)  # Rate limit protection
    return {"doc_text": response.content}


# --- CLASS DIAGRAM LOOP ---
def class_diagram_node(state: AgentState):
    iteration = state.get("class_iteration", 0)
    print(f"--- PIPELINE: GENERÁCIA CLASS DIAGRAM (Iterácia {iteration + 1}/3) ---")
    chat_history = "\n".join(
        [f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" for m in state["messages"][-4:]])
    enriched_query = f"Kontext rozhovoru:\n{chat_history}\n\nAktuálna požiadavka: {state['query']}"

    prompt_text = CLASS_DIAGRAM_PROMPT.format(
        query=enriched_query,
        critique=state.get("class_critique", ""),
        context_code=state["context_code"][:5000]
    )
    response = llm_generator.invoke([HumanMessage(content=prompt_text)])

    time.sleep(5)
    return {"diagram_class": response.content, "class_iteration": iteration + 1}


def review_class_node(state: AgentState):
    print("--- REVIEWER: KONTROLA CLASS DIAGRAMU ---")
    prompt = REVIEWER_PROMPT.format(uml_code=state["diagram_class"])
    response = llm_reviewer.invoke([HumanMessage(content=prompt)])
    print(f"Verdict: {response.content[:50]}...")

    time.sleep(5)
    return {"class_critique": response.content}


# --- SEQUENCE DIAGRAM LOOP ---
def sequence_diagram_node(state: AgentState):
    iteration = state.get("seq_iteration", 0)
    print(f"--- PIPELINE: GENERÁCIA SEQUENCE DIAGRAM (Iterácia {iteration + 1}/3) ---")
    chat_history = "\n".join(
        [f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" for m in state["messages"][-4:]])
    enriched_query = f"Kontext rozhovoru:\n{chat_history}\n\nAktuálna požiadavka: {state['query']}"

    prompt_text = SEQUENCE_DIAGRAM_PROMPT.format(
        query=enriched_query,
        critique=state.get("seq_critique", ""),
        context_code=state["context_code"][:5000]
    )
    response = llm_generator.invoke([HumanMessage(content=prompt_text)])

    time.sleep(5)  # RATE LIMIT PROTECTION
    return {"diagram_sequence": response.content, "seq_iteration": iteration + 1}


def review_sequence_node(state: AgentState):
    print("--- REVIEWER: KONTROLA SEQUENCE DIAGRAMU ---")
    prompt = REVIEWER_PROMPT.format(uml_code=state["diagram_sequence"])
    response = llm_reviewer.invoke([HumanMessage(content=prompt)])
    print(f"Verdict: {response.content[:50]}...")

    time.sleep(5)
    return {"seq_critique": response.content}


# --- WEIGHTED GRAPH LOOP ---
def weighted_graph_node(state: AgentState):
    iteration = state.get("graph_iteration", 0)
    print(f"--- PIPELINE: GENERÁCIA VÁŽENÉHO GRAFU (Iterácia {iteration + 1}/3) ---")
    chat_history = "\n".join(
        [f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" for m in state["messages"][-4:]])
    enriched_query = f"Kontext rozhovoru:\n{chat_history}\n\nAktuálna požiadavka: {state['query']}"

    prompt_text = WEIGHTED_GRAPH_PROMPT.format(
        query=enriched_query,
        critique=state.get("graph_critique", ""),
        context_code=state["context_code"][:5000]
    )
    response = llm_generator.invoke([HumanMessage(content=prompt_text)])

    time.sleep(5)
    return {"diagram_weighted_graph": response.content, "graph_iteration": iteration + 1}


def review_graph_node(state: AgentState):
    print("--- REVIEWER: KONTROLA VÁŽENÉHO GRAFU ---")
    prompt = REVIEWER_PROMPT.format(uml_code=state["diagram_weighted_graph"])
    response = llm_reviewer.invoke([HumanMessage(content=prompt)])
    print(f"Verdict: {response.content[:50]}...")

    time.sleep(5)
    return {"graph_critique": response.content}


def chat_node(state: AgentState):
    print("--- PRÁCA V REŽIME CHATU ---")
    response = llm_generator.invoke(state["messages"])
    return {"messages": [AIMessage(content=response.content)]}


# --- 3. ROUTERY ---

def main_router(state: AgentState):
    last_message = state["messages"][-1].content.lower()
    trigger_words = ["dokumentáci", "zgeneruj", "vytvor", "pipeline", "generate"]
    if any(word in last_message for word in trigger_words):
        print("-> SPUSTENIE ÚPLNÉHO PIPELINU DOKUMENTÁCIE")
        return "text_doc"
    else:
        print("-> BEŽNÁ ODPOVEĎ CHATU")
        return "chat"


def check_verdict(critique_json: str) -> bool:
    """Parsuje JSON od Reviewera a kontroluje, či verdict == APPROVE"""
    if not critique_json:
        return False
    try:
        clean_json = critique_json.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        return data.get("verdict", "").upper() == "APPROVE"
    except json.JSONDecodeError:
        print(f"⚠️ Chyba parsovania JSON od Reviewera: {critique_json}")
        return "APPROVE" in critique_json.upper()


def route_class(state: AgentState):
    if check_verdict(state.get("class_critique", "")) or state.get("class_iteration", 0) >= 3:
        return "sequence_diagram"
    print("-> CHYBA V CLASS DIAGRAME (Metriky nesplnené), GENERUJEM ZNOVA...")
    return "class_diagram"


def route_sequence(state: AgentState):
    if check_verdict(state.get("seq_critique", "")) or state.get("seq_iteration", 0) >= 3:
        return "weighted_graph"
    print("-> CHYBA V SEQUENCE DIAGRAME (Metriky nesplnené), GENERUJEM ZNOVA...")
    return "sequence_diagram"


def route_graph(state: AgentState):
    if check_verdict(state.get("graph_critique", "")) or state.get("graph_iteration", 0) >= 3:
        return END
    print("-> CHYBA VO VÁŽENOM GRAFE (Metriky nesplnené), GENERUJEM ZNOVA...")
    return "weighted_graph"


# --- 4. ZOSTAVENIE GRAFU ---
def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("text_doc", text_doc_node)
    workflow.add_node("class_diagram", class_diagram_node)
    workflow.add_node("review_class", review_class_node)
    workflow.add_node("sequence_diagram", sequence_diagram_node)
    workflow.add_node("review_sequence", review_sequence_node)
    workflow.add_node("weighted_graph", weighted_graph_node)
    workflow.add_node("review_graph", review_graph_node)
    workflow.add_node("chat", chat_node)

    workflow.set_conditional_entry_point(main_router, {"text_doc": "text_doc", "chat": "chat"})

    workflow.add_edge("text_doc", "class_diagram")
    workflow.add_edge("class_diagram", "review_class")
    workflow.add_conditional_edges("review_class", route_class,
                                   {"sequence_diagram": "sequence_diagram", "class_diagram": "class_diagram"})

    workflow.add_edge("sequence_diagram", "review_sequence")
    workflow.add_conditional_edges("review_sequence", route_sequence,
                                   {"weighted_graph": "weighted_graph", "sequence_diagram": "sequence_diagram"})

    workflow.add_edge("weighted_graph", "review_graph")
    workflow.add_conditional_edges("review_graph", route_graph, {END: END, "weighted_graph": "weighted_graph"})

    workflow.add_edge("chat", END)

    return workflow.compile()