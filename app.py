"""
app.py — PhysicsMentor AI — Streamlit Interfa

Features:
- Chat interface with physics-themed styling
- Sidebar: topic list, difficulty indicator, session stats
- Supports derivation mode display (numbered steps)
- Formula checker results shown with ⚠️ / ✅ icons
- New Conversation button resets thread_id
- All expensive initialisations in @st.cache_resource

Run: streamlit run app.py
"""

import streamlit as st
import uuid
import os

# ── Page Config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="PhysicsMentor AI",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Cache heavy resources (LLM, embedder, ChromaDB, graph) ───────────────────
@st.cache_resource
def load_system():
    """
    Load all expensive components once and cache them.
    Re-used across all Streamlit reruns.
    """
    from data import build_knowledge_base
    from graph import build_graph

    collection, embedder = build_knowledge_base()
    app = build_graph(collection, embedder)
    return app


# ── Session State Init ────────────────────────────────────────────────────────
def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []  # Chat display history
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "session_stats" not in st.session_state:
        st.session_state.session_stats = {
            "questions_asked": 0,
            "derivations_done": 0,
            "formulas_checked": 0,
            "avg_faithfulness": [],
        }
    if "difficulty_level" not in st.session_state:
        st.session_state.difficulty_level = 1


init_session()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚛️ PhysicsMentor AI")
    st.markdown("*Your adaptive physics tutor*")
    st.markdown("---")

    # New conversation button
    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.session_stats = {
            "questions_asked": 0,
            "derivations_done": 0,
            "formulas_checked": 0,
            "avg_faithfulness": [],
        }
        st.session_state.difficulty_level = 1
        st.rerun()

    st.markdown("### 📚 Topics Covered")
    topics = [
        "Newton's Laws of Motion",
        "Work, Energy & Power",
        "Laws of Thermodynamics",
        "Electric Current & Ohm's Law",
        "Capacitors & Capacitance",
        "Magnetic Force & Faraday's Law",
        "Wave Motion & Sound",
        "Optics — Reflection & Refraction",
        "Modern Physics & Photoelectric Effect",
        "Circular Motion & Gravitation",
        "Simple Harmonic Motion",
        "Fluid Mechanics & Bernoulli",
    ]
    for topic in topics:
        st.markdown(f"• {topic}")

    st.markdown("---")
    st.markdown("### 📊 Session Stats")

    # Difficulty level indicator
    level = st.session_state.difficulty_level
    level_labels = {1: "🟢 Beginner", 2: "🟡 Intermediate", 3: "🔴 Advanced"}
    st.markdown(f"**Difficulty Level:** {level_labels.get(level, '🟢 Beginner')}")

    stats = st.session_state.session_stats
    st.markdown(f"**Questions Asked:** {stats['questions_asked']}")
    st.markdown(f"**Derivations Done:** {stats['derivations_done']}")
    st.markdown(f"**Formulas Checked:** {stats['formulas_checked']}")

    if stats['avg_faithfulness']:
        avg = sum(stats['avg_faithfulness']) / len(stats['avg_faithfulness'])
        st.markdown(f"**Avg Faithfulness:** {avg:.2f}")

    st.markdown("---")
    st.markdown("### 💡 Try asking:")
    st.markdown("*\"I don't understand why energy is conserved when a ball falls\"*")
    st.markdown("*\"Derive the kinetic energy formula from scratch\"*")
    st.markdown("*\"So KE = mv², right?\"*")
    st.markdown("*\"Calculate KE if mass is 3 kg and velocity is 4 m/s\"*")


# ── Main Chat Area ────────────────────────────────────────────────────────────
st.markdown("## ⚛️ PhysicsMentor AI")
st.markdown("*Ask me anything from your B.Tech Physics syllabus. I adapt to your level.*")
st.markdown("---")

# Display chat history
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]

    if role == "user":
        with st.chat_message("user", avatar="🎓"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="⚛️"):
            # Check for formula check result (show with icon styling)
            if "⚠️ Formula Check" in content:
                st.warning(content)
            elif "✅ Correct!" in content:
                st.success(content)
            # Check for derivation (show steps in expander if long)
            elif content.count("Step") >= 3:
                # Show first paragraph, then steps in expander
                lines = content.split("\n")
                intro_lines = [l for l in lines[:3] if l.strip()]
                step_content = content
                if intro_lines:
                    st.markdown(" ".join(intro_lines[:2]))
                with st.expander("📐 View Step-by-Step Derivation", expanded=True):
                    st.markdown(step_content)
            else:
                st.markdown(content)

            # Show metadata tags if available
            if msg.get("metadata"):
                meta = msg["metadata"]
                cols = st.columns(3)
                if meta.get("route"):
                    cols[0].caption(f"🔀 Route: {meta['route']}")
                if meta.get("faithfulness") is not None:
                    cols[1].caption(f"✔️ Faithfulness: {meta['faithfulness']:.2f}")
                if meta.get("sources"):
                    cols[2].caption(f"📖 {', '.join(meta['sources'][:2])}")


# ── Chat Input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask a physics question... (e.g., 'I don't get how waves carry energy')")

if user_input and user_input.strip():
    # Immediately show user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user", avatar="🎓"):
        st.markdown(user_input)

    # Run the graph
    with st.chat_message("assistant", avatar="⚛️"):
        with st.spinner("PhysicsMentor is thinking..."):
            try:
                app = load_system()

                # Build initial state from session
                from graph import ask
                result = ask(app, user_input, thread_id=st.session_state.thread_id)

                answer = result.get("answer", "I encountered an error. Please try again.")
                faithfulness = result.get("faithfulness", 0.0)
                route = result.get("route", "retrieve")
                sources = result.get("sources", [])
                difficulty = result.get("difficulty_level", 1)
                formula_check = result.get("formula_check", None)
                is_derivation = result.get("is_derivation_request", False)

                # Update session state
                st.session_state.difficulty_level = difficulty
                st.session_state.session_stats["questions_asked"] += 1
                st.session_state.session_stats["avg_faithfulness"].append(faithfulness)
                if is_derivation:
                    st.session_state.session_stats["derivations_done"] += 1
                if formula_check:
                    st.session_state.session_stats["formulas_checked"] += 1

                # Display answer
                if "⚠️ Formula Check" in answer:
                    st.warning(answer)
                elif "✅ Correct!" in answer:
                    st.success(answer)
                elif answer.count("Step") >= 3:
                    lines = answer.split("\n")
                    intro = " ".join([l for l in lines[:2] if l.strip()])
                    if intro:
                        st.markdown(intro)
                    with st.expander("📐 View Step-by-Step Derivation", expanded=True):
                        st.markdown(answer)
                else:
                    st.markdown(answer)

                # Metadata display
                meta_cols = st.columns(3)
                meta_cols[0].caption(f"🔀 Route: {route}")
                if faithfulness > 0:
                    meta_cols[1].caption(f"✔️ Faithfulness: {faithfulness:.2f}")
                if sources:
                    meta_cols[2].caption(f"📖 {', '.join(sources[:2])}")

                # Save to session messages with metadata
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "metadata": {
                        "route": route,
                        "faithfulness": faithfulness,
                        "sources": sources,
                    }
                })

            except Exception as e:
                error_msg = f"⚠️ System error: {str(e)}\n\nPlease check your GROQ_API_KEY is set."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "metadata": {}
                })

    st.rerun()
