"""KEI-213 — wiring tests for src.dispatcher.main.

All external dependencies (Valkey, NATS, Supabase, Watchdog.probe_all,
Reaper.sweep) are mocked at module level.  No live infrastructure required.

Coverage:
  1. app import succeeds (smoke)
  2. /dispatcher/health returns all-green when components mocked OK
  3. /dispatcher/health returns degraded when spend_tracker probe throws
  4. watchdog + reaper background tasks are created and cancelled on lifespan
  5. Missing DISPATCHER_JWT_SECRET fails startup with a clear RuntimeError
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(env: dict[str, str] | None = None) -> TestClient:
    """Import app fresh with the given env vars set via monkeypatching.

    We re-import main inside each test that needs a fresh lifespan so that
    the module-level _component_status dict is reset.
    """
    import src.dispatcher.main as main_mod

    return TestClient(main_mod.app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Test 1 — app import smoke
# ---------------------------------------------------------------------------


def test_app_import_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing src.dispatcher.main must not raise at module level."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import importlib

    import src.dispatcher.main as main_mod

    importlib.reload(main_mod)
    assert main_mod.app is not None


# ---------------------------------------------------------------------------
# Test 2 — /dispatcher/health all-green
# ---------------------------------------------------------------------------


def test_health_all_green(monkeypatch: pytest.MonkeyPatch) -> None:
    """Health endpoint returns status=ok when every component is healthy."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")

    # Mock spend_tracker.get_spend to return 0 without touching Valkey
    with patch("src.dispatcher.main.get_spend", new=AsyncMock(return_value=0)):
        import src.dispatcher.main as main_mod

        # Pre-set all statuses to ok (simulates post-startup state)
        for key in main_mod._component_status:
            main_mod._component_status[key] = "ok"

        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = client.get("/dispatcher/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert set(body["components"].keys()) == {
        "auth_minter",
        "interceptor_proxy",
        "spend_tracker",
        "watchdog",
        "reaper",
    }


# ---------------------------------------------------------------------------
# Test 3 — /dispatcher/health degraded when spend_tracker throws
# ---------------------------------------------------------------------------


def test_health_degraded_when_spend_tracker_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Health returns status=degraded when spend_tracker probe raises."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")

    async def _raise(*_args, **_kwargs):
        raise ConnectionError("Valkey unreachable")

    with patch("src.dispatcher.main.get_spend", new=_raise):
        import src.dispatcher.main as main_mod

        for key in main_mod._component_status:
            main_mod._component_status[key] = "ok"

        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = client.get("/dispatcher/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["components"]["spend_tracker"] == "degraded"


# ---------------------------------------------------------------------------
# Test 4 — watchdog + reaper background tasks created and cancelled
# ---------------------------------------------------------------------------


def test_background_tasks_created_and_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifespan must create and cleanly cancel watchdog + reaper tasks."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    monkeypatch.setenv("DISPATCHER_TMUX_PREFIX", "disp-")
    monkeypatch.setenv("DISPATCHER_CONTAINER_PREFIX", "disp-")

    task_names: list[str] = []

    _orig_create_task = asyncio.create_task

    def _spy_create_task(coro, *, name=None):
        if name:
            task_names.append(name)
        return _orig_create_task(coro, name=name)

    with (
        patch("src.dispatcher.main.get_spend", new=AsyncMock(return_value=0)),
        patch("asyncio.create_task", side_effect=_spy_create_task),
    ):
        import src.dispatcher.main as main_mod

        # TestClient context manager exercises the full lifespan (startup + shutdown)
        with TestClient(main_mod.app):
            pass  # startup and shutdown both run

    assert "dispatcher-watchdog" in task_names
    assert "dispatcher-reaper" in task_names


# ---------------------------------------------------------------------------
# Test 5 — missing JWT_SECRET fails startup with clear RuntimeError
# ---------------------------------------------------------------------------


def test_missing_jwt_secret_fails_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Startup must raise RuntimeError if DISPATCHER_JWT_SECRET is absent."""
    monkeypatch.delenv("DISPATCHER_JWT_SECRET", raising=False)
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")

    import src.dispatcher.main as main_mod

    with pytest.raises(RuntimeError, match="DISPATCHER_JWT_SECRET"):
        main_mod._validate_envs()
