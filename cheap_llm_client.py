"""In-house "prompting" leg readiness client - not wired into the live
website/app-mockup generation yet.

Per the investor cost plan's own honest read: fully self-hosting an
open-weight model doesn't pencil out at current volume (a single dedicated
GPU instance costs more per month than the entire Claude spend line). The
realistic move named there is a hybrid split - route low-stakes generation
(template previews, simple copy) to a cheap hosted model, keep Claude only
where output quality is customer-facing.

Groq hosts open-weight models (Llama 3.3 70B et al.) behind an
OpenAI-compatible chat completions API, at a small fraction of Claude's
per-token cost, with very low latency. This module is inert until
GROQ_API_KEY is set - same readiness pattern as snov_client.py. Once it's
set, generate() is a drop-in for the one concrete low-stakes candidate
already in the codebase: template preview HTML (the sample content shown
in the layout gallery, not real customer-facing generation) - currently
generated via Claude in the n8n "Generate Template Preview" workflow,
which is exactly the kind of call this should take over first.
"""
import os

import requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def is_configured() -> bool:
    return bool(GROQ_API_KEY)


def generate(prompt: str, max_tokens: int = 4000, temperature: float = 0.7) -> str | None:
    """Returns generated text, or None if not configured or the call fails.
    Callers should fall back to Claude on None rather than surface an error -
    this is meant to be a cost optimization, not a new point of failure."""
    if not is_configured():
        return None

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        return None
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return None
    return choices[0].get("message", {}).get("content")
