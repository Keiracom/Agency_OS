"""Unit tests for src.session_resumption.watchdog — Drevon PR-C."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.session_resumption import watchdog


@pytest.fixture
def captured_sb_get(monkeypatch):
    captured: dict = {"table": None, "params": None, "response": []}

    def fake(table, params):
        captured["table"] = table
        captured["params"] = params
        return captured["response"]

    monkeypatch.setattr(watchdog, "sb_get", fake)
    return captured


@pytest.fixture
def captured_mark_stuck(monkeypatch):
    """Capture every UUID passed to mark_session_stuck."""
    captured: list = []

    def fake(session_id):
        captured.append(session_id)

    monkeypatch.setattr(
        "src.session_store.recorder.mark_session_stuck",
        fake,
    )
    return captured


def test_clear_returns_zero_when_no_stale_rows(captured_sb_get, captured_mark_stuck):
    captured_sb_get["response"] = []
    assert watchdog.clear_stuck_sessions() == 0
    assert captured_mark_stuck == []


def test_clear_marks_each_stale_row_as_stuck(captured_sb_get, captured_mark_stuck):
    ids = [str(uuid4()) for _ in range(3)]
    captured_sb_get["response"] = [{"id": i} for i in ids]
    cleared = watchdog.clear_stuck_sessions()
    assert cleared == 3
    assert {str(u) for u in captured_mark_stuck} == set(ids)


def test_clear_filters_to_active_unended_undeleted(captured_sb_get, captured_mark_stuck):
    watchdog.clear_stuck_sessions()
    p = captured_sb_get["params"]
    assert p["status"] == "eq.active"
    assert p["ended_at"] == "is.null"
    assert p["deleted_at"] == "is.null"


def test_clear_uses_lt_started_at_with_default_60_minutes(captured_sb_get, captured_mark_stuck):
    watchdog.clear_stuck_sessions()
    cutoff = captured_sb_get["params"]["started_at"]
    assert cutoff.startswith("lt.")
    parsed = datetime.fromisoformat(cutoff.removeprefix("lt."))
    delta = datetime.now(UTC) - parsed
    assert timedelta(minutes=59, seconds=55) <= delta <= timedelta(minutes=60, seconds=5)


def test_clear_honours_stuck_minutes_argument(captured_sb_get, captured_mark_stuck):
    watchdog.clear_stuck_sessions(stuck_minutes=10)
    cutoff = captured_sb_get["params"]["started_at"]
    parsed = datetime.fromisoformat(cutoff.removeprefix("lt."))
    delta = datetime.now(UTC) - parsed
    assert timedelta(minutes=9, seconds=55) <= delta <= timedelta(minutes=10, seconds=5)


def test_clear_scopes_to_callsign_when_provided(captured_sb_get, captured_mark_stuck):
    watchdog.clear_stuck_sessions(callsign="orion")
    assert captured_sb_get["params"]["callsign"] == "eq.orion"


def test_clear_omits_callsign_filter_when_scope_is_all(captured_sb_get, captured_mark_stuck):
    watchdog.clear_stuck_sessions(callsign=None)
    assert "callsign" not in captured_sb_get["params"]


def test_clear_returns_zero_when_supabase_raises(monkeypatch, captured_mark_stuck):
    """Best-effort contract — watchdog must never crash the surrounding
    scheduler if Supabase is unreachable."""

    def boom(table, params):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(watchdog, "sb_get", boom)
    assert watchdog.clear_stuck_sessions() == 0
    assert captured_mark_stuck == []


def test_clear_skips_rows_missing_id(captured_sb_get, captured_mark_stuck):
    captured_sb_get["response"] = [{"id": str(uuid4())}, {"id": None}, {}]
    cleared = watchdog.clear_stuck_sessions()
    assert cleared == 1


def test_clear_continues_when_individual_mark_stuck_raises(captured_sb_get, monkeypatch):
    ids = [str(uuid4()) for _ in range(3)]
    captured_sb_get["response"] = [{"id": i} for i in ids]
    call_count = {"n": 0}

    def fake(session_id):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("transient DB blip")

    monkeypatch.setattr(
        "src.session_store.recorder.mark_session_stuck",
        fake,
    )
    cleared = watchdog.clear_stuck_sessions()
    assert cleared == 2  # rows 1 and 3 succeed; row 2 swallowed
