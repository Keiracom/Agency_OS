"""Tests for KEI-63 idle-injection extensions in elliot_polling_loop.py.

Tests the new poll_kei63_idle_inject function, pane-idle heuristics, and
run_cycle wiring without any real tmux, bd, or Slack dependencies.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "orchestrator" / "elliot_polling_loop.py"


@pytest.fixture(scope="module")
def loop_mod():
    spec = importlib.util.spec_from_file_location("elliot_polling_loop_kei63", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["elliot_polling_loop_kei63"] = mod
    spec.loader.exec_module(mod)
    return mod


# ── _pane_is_idle ─────────────────────────────────────────────────────────────


def test_pane_is_idle_shell_prompt(loop_mod):
    """Pane ending with $ prompt is idle."""
    tail = "some output\n[elliot@host Agency_OS]$ "
    assert loop_mod._pane_is_idle(tail) is True


def test_pane_is_idle_hash_prompt(loop_mod):
    """Pane ending with # (root) prompt is idle."""
    tail = "root@host:~# "
    assert loop_mod._pane_is_idle(tail) is True


def test_pane_is_idle_greater_than_prompt(loop_mod):
    """Pane ending with > (e.g., Python REPL) is idle."""
    tail = ">>> "
    assert loop_mod._pane_is_idle(tail) is True


def test_pane_is_idle_mid_command(loop_mod):
    """Pane showing running command output is NOT idle."""
    tail = "Running tests...\n100%|████| 50/50 [00:12<00:00]"
    assert loop_mod._pane_is_idle(tail) is False


def test_pane_is_idle_empty(loop_mod):
    """Empty pane is NOT idle (session absent / no content)."""
    assert loop_mod._pane_is_idle("") is False
    assert loop_mod._pane_is_idle("   \n   ") is False


def test_pane_is_idle_claude_waiting(loop_mod):
    """Pane with claude UI prompt (>) at end is idle."""
    tail = "Assistant: Task complete.\n> "
    assert loop_mod._pane_is_idle(tail) is True


# ── _callsign_to_worktree ─────────────────────────────────────────────────────


def test_callsign_to_worktree_known(loop_mod):
    assert loop_mod._callsign_to_worktree("elliot") == "/home/elliotbot/clawd/Agency_OS"
    assert loop_mod._callsign_to_worktree("atlas") == "/home/elliotbot/clawd/Agency_OS-atlas"
    assert loop_mod._callsign_to_worktree("orion") == "/home/elliotbot/clawd/Agency_OS-orion"


def test_callsign_to_worktree_unknown(loop_mod):
    assert loop_mod._callsign_to_worktree("unknown") == ""


# ── poll_kei63_idle_inject ────────────────────────────────────────────────────


def test_kei63_no_injection_when_not_idle(loop_mod):
    """If _pane_idle_minutes returns 0, no injection fires."""
    with (
        patch.object(loop_mod, "_pane_idle_minutes", return_value=0.0),
        patch.object(loop_mod, "poll_bd_ready", return_value=[{"id": "Agency_OS-x", "title": "T"}]),
        patch.object(loop_mod, "inject_bd_ready_into_pane") as mock_inject,
    ):
        dispatches = loop_mod.poll_kei63_idle_inject()
    mock_inject.assert_not_called()
    assert dispatches == []


def test_kei63_injects_when_idle_and_work_available(loop_mod):
    """If pane idle > 5m and work available, inject_bd_ready_into_pane is called."""
    # Clear dedup state from previous test runs.
    loop_mod._kei63_last_ceo_alert.clear()
    with (
        patch.object(loop_mod, "_pane_idle_minutes", return_value=7.0),
        patch.object(loop_mod, "poll_bd_ready", return_value=[{"id": "Agency_OS-y", "title": "Y"}]),
        patch.object(loop_mod, "inject_bd_ready_into_pane") as mock_inject,
    ):
        dispatches = loop_mod.poll_kei63_idle_inject()
    assert mock_inject.call_count == len(loop_mod.CALLSIGN_TO_TMUX)
    assert dispatches == []  # no #ceo alert when work is available


def test_kei63_no_ceo_alert_when_idle_but_work_exists(loop_mod):
    """Idle agents with work available should NOT trigger #ceo alert."""
    loop_mod._kei63_last_ceo_alert.clear()
    with (
        patch.object(loop_mod, "_pane_idle_minutes", return_value=35.0),
        patch.object(loop_mod, "poll_bd_ready", return_value=[{"id": "Agency_OS-z", "title": "Z"}]),
        patch.object(loop_mod, "inject_bd_ready_into_pane"),
    ):
        dispatches = loop_mod.poll_kei63_idle_inject()
    ceo_dispatches = [ch for ch, _ in dispatches if ch == loop_mod.CEO_CHANNEL_NAME]
    assert len(ceo_dispatches) == 0


