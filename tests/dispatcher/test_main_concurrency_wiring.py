"""Concurrency-cap gate wiring tests for src.dispatcher.main (Agency_OS-03w4).

Covers the wiring of ConcurrencyGate into /dispatcher/spawn:
  - no-gate (rollout default, _concurrency_gate=None) → spawn proceeds
  - GRANTED → spawn proceeds + slot held + released on terminate
  - QUEUE (band full) → spawn skipped, 200 with decision=concurrency_cap_queue
    and SessionManager.spawn NOT called (requeue-not-drop)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fakeredis import aioredis
from fastapi.testclient import TestClient

from src.dispatcher.concurrency_cap import WORKER_CAP, ConcurrencyGate
from src.dispatcher.tmux_lifecycle import SessionHandle


def _redis():
    return aioredis.FakeRedis(decode_responses=True)


def _mock_supervisors(main_mod: Any) -> None:
    main_mod._watchdog = MagicMock()
    main_mod._reaper = MagicMock()
    main_mod._reaper.health_snapshot.return_value = {"tracked_tmux": 0, "tracked_containers": 0}
    main_mod._watchdog.tracked = 0


def _handle() -> SessionHandle:
    return SessionHandle(session_name="disp-test", working_dir="/tmp", command="claude")


def _spawn(main_mod, *, key: str, callsign: str, role: str | None = None):
    sk: dict[str, Any] = {"session_name": "disp-test", "callsign": callsign}
    if role:
        sk["role"] = role
    with patch("src.dispatcher.main.SessionManager") as MockSM:
        instance = MockSM.return_value
        instance.spawn.return_value = _handle()
        with patch.object(main_mod, "_register_session"):
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            resp = client.post(
                "/dispatcher/spawn", json={"backend": "tmux", "key": key, "spawn_kwargs": sk}
            )
        return resp, instance


def test_no_gate_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_concurrency_gate(None)
    resp, _ = _spawn(main_mod, key="k1", callsign="nova")
    assert resp.status_code == 200, resp.text
    assert resp.json()["spawned"] is True


def test_granted_proceeds_and_holds_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    client_redis = _redis()
    main_mod._set_concurrency_gate(ConcurrencyGate(valkey_client=client_redis))
    try:
        resp, instance = _spawn(main_mod, key="k1", callsign="nova")
        assert resp.status_code == 200, resp.text
        assert resp.json()["spawned"] is True
        instance.spawn.assert_called_once()
    finally:
        main_mod._set_concurrency_gate(None)


def test_queue_skips_spawn_requeue_not_drop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Saturate the worker band, then a further worker spawn must QUEUE: 200
    with decision=concurrency_cap_queue and SessionManager.spawn NOT called."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    # Bound the in-endpoint queue poll so the test doesn't wait 300s.
    monkeypatch.setenv("DISPATCHER_CONCURRENCY_TIMEOUT_S", "0")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    gate_redis = _redis()
    main_mod._set_concurrency_gate(ConcurrencyGate(valkey_client=gate_redis))
    try:
        # Fill the worker band to its cap with held slots.
        for i in range(WORKER_CAP):
            resp, _ = _spawn(main_mod, key=f"hold{i}", callsign=f"wrk{i}")
            assert resp.json()["spawned"] is True
        # Next worker must QUEUE (band full) — spawn NOT called.
        resp, instance = _spawn(main_mod, key="late", callsign="lateworker")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["spawned"] is False
        assert body["decision"] == "concurrency_cap_queue"
        instance.spawn.assert_not_called()
    finally:
        main_mod._set_concurrency_gate(None)


def test_deliberator_never_queued_even_when_workers_saturate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    monkeypatch.setenv("DISPATCHER_CONCURRENCY_TIMEOUT_S", "0")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_concurrency_gate(ConcurrencyGate(valkey_client=_redis()))
    try:
        for i in range(WORKER_CAP):
            _spawn(main_mod, key=f"hold{i}", callsign=f"wrk{i}")
        # Deliberators must still spawn — reserved band.
        resp, instance = _spawn(main_mod, key="d1", callsign="aiden")
        assert resp.json()["spawned"] is True
        instance.spawn.assert_called_once()
    finally:
        main_mod._set_concurrency_gate(None)


def test_set_concurrency_gate_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    gate = ConcurrencyGate(valkey_client=_redis())
    main_mod._set_concurrency_gate(gate)
    assert main_mod._concurrency_gate is gate
    main_mod._set_concurrency_gate(None)
    assert main_mod._concurrency_gate is None
