"""Unit tests for src.retrieval.workflow_recall (Wave 3).

Covers the cache semantics the dispatcher relies on: cache hit avoids
re-query, TTL expiry forces re-query (no cross-workflow bleed), 500-token
cap, blank workflow_id no-op, and fail-open on recall errors.
"""

from __future__ import annotations

from src.retrieval.workflow_recall import (
    CHARS_PER_TOKEN,
    MAX_CONTEXT_TOKENS,
    WorkflowRecallContext,
)


class _Clock:
    """Manually-advanced clock for deterministic TTL tests."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, secs: float) -> None:
        self.t += secs


def _counting_fn(text: str) -> tuple[list[int], object]:
    calls = [0]

    def fn() -> str:
        calls[0] += 1
        return text

    return calls, fn


def test_first_recall_misses_then_second_hits_without_requery() -> None:
    """The core win: spawn 2 reuses spawn 1's recall — recall_fn fires once."""
    cache = WorkflowRecallContext()
    calls, fn = _counting_fn("atoms for wf-1")

    first = cache.get_or_recall("wf-1", fn)
    second = cache.get_or_recall("wf-1", fn)

    assert first.cached is False
    assert first.context == "atoms for wf-1"
    assert second.cached is True
    assert second.context == "atoms for wf-1"
    assert calls[0] == 1  # recall_fn called exactly once across both spawns


def test_distinct_workflows_do_not_share() -> None:
    cache = WorkflowRecallContext()
    cache.get_or_recall("wf-a", lambda: "context A")
    out_b = cache.get_or_recall("wf-b", lambda: "context B")
    assert out_b.cached is False
    assert out_b.context == "context B"
    assert cache.peek("wf-a") == "context A"


def test_ttl_expiry_forces_requery_no_stale_bleed() -> None:
    clock = _Clock()
    cache = WorkflowRecallContext(ttl_s=600.0, clock=clock)
    calls, fn = _counting_fn("first")

    cache.get_or_recall("wf-1", fn)
    clock.advance(599.0)
    mid = cache.get_or_recall("wf-1", fn)
    assert mid.cached is True  # still within TTL
    assert calls[0] == 1

    clock.advance(2.0)  # now 601s — past the 600s TTL
    after = cache.get_or_recall("wf-1", lambda: "fresh")
    assert after.cached is False
    assert after.context == "fresh"  # stale entry not served


def test_context_capped_at_500_tokens() -> None:
    cache = WorkflowRecallContext()
    oversized = "x" * (MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN * 3)
    out = cache.get_or_recall("wf-big", lambda: oversized)
    assert len(out.context) == MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN


def test_blank_workflow_id_is_noop() -> None:
    cache = WorkflowRecallContext()
    calls, fn = _counting_fn("never")
    out = cache.get_or_recall("", fn)
    assert out.context == ""
    assert out.cached is False
    assert calls[0] == 0  # no scope to share in → recall_fn never called

    out_none = cache.get_or_recall(None, fn)
    assert out_none.context == ""
    assert calls[0] == 0


def test_recall_failure_is_fail_open() -> None:
    cache = WorkflowRecallContext()

    def boom() -> str:
        raise RuntimeError("recall backend down")

    out = cache.get_or_recall("wf-err", boom)
    assert out.context == ""
    assert out.cached is False
    assert cache.peek("wf-err") is None  # nothing stored on failure


def test_recall_fn_returning_none_yields_empty() -> None:
    cache = WorkflowRecallContext()
    out = cache.get_or_recall("wf-none", lambda: None)  # type: ignore[arg-type,return-value]
    assert out.context == ""
    # Stored as empty so a subsequent spawn still hits cache (no needless re-query).
    assert cache.peek("wf-none") == ""


def test_expired_entries_evicted_on_write() -> None:
    clock = _Clock()
    cache = WorkflowRecallContext(ttl_s=10.0, clock=clock)
    cache.get_or_recall("wf-old", lambda: "old")
    clock.advance(20.0)
    # Writing a new workflow sweeps the expired one.
    cache.get_or_recall("wf-new", lambda: "new")
    assert cache.peek("wf-old") is None
    assert cache.peek("wf-new") == "new"
