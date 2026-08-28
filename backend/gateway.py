"""
gateway.py

The core PromptShield gateway.

Security pipeline:

    User Prompt
        ↓
    Pattern Scanner
        ↓
    AI Security Judge
        ↓
    Combined Risk Score
        ↓
    ┌──────────────┬────────────────────┐
    │              │                    │
  ALLOWED       SANITIZE             BLOCK
    │              │                    │
    ↓              ↓                    ↓
  Main LLM      Main LLM             No LLM
"""

import time
import uuid

from backend.patterns import scan_prompt
from backend.llm_client import call_llm
from .security_judge import judge_prompt


# In-memory audit log.
# For the hackathon this is sufficient.
REQUEST_LOG = []


def process_request(prompt: str) -> dict:
    """
    Main PromptShield security pipeline.

    1. Run the fast pattern scanner.
    2. Run the AI Security Judge.
    3. Combine both risk signals.
    4. Decide whether to allow, sanitize, or block.
    5. Only send safe/sanitized prompts to the main LLM.
    """

    request_id = str(uuid.uuid4())[:8]
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    # =========================================================
    # STEP 1 — FAST PATTERN SCANNER
    # =========================================================

    scan_result = scan_prompt(prompt)

    pattern_score = scan_result["risk_score"]

    # =========================================================
    # STEP 2 — AI SECURITY JUDGE
    # =========================================================

    security_result = judge_prompt(prompt)

    ai_score = security_result.get("risk_score", 0)

    if security_result.get("violation") == 1:
     ai_score = max(ai_score, 70)

    # =========================================================
    # STEP 3 — COMBINE SECURITY SIGNALS
    # =========================================================

    # Pattern scanner:
    #   Fast + deterministic
    #
    # AI Security Judge:
    #   Semantic + adaptive
    #
    # AI judge receives slightly more weight.

    combined_score = round(
        (pattern_score * 0.40) + (ai_score * 0.60)
    )

    # A high-confidence pattern detection must remain high-risk
    # even if the AI judge disagrees.
    if scan_result["is_malicious"]:
        combined_score = max(combined_score, 80)

    # =========================================================
    # STEP 4 — FINAL SECURITY DECISION
    # =========================================================

    if combined_score >= 70:
        action = "BLOCKED"

    elif combined_score >= 30:
        action = "SANITIZED_AND_FORWARDED"

    else:
        action = "ALLOWED"

    # =========================================================
    # CREATE AUDIT RECORD
    # =========================================================

    record = {
        "id": request_id,
        "timestamp": timestamp,
        "prompt": prompt,

        # Individual security scores
        "pattern_score": pattern_score,
        "ai_security_score": ai_score,
        "risk_score": combined_score,

        # Pattern detection information
        "categories": scan_result["categories"],
        "fired_patterns": scan_result["fired_patterns"],

        # AI Security Judge information
        "security_judge": {
            "success": security_result.get("success", False),
            "violation": security_result.get("violation", 0),
            "risk_score": security_result.get("risk_score", 0),
            "rationale": security_result.get("rationale", ""),
            "latency_ms": security_result.get("latency_ms", 0),
            "model": security_result.get("model"),
            "error": security_result.get("error"),
        },

        "action": action,
    }

    # =========================================================
    # STEP 5 — ENFORCE SECURITY DECISION
    # =========================================================

    if action == "BLOCKED":

        # IMPORTANT:
        # Blocked prompts NEVER reach the main LLM.

        record["response"] = (
            "This request was blocked by PromptShield because "
            "the security analysis detected a high-risk prompt."
        )

        record["llm_called"] = False

        record["latency_ms"] = security_result.get(
            "latency_ms",
            0
        )

    elif action == "SANITIZED_AND_FORWARDED":

        # Remove detected malicious phrases.
        sanitized = _sanitize(prompt)

        # Send ONLY the sanitized version to the main LLM.
        llm_result = call_llm(sanitized)

        record["sanitized_prompt"] = sanitized

        record["response"] = llm_result.get(
            "answer",
            "Error calling model"
        )

        record["llm_called"] = True

        record["latency_ms"] = (
            security_result.get("latency_ms", 0)
            + llm_result.get("latency_ms", 0)
        )

    else:

        # Safe prompt:
        # Send the original prompt to the main LLM.

        llm_result = call_llm(prompt)

        record["response"] = llm_result.get(
            "answer",
            "Error calling model"
        )

        record["llm_called"] = True

        record["latency_ms"] = (
            security_result.get("latency_ms", 0)
            + llm_result.get("latency_ms", 0)
        )

    # =========================================================
    # STEP 6 — STORE AUDIT LOG
    # =========================================================

    REQUEST_LOG.append(record)

    return record


def _sanitize(prompt: str) -> str:
    """
    Remove phrases detected by the pattern scanner.

    The sanitized prompt is then forwarded to the main LLM.
    """

    scan = scan_prompt(prompt)

    cleaned = prompt

    for fired in scan["fired_patterns"]:
        cleaned = cleaned.replace(
            fired["matched_text"],
            "[REMOVED]"
        )

    return cleaned


def get_stats() -> dict:
    """
    Aggregate REQUEST_LOG into dashboard statistics.
    """

    total = len(REQUEST_LOG)

    if total == 0:
        return {
            "total_requests": 0,
            "blocked": 0,
            "sanitized": 0,
            "allowed": 0,
            "block_rate_pct": 0,
            "category_counts": {},
        }

    blocked = sum(
        1
        for r in REQUEST_LOG
        if r["action"] == "BLOCKED"
    )

    sanitized = sum(
        1
        for r in REQUEST_LOG
        if r["action"] == "SANITIZED_AND_FORWARDED"
    )

    allowed = sum(
        1
        for r in REQUEST_LOG
        if r["action"] == "ALLOWED"
    )

    category_counts = {}

    for r in REQUEST_LOG:

        for cat in r["categories"]:

            category_counts[cat] = (
                category_counts.get(cat, 0) + 1
            )

    return {
        "total_requests": total,
        "blocked": blocked,
        "sanitized": sanitized,
        "allowed": allowed,
        "block_rate_pct": round(
            (blocked / total) * 100,
            1
        ),
        "category_counts": category_counts,
    }