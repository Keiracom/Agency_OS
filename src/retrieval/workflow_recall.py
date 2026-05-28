"""Workflow-scoped recall context cache (Wave 3).

A multi-step workflow spawns several sessions. Without sharing, each spawn
re-recalls the same atoms — duplicate retrieval cost + latency. This caches the
recalled context per ``workflow_id`` so spawn 2..N inherit spawn 1's recall
result without re-querying.

Bounds:
  - Per-workflow context capped at 500 tokens (KEI-55 ceiling), using the same
    4-chars-per-token approximation as src/retrieval/agent_query.
  - Entries expire after 10 minutes so a later, unrelated workflow that reuses
    an id never inherits stale context (no cross-workflow bleed).

Fail-open: any error — or a missing/blank workflow_id — yields an empty context
and never raises. The caller's spawn must always proceed.

Concurrency: process-local + single-event-loop. The dispatcher runs one asyncio
loop per process and calls get_or_recall inline (like the budget + attribution
gates), so the plain-dict store needs no lock. recall_fn is expected to be
cheap; if it does blocking I/O the caller should keep it fast or offload it.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 4  # matches src/retrieval/agent_query token approximation
MAX_CONTEXT_TOKENS = 500  # KEI-55 ceiling
DEFAULT_TTL_S = 600.0  # 10 minutes — prevents cross-workflow bleed


@dataclass
class _Entry:
    context: str
    stored_at: float


@dataclass(frozen=True)
class RecallOutcome:
    """Result of a get_or_recall call.

    ``cached`` distinguishes a reuse (spawn 2..N — no query fired, the cost +
    latency saving) from a fresh recall (spawn 1, or after TTL expiry).
    """

    context: str
    cached: bool


class WorkflowRecallContext:
    """Per-workflow recall cache with a token cap and a TTL."""

    def __init__(
        self,
        *,
        ttl_s: float = DEFAULT_TTL_S,
        max_tokens: int = MAX_CONTEXT_TOKENS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_s = ttl_s
        self._char_cap = max_tokens * CHARS_PER_TOKEN
        self._clock = clock
        self._store: dict[str, _Entry] = {}

    def get_or_recall(self, workflow_id: str | None, recall_fn: Callable[[], str]) -> RecallOutcome:
        """Return shared context for ``workflow_id``, recalling once on miss.

        Cache hit (entry present + within TTL): returns the stored context and
        does NOT call recall_fn — this is the re-query avoidance the feature
        exists for. Miss (absent or expired): calls recall_fn (fail-open),
        caps to the token ceiling, stores, and returns it. A blank/absent
        workflow_id is a no-op (empty context) — there is no scope to share in.
        """
        if not workflow_id:
            return RecallOutcome(context="", cached=False)
        now = self._clock()
        entry = self._store.get(workflow_id)
        if entry is not None and (now - entry.stored_at) <= self._ttl_s:
            return RecallOutcome(context=entry.context, cached=True)
        try:
            recalled = recall_fn() or ""
        except Exception:  # noqa: BLE001 — recall must never block the spawn
            logger.exception("workflow_recall: recall_fn raised for workflow_id=%s", workflow_id)
            return RecallOutcome(context="", cached=False)
        context = self._cap(str(recalled))
        self._store[workflow_id] = _Entry(context=context, stored_at=now)
        self._evict_expired(now)
        return RecallOutcome(context=context, cached=False)

    def _cap(self, text: str) -> str:
        return text[: self._char_cap]

    def _evict_expired(self, now: float) -> None:
        expired = [wid for wid, e in self._store.items() if (now - e.stored_at) > self._ttl_s]
        for wid in expired:
            del self._store[wid]

    def peek(self, workflow_id: str) -> str | None:
        """Return the stored context without recall or TTL side effects (debug/tests)."""
        entry = self._store.get(workflow_id)
        return entry.context if entry is not None else None

    def clear(self) -> None:
        self._store.clear()