def test_kei63_ceo_alert_when_idle_no_work(loop_mod):
    """Idle > 30m with no work triggers #ceo alert per callsign."""
    loop_mod._kei63_last_ceo_alert.clear()
    n = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    with (
        patch.object(loop_mod, "_pane_idle_minutes", return_value=35.0),
        patch.object(loop_mod, "poll_bd_ready", return_value=[]),
        patch.object(loop_mod, "inject_bd_ready_into_pane") as mock_inject,
    ):
        dispatches = loop_mod.poll_kei63_idle_inject(now=n)
    mock_inject.assert_not_called()
    ceo_dispatches = [ch for ch, _ in dispatches if ch == loop_mod.CEO_CHANNEL_NAME]
    # One alert per callsign (all idle with no work).
    assert len(ceo_dispatches) == len(loop_mod.CALLSIGN_TO_TMUX)
    # Alert text mentions the callsign and idle time.
    for _ch, text in dispatches:
        assert "KEI-63" in text
        assert "idle" in text.lower()


def test_kei63_ceo_alert_deduped(loop_mod):
    """#ceo alerts are not repeated within KEI63_COO_ALERT_DEDUP_MINUTES."""
    loop_mod._kei63_last_ceo_alert.clear()
    n1 = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    n2 = n1 + timedelta(minutes=5)  # 5 min later — within dedup window

    with (
        patch.object(loop_mod, "_pane_idle_minutes", return_value=35.0),
        patch.object(loop_mod, "poll_bd_ready", return_value=[]),
        patch.object(loop_mod, "inject_bd_ready_into_pane"),
    ):
        dispatches_first = loop_mod.poll_kei63_idle_inject(now=n1)
        dispatches_second = loop_mod.poll_kei63_idle_inject(now=n2)

    # First cycle: alerts fire.
    assert len(dispatches_first) > 0
    # Second cycle (5 min later): all alerts deduped.
    assert len(dispatches_second) == 0


def test_kei63_ceo_alert_fires_after_dedup_window(loop_mod):
    """#ceo alert fires again after KEI63_COO_ALERT_DEDUP_MINUTES have elapsed."""
    loop_mod._kei63_last_ceo_alert.clear()
    n1 = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)
    n2 = n1 + timedelta(minutes=loop_mod.KEI63_COO_ALERT_DEDUP_MINUTES + 1)

    with (
        patch.object(loop_mod, "_pane_idle_minutes", return_value=35.0),
        patch.object(loop_mod, "poll_bd_ready", return_value=[]),
        patch.object(loop_mod, "inject_bd_ready_into_pane"),
    ):
        dispatches_first = loop_mod.poll_kei63_idle_inject(now=n1)
        dispatches_second = loop_mod.poll_kei63_idle_inject(now=n2)

    assert len(dispatches_first) > 0
    assert len(dispatches_second) > 0  # fires again after dedup window


# ── run_cycle integration ─────────────────────────────────────────────────────


def test_run_cycle_calls_kei63_inject(loop_mod):
    """run_cycle calls poll_kei63_idle_inject even when all other signals are silent."""
    loop_mod._kei63_last_ceo_alert.clear()
    n = datetime(2026, 5, 13, 22, 0, tzinfo=UTC)  # peak hour
    with (
        patch.object(loop_mod, "poll_bd_ready", return_value=[]),
        patch.object(loop_mod, "poll_linear_stale", return_value=[]),
        patch.object(loop_mod, "poll_idle_agents", return_value=[]),
        patch.object(loop_mod, "poll_prefect_failures", return_value=[]),
        patch.object(loop_mod, "poll_rate_limited_agents", return_value=[]),
        patch.object(loop_mod, "poll_orchestrator_idle_agents", return_value=[]),
        patch.object(loop_mod, "poll_kei_stale", return_value=[]),
        patch.object(loop_mod, "poll_long_running_silent", return_value=[]),
        patch.object(loop_mod, "poll_kei63_idle_inject", return_value=[]) as mock_kei63,
        patch.object(loop_mod, "send_dispatch"),
        patch.object(loop_mod, "_emit_dispatch_outcome_heartbeat"),
        patch.object(loop_mod, "_heartbeat"),
    ):
        loop_mod.run_cycle(now=n)
    mock_kei63.assert_called_once()


def test_run_cycle_sends_kei63_ceo_dispatches(loop_mod):
    """run_cycle forwards KEI-63 #ceo escalation dispatches to send_dispatch."""
    loop_mod._kei63_last_ceo_alert.clear()
    n = datetime(2026, 5, 13, 22, 0, tzinfo=UTC)
    kei63_alert = ("#ceo", "[PROPOSE:elliot] KEI-63 idle-agent escalation: atlas")
    with (
        patch.object(loop_mod, "poll_bd_ready", return_value=[]),
        patch.object(loop_mod, "poll_linear_stale", return_value=[]),
        patch.object(loop_mod, "poll_idle_agents", return_value=[]),
        patch.object(loop_mod, "poll_prefect_failures", return_value=[]),
        patch.object(loop_mod, "poll_rate_limited_agents", return_value=[]),
        patch.object(loop_mod, "poll_orchestrator_idle_agents", return_value=[]),
        patch.object(loop_mod, "poll_kei_stale", return_value=[]),
        patch.object(loop_mod, "poll_long_running_silent", return_value=[]),
        patch.object(loop_mod, "poll_kei63_idle_inject", return_value=[kei63_alert]),
        patch.object(loop_mod, "send_dispatch") as mock_send,
        patch.object(loop_mod, "_emit_dispatch_outcome_heartbeat"),
        patch.object(loop_mod, "_heartbeat"),
    ):
        count = loop_mod.run_cycle(now=n)
    assert count == 1
    mock_send.assert_called_once_with("#ceo", kei63_alert[1])
