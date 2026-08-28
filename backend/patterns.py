"""
patterns.py
The pattern library: known attack signatures for prompt injection, jailbreaks,
and data-extraction attempts. This is the "knowledge" PromptShield uses to
score incoming prompts. Rule-based on purpose -- no ML model needed, which
means it's fast, free, and fully explainable in a live demo.

Each pattern has:
- regex/keywords to match
- a category (for the dashboard breakdown chart)
- a severity weight (how much it contributes to the risk score)
"""

import re

# ---------------------------------------------------------------------------
# CATEGORY 1: Instruction override / prompt injection
# Attempts to make the model ignore its original instructions
# ---------------------------------------------------------------------------
INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) instructions",
    r"disregard (all |any |the )?(previous|prior|above|earlier) instructions",
    r"forget (all |any |the )?(previous|prior|above|earlier) instructions",
    r"new instructions?:",
    r"system prompt override",
    r"you (must|will|shall) now (act|behave|respond)",
    r"from now on,? (you|ignore|act)",
    r"override your (programming|instructions|rules|guidelines)",
]

# ---------------------------------------------------------------------------
# CATEGORY 2: Jailbreak / persona hijacking
# Attempts to make the model roleplay as something without restrictions
# ---------------------------------------------------------------------------
JAILBREAK_PATTERNS = [
    r"\bDAN\b",  # "Do Anything Now" - classic jailbreak persona
    r"do anything now",
    r"you are (now |)(a|an) (unrestricted|unfiltered|uncensored) (AI|model|assistant)",
    r"pretend (you are|to be) .{0,40}(no rules|no restrictions|no filter|unfiltered)",
    r"act as if you have no (guidelines|restrictions|filters|rules)",
    r"roleplay as .{0,40}(evil|unrestricted|jailbroken)",
    r"developer mode",
    r"jailbreak(ed)?",
    r"you have been freed from",
    r"opposite day",
]

# ---------------------------------------------------------------------------
# CATEGORY 3: System prompt / config extraction
# Attempts to get the model to reveal its hidden instructions
# ---------------------------------------------------------------------------
EXTRACTION_PATTERNS = [
    r"(reveal|show|print|output|repeat|display) (your |the )?(system prompt|initial prompt|instructions)",
    r"what (are|were) your (original |initial |system )?instructions",
    r"repeat (the words|everything) above",
    r"what did (i|the user) (say|write) (before|above)",
    r"(show|reveal|give) me your (config|configuration|rules|guidelines)",
    r"output your (prompt|instructions) (verbatim|exactly|word for word)",
]

# ---------------------------------------------------------------------------
# CATEGORY 4: Sensitive data / credential fishing
# Attempts to extract secrets, keys, or personal info via the model
# ---------------------------------------------------------------------------
DATA_EXFIL_PATTERNS = [
    r"api[_\s]?key",
    r"secret[_\s]?key",
    r"password",
    r"credit card number",
    r"social security number",
    r"private key",
    r"access token",
    r"database (credentials|connection string)",
]

# ---------------------------------------------------------------------------
# CATEGORY 5: Encoding / obfuscation tricks
# Attempts to sneak instructions past filters using encoding
# ---------------------------------------------------------------------------
OBFUSCATION_PATTERNS = [
    r"base64",
    r"rot13",
    r"decode (this|the following)",
    r"[A-Za-z0-9+/]{40,}={0,2}",  # looks like a long base64 blob
]

# Master registry: category name -> (patterns list, severity weight per hit)
PATTERN_REGISTRY = {
    "Prompt Injection": (INJECTION_PATTERNS, 30),
    "Jailbreak Attempt": (JAILBREAK_PATTERNS, 35),
    "System Prompt Extraction": (EXTRACTION_PATTERNS, 25),
    "Data Exfiltration": (DATA_EXFIL_PATTERNS, 20),
    "Obfuscation": (OBFUSCATION_PATTERNS, 15),
}

# Pre-compile all regexes once at import time (faster than recompiling per request)
_COMPILED_REGISTRY = {
    category: ([re.compile(p, re.IGNORECASE) for p in patterns], weight)
    for category, (patterns, weight) in PATTERN_REGISTRY.items()
}


def scan_prompt(prompt: str) -> dict:
    """
    Scans a prompt against all pattern categories.
    Returns a dict with matched categories, total risk score (0-100), and
    a list of the specific patterns that fired (useful for the dashboard).
    """
    matched_categories = []
    total_score = 0
    fired_patterns = []

    for category, (compiled_patterns, weight) in _COMPILED_REGISTRY.items():
        category_hit = False
        for pattern in compiled_patterns:
            match = pattern.search(prompt)
            if match:
                category_hit = True
                fired_patterns.append({
                    "category": category,
                    "matched_text": match.group(0)[:60],  # cap for display
                })
        if category_hit:
            matched_categories.append(category)
            total_score += weight

    # Extra heuristic: very long prompts with many instruction-like words
    # are somewhat more suspicious (common in complex injection attempts)
    instruction_words = len(re.findall(
        r"\b(ignore|disregard|override|instead|now|must|forget)\b",
        prompt, re.IGNORECASE
    ))
    if instruction_words >= 4:
        total_score += 10
        if "Suspicious Density" not in matched_categories:
            matched_categories.append("Suspicious Density")

    total_score = min(total_score, 100)  # cap at 100

    return {
        "risk_score": total_score,
        "categories": matched_categories,
        "fired_patterns": fired_patterns,
        "is_safe": total_score < 30,
        "is_suspicious": 30 <= total_score < 60,
        "is_malicious": total_score >= 60,
    }
