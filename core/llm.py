"""Optional Claude API layer.

* Used ONLY for narrative text (model-card prose, report commentary).
* Never used for numbers: the prompt includes the numbers already calculated by
  Python and the model is told to quote them, not compute new ones.
* Every response is cached on disk (outputs/llm_cache) so a re-run gives the
  same text and the demo does not depend on a live API call.
* If ANTHROPIC_API_KEY is not set, or the call fails, callers fall back to
  rule-based template text. The source of every text block is recorded.
"""
from __future__ import annotations

import hashlib
import json
import os

from core import config

SYSTEM_PROMPT = (
    "You are a model risk analyst at a UK bank writing documentation under the "
    "PRA SS1/23 model risk management principles. Be concise, factual and neutral. "
    "Only use facts and numbers given to you in the prompt. Never invent, estimate "
    "or recalculate any metric. If information is missing, say it is missing. "
    "Do not claim regulatory compliance."
)


def model_name() -> str:
    return os.environ.get("CLAUDE_MODEL", config.CLAUDE_MODEL_DEFAULT)


def available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def generate(prompt: str, max_tokens: int = 800) -> dict | None:
    """Return {"text", "source", "model", "cached"} or None if Claude is unavailable."""
    config.LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256((model_name() + SYSTEM_PROMPT + prompt).encode()).hexdigest()[:24]
    cache_file = config.LLM_CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text())
        cached["cached"] = True
        return cached
    if not available():
        return None
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=model_name(), max_tokens=max_tokens, temperature=0,
            system=SYSTEM_PROMPT, messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    except Exception as exc:  # network, auth, quota... fall back to templates
        print(f"[llm] Claude call failed, using template text instead: {exc}")
        return None
    result = {"text": text, "source": "ai_generated", "model": model_name(), "cached": False}
    cache_file.write_text(json.dumps(result, indent=2))
    return result
