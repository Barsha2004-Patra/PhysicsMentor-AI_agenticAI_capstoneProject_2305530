"""
graph.py — PhysicsMentor AI

Assembles the LangGraph StateGraph with 10 nodes and conditional routing.

GRAPH FLOW:
  memory → confusion_detector → router →
    [retrieve]  → retrieval → difficulty_adapter → derivation → answer → eval → save → END
    [tool]      → tool → difficulty_adapter → answer → eval → save → END
    [skip]      → skip → answer → eval → save → END
    [quiz]      → (future: quiz_node) → answer → eval → save → END

  eval_decision:
    faithfulness >= 0.7 OR eval_retries >= 2  → save
    faithfulness < 0.7 AND eval_retries < 2   → answer (retry)

Design note: difficulty_adapter runs BEFORE derivation and answer nodes
so both can use the difficulty instruction. It runs AFTER retrieval so
it has access to the retrieved context level.
"""

from functools import partial
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import MentorState
from nodes import (
    memory_node,
    confusion_detector_node,
    router_node,
    retrieval_node,
    skip_node,
    tool_node,
    difficulty_adapter_node,
    derivation_node,
    answer_node,
    eval_node,
    save_node,
)
from data import build_knowledge_base


def route_decision(state: MentorState) -> str:
    """
    Conditional edge function after router_node.
    Returns: "retrieve" | "tool" | "skip" | "quiz"
    """
    return state.get("route", "retrieve")


def eval_decision(state: MentorState) -> str:
    """
    Conditional edge function after eval_node.
    Returns: "answer" (retry) | "save" (pass)

    Retry when:
    - faithfulness < 0.7
    - eval_retries < 2 (max 2 retries to prevent infinite loops)
    """
    faithfulness = state.get("faithfulness", 1.0)
    eval_retries = state.get("eval_retries", 0)
    MAX_RETRIES = 2

    if faithfulness < 0.7 and eval_retries < MAX_RETRIES:
        print(f"[graph] Low faithfulness ({faithfulness:.2f}), triggering retry #{eval_retries}")
        return "answer"
    return "save"


def build_graph(collection, embedder):
    """
    Builds and compiles the PhysicsMentor AI LangGraph.

    Uses functools.partial to inject collection and embedder into
    retrieval_node (they're loaded once at startup and reused).

    Returns the compiled app with MemorySaver checkpointing.
    """
    # Bind KB dependencies to retrieval_node
    bound_retrieval = partial(retrieval_node, collection=collection, embedder=embedder)

    # ── Graph instantiation ──────────────────────────────────────────────────
    graph = StateGraph(MentorState)

    # ── Add all 10 nodes ─────────────────────────────────────────────────────
    graph.add_node("memory", memory_node)
    graph.add_node("confusion_detector", confusion_detector_node)
    graph.add_node("router", router_node)
    graph.add_node("retrieval", bound_retrieval)
    graph.add_node("skip", skip_node)
    graph.add_node("tool", tool_node)
    graph.add_node("difficulty_adapter", difficulty_adapter_node)
    graph.add_node("derivation", derivation_node)
    graph.add_node("answer", answer_node)
    graph.add_node("eval", eval_node)
    graph.add_node("save", save_node)

    # ── Entry point ──────────────────────────────────────────────────────────
    graph.set_entry_point("memory")

    # ── Fixed edges ──────────────────────────────────────────────────────────
    graph.add_edge("memory", "confusion_detector")
    graph.add_edge("confusion_detector", "router")

    # After retrieval/skip/tool → difficulty_adapter
    graph.add_edge("retrieval", "difficulty_adapter")
    graph.add_edge("skip", "difficulty_adapter")
    graph.add_edge("tool", "difficulty_adapter")

    # After difficulty_adapter → derivation (which may pass through)
    graph.add_edge("difficulty_adapter", "derivation")

    # After derivation → answer
    graph.add_edge("derivation", "answer")

    # After answer → eval
    graph.add_edge("answer", "eval")

    # After save → END
    graph.add_edge("save", END)

    # ── Conditional edges ────────────────────────────────────────────────────
    # After router: route to retrieve / tool / skip
    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "retrieve": "retrieval",
            "tool": "tool",
            "skip": "skip",
            "quiz": "skip",  # Quiz falls back to skip for now
        }
    )

    # After eval: retry answer or proceed to save
    graph.add_conditional_edges(
        "eval",
        eval_decision,
        {
            "answer": "answer",  # Retry path
            "save": "save",      # Pass path
        }
    )

    # ── Compile with MemorySaver ──────────────────────────────────────────────
    checkpointer = MemorySaver()
    app = graph.compile(checkpointer=checkpointer)

    print("✅ PhysicsMentor AI graph compiled successfully.")
    return app


def ask(app, question: str, thread_id: str = "default_session") -> dict:
    """
    Helper function to invoke the graph with a question.
    Returns the full final state.

    Args:
        app: compiled LangGraph app
        question: student's question string
        thread_id: session identifier for MemorySaver

    Returns:
        dict with keys: answer, faithfulness, route, sources, difficulty_level
    """
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "question": question,
        "messages": [],
        "route": "retrieve",
        "confusion_detected": False,
        "is_derivation_request": False,
        "difficulty_level": 1,
        "student_name": None,
        "retrieved": "",
        "sources": [],
        "tool_result": "",
        "formula_check": None,
        "answer": "",
        "derivation_steps": [],
        "faithfulness": 0.0,
        "eval_retries": 0,
        "quiz_active": False,
        "quiz_score": 0,
        "quiz_question_count": 0,
        "difficulty_instruction": "",
    }

    result = app.invoke(initial_state, config=config)
    return result
