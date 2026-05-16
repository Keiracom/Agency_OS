"""bd claim context injection — 500-token ceiling per KEI-55 ratified rule.

Consumers (KEI-51 `bd claim` integration) call `render_for_claim()` to get
the discovery context block to inject. The ceiling is hard-capped at 500
tokens (tiktoken cl100k_base) — discoveries are sorted by recency and
truncated to fit.

Compositions with KEI-58 freshness ladder: each row carries `_freshness`
from `compute_freshness()`; the renderer prepends the staleness flag
(`⚠ stale`, `[~Nd]`, etc.) to the line. Discoveries with state=staging or
state=expired are excluded — only permanent + non-expired rows surface.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

TOKEN_CEILING = 500
_DEFAULT_ENCODING = "cl100k_base"


def _count_tokens(text: str) -> int:
    """tiktoken cl100k_base count. Falls back to char/4 if tiktoken absent."""
    try:
        import tiktoken  # noqa: PLC0415 — defer import for optional dep
    except ImportError:
        return len(text) // 4
    enc = tiktoken.get_encoding(_DEFAULT_ENCODING)
    return len(enc.encode(text))


def _render_row(row: dict[str, Any]) -> str:
    """One-line rendering of a discovery row for injection."""
    freshness = (row.get("_freshness") or {}).get("flag", "")
    prefix = f"{freshness} " if freshness else ""
    kei = row.get("kei", "")
    finding = row.get("finding") or row.get("verified_path") or ""
    failed = row.get("failed_path", "")
    tier = row.get("validation_tier", 1)
    line = f"{prefix}[{kei} T{tier}] {finding}"
    if failed:
        line += f" (failed: {failed})"
    return line.strip()


def render_for_claim(
    rows: list[dict[str, Any]],
    token_ceiling: int = TOKEN_CEILING,
) -> tuple[str, dict[str, int]]:
    """Render permanent + fresh discoveries into a token-capped block.

    Returns (rendered_text, stats). Stats keys:
        rows_in:        rows provided
        rows_eligible:  rows after state/expiry filter
        rows_rendered:  rows that fit under the cap
        tokens:         total tokens of rendered_text
        truncated:      1 if any rows dropped, 0 otherwise
    """
    eligible = [
        r
        for r in rows
        if r.get("state", "permanent") == "permanent"
        and (r.get("_freshness") or {}).get("verdict") != "expired"
    ]
    eligible.sort(
        key=lambda r: (r.get("_freshness") or {}).get("age_days", 9999),
    )

    rendered_lines: list[str] = []
    running_tokens = 0
    for row in eligible:
        line = _render_row(row)
        line_tokens = _count_tokens(line + "\n")
        if running_tokens + line_tokens > token_ceiling:
            break
        rendered_lines.append(line)
        running_tokens += line_tokens

    text = "\n".join(rendered_lines)
    stats = {
        "rows_in": len(rows),
        "rows_eligible": len(eligible),
        "rows_rendered": len(rendered_lines),
        "tokens": _count_tokens(text),
        "truncated": int(len(rendered_lines) < len(eligible)),
    }
    return text, stats
