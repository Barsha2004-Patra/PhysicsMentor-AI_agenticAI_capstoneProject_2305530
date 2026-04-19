"""
tools.py — PhysicsMentor AI

Two tools:
1. safe_calculator   — evaluates numerical physics expressions
2. formula_checker   — checks a student-stated formula against the knowledge base

Design decision: formula_checker is the key differentiator.
When a student says "so E = mgh² right?", the reference project would just answer
their next question. This system catches the error, explains what's wrong, and
shows the correct form. This is what a real tutor does.

Both tools NEVER raise exceptions — they return error strings so the graph
continues cleanly even on bad input.
"""

import math
import re
from typing import Optional


# ── Whitelist of safe names for the calculator sandbox ──────────────────────
SAFE_MATH_NAMESPACE = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
    "tan": math.tan, "pi": math.pi, "e": math.e,
    "log": math.log, "log10": math.log10, "exp": math.exp,
    "pow": pow, "ceil": math.ceil, "floor": math.floor,
}


def safe_calculator(expression: str) -> str:
    """
    Safely evaluate a mathematical physics expression.
    Returns the numeric result as a string, or a descriptive error.

    Examples:
        "0.5 * 2 * 9**2"        → "81.0"
        "9.8 * 5 * 10"          → "490.0"
        "import os; os.system()" → "[Error] Unsafe expression."
    """
    # Reject any expression with dangerous keywords
    danger_patterns = [
        "import", "exec", "eval", "open", "os.", "sys.", "__",
        "subprocess", "globals", "locals", "getattr", "setattr"
    ]
    expr_lower = expression.lower()
    for pattern in danger_patterns:
        if pattern in expr_lower:
            return "[Error] Unsafe expression — only math operations allowed."

    # Allow only safe characters: digits, operators, parentheses, dots, spaces
    if not re.match(r'^[\d\s\+\-\*\/\.\(\)\^eE]+$', expression.replace("sqrt", "")
                                                                .replace("sin", "")
                                                                .replace("cos", "")
                                                                .replace("tan", "")
                                                                .replace("log", "")
                                                                .replace("exp", "")
                                                                .replace("pi", "")
                                                                .replace("abs", "")
                                                                .replace("pow", "")
                                                                .replace(",", "")):
        # Try anyway — the sandbox will catch it
        pass

    try:
        # Replace ^ with ** for user convenience (physics notation)
        clean_expr = expression.replace("^", "**")
        result = eval(clean_expr, {"__builtins__": {}}, SAFE_MATH_NAMESPACE)
        # Round to 4 significant figures for readability
        if isinstance(result, float):
            return f"{result:.4g}"
        return str(result)
    except ZeroDivisionError:
        return "[Error] Division by zero."
    except Exception as e:
        return f"[Error] Could not evaluate expression: {str(e)}"


# ── Known physics formulas for the formula checker ──────────────────────────
# Format: (canonical_formula, common_mistakes, explanation)
FORMULA_DATABASE = {
    "kinetic_energy": {
        "correct": "KE = (1/2) * m * v²",
        "symbol": "KE",
        "common_errors": ["KE = mv²", "KE = mv", "KE = 2mv²", "E = mv²"],
        "explanation": (
            "Kinetic energy is KE = ½mv². The factor of ½ comes from integrating "
            "F = ma over displacement. Without the ½, you overcount by exactly 2×. "
            "This is derived from the work-energy theorem: W = ∫F·dx = ∫ma·dx = ½mv²."
        )
    },
    "potential_energy": {
        "correct": "PE = m * g * h",
        "symbol": "PE",
        "common_errors": ["PE = mgh²", "PE = mg²h", "E = mgh²"],
        "explanation": (
            "Gravitational potential energy is PE = mgh. Height h appears once — "
            "it's a linear relationship. If you square h, the units become m²·J/m = J·m, "
            "which has wrong dimensions."
        )
    },
    "newton_second": {
        "correct": "F = m * a",
        "symbol": "F",
        "common_errors": ["F = ma²", "F = m²a", "a = Fm"],
        "explanation": (
            "Newton's Second Law: F = ma. Force equals mass times acceleration. "
            "If you write F = ma², the units become kg·(m/s²)² = kg·m/s⁴, not Newtons."
        )
    },
    "ohms_law": {
        "correct": "V = I * R",
        "symbol": "V",
        "common_errors": ["V = IR²", "I = VR", "R = IV"],
        "explanation": (
            "Ohm's Law: V = IR. Voltage equals current times resistance. "
            "A common error is writing I = VR — the correct rearrangement is I = V/R."
        )
    },
    "wave_speed": {
        "correct": "v = f * λ",
        "symbol": "v",
        "common_errors": ["v = f/λ", "v = λ/f", "f = vλ"],
        "explanation": (
            "Wave speed: v = fλ. Speed equals frequency times wavelength. "
            "Think of it as: each second, f wavefronts pass, each of length λ, "
            "so total distance covered per second = fλ."
        )
    },
    "coulombs_law": {
        "correct": "F = k * q1 * q2 / r²",
        "symbol": "F_coulomb",
        "common_errors": ["F = kq1q2/r", "F = kq1q2r²"],
        "explanation": (
            "Coulomb's Law: F = kq₁q₂/r². Force falls off as r² (inverse-square), "
            "not r. The inverse-square relationship is fundamental to central force laws "
            "in 3D space."
        )
    },
}


