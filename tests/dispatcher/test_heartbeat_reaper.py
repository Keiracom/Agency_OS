"""KEI-211 — tests for src.dispatcher.heartbeat_reaper.

Covers:
  - thread_count_key() namespace + blank rejection
  - _mark_task_failed() idempotent UPDATE
  - _decrement_thread_count() with floor-at-zero behaviour
  - _log_reap_observation() with reaper_observation source_type
  - reap_one() all-legs success + partial-failure fail-open
  - parse_zombie_event() valid + malformed payloads
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dispatcher import heartbeat_reaper as hr

# ─── thread_count_key ────────────────────────────────────────────────────────


def test_thread_count_key_builds_namespaced():
    assert hr.thread_count_key("scout") == "thr:scout"
    assert hr.thread_count_key("  atlas  ") == "thr:atlas"


def test_thread_count_key_rejects_blank():
    with pytest.raises(ValueError, match="callsign"):
        hr.thread_count_key("")
    with pytest.raises(ValueError, match="callsign"):
        hr.thread_count_key("   ")


# ─── _mark_task_failed ───────────────────────────────────────────────────────


def test_mark_task_failed_updates_only_active_rows(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    cur = MagicMock()
    cur.rowcount = 1
    cur_ctx = MagicMock()
    cur_ctx.__enter__ = MagicMock(return_value=cur)
    cur_ctx.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_ctx
    conn.commit = MagicMock()
    conn_ctx = MagicMock()
    conn_ctx.__enter__ = MagicMock(return_value=conn)
    conn_ctx.__exit__ = MagicMock(return_value=False)
    with patch("psycopg.connect", return_value=conn_ctx):
        assert hr._mark_task_failed("task-uuid-1") is True
    sql = cur.execute.call_args[0][0]
    assert "UPDATE public.tasks" in sql
    assert "status = 'failed'" in sql
    assert "released_at = NOW()" in sql
    assert "status = 'active'" in sql  # idempotency guard


def test_mark_task_failed_returns_false_when_no_rows_affected(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    cur = MagicMock()
    cur.rowcount = 0
    cur_ctx = MagicMock()
    cur_ctx.__enter__ = MagicMock(return_value=cur)
    cur_ctx.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_ctx
    conn.commit = MagicMock()
    conn_ctx = MagicMock()
    conn_ctx.__enter__ = MagicMock(return_value=conn)
    conn_ctx.__exit__ = MagicMock(return_value=False)
    with patch("psycopg.connect", return_value=conn_ctx):
        assert hr._mark_task_failed("task-uuid-1") is False


def test_mark_task_failed_fails_open_on_db_error(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    with patch("psycopg.connect", side_effect=OSError("db down")):
        assert hr._mark_task_failed("task-uuid-1") is False


# ─── _decrement_thread_count ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decrement_thread_count_decrs_key():
    fake = MagicMock()
    fake.decr = AsyncMock(return_value=3)
    fake.set = AsyncMock()
    with patch("src.dispatcher.valkey_pool.get_valkey_client", new=AsyncMock(return_value=fake)):
        ok = await hr._decrement_thread_count("scout")
    assert ok is True
    fake.decr.assert_awaited_once_with("thr:scout")
    fake.set.assert_not_called()


@pytest.mark.asyncio
async def test_decrement_thread_count_floors_at_zero():
    """If DECR returns negative (transient over-decrement), reset to 0."""
    fake = MagicMock()
    fake.decr = AsyncMock(return_value=-1)
    fake.set = AsyncMock()
    with patch("src.dispatcher.valkey_pool.get_valkey_client", new=AsyncMock(return_value=fake)):
        ok = await hr._decrement_thread_count("scout")
    assert ok is True
    fake.set.assert_awaited_once_with("thr:scout", 0)


@pytest.mark.asyncio
async def test_decrement_thread_count_fails_open_on_valkey_error():
    with patch(
        "src.dispatcher.valkey_pool.get_valkey_client",
        new=AsyncMock(side_effect=OSError("valkey down")),
    ):
        ok = await hr._decrement_thread_count("scout")
    assert ok is False


# ─── _log_reap_observation ───────────────────────────────────────────────────


def test_log_reap_observation_uses_correct_source_type(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    cur = MagicMock()
    cur_ctx = MagicMock()
    cur_ctx.__enter__ = MagicMock(return_value=cur)
    cur_ctx.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_ctx
    conn.commit = MagicMock()
    conn_ctx = MagicMock()
    conn_ctx.__enter__ = MagicMock(return_value=conn)
    conn_ctx.__exit__ = MagicMock(return_value=False)
    with patch("psycopg.connect", return_value=conn_ctx):
        ok = hr._log_reap_observation("task-uuid-1", "scout", True)
    assert ok is True
    sql = cur.execute.call_args[0][0]
    assert "reaper_observation" in sql
    assert "agent_memories" in sql


def test_log_reap_observation_fails_open_on_db_error(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    with patch("psycopg.connect", side_effect=OSError("db down")):
        assert hr._log_reap_observation("t-1", "scout", True) is False


# ─── reap_one ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reap_one_all_legs_succeed():
    with (
        patch.object(hr, "_mark_task_failed", return_value=True),
        patch.object(hr, "_decrement_thread_count", new=AsyncMock(return_value=True)),
        patch.object(hr, "_log_reap_observation", return_value=True),
    ):
        result = await hr.reap_one("t-1", "scout")
    assert result.task_id == "t-1"
    assert result.callsign == "scout"
    assert result.task_marked_failed is True
    assert result.valkey_decremented is True
    assert result.audit_logged is True


@pytest.mark.asyncio
async def test_reap_one_partial_failure_does_not_abort_other_legs():
    """If task UPDATE fails, Valkey + audit log must still run."""
    with (
        patch.object(hr, "_mark_task_failed", return_value=False),
        patch.object(hr, "_decrement_thread_count", new=AsyncMock(return_value=True)),
        patch.object(hr, "_log_reap_observation", return_value=True),
    ):
        result = await hr.reap_one("t-1", "scout")
    assert result.task_marked_failed is False
    assert result.valkey_decremented is True
    assert result.audit_logged is True


# ─── parse_zombie_event ──────────────────────────────────────────────────────


def test_parse_zombie_event_valid_payload():
    payload = json.dumps(
        {
            "type": "zombie_detected",
            "task_id": "t-1",
            "callsign": "scout",
            "last_heartbeat_at": "2026-05-19T12:00:00+00:00",
            "stale_seconds": 600,
        }
    ).encode()
    parsed = hr.parse_zombie_event(payload)
    assert parsed == {"task_id": "t-1", "callsign": "scout"}


def test_parse_zombie_event_wrong_type_returns_none():
    payload = json.dumps({"type": "something_else", "task_id": "t-1", "callsign": "scout"}).encode()
    assert hr.parse_zombie_event(payload) is None


def test_parse_zombie_event_missing_fields_returns_none():
    payload = json.dumps({"type": "zombie_detected", "task_id": "t-1"}).encode()  # no callsign
    assert hr.parse_zombie_event(payload) is None


def test_parse_zombie_event_malformed_json_returns_none():
    assert hr.parse_zombie_event(b"not-json") is None
