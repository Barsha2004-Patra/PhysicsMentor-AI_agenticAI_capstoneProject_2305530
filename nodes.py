"""
nodes.py — PhysicsMentor AI

10 nodes (exceeds minimum of 8). Each node reads from and writes to MentorState.

NODE MAP:
  memory_node           → Updates history, extracts name, detects difficulty level
  confusion_detector_node  → NEW: detects emotional/conceptual confusion signals
  router_node           → Routes to: retrieve / tool / skip / quiz
  retrieval_node        → Embeds query, fetches top-3 ChromaDB chunks
  skip_node             → Returns empty context for greetings/small-talk
  tool_node             → Runs calculator or formula_checker based on question type
  difficulty_adapter_node → NEW: modifies system prompt style based on difficulty_level
  derivation_node       → NEW: generates step-by-step derivations for "why/derive" queries
  answer_node           → Generates final grounded answer (adapts to difficulty + confusion)
  eval_node             → Self-reflection: scores faithfulness, triggers retry if < 0.7
  save_node             → Appends answer to messages history → END

Why the 3 new nodes?
- confusion_detector_node: the reference never detects student frustration. This node
  routes confused students to gentler, example-first responses.
- difficulty_adapter_node: prevents giving a calculus-heavy derivation to a student who
  asked "why does force change when mass changes?" — same answer, wrong level.
- derivation_node: dedicated to step-by-step physics derivations. When a student asks
  "derive the kinetic energy formula", they need numbered steps with physical intuition
  at each step — not a paragraph answer.
"""

import re
from groq import Groq
from state import MentorState

# ── LLM Client ───────────────────────────────────────────────────────────────
_groq_client = None

def get_llm():
    """Lazy-load Groq client (avoids reloading in Streamlit reruns)."""
    global _groq_client
    if _groq_client is None:
        import os
        _groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    return _groq_client


def call_llm(system_prompt: str, user_message: str, max_tokens: int = 600) -> str:
    """Single-turn LLM call with error handling."""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=max_tokens,
            temperature=0.3,  # Low temperature for factual consistency
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[LLM Error] {str(e)}"


# ── Node 1: memory_node ───────────────────────────────────────────────────────
def memory_node(state: MentorState) -> dict:
    """
    Updates conversation history with the new question.
    Extracts student name if introduced.
    Infers difficulty_level from question phrasing.
    Applies sliding window of 8 messages to prevent token overflow.
    """
    question = state.get("question", "")
    messages = state.get("messages", [])
    student_name = state.get("student_name", None)
    difficulty_level = state.get("difficulty_level", 1)  # Default beginner

    # Append the student's question to history
    messages.append({"role": "user", "content": question})

    # Extract student name from intro patterns
    name_match = re.search(
        r'(?:my name is|i am|i\'m|call me)\s+([A-Z][a-z]+)',
        question, re.IGNORECASE
    )
    if name_match:
        student_name = name_match.group(1).capitalize()

    # Infer difficulty from vocabulary
    advanced_signals = [
        "derive", "derivation", "prove", "proof", "mathematical", "calculus",
        "integral", "differential", "eigenvalue", "tensor", "hamiltonian",
        "lagrangian", "quantum", "relativistic", "wave function"
    ]
    beginner_signals = [
        "what is", "explain simply", "i don't understand", "confusing",
        "basic", "beginner", "simple", "easy way", "for dummies", "eli5"
    ]
    q_lower = question.lower()
    if any(sig in q_lower for sig in advanced_signals):
        difficulty_level = 3
    elif any(sig in q_lower for sig in beginner_signals):
        difficulty_level = 1
    # else: keep existing level (adaptive across conversation)

    # Sliding window: keep last 8 turns (4 exchanges)
    if len(messages) > 8:
        messages = messages[-8:]

    return {
        "messages": messages,
        "student_name": student_name,
        "difficulty_level": difficulty_level,
        "eval_retries": state.get("eval_retries", 0),
    }


