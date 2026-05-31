"""Tests for the Elliot resume-path fix (2026-05-31).

Root cause: Stop hook (write_heartbeat.py, 8s timeout) ran after /clear.
The old fixed 4s delay sent the wake prompt while the hook was still running.
Claude Code reset terminal input on new-context start, losing the buffered prompt.

Fix: wait_for_prompt() polls for ❯ before injecting; restart_elliot() uses it.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from scripts.orchestrator.context_watchdog import (  # noqa: E402
    ELLIOT_PANE,
    WAKE_TIMEOUT_SEC,
    pane_hash,
    restart_elliot,
    wait_for_prompt,
    wake_idle_elliot,
)


# ─── wait_for_prompt ──────────────────────────────────────────────────────────

def test_wait_for_prompt_returns_true_immediately_when_prompt_visible():
    with patch("scripts.orchestrator.context_watchdog.pane_capture") as cap:
        cap.return_value = "some text\n❯ \n── status ──"
        assert wait_for_prompt("test:0", timeout=5.0) is True
        assert cap.call_count == 1


def test_wait_for_prompt_retries_until_prompt_appears():
    responses = ["loading...", "still loading", "❯ ready"]
    with patch("scripts.orchestrator.context_watchdog.pane_capture", side_effect=responses), \
         patch("scripts.orchestrator.context_watchdog.time") as mock_time:
        mock_time.time.side_effect = [0.0, 1.0, 2.0, 3.0, 99.0]
        mock_time.sleep = MagicMock()
        result = wait_for_prompt("test:0", timeout=10.0)
    assert result is True


def test_wait_for_prompt_returns_false_on_timeout():
    with patch("scripts.orchestrator.context_watchdog.pane_capture", return_value="no prompt here"), \
         patch("scripts.orchestrator.context_watchdog.time") as mock_time:
        # Simulate time advancing past deadline immediately
        mock_time.time.side_effect = [0.0, 31.0]
        mock_time.sleep = MagicMock()
        result = wait_for_prompt("test:0", timeout=30.0)
    assert result is False


# ─── WAKE_TIMEOUT_SEC is 2 cycles ─────────────────────────────────────────────

def test_wake_timeout_is_at_least_two_timer_cycles():
    # Timer fires every 10 min (600s). Timeout must be > 600 so there's a buffer.
    assert WAKE_TIMEOUT_SEC > 600, (
        f"WAKE_TIMEOUT_SEC={WAKE_TIMEOUT_SEC} equals the timer interval — "
        "escalation fires before the second cycle can confirm success"
    )


# ─── restart_elliot: prompt-verified injection ────────────────────────────────

def _base_state():
    return {"elliot_last_hash": "oldhash", "elliot_last_hash_ts": 0.0}


def test_restart_elliot_waits_for_prompt_before_injecting():
    """Wake prompt must not be sent until wait_for_prompt returns True."""
    inject_calls = []

    def fake_send(target, text, delay=0):
        inject_calls.append(text)

    with patch("scripts.orchestrator.context_watchdog.ensure_compact_state"), \
         patch("scripts.orchestrator.context_watchdog.send_pane", side_effect=fake_send), \
         patch("scripts.orchestrator.context_watchdog.wait_for_prompt", return_value=True) as wfp, \
         patch("scripts.orchestrator.context_watchdog.slack_ceo"), \
         patch("scripts.orchestrator.context_watchdog.pane_capture", return_value="❯ \n──"):
        restart_elliot(_base_state(), 100.0)

    # wait_for_prompt called after /clear
    wfp.assert_called_once_with(ELLIOT_PANE, timeout=30.0)
    # wake prompt (CONTEXT-CYCLE RESUME...) was injected
    assert any("CONTEXT-CYCLE RESUME" in c for c in inject_calls)


def test_restart_elliot_skips_wake_when_prompt_never_appears():
    """/clear hung — no ❯ seen in 30s. Must NOT inject wake prompt; escalate instead."""
    inject_calls = []

    def fake_send(target, text, delay=0):
        inject_calls.append(text)

    ceo_msgs = []
    with patch("scripts.orchestrator.context_watchdog.ensure_compact_state"), \
         patch("scripts.orchestrator.context_watchdog.send_pane", side_effect=fake_send), \
         patch("scripts.orchestrator.context_watchdog.wait_for_prompt", return_value=False), \
         patch("scripts.orchestrator.context_watchdog.slack_ceo", side_effect=lambda m: ceo_msgs.append(m)), \
         patch("scripts.orchestrator.context_watchdog.pane_capture", return_value="stuck"):
        state = restart_elliot(_base_state(), 100.0)

    # No wake prompt injected
    assert not any("CONTEXT-CYCLE RESUME" in c for c in inject_calls)
    # Wake-sent timer still stamped (so escalation path runs on next cycle)
    assert state["elliot_wake_sent"] == 100.0
    assert state["elliot_wake_reason"] == "context-full-clear-hung"
    # #ceo alerted
    assert any("hung" in m or "❯" in m for m in ceo_msgs)


# ─── wake_idle_elliot: prompt guard ───────────────────────────────────────────

def test_wake_idle_skips_when_no_prompt_visible():
    """idle wake must not send if ❯ is not visible (e.g. Claude mid-output)."""
    inject_calls = []
    with patch("scripts.orchestrator.context_watchdog.wait_for_prompt", return_value=False), \
         patch("scripts.orchestrator.context_watchdog.send_pane", side_effect=lambda t, txt, delay=0: inject_calls.append(txt)), \
         patch("scripts.orchestrator.context_watchdog.pane_capture", return_value="mid-output"):
        state = wake_idle_elliot(_base_state(), 200.0)

    assert not any("CONTEXT-CYCLE RESUME" in c for c in inject_calls)
    assert state["elliot_wake_reason"] == "idle-no-prompt"


def test_wake_idle_sends_when_prompt_visible():
    inject_calls = []
    with patch("scripts.orchestrator.context_watchdog.wait_for_prompt", return_value=True), \
         patch("scripts.orchestrator.context_watchdog.send_pane", side_effect=lambda t, txt, delay=0: inject_calls.append(txt)), \
         patch("scripts.orchestrator.context_watchdog.pane_capture", return_value="❯ \n── status ──"):
        state = wake_idle_elliot(_base_state(), 200.0)

    assert any("CONTEXT-CYCLE RESUME" in c for c in inject_calls)
    assert state["elliot_wake_reason"] == "idle"
