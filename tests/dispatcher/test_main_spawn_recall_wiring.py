"""Wave 3 — spawn-recall lifecycle hook wiring tests for src.dispatcher.main.

Covers the /dispatcher/spawn integration of src/retrieval/spawn_recall:
  - flag off  → no recall, spawn env untouched
  - flag on   → recall fires, top-3 block injected into spawn env
  - recall failure → fail-open, spawn still succeeds

Mirrors tests/dispatcher/test_main_spawn_attribution_wiring.py: SessionManager
is mocked so spawn_kwargs is never forwarded to the real backend.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.dispatcher.tmux_lifecycle import SessionHandle
from src.retrieval import spawn_recall


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


def _spawn(main_mod: Any, spawn_kwargs: dict) -> tuple[Any, Any]:
    """Drive one /dispatcher/spawn call; return (response, spawn MagicMock)."""
    _mock_supervisors(main_mod)
    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = client.post(
            "/dispatcher/spawn",
            json={"backend": "tmux", "key": "k1", "spawn_kwargs": spawn_kwargs},
        )
        return resp, MockSM.return_value.spawn


def _base_env(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    return main_mod


# ─── flag off ────────────────────────────────────────────────────────────────


def test_disabled_does_not_inject_prior_context(monkeypatch: pytest.MonkeyPatch) -> None:
    main_mod = _base_env(monkeypatch)
    monkeypatch.setattr(main_mod, "spawn_recall_enabled", False)
    # Guard: query_for_spawn must not even be reached when the flag is off.
    monkeypatch.setattr(
        main_mod.spawn_recall,
        "query_for_spawn",
        lambda *a, **k: pytest.fail("recall fired while disabled"),
    )

    resp, spawn = _spawn(main_mod, {"brief": "do thing"})

    assert resp.status_code == 200, resp.text
    env = spawn.call_args.kwargs.get("env") or {}
    assert spawn_recall.PRIOR_CONTEXT_ENV_KEY not in env


# ─── flag on ─────────────────────────────────────────────────────────────────


def test_enabled_injects_top3_block_into_spawn_env(monkeypatch: pytest.MonkeyPatch) -> None:
    main_mod = _base_env(monkeypatch)
    monkeypatch.setattr(main_mod, "spawn_recall_enabled", True)
    monkeypatch.setattr(
        main_mod.spawn_recall,
        "query_for_spawn",
        lambda task_type, task_brief: ["[D-1 · Decisions] canonical approach is X"],
    )

    resp, spawn = _spawn(main_mod, {"brief": "ship feature", "callsign": "orion"})

    assert resp.status_code == 200, resp.text
    injected = spawn.call_args.kwargs["env"][spawn_recall.PRIOR_CONTEXT_ENV_KEY]
    assert spawn_recall.BLOCK_HEADER in injected
    assert "canonical approach is X" in injected


def test_enabled_passes_derived_task_type_and_brief(monkeypatch: pytest.MonkeyPatch) -> None:
    main_mod = _base_env(monkeypatch)
    monkeypatch.setattr(main_mod, "spawn_recall_enabled", True)
    seen: dict[str, str] = {}

    def _capture(task_type: str, task_brief: str) -> list[str]:
        seen["task_type"] = task_type
        seen["task_brief"] = task_brief
        return []

    monkeypatch.setattr(main_mod.spawn_recall, "query_for_spawn", _capture)

    # No spawn_kwargs task_type → derived from REVIEW-PR registry key.
    _mock_supervisors(main_mod)
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
                "key": "REVIEW-PR-1238",
                "spawn_kwargs": {"brief": "check the hook tests"},
            },
        )

    assert resp.status_code == 200, resp.text
    assert seen["task_type"] == "pr_review"
    assert seen["task_brief"] == "check the hook tests"


# ─── fail-open ───────────────────────────────────────────────────────────────


def test_recall_failure_does_not_block_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    main_mod = _base_env(monkeypatch)
    monkeypatch.setattr(main_mod, "spawn_recall_enabled", True)

    def _boom(*_a: Any, **_k: Any) -> list[str]:
        raise RuntimeError("simulated hindsight failure")

    monkeypatch.setattr(main_mod.spawn_recall, "query_for_spawn", _boom)

    resp, spawn = _spawn(main_mod, {"brief": "do thing"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["spawned"] is True
    # Fail-open: no block injected, spawn proceeded.
    env = spawn.call_args.kwargs.get("env") or {}
    assert spawn_recall.PRIOR_CONTEXT_ENV_KEY not in env
