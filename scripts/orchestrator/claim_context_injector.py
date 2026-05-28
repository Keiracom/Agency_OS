"""claim_context_injector.py — KEI-51 bd claim context preamble emitter.

Formats a token-capped block of "related" discoveries before the
`claimed <id> by <agent>: <title>` success line in tasks_cli.cmd_claim.

Read path:
  - discovery_log.load_active_discoveries() (KEI-63 deprecation-aware, jsonl)
  - weaviate_recall_source(kei, title, callsign) (KEI-103, Weaviate via
    src.retrieval.agent_query.query — also writes retrieval_events for
    observability)

Token cap: 500 (KEI-55 ratified). Lower-priority entries DROP entirely;
mid-sentence truncation is forbidden (per KEI-55 design note).

Priority key (descending) — exact KEI match > tag overlap count > validation_tier
weight (T3=3, T2=2, T1=1) > recency (later context_version write).
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable, Iterable

logger = logging.getLogger("claim_context_injector")

# scripts/orchestrator/ is not packaged (no __init__.py) — mirror the
# sys.path pattern used implicitly by sibling shims (KEI-63 cmd_deprecate
# resolves discovery_log via spec_from_file_location). At module level
# we just add the directory once.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Repo root on sys.path so `from src.retrieval import agent_query` resolves
# regardless of caller cwd (KEI-103 — Weaviate recall source needs the
# `src` package importable from bd claim's child process).
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from discovery_log import load_active_discoveries  # noqa: E402

TOKEN_CAP_DEFAULT = 500
WEAVIATE_RECALL_K_RETURNED = 5
WEAVIATE_RECALL_EXCERPT_PREVIEW_CHARS = 220


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
        f"  [{d.get('kei', '?')} | T{_tier_weight(d)} | {d.get('agent', '?')}] "
        f"{d.get('finding', '')}\n"
        f"    failed: {d.get('failed_path', '')}\n"
        f"    verified: {d.get('verified_path', '')}"
    )


def weaviate_recall_source(kei: str, title: str, callsign: str) -> Callable[[], list[dict]]:
    """KEI-103 — return a callable that recalls related context from Weaviate.

    The returned callable performs one `src.retrieval.agent_query.query()`
    against the default 3-collection set (Discoveries, Decisions, Keis) and
    converts every Citation into the discovery-dict shape format_preamble
    expects. Each dict is tagged with `kei=<claim_kei>` so the downstream
    relevance filter (kei-match OR tag-overlap) keeps Weaviate hits in —
    similarity score already established relevance, no need to re-filter.

    Fail-open: import errors, missing DSN, or query failure → empty list
    (callers must not block bd claim on knowledge-graph health).

    Side-effect: `agent_query.query()` internally calls `_record_event()`
    which logs the retrieval AND inserts a row into `public.retrieval_events`
    when `RETRIEVAL_EVENTS_DSN` or `DATABASE_URL` is set. THIS is the wire
    that makes retrieval_events count > 0 per bd claim cycle (KEI-103).
    """

    def _recall() -> list[dict]:
        try:
            from src.retrieval import (
                agent_query,  # noqa: PLC0415 — lazy import
                orchestrator,  # noqa: PLC0415 — lazy import
            )
        except ImportError as exc:
            logger.debug("KEI-103 weaviate recall import failed: %s", exc)
            return []
        query_text = f"{kei}: {title}".strip() if title else kei
        try:
            # Fleet-internal claim-context recall reads shared fleet_* banks
            # under FLEET_TENANT_SLUG (audit fix YELLOW-4, Agency_OS-7sj6).
            result = agent_query.query(
                query_text,
                agent=callsign or "atlas",
                tenant_id=orchestrator.FLEET_TENANT_SLUG,
            )
        except Exception as exc:  # noqa: BLE001 — fail-open
            logger.debug("KEI-103 weaviate recall query failed: %s", exc)
            return []
        out: list[dict] = []
        for c in result.citations[:WEAVIATE_RECALL_K_RETURNED]:
            preview = c.excerpt[:WEAVIATE_RECALL_EXCERPT_PREVIEW_CHARS]
            if len(c.excerpt) > WEAVIATE_RECALL_EXCERPT_PREVIEW_CHARS:
                preview += "…"
            out.append(
                {
                    # Tag with claim KEI so format_preamble's relevance filter
                    # (kei-match OR tag-overlap) keeps the Weaviate-derived
                    # rows in — similarity score already established relevance.
                    "kei": kei,
                    "agent": "weaviate",
                    "validation_tier": 2,
                    "tags": ["weaviate-recall", c.collection.lower()],
                    "finding": preview,
                    "failed_path": "",
                    "verified_path": f"[{c.source_id} | {c.collection} | score={c.score:.2f}]",
                }
            )
        return out

    return _recall


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
    filtered = [r for r in rows if r.get("kei") == kei or (set(r.get("tags") or []) & target_tags)]
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