def formula_checker(student_formula: str) -> str:
    """
    Check a student-stated formula for correctness.
    Returns a corrective explanation if the formula is wrong,
    or a confirmation if it's correct.

    The agent calls this when it detects patterns like:
    "so the formula is...", "KE = ...", "isn't it F = ..."
    """
    if not student_formula or len(student_formula.strip()) < 3:
        return "[Formula Check] No clear formula detected to verify."

    student_lower = student_formula.lower().replace(" ", "")
    result_parts = []

    for concept, data in FORMULA_DATABASE.items():
        correct_normalized = data["correct"].lower().replace(" ", "")

        # Check if student stated the correct formula
        if correct_normalized in student_lower or student_lower in correct_normalized:
            result_parts.append(
                f"✅ Correct! {data['correct']} — your formula is right."
            )
            break

        # Check against known errors for this concept
        for error in data["common_errors"]:
            error_norm = error.lower().replace(" ", "")
            if error_norm in student_lower or student_lower in error_norm:
                result_parts.append(
                    f"⚠️ Formula Check — Not quite!\n"
                    f"You wrote: {student_formula}\n"
                    f"Correct form: {data['correct']}\n\n"
                    f"Why: {data['explanation']}"
                )
                return "\n".join(result_parts)

    if not result_parts:
        return (
            f"[Formula Check] I couldn't match '{student_formula}' to a known formula "
            f"in the knowledge base. Please double-check with your textbook, or ask me "
            f"to explain the concept and I'll show you the correct formula."
        )

    return "\n".join(result_parts)


def extract_math_expression(question: str) -> Optional[str]:
    """
    Extract a calculable math expression from a natural language question.
    Returns the expression string, or None if nothing calculable found.

    Examples:
        "what is 5 * 9.8 * 10" → "5 * 9.8 * 10"
        "force if mass is 3 kg and acceleration is 4 m/s²" → "3 * 4"
    """
    # Direct numeric expression pattern
    expr_pattern = re.search(
        r'[\d\.]+\s*[\+\-\*\/\^]\s*[\d\.]+(?:\s*[\+\-\*\/\^]\s*[\d\.]+)*',
        question
    )
    if expr_pattern:
        return expr_pattern.group(0).strip()

    # "mass is X kg and acceleration is Y" → X * Y
    mass_accel = re.search(
        r'mass\s+(?:is|of|=)?\s*([\d\.]+).*?acceleration\s+(?:is|of|=)?\s*([\d\.]+)',
        question, re.IGNORECASE
    )
    if mass_accel:
        return f"{mass_accel.group(1)} * {mass_accel.group(2)}"

    # "velocity X and mass Y" for KE
    ke_pattern = re.search(
        r'(?:velocity|speed)\s+(?:is|of|=)?\s*([\d\.]+).*?mass\s+(?:is|of|=)?\s*([\d\.]+)',
        question, re.IGNORECASE
    )
    if ke_pattern:
        v = float(ke_pattern.group(1))
        m = float(ke_pattern.group(2))
        return f"0.5 * {m} * {v}**2"

    return None


def detect_stated_formula(question: str) -> Optional[str]:
    """
    Detect when a student states a formula in their question.
    Returns the formula portion, or None.

    Examples:
        "so KE = mv² right?" → "KE = mv²"
        "isn't the formula F = ma²?" → "F = ma²"
    """
    formula_pattern = re.search(
        r'(?:formula\s+is|so|right\?|isn\'t\s+it|means|equals?\s+)?\s*'
        r'([A-Za-z_]+\s*=\s*[\w\s\*\/\+\-\^\(\)]+)',
        question, re.IGNORECASE
    )
    if formula_pattern:
        candidate = formula_pattern.group(1).strip()
        # Must contain an = sign and at least one variable
        if '=' in candidate and re.search(r'[a-zA-Z]', candidate):
            return candidate
    return None