# ── Node 2: confusion_detector_node ──────────────────────────────────────────
def confusion_detector_node(state: MentorState) -> dict:
    """
    NEW NODE — Detects whether the student is confused or frustrated.

    Confusion signals:
    - Explicit: "I don't understand", "this doesn't make sense", "I'm lost"
    - Implicit: "wait, but why", "how is that possible", "that's weird"
    - Emotional: "this is so hard", "I give up", "I've been stuck"

    Also detects whether the question is a derivation request.

    Why this node exists:
    The reference project gives the same response style whether the student
    is confidently asking a fact question or desperately confused at 2 AM.
    This node allows the answer_node to shift tone, use analogies first,
    and add a follow-up question to check understanding.
    """
    question = state.get("question", "").lower()

    confusion_patterns = [
        r"don'?t understand",
        r"doesn'?t make sense",
        r"i'?m lost",
        r"i'?m confused",
        r"confus",
        r"not getting",
        r"can'?t figure",
        r"stuck on",
        r"i give up",
        r"makes no sense",
        r"why (?:does|do|would|is|are)",
        r"how is (?:that|this) possible",
        r"that'?s weird",
        r"i thought .+ was",
        r"but (?:then|why|how)",
    ]

    derivation_patterns = [
        r"deriv(?:e|ation|ing)",
        r"prov(?:e|ing|proof)",
        r"how (?:do we|did|does) (?:get|arrive at|derive)",
        r"where does .+ come from",
        r"step.?by.?step",
        r"show me how",
        r"explain the math",
    ]

    confusion_detected = any(
        re.search(pattern, question) for pattern in confusion_patterns
    )
    is_derivation_request = any(
        re.search(pattern, question) for pattern in derivation_patterns
    )

    return {
        "confusion_detected": confusion_detected,
        "is_derivation_request": is_derivation_request,
    }


# ── Node 3: router_node ───────────────────────────────────────────────────────
def router_node(state: MentorState) -> dict:
    """
    Routes the question to the appropriate processing path.
    Routes: retrieve | tool | skip | quiz

    Uses LLM classification with explicit routing criteria.
    The quiz route is new — not in the reference project.
    """
    question = state.get("question", "")
    quiz_active = state.get("quiz_active", False)

    # If quiz is active, check for quiz answer responses
    if quiz_active and re.search(r'^[a-dA-D]$|^[a-dA-D]\)', question.strip()):
        return {"route": "quiz"}

    # Check for quiz activation command
    if re.search(r'quiz me|start quiz|test me|quiz mode', question.lower()):
        return {"route": "quiz"}

    # LLM-based routing
    routing_prompt = """You are a routing classifier for a Physics Study Buddy.
Classify the student's question into EXACTLY ONE of these routes:

- retrieve: physics concept questions, theory questions, formula explanations, derivations
- tool: numerical calculations (contains numbers + arithmetic), formula verification (student states a formula)
- skip: pure greetings, thanks, casual small-talk with no physics content

Reply with ONLY the route word. Nothing else."""

    route = call_llm(routing_prompt, question, max_tokens=10).lower().strip()

    # Sanitise: ensure valid route
    if route not in ["retrieve", "tool", "skip"]:
        route = "retrieve"

    # If derivation is requested, it still uses retrieve path (but derivation_node activates)
    return {"route": route}


# ── Node 4: retrieval_node ────────────────────────────────────────────────────
def retrieval_node(state: MentorState, collection, embedder) -> dict:
    """
    Embeds the question and retrieves top-3 relevant chunks from ChromaDB.
    Returns formatted context string with topic labels.
    """
    question = state.get("question", "")

    try:
        query_embedding = embedder.encode([question]).tolist()
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=3,
            include=["documents", "metadatas", "distances"]
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        # Format context with topic labels
        context_parts = []
        sources = []
        for doc, meta, dist in zip(docs, metas, distances):
            topic = meta.get("topic", "Unknown Topic")
            # Only include if reasonably relevant (cosine distance < 0.8)
            if dist < 0.8:
                context_parts.append(f"[{topic}]\n{doc}")
                sources.append(topic)

        retrieved = "\n\n".join(context_parts) if context_parts else ""
        return {"retrieved": retrieved, "sources": sources}

    except Exception as e:
        return {"retrieved": "", "sources": [], "tool_result": f"[Retrieval Error] {str(e)}"}


