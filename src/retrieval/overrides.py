"""Customer memory overrides for the retrieval read-path (Wave 5).

A customer records an intent against a specific memory:
    * ``ignore``  — suppress it from recall entirely.
    * ``prefer``  — boost its score so it ranks higher.

Overrides may be scoped to a single ``task_type`` (else they apply to every
query) and may carry an ``expires_at`` (else they never expire). Rows live in
``public.memory_overrides``; this module owns both the read (``load_active``)
and write (``insert_override``) DB paths, mirroring the psycopg DSN handling in
``agent_query._record_event``.

The whole feature sits behind ``RETRIEVAL_OVERRIDES_ENABLED`` (default off):
``apply_overrides`` is a no-op when the flag is unset, so the retrieval contract
is unchanged for callers who never opt in.

Import note: ``apply_overrides`` returns boosted citations via
``dataclasses.replace``, which clones the instance without needing the
``Citation`` symbol at runtime — that keeps this module free of a circular
import back into ``agent_query``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, replace
from datetime import datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:  # pragma: no cover — typing only, avoids agent_query cycle
    from collections.abc import Sequence

    from src.retrieval.agent_query import Citation

logger = logging.getLogger(__name__)

OverrideType = Literal["ignore", "prefer"]

# Additive boost applied to a 'prefer'-ed citation's score before the top-N
# sort. Additive (not multiplicative) so it still lifts memories whose raw
# score collapsed to 0.0 under the vectorizer-regression sentinel (KEI-198).
PREFER_SCORE_BOOST = 0.5


@dataclass(frozen=True)
class MemoryOverride:
    memory_id: str
    override_type: OverrideType
    task_type: str | None = None
    expires_at: datetime | None = None


def is_enabled() -> bool:
    """True when RETRIEVAL_OVERRIDES_ENABLED is a truthy env value (default off)."""
    return os.environ.get("RETRIEVAL_OVERRIDES_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _dsn() -> str | None:
    """Resolve + normalise the Supabase DSN (same handling as agent_query)."""
    dsn = os.environ.get("RETRIEVAL_EVENTS_DSN") or os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    # psycopg3 can't parse the `postgresql+asyncpg://` dialect tag the Supabase
    # pooler hands out (reference_psycopg_supabase_pgbouncer).
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def load_active(task_type: str | None) -> list[MemoryOverride]:
    """Load non-expired overrides applicable to ``task_type``.

    An override applies when its own ``task_type`` is NULL (global) or equals
    the query's ``task_type``. Best-effort: returns ``[]`` if no DSN is set or
    the query fails, so retrieval degrades gracefully rather than erroring.
    """
    dsn = _dsn()
    if not dsn:
        return []
    try:
        import psycopg

        with (
            psycopg.connect(dsn, prepare_threshold=None, autocommit=True) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                """
                SELECT memory_id, override_type, task_type, expires_at
                FROM public.memory_overrides
                WHERE (expires_at IS NULL OR expires_at > NOW())
                  AND (task_type IS NULL OR task_type = %s)
                """,
                (task_type,),
            )
            rows = cur.fetchall()
    except Exception:  # noqa: BLE001 — best-effort; never break recall
        logger.debug("memory_overrides load failed (non-fatal)", exc_info=True)
        return []
    return [
        MemoryOverride(memory_id=r[0], override_type=r[1], task_type=r[2], expires_at=r[3])
        for r in rows
    ]


def insert_override(
    memory_id: str,
    override_type: OverrideType,
    *,
    task_type: str | None = None,
    expires_at: datetime | None = None,
) -> dict:
    """Persist one override and return the created row (id + created_at).

    Raises ``RuntimeError`` if no DSN is configured — the write path, unlike
    the read path, must fail loudly so the customer learns the save did not
    land. DB errors propagate to the caller (the route maps them to 500).
    """
    dsn = _dsn()
    if not dsn:
        raise RuntimeError("memory_overrides insert requires DATABASE_URL/RETRIEVAL_EVENTS_DSN")
    import psycopg

    with (
        psycopg.connect(dsn, prepare_threshold=None, autocommit=True) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            """
            INSERT INTO public.memory_overrides (memory_id, override_type, task_type, expires_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id, memory_id, override_type, task_type, expires_at, created_at
            """,
            (memory_id, override_type, task_type, expires_at),
        )
        row = cur.fetchone()
    return {
        "id": str(row[0]),
        "memory_id": row[1],
        "override_type": row[2],
        "task_type": row[3],
        "expires_at": row[4],
        "created_at": row[5],
    }


def _by_memory_id(overrides: Sequence[MemoryOverride]) -> dict[str, MemoryOverride]:
    """Index overrides by memory_id, letting a task-scoped override win over a
    global one for the same memory (more specific intent takes precedence)."""
    indexed: dict[str, MemoryOverride] = {}
    for ov in overrides:
        existing = indexed.get(ov.memory_id)
        if existing is None or (existing.task_type is None and ov.task_type is not None):
            indexed[ov.memory_id] = ov
    return indexed


def apply_overrides(
    citations: list[Citation],
    *,
    task_type: str | None,
    overrides: Sequence[MemoryOverride] | None = None,
) -> list[Citation]:
    """Filter out ignored citations and boost preferred ones.

    No-op (returns the input unchanged) when the feature flag is off, when
    there are no citations, or when no override applies. ``overrides`` may be
    passed directly (tests); otherwise they're loaded from the DB.
    """
    if not is_enabled() or not citations:
        return citations
    active = overrides if overrides is not None else load_active(task_type)
    if not active:
        return citations
    indexed = _by_memory_id(active)
    result: list[Citation] = []
    for citation in citations:
        ov = indexed.get(citation.source_id)
        if ov is None:
            result.append(citation)
        elif ov.override_type == "ignore":
            continue
        else:  # prefer
            result.append(replace(citation, score=citation.score + PREFER_SCORE_BOOST))
    return result
