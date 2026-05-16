"""claim_context_injector.py — KEI-51 bd claim context preamble emitter.

Formats a token-capped block of "related" discoveries before the
`claimed <id> by <agent>: <title>` success line in tasks_cli.cmd_claim.

Read path: discovery_log.load_active_discoveries() (KEI-63 deprecation-aware).
Token cap: 500 (KEI-55 ratified). Lower-priority entries DROP entirely;
mid-sentence truncation is forbidden (per KEI-55 design note).

Weaviate retrieval (post-KEI-49 / PR #887) is an additive future source —
extension point is the `extra_sources` kwarg: each callable returns a list
of discovery dicts merged before ranking. Default keeps the jsonl-only path.

Priority key (descending) — exact KEI match > tag overlap count > validation_tier
weight (T3=3, T2=2, T1=1) > recency (later context_version write).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterable

# scripts/orchestrator/ is not packaged (no __init__.py) — mirror the
# sys.path pattern used implicitly by sibling shims (KEI-63 cmd_deprecate
# resolves discovery_log via spec_from_file_location). At module level
# we just add the directory once.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from discovery_log import load_active_discoveries  # noqa: E402

TOKEN_CAP_DEFAULT = 500


def _approx_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _tier_weight(d: dict) -> int:
    v = d.get("validation_tier")
    return v if isinstance(v, int) and v in (1, 2, 3) else 1


def _priority_key(d: dict, target_kei: str, target_tags: set[str]) -> tuple:
    kei_hit = 1 if d.get("kei") == target_kei else 0
    tag_overlap = len(set(d.get("tags") or []) & target_tags)
    return (kei_hit, tag_overlap, _tier_weight(d))


def _format_entry(d: dict) -> str:
    return (
        f"  [{d.get('kei','?')} | T{_tier_weight(d)} | {d.get('agent','?')}] "
        f"{d.get('finding','')}\n"
        f"    failed: {d.get('failed_path','')}\n"
        f"    verified: {d.get('verified_path','')}"
    )


def format_preamble(
    kei: str,
    tags: Iterable[str] = (),
    max_tokens: int = TOKEN_CAP_DEFAULT,
    extra_sources: tuple[Callable[[], list[dict]], ...] = (),
) -> str:
    """Return preamble text or empty string when no related discoveries fit.

    Filtering: keep rows with KEI match OR tag overlap. Pure-zero rows skipped.
    Ordering: priority key descending; tie-break stable on input order.
    Drop semantics: KEI-55 — any entry that would push the running total past
    max_tokens is skipped entirely; the loop continues so smaller later entries
    may still fit (better than first-overflow termination).
    """
    target_tags = {t for t in (tags or []) if t}
    rows: list[dict] = list(load_active_discoveries())
    for src in extra_sources:
        rows.extend(src() or [])
    if not rows:
        return ""
    filtered = [
        r for r in rows
        if r.get("kei") == kei or (set(r.get("tags") or []) & target_tags)
    ]
    if not filtered:
        return ""
    ranked = sorted(filtered, key=lambda r: _priority_key(r, kei, target_tags), reverse=True)
    header = f"=== bd claim context preamble (kei={kei}, KEI-55 cap={max_tokens}t) ==="
    used = _approx_tokens(header)
    lines: list[str] = []
    for r in ranked:
        entry = _format_entry(r)
        cost = _approx_tokens(entry) + 1
        if used + cost > max_tokens:
            continue
        lines.append(entry)
        used += cost
    if not lines:
        return ""
    return header + "\n" + "\n".join(lines)