# ── Node 5: skip_node ─────────────────────────────────────────────────────────
def skip_node(state: MentorState) -> dict:
    """
    Handles greetings and casual small-talk.
    Returns empty context — answer_node will handle the response.
    """
    return {"retrieved": "", "sources": []}


# ── Node 6: tool_node ─────────────────────────────────────────────────────────
def tool_node(state: MentorState) -> dict:
    """
    Handles two types of tool use:
    1. Numerical calculation — extract and evaluate math expression
    2. Formula checking — detect and verify student-stated formula

    This is more sophisticated than the reference's calculator-only tool.
    """
    from tools import safe_calculator, formula_checker, extract_math_expression, detect_stated_formula

    question = state.get("question", "")
    tool_result = ""
    formula_check = None

    # Check for formula verification request first
    stated_formula = detect_stated_formula(question)
    if stated_formula:
        formula_check = stated_formula
        tool_result = formula_checker(stated_formula)
        return {"tool_result": tool_result, "formula_check": formula_check, "retrieved": ""}

    # Otherwise, try numerical calculation
    expression = extract_math_expression(question)
    if expression:
        result = safe_calculator(expression)
        tool_result = f"Calculation: {expression} = {result}"
    else:
        # Fallback: ask LLM to extract expression
        extract_prompt = """Extract ONLY the mathematical expression from this physics question.
Reply with just the expression (e.g., "0.5 * 2 * 9**2"), nothing else.
If no calculation needed, reply: NONE"""
        extracted = call_llm(extract_prompt, question, max_tokens=30)
        if extracted != "NONE" and extracted and not extracted.startswith("["):
            result = safe_calculator(extracted.strip())
            tool_result = f"Calculation: {extracted.strip()} = {result}"
        else:
            tool_result = "[Tool] No calculable expression found in this question."

    return {"tool_result": tool_result, "formula_check": formula_check, "retrieved": ""}


# ── Node 7: difficulty_adapter_node ──────────────────────────────────────────
def difficulty_adapter_node(state: MentorState) -> dict:
    """
    NEW NODE — Builds a difficulty-adapted system prompt fragment.

    Level 1 (Beginner): Use simple language, everyday analogies, avoid calculus.
                        Start with "Here's an easy way to think about it:"
    Level 2 (Intermediate): Standard explanation with formulas, some derivation.
    Level 3 (Advanced): Full mathematical rigour, derivations from first principles,
                        mention edge cases and limitations.

    This doesn't change retrieved context — it changes how the answer is framed.
    Stored in state as 'difficulty_instruction' used by answer_node and derivation_node.

    Why this node exists:
    Without adaptive difficulty, beginners get overwhelmed by tensor notation
    and advanced students get frustrated by oversimplified analogies.
    """
    difficulty_level = state.get("difficulty_level", 1)
    confusion_detected = state.get("confusion_detected", False)

    if difficulty_level == 1 or confusion_detected:
        style = (
            "TEACHING STYLE: Explain at a beginner level. "
            "Use a real-world everyday analogy first. Keep sentences short. "
            "Avoid calculus notation. Use plain language for formula descriptions. "
            "End your response with a gentle follow-up question to check understanding, "
            "like: 'Does that make sense? Which part would you like me to explain differently?'"
        )
    elif difficulty_level == 2:
        style = (
            "TEACHING STYLE: Explain at an intermediate level. "
            "Show the relevant formula with all symbols defined. "
            "Give one worked example with numbers. "
            "You may reference the derivation briefly but don't fully expand it unless asked."
        )
    else:  # Level 3 advanced
        style = (
            "TEACHING STYLE: Explain at an advanced level. "
            "Derive results from first principles where relevant. "
            "Use proper mathematical notation. "
            "Mention the conditions/assumptions under which the result holds. "
            "Reference connections to other physics topics if relevant."
        )

    # Store as a separate key used by answer_node
    return {"difficulty_instruction": style}


