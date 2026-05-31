"""tmux_send.py — Verified pane injection for all inter-agent messaging.

Canonical replacement for every ad-hoc `tmux send-keys` call in scripts/.
Implements the three-layer jne8 pattern from inbox_watcher.sh, generalised
so Python scripts don't each roll their own half-correct version:

  Layer 1 — Prompt guard: wait for ❯ before typing (same race that killed
             Elliot resume 5× overnight — Stop hook delays the new context).
  Layer 2 — Literal send + separated Enter: text sent with -l flag (no tmux
             key-name interpretation), then C-m as a separate call after a
             brief settle (avoids Enter-before-text-committed race).
  Layer 3 — Commit verify + retry: after C-m, check whether the probe string
             (first 40 chars of content) is GONE from the bottom lines of the
             pane. If still there, Enter was swallowed — retry C-m up to
             MAX_COMMIT_RETRIES times. An extra Enter on an empty prompt is a
             no-op, so retrying is safe.

Reference: Agency_OS-jne8 (inbox_watcher) + Agency_OS watchdog resume fix
(2026-05-31). Both trace to the same root cause: sent ≠ submitted.
"""
from __future__ import annotations

import subprocess
import time
from typing import Optional


def pane_content(target: str) -> str:
    """Capture the current visible content of a tmux pane."""
    try:
        r = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", target],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def wait_for_prompt(target: str, timeout: float = 30.0) -> bool:
    """Block until Claude Code's ❯ prompt is visible in the pane.

    Returns True when prompt found, False if timeout expires.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if "❯" in pane_content(target):
            return True
        time.sleep(1.0)
    return False


def safe_send(
    target: str,
    text: str,
    *,
    wait_prompt: float = 30.0,
    settle: float = 0.4,
    commit_retries: int = 3,
    commit_settle: float = 2.0,
    skip_prompt_wait: bool = False,
) -> bool:
    """Send text to a tmux pane and verify it was submitted (jne8 pattern).

    Args:
        target:         tmux target (e.g. 'elliottbot:0.0').
        text:           Message to inject.
        wait_prompt:    Seconds to wait for ❯ before aborting. 0 to skip.
        settle:         Seconds between text send and C-m.
        commit_retries: Max C-m retries if probe still visible after Enter.
        commit_settle:  Seconds after C-m before checking commit.
        skip_prompt_wait: If True, skip the ❯ check (caller already verified).

    Returns:
        True  — message was submitted (probe gone from pane bottom).
        False — all retries exhausted; message may still be in compose box.
    """
    if not skip_prompt_wait and wait_prompt > 0:
        if not wait_for_prompt(target, timeout=wait_prompt):
            return False

    # Layer 2a: send text with -l (literal — no tmux key-name interpretation).
    try:
        r = subprocess.run(
            ["tmux", "send-keys", "-t", target, "-l", text],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode != 0:
            return False
    except Exception:
        return False

    if settle > 0:
        time.sleep(settle)

    # Layer 3: send C-m (Enter) and verify the probe is gone from the input line.
    probe = text[:40]
    for attempt in range(1, commit_retries + 1):
        try:
            subprocess.run(
                ["tmux", "send-keys", "-t", target, "C-m"],
                capture_output=True, text=True, timeout=5
            )
        except Exception:
            return False

        time.sleep(commit_settle)

        # Probe check: after Enter, the input line clears and the message appears
        # in the conversation above. If probe is still on the bottom lines, the
        # Enter was swallowed — retry.
        pane = pane_content(target)
        bottom = "\n".join(pane.splitlines()[-3:])
        if probe not in bottom:
            return True  # committed

    return False  # exhausted retries


def send_or_log(
    target: str,
    text: str,
    label: str = "",
    **kwargs,
) -> bool:
    """safe_send with a logging fallback. Returns True if submitted."""
    result = safe_send(target, text, **kwargs)
    if not result:
        import sys
        tag = f"[{label}] " if label else ""
        print(
            f"{tag}tmux_send: FAILED to commit to {target!r} — "
            f"message may be parked in compose box. Text[:80]: {text[:80]!r}",
            file=sys.stderr,
        )
    return result
