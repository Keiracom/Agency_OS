"""Cost circuit breaker wiring tests for src.dispatcher.main (Agency_OS-wdws).

Covers the OUTER fail-SAFE breaker on /dispatcher/spawn:
  - no breaker → spawn proceeds (None default)
  - under ceilings → spawn proceeds
  - HALT → spawn skipped, HTTP 200 decision=cost_halt, SessionManager.spawn not called
  - Dave-DM bypass → spawn proceeds even over ceiling
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.dispatcher.cost_breaker import CostBreaker
from src.dispatcher.tmux_lifecycle import SessionHandle


def _make_breaker(daily_cents: int, monthly_cents: int = 0) -> CostBreaker:
    async def reader(tenant_id: int, period: str) -> int:
        return {"daily": daily_cents, "monthly": monthly_cents}[period]

    return CostBreaker(
        daily_alert_cents=2000,
        daily_halt_cents=3000,
        monthly_halt_cents=35000,
        alert_emitter=lambda _p: None,
        spend_reader=reader,
    )


def _mock_supervisors(main_mod: Any) -> None:
    main_mod._watchdog = MagicMock()
    main_mod._reaper = MagicMock()
    main_mod._reaper.health_snapshot.return_value = {"tracked_tmux": 0, "tracked_containers": 0}
    main_mod._watchdog.tracked = 0


def _handle() -> SessionHandle:
    return SessionHandle(session_name="disp-test", working_dir="/tmp", command="claude")


def _envs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")


def test_no_breaker_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _envs(monkeypatch)
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_cost_breaker(None)
    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
    ):
        MockSM.return_value.spawn.return_value = _handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = client.post(
            "/dispatcher/spawn", json={"backend": "tmux", "key": "k1", "spawn_kwargs": {}}
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["spawned"] is True


def test_under_ceiling_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _envs(monkeypatch)
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_cost_breaker(_make_breaker(daily_cents=500))  # A$5
    try:
        with (
            patch("src.dispatcher.main.SessionManager") as MockSM,
            patch.object(main_mod, "_register_session"),
        ):
            MockSM.return_value.spawn.return_value = _handle()
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            resp = client.post(
                "/dispatcher/spawn", json={"backend": "tmux", "key": "k1", "spawn_kwargs": {}}
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["spawned"] is True
    finally:
        main_mod._set_cost_breaker(None)


def test_halt_skips_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    _envs(monkeypatch)
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_cost_breaker(_make_breaker(daily_cents=5000))  # A$50 > A$30 halt
    try:
        with patch("src.dispatcher.main.SessionManager") as MockSM:
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            resp = client.post(
                "/dispatcher/spawn", json={"backend": "tmux", "key": "k1", "spawn_kwargs": {}}
            )
            MockSM.return_value.spawn.assert_not_called()
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["spawned"] is False
        assert body["decision"] == "cost_halt"
        assert body["daily_spend_aud"] == 50.0
    finally:
        main_mod._set_cost_breaker(None)


def test_monthly_cap_halts(monkeypatch: pytest.MonkeyPatch) -> None:
    _envs(monkeypatch)
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_cost_breaker(_make_breaker(daily_cents=500, monthly_cents=40000))  # A$400/mo
    try:
        with patch("src.dispatcher.main.SessionManager") as MockSM:
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            resp = client.post(
                "/dispatcher/spawn", json={"backend": "tmux", "key": "k1", "spawn_kwargs": {}}
            )
            MockSM.return_value.spawn.assert_not_called()
        assert resp.json()["decision"] == "cost_halt"
    finally:
        main_mod._set_cost_breaker(None)


def test_dave_dm_bypasses_halt(monkeypatch: pytest.MonkeyPatch) -> None:
    _envs(monkeypatch)
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_cost_breaker(_make_breaker(daily_cents=5000))  # over halt
    try:
        with (
            patch("src.dispatcher.main.SessionManager") as MockSM,
            patch.object(main_mod, "_register_session"),
        ):
            MockSM.return_value.spawn.return_value = _handle()
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            resp = client.post(
                "/dispatcher/spawn",
                json={"backend": "tmux", "key": "k1", "spawn_kwargs": {"from": "dave"}},
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["spawned"] is True  # CEO never blocked
    finally:
        main_mod._set_cost_breaker(None)


def test_set_cost_breaker_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    _envs(monkeypatch)
    import src.dispatcher.main as main_mod

    breaker = _make_breaker(daily_cents=0)
    main_mod._set_cost_breaker(breaker)
    assert main_mod._cost_breaker is breaker
    main_mod._set_cost_breaker(None)
    assert main_mod._cost_breaker is None