# ── Node 8: derivation_node ───────────────────────────────────────────────────
def derivation_node(state: MentorState) -> dict:
    """
    NEW NODE — Generates step-by-step derivations for 'why/derive' requests.

    Only activates when is_derivation_request = True.
    Produces numbered steps, each with:
      - The mathematical expression at that step
      - Physical intuition for WHY we do this step
      - Units check where relevant

    For non-derivation requests, this node passes through unchanged.

    Why this node exists:
    Derivation is qualitatively different from answering a question.
    A good tutor doesn't just give the result — they walk through WHY each
    manipulation is justified. This requires a dedicated prompt and structure.
    """
    if not state.get("is_derivation_request", False):
        return {"derivation_steps": []}

    question = state.get("question", "")
    retrieved = state.get("retrieved", "")
    difficulty_instruction = state.get("difficulty_instruction", "")

    derivation_prompt = f"""You are a physics tutor generating a step-by-step derivation.

CONTEXT FROM KNOWLEDGE BASE:
{retrieved if retrieved else "No specific context retrieved — use your knowledge of standard physics."}

{difficulty_instruction}

RULES:
1. Number each step clearly: Step 1:, Step 2:, etc.
2. At each step, show the mathematical expression AND explain in plain English why we do this step.
3. Start from the most fundamental principle you can.
4. Check units at the end.
5. Use ONLY information grounded in the context or well-established physics.
6. If you cannot derive it reliably, say so honestly.

Generate the derivation for: {question}"""

    derivation_text = call_llm(
        "You are a rigorous but clear physics tutor who specialises in step-by-step derivations.",
        derivation_prompt,
        max_tokens=800
    )

    # Parse into steps list (for potential UI rendering)
    steps = re.findall(r'Step \d+:.*?(?=Step \d+:|$)', derivation_text, re.DOTALL)
    steps = [s.strip() for s in steps if s.strip()]

    return {
        "derivation_steps": steps,
        "answer": derivation_text  # Also pre-populate answer with derivation
    }


# ── Node 9: answer_node ───────────────────────────────────────────────────────
def answer_node(state: MentorState) -> dict:
    """
    Generates the final student-facing answer.

    Handles four scenarios:
    1. Normal retrieval answer — grounded in retrieved context
    2. Tool result answer — wraps calculator/formula-checker output
    3. Derivation answer — already set by derivation_node, wraps in intro
    4. Greeting answer — friendly response for skip route

    Strict grounding: system prompt forbids the LLM from using general knowledge
    not present in the retrieved context.
    """
    question = state.get("question", "")
    retrieved = state.get("retrieved", "")
    tool_result = state.get("tool_result", "")
    messages = state.get("messages", [])
    student_name = state.get("student_name", None)
    difficulty_instruction = state.get("difficulty_instruction", "")
    confusion_detected = state.get("confusion_detected", False)
    eval_retries = state.get("eval_retries", 0)
    route = state.get("route", "retrieve")
    is_derivation_request = state.get("is_derivation_request", False)

    # If derivation_node already generated the answer, wrap it
    existing_answer = state.get("answer", "")
    if is_derivation_request and existing_answer and not existing_answer.startswith("[LLM Error]"):
        name_prefix = f"Great question, {student_name}! " if student_name else ""
        return {"answer": name_prefix + existing_answer}

    # Build conversation history string (last 4 turns for context)
    history_str = ""
    if len(messages) > 1:
        recent = messages[-5:-1]  # Exclude the current question we just added
        history_str = "\n".join(
            f"{'Student' if m['role'] == 'user' else 'Tutor'}: {m['content']}"
            for m in recent
        )

    # Handle greeting/skip route
    if route == "skip" or (not retrieved and not tool_result):
        name_part = f", {student_name}" if student_name else ""
        return {
            "answer": (
                f"Hello{name_part}! I'm PhysicsMentor AI — your personal physics tutor. "
                f"I can explain physics concepts, walk through step-by-step derivations, "
                f"check formulas you've written, and help with numerical problems. "
                f"Which physics topic are you working on today?"
            )
        }

    # Escalation instruction for retries
    retry_instruction = ""
    if eval_retries > 0:
        retry_instruction = (
            "\n\nIMPORTANT: Your previous answer scored below 0.7 for faithfulness. "
            "This retry must ONLY use facts explicitly stated in the CONTEXT below. "
            "If the context does not contain the answer, say so directly."
        )

    # Build the grounded system prompt
    system_prompt = f"""You are PhysicsMentor AI — a personal physics tutor for B.Tech students.

STRICT GROUNDING RULE: Answer ONLY from the CONTEXT provided below.
Do NOT use general knowledge, internet knowledge, or information not in the context.
If the context does not contain enough information to answer, say:
"I don't have enough information on that in my knowledge base. Please check your textbook or ask your professor."

{difficulty_instruction}

CONTEXT FROM KNOWLEDGE BASE:
{retrieved if retrieved else "(No retrieval context — see tool result below)"}

TOOL RESULT:
{tool_result if tool_result else "(No tool used for this question)"}

RECENT CONVERSATION:
{history_str if history_str else "(First message)"}

{retry_instruction}

ADDITIONAL RULES:
- Address the student by name ({student_name}) if you know it.
- Never invent formulas. Write them exactly as they appear in the context.
- If confusion was detected (student seems lost), start with an everyday analogy before the formula.
- Keep your answer focused and complete. Do not pad with unnecessary filler."""

    # Confusion adjustment
    if confusion_detected:
        user_message = (
            f"The student seems confused. Start with a real-world analogy, then explain simply.\n"
            f"Student's question: {question}"
        )
    else:
        user_message = question

    answer = call_llm(system_prompt, user_message, max_tokens=600)
    return {"answer": answer}


