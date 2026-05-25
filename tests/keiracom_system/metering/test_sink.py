"""Tests for src/keiracom_system/metering/sink.py — Phase 2 wave 2 item 3.

Sink is a thin pass-through to a _DBProtocol implementation. Tests inject
a FakeDB that captures calls so we can assert the contract without psycopg
in the test path.

5 cases — 2 happy + 3 negative/edge.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.metering.aggregator import MeteringRow  # noqa: E402
from src.keiracom_system.metering.sink import PostgresSink  # noqa: E402


class FakeDB:
    """In-memory _DBProtocol — captures rows + returns configured count."""

    def __init__(self, return_value: int = 0):
        self.calls: list[list[MeteringRow]] = []
        self._return_value = return_value

    def upsert_metering_rows(self, rows: list[MeteringRow]) -> int:
        self.calls.append(list(rows))
        return self._return_value


def _row(tenant: str = "t1", model: str = "x") -> MeteringRow:
    return MeteringRow(
        tenant_id=tenant,
        date_utc="2026-05-25",
        model=model,
        request_count=1,
        input_tokens_sum=10,
        output_tokens_sum=5,
    )


def test_write_rows_passes_batch_to_db_and_returns_count():
    """(1) non-empty batch → db.upsert called once, return value bubbled up."""
    db = FakeDB(return_value=3)
    sink = PostgresSink(db=db)
    rows = [_row(tenant="t1"), _row(tenant="t2"), _row(tenant="t3")]
    affected = sink.write_rows(rows)
    assert affected == 3
    assert len(db.calls) == 1
    assert [r.tenant_id for r in db.calls[0]] == ["t1", "t2", "t3"]


def test_write_rows_preserves_input_order():
    """(2) sink does NOT reorder — caller (or db adapter) owns ordering."""
    db = FakeDB(return_value=2)
    sink = PostgresSink(db=db)
    rows = [_row(model="z"), _row(model="a")]
    sink.write_rows(rows)
    assert [r.model for r in db.calls[0]] == ["z", "a"]


def test_write_rows_empty_input_is_no_op_no_db_call():
    """(3) empty rows → no DB round-trip + returns 0. Saves a no-op transaction."""
    db = FakeDB(return_value=99)
    sink = PostgresSink(db=db)
    affected = sink.write_rows([])
    assert affected == 0
    assert db.calls == []  # no upsert call at all


def test_write_rows_returns_zero_on_db_zero_affected():
    """(4) db reports 0 affected rows → sink propagates 0 (not coerced to len)."""
    db = FakeDB(return_value=0)
    sink = PostgresSink(db=db)
    rows = [_row()]
    affected = sink.write_rows(rows)
    assert affected == 0
    assert len(db.calls) == 1  # call still made even when 0 affected


def test_write_rows_multiple_calls_each_round_trip_db():
    """(5) sink holds no batch state — each call is a fresh DB round-trip.

    Locks the no-batching contract so callers know to batch upstream if they
    want larger transactions.
    """
    db = FakeDB(return_value=1)
    sink = PostgresSink(db=db)
    sink.write_rows([_row(tenant="t1")])
    sink.write_rows([_row(tenant="t2")])
    sink.write_rows([_row(tenant="t3")])
    assert len(db.calls) == 3
    assert [batch[0].tenant_id for batch in db.calls] == ["t1", "t2", "t3"]
