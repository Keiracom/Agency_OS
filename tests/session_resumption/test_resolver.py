"""Unit tests for src.session_resumption.resolver — Drevon PR-C."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.session_resumption import resolver


@pytest.fixture
def captured_sb_get(monkeypatch):
    """Capture the (table, params) passed to sb_get and return a configurable
    response. Avoids hitting Supabase in unit tests."""
    captured: dict = {"table": None, "params": None, "response": []}

    def fake(table, params):
        captured["table"] = table
        captured["params"] = params
        return captured["response"]

    monkeypatch.setattr(resolver, "sb_get", fake)
    return captured


def test_resolve_returns_none_when_no_rows(captured_sb_get):
    captured_sb_get["response"] = []
    assert resolver.resolve_session_uuid("orion") is None
    assert captured_sb_get["table"] == "sessions"


def test_resolve_returns_session_uuid_from_first_row(captured_sb_get):
    uid = str(uuid4())
    captured_sb_get["response"] = [{"session_uuid": uid}]
    assert resolver.resolve_session_uuid("aiden") == uid


def test_resolve_filters_by_callsign(captured_sb_get):
    resolver.resolve_session_uuid("max")
    assert captured_sb_get["params"]["callsign"] == "eq.max"


def test_resolve_filters_to_resumable_statuses(captured_sb_get):
    """PR-C clean-close: status IN ('active', 'closed_clean'). Stuck/closed
    sessions are still skipped; closed_clean rows (planned restart) ARE
    resumable so the next launcher exec can `claude --resume <uuid>`."""
    resolver.resolve_session_uuid("elliot")
    assert captured_sb_get["params"]["status"] == "in.(active,closed_clean)"


def test_resolve_does_not_filter_ended_at(captured_sb_get):
    """closed_clean rows have ended_at set by the Stop hook but are still
    resumable, so the resolver must NOT add ended_at IS NULL."""
    resolver.resolve_session_uuid("scout")
    assert "ended_at" not in captured_sb_get["params"]
    assert captured_sb_get["params"]["deleted_at"] == "is.null"


def test_resolve_returns_uuid_from_closed_clean_row(captured_sb_get):
    """Empirical contract: planned tmux kill → Stop hook writes
    status='closed_clean' + ended_at → next launcher resolves the same UUID
    so `claude --resume` actually fires."""
    uid = str(uuid4())
    captured_sb_get["response"] = [{"session_uuid": uid}]
    assert resolver.resolve_session_uuid("aiden") == uid


def test_resolve_requires_session_uuid_present(captured_sb_get):
    """A row with NULL session_uuid is not resumable — Claude needs a UUID
    to --resume against."""
    resolver.resolve_session_uuid("atlas")
    assert captured_sb_get["params"]["session_uuid"] == "not.is.null"


def test_resolve_orders_by_started_at_desc_limit_1(captured_sb_get):
    resolver.resolve_session_uuid("orion")
    assert captured_sb_get["params"]["order"] == "started_at.desc"
    assert captured_sb_get["params"]["limit"] == "1"


def test_resolve_freshness_window_uses_default_30_minutes(captured_sb_get):
    resolver.resolve_session_uuid("orion")
    cutoff = captured_sb_get["params"]["started_at"]
    assert cutoff.startswith("gte.")
    parsed = datetime.fromisoformat(cutoff.removeprefix("gte."))
    delta = datetime.now(UTC) - parsed
    # 30 minutes ± 5s wiggle for execution time.
    assert timedelta(minutes=29, seconds=55) <= delta <= timedelta(minutes=30, seconds=5)


def test_resolve_freshness_window_honours_argument(captured_sb_get):
    resolver.resolve_session_uuid("orion", fresh_minutes=5)
    cutoff = captured_sb_get["params"]["started_at"]
    parsed = datetime.fromisoformat(cutoff.removeprefix("gte."))
    delta = datetime.now(UTC) - parsed
    assert timedelta(minutes=4, seconds=55) <= delta <= timedelta(minutes=5, seconds=5)


def test_resolve_returns_none_when_supabase_raises(monkeypatch):
    """Best-effort contract — supabase failure must not crash the launcher."""

    def boom(table, params):
        raise RuntimeError("supabase unreachable")

    monkeypatch.setattr(resolver, "sb_get", boom)
    assert resolver.resolve_session_uuid("orion") is None


def test_claim_session_uuid_delegates_to_record_session_start(monkeypatch):
    """claim_session_uuid must NOT duplicate schema knowledge; it forwards to
    src.session_store.recorder.record_session_start verbatim."""
    captured: dict = {}

    def fake_record(callsign, working_directory, **kwargs):
        captured["callsign"] = callsign
        captured["working_directory"] = working_directory
        captured["kwargs"] = kwargs
        return uuid4()

    monkeypatch.setattr(
        "src.session_store.recorder.record_session_start",
        fake_record,
    )
    new_uid = "11111111-2222-3333-4444-555555555555"
    result = resolver.claim_session_uuid(
        "orion",
        new_uid,
        "/home/elliotbot/clawd/Agency_OS-orion",
        tmux_session="orion",
        model_id="claude-opus-4-7",
    )
    assert result is not None
    assert captured["callsign"] == "orion"
    assert captured["working_directory"] == "/home/elliotbot/clawd/Agency_OS-orion"
    assert captured["kwargs"]["session_uuid"] == new_uid
    assert captured["kwargs"]["tmux_session"] == "orion"
    assert captured["kwargs"]["model_id"] == "claude-opus-4-7"