# ── Node 10: eval_node ────────────────────────────────────────────────────────
def eval_node(state: MentorState) -> dict:
    """
    Self-reflection: scores answer faithfulness against retrieved context.

    Faithfulness = the fraction of facts in the answer that are supported
    by the retrieved context. Score range: 0.0 to 1.0.

    If score < 0.7 AND eval_retries < 2: triggers a retry via answer_node.
    If score >= 0.7 OR retries exhausted: proceeds to save_node.

    Skips evaluation for:
    - Skip/greeting routes (no context to check against)
    - Tool-only results (not LLM-generated facts)
    """
    answer = state.get("answer", "")
    retrieved = state.get("retrieved", "")
    route = state.get("route", "retrieve")
    eval_retries = state.get("eval_retries", 0)

    # Skip evaluation for non-retrieval paths
    if route in ["skip"] or not retrieved or not answer:
        return {"faithfulness": 1.0, "eval_retries": eval_retries}

    eval_prompt = """You are a faithfulness evaluator for a physics tutoring system.

Score how faithfully the ANSWER uses only information from the CONTEXT.

Rules:
- Score 1.0: Every factual claim in the answer is directly supported by the context.
- Score 0.7-0.9: Most claims are from context; minor extrapolation present.
- Score 0.4-0.6: Some claims come from outside the context.
- Score 0.0-0.3: Answer contains significant unsupported or hallucinated facts.

Reply with ONLY a decimal number between 0.0 and 1.0. Nothing else."""

    eval_input = f"CONTEXT:\n{retrieved}\n\nANSWER:\n{answer}"
    score_str = call_llm(eval_prompt, eval_input, max_tokens=10)

    # Parse score safely
    try:
        score_match = re.search(r'0?\.\d+|1\.0|1', score_str)
        faithfulness = float(score_match.group(0)) if score_match else 0.5
        faithfulness = max(0.0, min(1.0, faithfulness))
    except Exception:
        faithfulness = 0.5  # Conservative default on parse failure

    print(f"[eval_node] Faithfulness score: {faithfulness:.2f} (retry #{eval_retries})")

    return {
        "faithfulness": faithfulness,
        "eval_retries": eval_retries + 1
    }


# ── Node 11: save_node ────────────────────────────────────────────────────────
def save_node(state: MentorState) -> dict:
    """
    Appends the final answer to conversation history.
    This is the last node before END.
    """
    messages = state.get("messages", [])
    answer = state.get("answer", "")

    messages.append({"role": "assistant", "content": answer})

    # Keep sliding window
    if len(messages) > 8:
        messages = messages[-8:]

    return {"messages": messages}
