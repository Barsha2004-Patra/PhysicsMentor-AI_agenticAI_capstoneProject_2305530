"""
state.py — PhysicsMentor AI
Defines the shared TypedDict that every node reads from and writes to.
State is designed FIRST, before any node, to prevent KeyError bugs.

Design rationale:
- difficulty_level (1-3): enables adaptive explanations without re-asking the student
- confusion_detected (bool): routes confused students to a gentler, example-first path
- is_derivation_request (bool): routes "why/how to derive" to step-by-step derivation node
- formula_check: stores student-stated formula for verification
- quiz_active / quiz_score: supports stateful quiz mode within a session
"""

from typing import TypedDict, List, Optional


class MentorState(TypedDict):
    # Core input
    question: str                      # The student's current question

    # Conversation memory (sliding window applied in memory_node)
    messages: List[dict]               # Full turn history: [{role, content}, ...]

    # Routing signals (set by router_node and classifier nodes)
    route: str                         # "retrieve" | "tool" | "skip" | "quiz"
    confusion_detected: bool           # True if student seems confused/frustrated
    is_derivation_request: bool        # True if student asks "why" or "derive"

    # Difficulty adaptation (1=beginner, 2=intermediate, 3=advanced)
    difficulty_level: int              # Inferred from question phrasing
    student_name: Optional[str]        # Extracted from intro messages

    # Retrieval results
    retrieved: str                     # Formatted context from ChromaDB
    sources: List[str]                 # Topic labels of retrieved chunks

    # Tool results
    tool_result: str                   # Output from calculator or formula_checker
    formula_check: Optional[str]       # Student-stated formula to verify

    # Answer generation
    answer: str                        # Final answer to return to student
    derivation_steps: List[str]        # Populated only during derivation requests

    # Self-reflection evaluation
    faithfulness: float                # Score 0.0–1.0 from eval_node
    eval_retries: int                  # Counter to prevent infinite retry loops

    # Quiz mode (stateful across turns)
    quiz_active: bool                  # Whether quiz mode is running
    quiz_score: int                    # Running score in current quiz session
    quiz_question_count: int           # How many quiz questions asked so far
