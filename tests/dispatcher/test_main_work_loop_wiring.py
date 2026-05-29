"""Dispatcher → work-loop exit-hook wiring (Agency_OS-innu).

Proves /dispatcher/terminate calls work_loop.release_on_exit with the tenant_id
retained in the _spawned registry. release_on_exit is patched (its own behaviour
is covered in tests/keiracom_system/work_loop/test_integration.py).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.dispatcher.main as main_mod
from src.dispatcher.tmux_lifecycle import SessionHandle


async def test_terminate_calls_release_on_exit_with_tenant_id(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(main_mod, "_watchdog", MagicMock(tracked=0))
    monkeypatch.setattr(main_mod, "_reaper", MagicMock())
    monkeypatch.setattr(main_mod, "_bounded_spawn_enforcer", None)
    handle = SessionHandle(session_name="disp-x", working_dir="/tmp", command="bash")
    main_mod._spawned["k9"] = {
        "handle": handle,
        "backend": main_mod.Backend("tmux"),
        "tenant_id": "tnt",
    }

    with (
        patch.object(main_mod, "SessionManager"),
        patch.object(main_mod.work_loop, "release_on_exit", new=AsyncMock()) as rel,
    ):
        resp = await main_mod.dispatcher_terminate(main_mod.TerminateRequest(key="k9"))

    assert resp["terminated"] is True
    rel.assert_awaited_once_with("tnt", "k9")


async def test_terminate_without_tenant_id_skips_release(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(main_mod, "_watchdog", MagicMock(tracked=0))
    monkeypatch.setattr(main_mod, "_reaper", MagicMock())
    monkeypatch.setattr(main_mod, "_bounded_spawn_enforcer", None)
    handle = SessionHandle(session_name="disp-y", working_dir="/tmp", command="bash")
    main_mod._spawned["k0"] = {
        "handle": handle,
        "backend": main_mod.Backend("tmux"),
        "tenant_id": None,
    }

    with (
        patch.object(main_mod, "SessionManager"),
        patch.object(main_mod.work_loop, "release_on_exit", new=AsyncMock()) as rel,
    ):
        await main_mod.dispatcher_terminate(main_mod.TerminateRequest(key="k0"))

    rel.assert_not_awaited()  # non-work-loop spawn → no release
