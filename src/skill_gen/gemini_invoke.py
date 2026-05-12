"""gemini_invoke.py — Google Gemini 2.5 Flash Lite wrapper for skill-gen.

Drevon PR-B architecture pivot (2026-05-12): replaces the prior
`claude --print` subprocess approach (PR #720, PR #728) with direct
Gemini API calls. Reuses the existing `GEMINI_API_KEY` budget; the model
is ~3× cheaper than Anthropic Haiku for the compressed-session payload
shape used by skill-gen.

Why the pivot:
    - PR #728 empirical re-run revealed the spawned `claude --print`
      process exits 1 with "Credit balance is too low" — Max plan OAuth
      credits don't propagate to a subprocess. Topping up the bot
      account or setting ANTHROPIC_API_KEY were both rejected; the
      cheapest path that preserves the $0/skill promise is Gemini Flash
      Lite via the existing key.

SDK choice:
    The older `google.generativeai` package is deprecated and emits a
    FutureWarning recommending `google.genai` (the GA SDK). We use
    `google.genai` directly — the deprecated package is intentionally
    NOT imported.

Pricing (published 2026-05 — verify before re-running large batches):
    gemini-2.5-flash-lite — $0.10 / 1M input tokens, $0.40 / 1M output.
    Skill-gen compressed payload: ~15K input tokens, ~2K output per call.
    100 calls/day → 1.5M in + 0.2M out → $0.15/day input + $0.08/day
    output ≈ ~$7/month. Well inside the "$0 incremental" frame.

Shape mirrors src/skill_gen/claude_invoke.py (now deleted): caller-side
injection points so tests don't touch the real API.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
DEFAULT_MODEL = "gemini-2.5-flash-lite"


@dataclass(frozen=True)
class GeminiResult:
    text: str
    model: str
    prompt_tokens: int | None = None
    output_tokens: int | None = None


class GeminiNotConfigured(RuntimeError):
    """Raised when GEMINI_API_KEY isn't set."""


def _default_client_factory(api_key: str):
    """Build a real google.genai.Client. Imported lazily so test environments
    without the SDK installed can still import this module and inject stubs."""
    from google import genai

    return genai.Client(api_key=api_key)


def invoke(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    client_factory: Callable[[str], Any] = _default_client_factory,
) -> GeminiResult:
    """Send `prompt` to Gemini Flash Lite. Returns a structured result.

    `client_factory` is injectable for tests (default builds a real
    google.genai.Client). Tests pass a stub that returns an object with a
    `models.generate_content(...) → response.text` shape.
    """
    key = api_key or os.environ.get(GEMINI_API_KEY_ENV, "").strip()
    if not key:
        raise GeminiNotConfigured(
            f"{GEMINI_API_KEY_ENV} not set in environment. "
            "Source /home/elliotbot/.config/agency-os/.env first."
        )
    client = client_factory(key)
    response = client.models.generate_content(model=model, contents=prompt)
    usage = getattr(response, "usage_metadata", None)
    return GeminiResult(
        text=(response.text or ""),
        model=model,
        prompt_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
    )
