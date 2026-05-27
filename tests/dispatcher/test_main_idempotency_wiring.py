"""KEI-213 — idempotency gate wiring tests for src.dispatcher.main.

Covers the cutover-step-4.5 wiring of PR #1204 IdempotencyGate into the
/dispatcher/spawn endpoint:
  - no-gate fail-open (rollout phase 1 default, _idempotency_gate=None)
  - SPAWN_OK → spawn proceeds normally
  - DROP_DUPLICATE → spawn skipped, HTTP 200 with decision="drop_duplicate"

bd: cutover-step-4.5-dispatcher-wiring-pr-A (KEI-213 mirror of PR #1217)
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.dispatcher.idempotency import IdempotencyGate
from src.dispatcher.tmux_lifecycle import SessionHandle


class _FakeRedis:
    """Fake redis.asyncio client implementing only `set(name, value, *, nx, ex)`.

    `claim_returns` is consumed FIFO; truthy → new claim; None → key exists.
    """

    def __init__(self, claim_returns: list[Any]):
        self._returns = list(claim_returns)
        self.calls: list[tuple[str, str, bool, int | None]] = []

    def set(
        self, name: str, value: str, *, nx: bool = False, ex: int | None = None
    ) -> Awaitable[Any]:
        self.calls.append((name, value, nx, ex))

        async def _resolve() -> Any:
            return self._returns.pop(0) if self._returns else True

        return _resolve()


def _make_gate(*, returns: list[Any]) -> IdempotencyGate:
    return IdempotencyGate(valkey_client=_FakeRedis(returns))  # type: ignore[arg-type]


def _mock_supervisors(main_mod: Any) -> None:
    """Pre-set watchdog + reaper to non-None mocks so /spawn doesn't 503."""
    main_mod._watchdog = MagicMock()
    main_mod._reaper = MagicMock()
    main_mod._reaper.health_snapshot.return_value = {
        "tracked_tmux": 0,
        "tracked_containers": 0,
    }
    main_mod._watchdog.tracked = 0


# ----- no-gate fail-open -----


def test_no_gate_proceeds_to_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    """When _idempotency_gate is None, /dispatcher/spawn must call SessionManager.spawn."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")

    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_idempotency_gate(None)

    mock_handle = SessionHandle(
        session_name="disp-test",
        working_dir="/tmp",
        command="claude",
    )

    with patch("src.dispatcher.main.SessionManager") as MockSM:
        instance = MockSM.return_value
        instance.spawn.return_value = mock_handle
        with patch.object(main_mod, "_register_session"):
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            resp = client.post(
                "/dispatcher/spawn",
                json={
                    "backend": "tmux",
                    "key": "test-key-1",
                    "spawn_kwargs": {"session_name": "disp-test"},
                },
            )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("spawned") is True
    # Without the gate wired, no decision="drop_duplicate" path
    assert body.get("decision") != "drop_duplicate"


# ----- SPAWN_OK proceeds -----


def test_spawn_ok_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gate returns SPAWN_OK → /spawn proceeds to SessionManager.spawn."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")

    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    gate = _make_gate(returns=[True])  # SET NX returned truthy → new claim
    main_mod._set_idempotency_gate(gate)

    mock_handle = SessionHandle(
        session_name="disp-test",
        working_dir="/tmp",
        command="claude",
    )

    try:
        with patch("src.dispatcher.main.SessionManager") as MockSM:
            instance = MockSM.return_value
            instance.spawn.return_value = mock_handle
            with patch.object(main_mod, "_register_session"):
                client = TestClient(main_mod.app, raise_server_exceptions=False)
                resp = client.post(
                    "/dispatcher/spawn",
                    json={
                        "backend": "tmux",
                        "key": "test-key-1",
                        "spawn_kwargs": {"session_name": "disp-test"},
                    },
                )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body.get("spawned") is True
    finally:
        main_mod._set_idempotency_gate(None)


# ----- DROP_DUPLICATE skips spawn -----


def test_drop_duplicate_skips_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gate returns DROP_DUPLICATE → /spawn returns 200 with decision=drop_duplicate."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")

    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    gate = _make_gate(returns=[None])  # SET NX returned None → already-claimed
    main_mod._set_idempotency_gate(gate)

    try:
        with patch("src.dispatcher.main.SessionManager") as MockSM:
            instance = MockSM.return_value
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            resp = client.post(
                "/dispatcher/spawn",
                json={
                    "backend": "tmux",
                    "key": "test-key-duplicate",
                    "spawn_kwargs": {"session_name": "disp-test"},
                },
            )
            # Critical: SessionManager.spawn must NOT have been called
            instance.spawn.assert_not_called()

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["spawned"] is False
        assert body["decision"] == "drop_duplicate"
        assert body["key"] == "test-key-duplicate"
        assert body["backend"] == "tmux"
        assert "idempotency_key" in body
        assert body["idempotency_key"].startswith("idem:")
    finally:
        main_mod._set_idempotency_gate(None)


# ----- DI helper smoke -----


def test_set_idempotency_gate_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    """_set_idempotency_gate updates the module-level attribute correctly."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")

    import src.dispatcher.main as main_mod

    gate = _make_gate(returns=[True])
    main_mod._set_idempotency_gate(gate)
    assert main_mod._idempotency_gate is gate
    main_mod._set_idempotency_gate(None)
    assert main_mod._idempotency_gate is None


# ----- Distinct keys for distinct (backend, key) -----


def test_distinct_keys_produce_distinct_idempotency_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two spawn requests with different backend or key must produce different idempotency keys."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")

    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    # Both return None → both should report DROP_DUPLICATE,
    # but with DIFFERENT idempotency_key values.
    gate = _make_gate(returns=[None, None])
    main_mod._set_idempotency_gate(gate)

    keys: list[str] = []
    try:
        with patch("src.dispatcher.main.SessionManager"):
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            for backend, key in [("tmux", "k1"), ("container", "k1")]:
                resp = client.post(
                    "/dispatcher/spawn",
                    json={"backend": backend, "key": key, "spawn_kwargs": {}},
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["decision"] == "drop_duplicate"
                keys.append(body["idempotency_key"])

        assert len(set(keys)) == 2, f"expected distinct keys, got {keys}"
    finally:
        main_mod._set_idempotency_gate(None)
