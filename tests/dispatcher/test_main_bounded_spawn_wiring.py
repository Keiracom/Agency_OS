"""Wiring tests for bounded-spawn enforcer in /dispatcher/spawn + /terminate.

Agency_OS-gcpm / Audit RED-7. Verifies:
  - no-enforcer fail-open (default state)
  - first spawn for a callsign records as new active slot
  - second spawn for same callsign + different task_id → violation kills prior
  - /dispatcher/terminate releases the active slot so a fresh task is not flagged
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.dispatcher.bounded_spawn_enforcer import (
    DECISION_RECORDED,
    DECISION_VIOLATION,
    BoundedSpawnEnforcer,
)
from src.dispatcher.tmux_lifecycle import SessionHandle


def _mock_supervisors(main_mod: Any) -> None:
    main_mod._watchdog = MagicMock()
    main_mod._reaper = MagicMock()
    main_mod._reaper.health_snapshot.return_value = {
        "tracked_tmux": 0,
        "tracked_containers": 0,
    }
    main_mod._watchdog.tracked = 0


def _make_handle(name: str = "disp-test") -> SessionHandle:
    return SessionHandle(session_name=name, working_dir="/tmp", command="claude")


# ---------- no enforcer = fail-open ----------


def test_no_enforcer_spawn_proceeds_without_bounded_spawn_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_bounded_spawn_enforcer(None)

    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = client.post(
            "/dispatcher/spawn",
            json={
                "backend": "tmux",
                "key": "k1",
                "spawn_kwargs": {"callsign": "orion"},
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["spawned"] is True
    assert "bounded_spawn" not in body


# ---------- first spawn = recorded ----------


def test_first_spawn_records_active_slot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    enforcer = BoundedSpawnEnforcer(
        terminate_cb=MagicMock(return_value=True),
        alerts_emitter=MagicMock(),
        audit_log_path=tmp_path / "v.jsonl",
    )
    main_mod._set_bounded_spawn_enforcer(enforcer)

    try:
        with (
            patch("src.dispatcher.main.SessionManager") as MockSM,
            patch.object(main_mod, "_register_session"),
        ):
            MockSM.return_value.spawn.return_value = _make_handle()
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            resp = client.post(
                "/dispatcher/spawn",
                json={
                    "backend": "tmux",
                    "key": "k1",
                    "spawn_kwargs": {"callsign": "orion", "task_id": "t1"},
                },
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["spawned"] is True
        assert body["bounded_spawn"]["decision"] == DECISION_RECORDED
        assert body["bounded_spawn"]["killed_prior"] is False
        # Enforcer state reflects active slot.
        snap = enforcer.snapshot()
        assert "orion" in snap
        assert snap["orion"]["task_id"] == "t1"
    finally:
        main_mod._set_bounded_spawn_enforcer(None)


# ---------- violation path ----------


def test_second_distinct_task_violates_kills_prior(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    terminate_mock = MagicMock(return_value=True)
    alerts_mock = MagicMock()
    enforcer = BoundedSpawnEnforcer(
        terminate_cb=terminate_mock,
        alerts_emitter=alerts_mock,
        audit_log_path=tmp_path / "v.jsonl",
    )
    main_mod._set_bounded_spawn_enforcer(enforcer)

    try:
        with (
            patch("src.dispatcher.main.SessionManager") as MockSM,
            patch.object(main_mod, "_register_session"),
        ):
            MockSM.return_value.spawn.return_value = _make_handle()
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            # First task — fresh slot.
            r1 = client.post(
                "/dispatcher/spawn",
                json={
                    "backend": "tmux",
                    "key": "k1",
                    "spawn_kwargs": {"callsign": "orion", "task_id": "t1"},
                },
            )
            assert r1.status_code == 200, r1.text
            # Second task — different task_id, same callsign = VIOLATION.
            r2 = client.post(
                "/dispatcher/spawn",
                json={
                    "backend": "tmux",
                    "key": "k2",
                    "spawn_kwargs": {"callsign": "orion", "task_id": "t2"},
                },
            )
            assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["spawned"] is True
        assert body["bounded_spawn"]["decision"] == DECISION_VIOLATION
        assert body["bounded_spawn"]["killed_prior"] is True
        terminate_mock.assert_called_once_with("k1")
        alerts_mock.assert_called_once()
        # New task is now the active slot.
        assert enforcer.snapshot()["orion"]["task_id"] == "t2"
    finally:
        main_mod._set_bounded_spawn_enforcer(None)


# ---------- terminate releases slot ----------


def test_terminate_releases_slot_so_next_spawn_is_fresh(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    enforcer = BoundedSpawnEnforcer(
        terminate_cb=MagicMock(return_value=True),
        alerts_emitter=MagicMock(),
        audit_log_path=tmp_path / "v.jsonl",
    )
    main_mod._set_bounded_spawn_enforcer(enforcer)

    try:
        handle = _make_handle()
        # Seed _spawned manually so /terminate finds an entry.
        with (
            patch("src.dispatcher.main.SessionManager") as MockSM,
            patch.object(main_mod, "_register_session"),
        ):
            MockSM.return_value.spawn.return_value = handle
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            r1 = client.post(
                "/dispatcher/spawn",
                json={
                    "backend": "tmux",
                    "key": "k1",
                    "spawn_kwargs": {"callsign": "orion", "task_id": "t1"},
                },
            )
            assert r1.status_code == 200
            assert enforcer.snapshot()["orion"]["task_id"] == "t1"

            r_term = client.post(
                "/dispatcher/terminate",
                json={"key": "k1"},
            )
            assert r_term.status_code == 200, r_term.text
            # Slot released.
            assert enforcer.snapshot() == {}

            # Now a different task on the same callsign should be RECORDED, not VIOLATION.
            MockSM.return_value.spawn.return_value = _make_handle(name="disp-test-2")
            r2 = client.post(
                "/dispatcher/spawn",
                json={
                    "backend": "tmux",
                    "key": "k2",
                    "spawn_kwargs": {"callsign": "orion", "task_id": "t2"},
                },
            )
            assert r2.status_code == 200, r2.text
            assert r2.json()["bounded_spawn"]["decision"] == DECISION_RECORDED
    finally:
        main_mod._set_bounded_spawn_enforcer(None)


# ---------- default terminate callback path ----------


def test_default_terminate_callback_tears_down_via_spawned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    handle = _make_handle(name="disp-killme")
    main_mod._spawned["killme"] = {"handle": handle, "backend": MagicMock(value="tmux")}

    with patch("src.dispatcher.main.SessionManager") as MockSM:
        MockSM.return_value.terminate = MagicMock()
        result = main_mod._bounded_spawn_terminate("killme")
        assert result is True
        MockSM.return_value.terminate.assert_called_once_with(handle)
    # The handle was removed from _spawned.
    assert "killme" not in main_mod._spawned

    # Unknown key returns False without raising.
    assert main_mod._bounded_spawn_terminate("nope") is False
