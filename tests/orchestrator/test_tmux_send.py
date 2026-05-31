"""Tests for scripts.utils.tmux_send — the shared verified pane injection utility.

These tests verify the three-layer jne8 pattern:
  Layer 1: prompt guard (wait for ❯)
  Layer 2: -l flag (literal send) + separated C-m
  Layer 3: commit verify (probe gone from bottom) + retry
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from scripts.utils.tmux_send import (  # noqa: E402
    pane_content,
    safe_send,
    wait_for_prompt,
)

TARGET = "testpane:0.0"


# ─── pane_content ─────────────────────────────────────────────────────────────

def test_pane_content_returns_stdout_on_success():
    with patch("scripts.utils.tmux_send.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="hello world\n❯ \n")
        result = pane_content(TARGET)
    assert "❯" in result


def test_pane_content_returns_empty_string_on_failure():
    with patch("scripts.utils.tmux_send.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = pane_content(TARGET)
    assert result == ""


# ─── wait_for_prompt ──────────────────────────────────────────────────────────

def test_wait_for_prompt_returns_true_immediately():
    with patch("scripts.utils.tmux_send.pane_content", return_value="❯ "):
        assert wait_for_prompt(TARGET, timeout=5.0) is True


def test_wait_for_prompt_retries_until_found():
    side_effects = ["loading", "loading", "❯ ready"]
    with patch("scripts.utils.tmux_send.pane_content", side_effect=side_effects), \
         patch("scripts.utils.tmux_send.time") as mock_t:
        # deadline=0+10=10; iter1: time=1<10; iter2: time=2<10; iter3: time=3<10 → found
        mock_t.time.side_effect = [0, 1, 2, 3, 99]
        mock_t.sleep = MagicMock()
        assert wait_for_prompt(TARGET, timeout=10.0) is True


def test_wait_for_prompt_times_out():
    with patch("scripts.utils.tmux_send.pane_content", return_value="no prompt"), \
         patch("scripts.utils.tmux_send.time") as mock_t:
        mock_t.time.side_effect = [0, 31]
        mock_t.sleep = MagicMock()
        assert wait_for_prompt(TARGET, timeout=30.0) is False


# ─── safe_send: Layer 1 — prompt guard ────────────────────────────────────────

def test_safe_send_waits_for_prompt_before_sending():
    prompt_calls = []
    def fake_wait(target, timeout):
        prompt_calls.append(target)
        return True

    with patch("scripts.utils.tmux_send.wait_for_prompt", side_effect=fake_wait), \
         patch("scripts.utils.tmux_send.subprocess.run", return_value=MagicMock(returncode=0)), \
         patch("scripts.utils.tmux_send.pane_content", return_value="other content"), \
         patch("scripts.utils.tmux_send.time.sleep"):
        safe_send(TARGET, "hello")

    assert TARGET in prompt_calls


def test_safe_send_aborts_if_prompt_never_appears():
    with patch("scripts.utils.tmux_send.wait_for_prompt", return_value=False):
        result = safe_send(TARGET, "hello", wait_prompt=30.0)
    assert result is False


def test_safe_send_skips_prompt_wait_when_flag_set():
    calls = []
    with patch("scripts.utils.tmux_send.wait_for_prompt") as wfp, \
         patch("scripts.utils.tmux_send.subprocess.run", return_value=MagicMock(returncode=0)) as run, \
         patch("scripts.utils.tmux_send.pane_content", return_value="other content"), \
         patch("scripts.utils.tmux_send.time.sleep"):
        safe_send(TARGET, "hello", skip_prompt_wait=True)
    wfp.assert_not_called()


# ─── safe_send: Layer 2 — -l flag (literal send) ─────────────────────────────

def test_safe_send_uses_literal_flag_for_text():
    """Text must be sent with -l to prevent tmux key-name interpretation."""
    run_calls = []
    with patch("scripts.utils.tmux_send.wait_for_prompt", return_value=True), \
         patch("scripts.utils.tmux_send.subprocess.run",
               side_effect=lambda *a, **kw: run_calls.append(a[0]) or MagicMock(returncode=0)), \
         patch("scripts.utils.tmux_send.pane_content", return_value="different content"), \
         patch("scripts.utils.tmux_send.time.sleep"):
        safe_send(TARGET, "test message")

    # First subprocess call should include -l flag
    text_send = run_calls[0]
    assert "-l" in text_send
    assert "test message" in text_send


def test_safe_send_text_and_enter_are_separate_calls():
    """Text and C-m must be separate send-keys calls."""
    run_calls = []
    with patch("scripts.utils.tmux_send.wait_for_prompt", return_value=True), \
         patch("scripts.utils.tmux_send.subprocess.run",
               side_effect=lambda *a, **kw: run_calls.append(a[0]) or MagicMock(returncode=0)), \
         patch("scripts.utils.tmux_send.pane_content", return_value="other content"), \
         patch("scripts.utils.tmux_send.time.sleep"):
        safe_send(TARGET, "msg", settle=0)

    # There must be a text send call AND a separate C-m call
    has_text_send = any("-l" in c and "msg" in c for c in run_calls)
    has_cm_send = any("C-m" in c for c in run_calls)
    assert has_text_send, "No -l text send call found"
    assert has_cm_send, "No C-m call found"


# ─── safe_send: Layer 3 — commit verify + retry ───────────────────────────────

def test_safe_send_returns_true_when_probe_gone_first_try():
    """If probe is not in bottom lines after C-m, committed on first try."""
    with patch("scripts.utils.tmux_send.wait_for_prompt", return_value=True), \
         patch("scripts.utils.tmux_send.subprocess.run", return_value=MagicMock(returncode=0)), \
         patch("scripts.utils.tmux_send.pane_content", return_value="─── some output\n❯ \n── status ──"), \
         patch("scripts.utils.tmux_send.time.sleep"):
        result = safe_send(TARGET, "unique probe text 123")
    assert result is True


def test_safe_send_retries_cm_when_probe_still_visible():
    """If probe stays in bottom after C-m, retry C-m up to commit_retries."""
    pane_calls = [0]
    def pane_side_effect(t):
        pane_calls[0] += 1
        if pane_calls[0] < 3:
            return "❯ unique probe text 123"  # still on input line
        return "response above\n❯ \n──"  # committed

    with patch("scripts.utils.tmux_send.wait_for_prompt", return_value=True), \
         patch("scripts.utils.tmux_send.subprocess.run", return_value=MagicMock(returncode=0)), \
         patch("scripts.utils.tmux_send.pane_content", side_effect=pane_side_effect), \
         patch("scripts.utils.tmux_send.time.sleep"):
        result = safe_send(TARGET, "unique probe text 123", commit_retries=3, settle=0, commit_settle=0)
    assert result is True
    assert pane_calls[0] >= 3  # retried


def test_safe_send_returns_false_when_all_retries_exhausted():
    """If probe never goes away, returns False after all retries."""
    with patch("scripts.utils.tmux_send.wait_for_prompt", return_value=True), \
         patch("scripts.utils.tmux_send.subprocess.run", return_value=MagicMock(returncode=0)), \
         patch("scripts.utils.tmux_send.pane_content", return_value="❯ unique probe text 123"), \
         patch("scripts.utils.tmux_send.time.sleep"):
        result = safe_send(TARGET, "unique probe text 123", commit_retries=3, settle=0, commit_settle=0)
    assert result is False


def test_safe_send_returns_false_when_text_send_fails():
    with patch("scripts.utils.tmux_send.wait_for_prompt", return_value=True), \
         patch("scripts.utils.tmux_send.subprocess.run", return_value=MagicMock(returncode=1)):
        result = safe_send(TARGET, "hello", skip_prompt_wait=True)
    assert result is False
