"""Tests for the _spawned-dict GC inside _reaper_loop (Elliot 2026-05-30).

Without this GC, sessions that exit naturally (api_agent_cold_start finishes,
tmux closes) remain in _spawned forever. check_physical_ceiling reads
len(_spawned) and queues new spawns despite the box being idle.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.dispatcher import main as dmain


def _spawned_entry(session_name: str, backend: str = "tmux") -> dict:
    handle = MagicMock()
    handle.session_name = session_name
    return {"handle": handle, "backend": backend, "tenant_id": None}


async def _run_one_reaper_iteration() -> None:
    """Drive _reaper_loop through exactly one iteration then cancel.

    Patches asyncio.sleep so the iteration runs immediately. The sweep call
    is patched to a no-op since the GC path doesn't depend on its result.
    """
    rp = MagicMock()
    rp.sweep.return_value = MagicMock(total_reaped=0)

    real_sleep = asyncio.sleep

    iterations = {"n": 0}

    async def fake_sleep(_secs):
        iterations["n"] += 1
        if iterations["n"] >= 2:
            # Allow at least one full body pass before cancelling.
            raise asyncio.CancelledError
        await real_sleep(0)

    with patch.object(dmain.asyncio, "sleep", fake_sleep), pytest.raises(asyncio.CancelledError):
        await dmain._reaper_loop(rp)


def test_reaper_gc_removes_completed_tmux_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    """tmux session listed live → keep. Not listed → pop + unregister watchdog."""
    monkeypatch.setattr(dmain, "_spawned", {})
    dmain._spawned["alive"] = _spawned_entry("disp-alive-session")
    dmain._spawned["dead"] = _spawned_entry("disp-dead-session")

    fake_watchdog = MagicMock()
    monkeypatch.setattr(dmain, "_watchdog", fake_watchdog)

    monkeypatch.setattr(
        dmain, "_list_tmux_sessions", lambda: ["disp-alive-session", "other-system"]
    )

    asyncio.run(_run_one_reaper_iteration())

    assert "alive" in dmain._spawned
    assert "dead" not in dmain._spawned
    fake_watchdog.unregister.assert_called_once_with("dead")


def test_reaper_gc_skips_non_tmux_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    """Container backends are NOT in the tmux ls universe — keep them
    untouched (their lifecycle is managed by a different path)."""
    monkeypatch.setattr(dmain, "_spawned", {})
    dmain._spawned["k-container"] = _spawned_entry("any", backend="docker")
    dmain._spawned["k-tmux-dead"] = _spawned_entry("disp-dead", backend="tmux")

    monkeypatch.setattr(dmain, "_watchdog", MagicMock())
    monkeypatch.setattr(dmain, "_list_tmux_sessions", lambda: [])

    asyncio.run(_run_one_reaper_iteration())

    assert "k-container" in dmain._spawned  # untouched
    assert "k-tmux-dead" not in dmain._spawned  # GC'd


def test_reaper_gc_skipped_when_tmux_ls_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`_list_tmux_sessions` returning None (transient tmux probe failure) →
    GC pass skips entirely; no entries removed (fail-safe — don't drop
    sessions based on a None-signal)."""
    monkeypatch.setattr(dmain, "_spawned", {})
    dmain._spawned["k1"] = _spawned_entry("any-session")

    monkeypatch.setattr(dmain, "_watchdog", MagicMock())
    monkeypatch.setattr(dmain, "_list_tmux_sessions", lambda: None)

    asyncio.run(_run_one_reaper_iteration())

    assert "k1" in dmain._spawned  # preserved on None
