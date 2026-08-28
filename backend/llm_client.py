"""
llm_client.py
Thin wrapper around the Groq API. This is the "protected" LLM that
PromptShield sits in front of. Safe prompts get forwarded here;
blocked prompts never reach this file at all.

Groq is used because it's free-tier, fast, and needs no local setup --
important given your connection situation this week.
"""

import os
import time
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
# Reads GROQ_API_KEY from environment (loaded from .env by main.py)
_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Add it to your .env file. "
                "Get a free key at console.groq.com"
            )
        _client = Groq(api_key=api_key)
    return _client


def call_llm(prompt: str, model: str = "openai/gpt-oss-20b") -> dict:
    """
    Sends a prompt to Groq and returns the response plus timing info.
    Timing/token data feeds directly into the dashboard.
    """
    client = get_client()
    start = time.time()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        elapsed_ms = round((time.time() - start) * 1000, 1)

        answer = response.choices[0].message.content
        usage = response.usage

        return {
            "success": True,
            "answer": answer,
            "latency_ms": elapsed_ms,
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "model": model,
        }
    except Exception as e:
        elapsed_ms = round((time.time() - start) * 1000, 1)
        return {
            "success": False,
            "answer": None,
            "error": str(e),
            "latency_ms": elapsed_ms,
        }
