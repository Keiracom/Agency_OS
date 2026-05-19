"""KEI-211 — tests for src.dispatcher.heartbeat_watchdog.

Covers:
  - ZombieEvent dataclass + DSN munging (+asyncpg stripping)
  - poll_once() shape with mocked psycopg
  - publish_zombie() success + NATS-down fail-open
  - log_observation() success + DB-down fail-open
  - run_one_cycle() counters
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dispatcher import heartbeat_watchdog as hw

# ─── ZombieEvent + DSN helpers ───────────────────────────────────────────────


def test_zombie_event_dataclass_frozen():
    ev = hw.ZombieEvent(
        task_id="t-1", callsign="scout", last_heartbeat_at=datetime.now(UTC), stale_seconds=600
    )
    with pytest.raises(FrozenInstanceError):
        ev.task_id = "tampered"  # type: ignore[misc]


def test_dsn_strips_asyncpg_suffix(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert hw._dsn() == "postgresql://u:p@h/db"


def test_dsn_raises_when_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        hw._dsn()


# ─── poll_once ───────────────────────────────────────────────────────────────


def test_poll_once_maps_rows_to_zombie_events(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    fixed = datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)
    rows = [
        ("task-uuid-1", "scout", fixed - timedelta(seconds=600), 600),
        ("task-uuid-2", "atlas", fixed - timedelta(seconds=900), 900),
    ]
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cur_ctx = MagicMock()
    cur_ctx.__enter__ = MagicMock(return_value=cur)
    cur_ctx.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_ctx
    conn_ctx = MagicMock()
    conn_ctx.__enter__ = MagicMock(return_value=conn)
    conn_ctx.__exit__ = MagicMock(return_value=False)
    with patch("psycopg.connect", return_value=conn_ctx):
        events = hw.poll_once(threshold_seconds=300)
    assert len(events) == 2
    assert events[0].task_id == "task-uuid-1"
    assert events[0].callsign == "scout"
    assert events[0].stale_seconds == 600
    assert events[1].callsign == "atlas"


def test_poll_once_empty_returns_empty_list(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    cur = MagicMock()
    cur.fetchall.return_value = []
    cur_ctx = MagicMock()
    cur_ctx.__enter__ = MagicMock(return_value=cur)
    cur_ctx.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_ctx
    conn_ctx = MagicMock()
    conn_ctx.__enter__ = MagicMock(return_value=conn)
    conn_ctx.__exit__ = MagicMock(return_value=False)
    with patch("psycopg.connect", return_value=conn_ctx):
        assert hw.poll_once() == []


# ─── publish_zombie ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_zombie_emits_correct_subject_and_payload(monkeypatch):
    monkeypatch.setenv("NATS_URL", "nats://test:4222")
    fixed = datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)
    event = hw.ZombieEvent(
        task_id="t-1", callsign="scout", last_heartbeat_at=fixed, stale_seconds=600
    )

    captured: dict[str, object] = {}

    async def _capture(
        url, subject, payload
    ):  # NOSONAR python:S7503 — _nats_publish is awaited; mock side_effect must return awaitable
        captured["url"] = url
        captured["subject"] = subject
        captured["payload"] = payload

    with patch.object(hw, "_nats_publish", side_effect=_capture):
        ok = await hw.publish_zombie(event)

    assert ok is True
    assert captured["url"] == "nats://test:4222"
    assert captured["subject"] == "keiracom.agent.status.scout"
    import json as _j

    body = _j.loads(captured["payload"])
    assert body["type"] == "zombie_detected"
    assert body["task_id"] == "t-1"
    assert body["callsign"] == "scout"
    assert body["stale_seconds"] == 600


@pytest.mark.asyncio
async def test_publish_zombie_fails_open_on_nats_down():
    event = hw.ZombieEvent(
        task_id="t-1", callsign="scout", last_heartbeat_at=datetime.now(UTC), stale_seconds=600
    )
    with patch.object(hw, "_nats_publish", side_effect=OSError("connection refused")):
        ok = await hw.publish_zombie(event)
    assert ok is False


# ─── log_observation ─────────────────────────────────────────────────────────


def test_log_observation_inserts_with_correct_source_type(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    event = hw.ZombieEvent(
        task_id="t-1", callsign="scout", last_heartbeat_at=datetime.now(UTC), stale_seconds=600
    )
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
        ok = hw.log_observation(event)
    assert ok is True
    sql = cur.execute.call_args[0][0]
    assert "watchdog_observation" in sql
    assert "agent_memories" in sql


def test_log_observation_fails_open_on_db_error(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    event = hw.ZombieEvent(
        task_id="t-1", callsign="scout", last_heartbeat_at=datetime.now(UTC), stale_seconds=600
    )
    with patch("psycopg.connect", side_effect=OSError("db down")):
        ok = hw.log_observation(event)
    assert ok is False


# ─── run_one_cycle ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_one_cycle_counters_on_happy_path(monkeypatch):
    fixed = datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)
    events = [
        hw.ZombieEvent(
            task_id=f"t-{i}", callsign="scout", last_heartbeat_at=fixed, stale_seconds=600
        )
        for i in range(3)
    ]
    with (
        patch.object(hw, "poll_once", return_value=events),
        patch.object(hw, "publish_zombie", new=AsyncMock(return_value=True)),
        patch.object(hw, "log_observation", return_value=True),
    ):
        counters = await hw.run_one_cycle()
    assert counters == {"polled": 3, "published": 3, "logged": 3, "errors": 0}


@pytest.mark.asyncio
async def test_run_one_cycle_fails_open_when_poll_raises():
    with patch.object(hw, "poll_once", side_effect=OSError("db down")):
        counters = await hw.run_one_cycle()
    assert counters == {"polled": 0, "published": 0, "logged": 0, "errors": 1}


@pytest.mark.asyncio
async def test_run_one_cycle_partial_publish_failure_continues():
    fixed = datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)
    events = [
        hw.ZombieEvent(task_id="t-1", callsign="scout", last_heartbeat_at=fixed, stale_seconds=600),
        hw.ZombieEvent(task_id="t-2", callsign="atlas", last_heartbeat_at=fixed, stale_seconds=900),
    ]
    pub_results = iter([True, False])
    with (
        patch.object(hw, "poll_once", return_value=events),
        patch.object(hw, "publish_zombie", new=AsyncMock(side_effect=lambda _e: next(pub_results))),
        patch.object(hw, "log_observation", return_value=True),
    ):
        counters = await hw.run_one_cycle()
    assert counters["polled"] == 2
    assert counters["published"] == 1
    assert counters["logged"] == 2
