"""Unit tests for src/observability/heartbeat.py (KEI-91 Gate 4).

No DB. Pure-function tests for compute_next_state + _period_start_for.
Integration tests for tick() live in the acceptance-test smoke driver
(scripts/orchestrator/test_heartbeat_acceptance.py).
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from observability import heartbeat as hb  # noqa: E402


def _ts(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> _dt.datetime:
    return _dt.datetime(year, month, day, hour, minute, second, tzinfo=_dt.UTC)


def test_period_start_aligns_to_bucket():
    # 5-minute buckets — 00:03:30 falls in the [00:00, 00:05) bucket.
    now = _ts(2026, 5, 17, 0, 3, 30)
    assert hb._period_start_for(now, period_seconds=300) == _ts(2026, 5, 17, 0, 0, 0)


def test_period_start_at_bucket_boundary():
    now = _ts(2026, 5, 17, 0, 5, 0)
    assert hb._period_start_for(now, period_seconds=300) == _ts(2026, 5, 17, 0, 5, 0)


def test_first_tick_starts_fresh_counter():
    state = hb.compute_next_state(
        None,
        now=_ts(2026, 5, 17, 0, 1, 0),
        outcome_increment=3,
        status="ok",
        error_message=None,
    )
    assert state["last_outcome_counter_value"] == 3
    assert state["last_status"] == "ok"
    assert state["last_error_message"] is None
    assert state["last_period_start"] == "2026-05-17T00:00:00+00:00"


def test_same_period_accumulates_counter():
    first = hb.compute_next_state(
        None,
        now=_ts(2026, 5, 17, 0, 1, 0),
        outcome_increment=3,
        status="ok",
        error_message=None,
    )
    second = hb.compute_next_state(
        first,
        now=_ts(2026, 5, 17, 0, 2, 0),
        outcome_increment=5,
        status="ok",
        error_message=None,
    )
    assert second["last_outcome_counter_value"] == 8


def test_new_period_resets_counter():
    first = hb.compute_next_state(
        None,
        now=_ts(2026, 5, 17, 0, 1, 0),
        outcome_increment=3,
        status="ok",
        error_message=None,
    )
    second = hb.compute_next_state(
        first,
        now=_ts(2026, 5, 17, 0, 6, 0),  # different bucket (00:05-00:10)
        outcome_increment=2,
        status="ok",
        error_message=None,
    )
    assert second["last_outcome_counter_value"] == 2
    assert second["last_period_start"] == "2026-05-17T00:05:00+00:00"


def test_error_status_and_message_persist():
    state = hb.compute_next_state(
        None,
        now=_ts(2026, 5, 17, 0, 1, 0),
        outcome_increment=0,
        status="error",
        error_message="HMAC verification failed",
    )
    assert state["last_status"] == "error"
    assert state["last_error_message"] == "HMAC verification failed"
    assert state["last_outcome_counter_value"] == 0


def test_state_shape_matches_kei91_spec():
    """Spec from KEI-91: last_tick_ts, last_outcome_counter_period(_seconds),
    last_outcome_counter_value, last_status, last_error_message.
    """
    state = hb.compute_next_state(
        None,
        now=_ts(2026, 5, 17, 1, 0, 0),
        outcome_increment=1,
        status="ok",
        error_message=None,
    )
    expected_keys = {
        "last_tick_ts",
        "last_period_start",
        "last_outcome_counter_period_seconds",
        "last_outcome_counter_value",
        "last_status",
        "last_error_message",
    }
    assert set(state.keys()) == expected_keys
