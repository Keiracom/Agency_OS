"""Tests for src/keiracom_system/metering/aggregator.py — Phase 2 wave 2 item 3.

Bucket key = (tenant_id, date_utc, model). Need to verify each axis of the
key actually splits buckets, plus the aggregation arithmetic + flush
semantics.

10 cases — 4 happy-path + 6 negative/edge.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.metering.aggregator import (  # noqa: E402
    Aggregator,
    MeteringRow,
)
from src.keiracom_system.metering.log_reader import MeteringEvent  # noqa: E402


def _ev(
    tenant: str = "t1",
    model: str = "gpt-4o-mini",
    ts: str = "2026-05-25T10:00:00+00:00",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MeteringEvent:
    return MeteringEvent(
        tenant_id=tenant,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        timestamp=datetime.fromisoformat(ts),
    )


def test_single_event_produces_single_row():
    """(1) one event → one row with count=1, tokens carried through."""
    agg = Aggregator()
    agg.add_event(_ev())
    rows = agg.flush()
    assert len(rows) == 1
    r = rows[0]
    assert r.tenant_id == "t1"
    assert r.date_utc == "2026-05-25"
    assert r.model == "gpt-4o-mini"
    assert r.request_count == 1
    assert r.input_tokens_sum == 100
    assert r.output_tokens_sum == 50


def test_two_events_same_bucket_aggregate():
    """(2) same (tenant, date, model) → counts + tokens accumulate."""
    agg = Aggregator()
    agg.add_event(_ev(input_tokens=10, output_tokens=20))
    agg.add_event(_ev(input_tokens=100, output_tokens=200))
    rows = agg.flush()
    assert len(rows) == 1
    assert rows[0].request_count == 2
    assert rows[0].input_tokens_sum == 110
    assert rows[0].output_tokens_sum == 220


def test_add_events_consumes_iterable():
    """(3) add_events drains any iterable of events into the accumulator."""
    agg = Aggregator()
    agg.add_events(_ev() for _ in range(5))
    rows = agg.flush()
    assert len(rows) == 1
    assert rows[0].request_count == 5


def test_flush_resets_internal_state():
    """(4) flush returns rows + clears accumulator → second flush is empty."""
    agg = Aggregator()
    agg.add_event(_ev())
    first = agg.flush()
    second = agg.flush()
    assert len(first) == 1
    assert second == []


def test_different_tenant_id_creates_separate_buckets():
    """(5) (t1, date, model) and (t2, date, model) → 2 rows."""
    agg = Aggregator()
    agg.add_event(_ev(tenant="t1"))
    agg.add_event(_ev(tenant="t2"))
    rows = agg.flush()
    assert len(rows) == 2
    assert {r.tenant_id for r in rows} == {"t1", "t2"}


def test_different_date_utc_creates_separate_buckets():
    """(6) same tenant/model but different UTC date → 2 rows.

    Verifies the date_utc derivation cuts at midnight UTC regardless of
    the source timestamp's offset. Day-rollover correctness anchor.
    """
    agg = Aggregator()
    agg.add_event(_ev(ts="2026-05-25T23:59:59+00:00"))
    agg.add_event(_ev(ts="2026-05-26T00:00:01+00:00"))
    rows = agg.flush()
    assert len(rows) == 2
    assert {r.date_utc for r in rows} == {"2026-05-25", "2026-05-26"}


def test_different_model_creates_separate_buckets():
    """(7) same tenant + date but different model → 2 rows (per-model cost)."""
    agg = Aggregator()
    agg.add_event(_ev(model="gpt-4o-mini"))
    agg.add_event(_ev(model="claude-opus"))
    rows = agg.flush()
    assert len(rows) == 2
    assert {r.model for r in rows} == {"gpt-4o-mini", "claude-opus"}


def test_flush_on_empty_aggregator_returns_empty_list():
    """(8) flush() before any add_event → []. No exception on empty drain."""
    assert Aggregator().flush() == []


def test_zero_token_events_aggregate_to_zero_sums():
    """(9) events with 0 input/output tokens still count requests + sum to 0."""
    agg = Aggregator()
    agg.add_event(_ev(input_tokens=0, output_tokens=0))
    agg.add_event(_ev(input_tokens=0, output_tokens=0))
    rows = agg.flush()
    assert rows[0].request_count == 2
    assert rows[0].input_tokens_sum == 0
    assert rows[0].output_tokens_sum == 0


def test_metering_row_add_mutates_in_place():
    """(10) MeteringRow.add() mutates request_count + sums in place (no return value).

    Locks the contract: aggregator relies on in-place mutation, not on a
    new-row-per-add immutable pattern. If we ever switch to immutable rows
    the aggregator's bucket lookup needs to update too.
    """
    row = MeteringRow(tenant_id="t1", date_utc="2026-05-25", model="x")
    row.add(_ev(input_tokens=7, output_tokens=11))
    assert row.request_count == 1
    assert row.input_tokens_sum == 7
    assert row.output_tokens_sum == 11
