"""cognee_recall_injector.py — KEI-76 Cognee session-memory preamble for `bd claim`.

Mirror of claim_context_injector.format_preamble (KEI-51, PR #888). Emits a
second context block (Cognee session memory) before the `claimed <id>` success
line, alongside the discovery_log preamble. The combined preamble pair is
budgeted under one 500-token cap per KEI-55 ratified — cmd_claim is responsible
for splitting that budget between the two injectors.

Read path: scripts.cognee_recall.enrich_dispatch — fail-open by contract.
Any failure (Cognee idle, no GEMINI_API_KEY, search raises) → empty preamble.

Per Cognee audit 2026-05-16: Cognee writers idle since 2026-05-13 21:27 UTC;
this hook will succeed but recall may be stale. KEI-77 covers write-path
recovery. Layered architecture: Cognee = per-session graph memory; Weaviate +
LlamaIndex = collective semantic store; these blocks compose on task start.
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

# cognee_recall import is deferred to call-time so module load never raises.

TOKEN_CAP_DEFAULT = 500


def _approx_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _build_query(kei: str, callsign: str) -> str:
    return (
        f"Recent decisions + open context for callsign {callsign} on {kei} — "
        "what was decided, what is blocked, what should resume."
    )


def format_preamble(
    kei: str,
    callsign: str,
    max_tokens: int = TOKEN_CAP_DEFAULT,
) -> str:
    """Return Cognee session-memory preamble or empty string on any failure.

    KEI-55 drop-entirely semantics: if the rendered block exceeds max_tokens,
    the entire block is dropped (never mid-sentence truncate). Fail-open
    contract: any exception during recall → empty preamble (matches the
    contract of the underlying cognee_recall wrapper)."""
    if not kei or not callsign or max_tokens <= 0:
        return ""
    try:
        from cognee_recall import enrich_dispatch  # type: ignore[import-not-found]
    except Exception:
        return ""
    query = _build_query(kei, callsign)
    try:
        enriched = enrich_dispatch(query, limit=5, agent_id=callsign)
    except Exception:
        return ""
    if not enriched or enriched == query or not enriched.startswith("## Cognee context"):
        return ""
    end = enriched.find("\n\n")
    block = enriched if end == -1 else enriched[:end]
    if _approx_tokens(block) > max_tokens:
        return ""
    return block
