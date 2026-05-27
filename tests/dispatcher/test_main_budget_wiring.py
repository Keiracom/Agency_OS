"""KEI-213 — budget ceiling gate wiring tests for src.dispatcher.main.

Covers the cutover-step-4.5 wiring of PR #1203 BudgetCeilingGate into the
/dispatcher/spawn endpoint:
  - no-gate fail-open (rollout phase 1 default, _budget_gate=None)
  - SPAWN_OK / DAVE_BYPASS → spawn proceeds
  - QUEUE_NEXT_DAY / DROP_WITH_LOG → spawn skipped, HTTP 200 with decision name

bd: cutover-step-4.5-dispatcher-wiring-pr-B (KEI-213 mirror of PR #1218)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.dispatcher.tmux_lifecycle import SessionHandle
from src.relay.budget_ceiling import BudgetCeilingGate, BudgetDecision


class _FakeDB:
    """Fake DB cursor returning a fixed request_count → fleet spend."""

    def __init__(self, request_count: int = 0):
        self._request_count = request_count
        self._row: tuple[int] | None = None

    def execute(self, query: str, *params: Any) -> None:
        self._row = (self._request_count,)

    def fetchone(self) -> tuple[int] | None:
        return self._row


def _make_gate(*, request_count: int = 0, budget_aud: float = 25.0) -> BudgetCeilingGate:
    return BudgetCeilingGate(
        db=_FakeDB(request_count=request_count),
        daily_budget_aud=budget_aud,
        alerts_emitter=lambda _payload: None,
    )


def _mock_supervisors(main_mod: Any) -> None:
    main_mod._watchdog = MagicMock()
    main_mod._reaper = MagicMock()
    main_mod._reaper.health_snapshot.return_value = {
        "tracked_tmux": 0,
        "tracked_containers": 0,
    }
    main_mod._watchdog.tracked = 0


def _make_handle() -> SessionHandle:
    return SessionHandle(session_name="disp-test", working_dir="/tmp", command="claude")


# ----- no-gate fail-open -----


def test_no_gate_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_budget_gate(None)

    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = client.post(
            "/dispatcher/spawn",
            json={"backend": "tmux", "key": "k1", "spawn_kwargs": {}},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["spawned"] is True


# ----- SPAWN_OK proceeds -----


def test_spawn_ok_under_budget_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_budget_gate(_make_gate(request_count=0, budget_aud=25.0))

    try:
        with (
            patch("src.dispatcher.main.SessionManager") as MockSM,
            patch.object(main_mod, "_register_session"),
        ):
            MockSM.return_value.spawn.return_value = _make_handle()
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            resp = client.post(
                "/dispatcher/spawn",
                json={"backend": "tmux", "key": "k1", "spawn_kwargs": {}},
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["spawned"] is True
    finally:
        main_mod._set_budget_gate(None)


# ----- DAVE_BYPASS proceeds -----


def test_dave_dm_bypass_proceeds_even_over_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    main_mod._set_budget_gate(_make_gate(request_count=1000, budget_aud=25.0))

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
                    "spawn_kwargs": {"from": "dave"},
                },
            )
        assert resp.status_code == 200, resp.text
        # Dave bypass means spawn proceeds — body should be the normal spawn response
        assert resp.json()["spawned"] is True
    finally:
        main_mod._set_budget_gate(None)


# ----- QUEUE_NEXT_DAY skips spawn -----


def test_normal_priority_over_budget_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    _mock_supervisors(main_mod)
    # 100 req × 0.79 AUD = 79 AUD > 25 AUD budget; priority=normal → QUEUE_NEXT_DAY
    main_mod._set_budget_gate(_make_gate(request_count=100, budget_aud=25.0))

    try:
        with patch("src.dispatcher.main.SessionManager") as MockSM:
            client = TestClient(main_mod.app, raise_server_exceptions=False)
            resp = client.post(
                "/dispatcher/spawn",
                json={"backend": "tmux", "key": "k1", "spawn_kwargs": {}},
            )
            MockSM.return_value.spawn.assert_not_called()
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["spawned"] is False
        assert body["decision"] == BudgetDecision.QUEUE_NEXT_DAY.value
        assert "current_day_spend_aud" in body
        assert body["daily_budget_aud"] == 25.0
    finally:
        main_mod._set_budget_gate(None)


# ----- DI helper smoke -----


def test_set_budget_gate_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    gate = _make_gate()
    main_mod._set_budget_gate(gate)
    assert main_mod._budget_gate is gate
    main_mod._set_budget_gate(None)
    assert main_mod._budget_gate is None
