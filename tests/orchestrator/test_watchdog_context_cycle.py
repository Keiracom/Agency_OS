"""Negative test A — context-cycle revive path for non-Elliot agents.

Per HEAD-OF-OPS DIRECTIVE 2026-06-03 (Component 2 of 2), exercise the
context-full revive path in scripts.orchestrator.context_watchdog:

  (a) mocks a pane with '100% context used'
  (b) confirms is_context_full() returns True
  (c) mocks /clear + wake-prompt injection
  (d) confirms the agent gets re-briefed

Pattern matches the existing tests/orchestrator/test_context_watchdog.py:
monkeypatch the side-effecting seams (pane_capture, safe_send, slack_ceo,
wait_for_prompt) so no real tmux/Slack/DB is touched.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def cw():
    """Fresh import of the watchdog module per test so monkeypatched
    module-level attrs don't bleed between tests."""
    mod = importlib.import_module("scripts.orchestrator.context_watchdog")
    return importlib.reload(mod)


def test_a_context_full_pane_triggers_revive(cw, monkeypatch):
    """(a)+(b)+(c)+(d) negative test A — happy-path revive on context-full."""

    # (a) Mock pane with '100% context used'.
    fake_pane = "some scrollback content here\nmore scrollback\n100% context used\n❯ \n"

    # Restrict to a single target agent so the loop runs deterministically.
    monkeypatch.setattr(cw, "AGENTS", {"orion": "orion:0.0"})

    # pane_capture: return fake_pane every call.
    monkeypatch.setattr(cw, "pane_capture", lambda _target: fake_pane)

    # (b) Sanity: is_context_full() returns True for this pane.
    assert cw.is_context_full(fake_pane) is True

    # (c) Mock /clear + wake-prompt injection: capture safe_send + slack_ceo.
    sends: list[tuple[str, str]] = []

    def fake_safe_send(target, text, **_kwargs):
        sends.append((target, text))
        return True

    monkeypatch.setattr(cw, "safe_send", fake_safe_send)
    monkeypatch.setattr(cw, "wait_for_prompt", lambda _t, timeout=0: True)

    slack_msgs: list[str] = []
    monkeypatch.setattr(cw, "slack_ceo", lambda msg: slack_msgs.append(msg))

    # Run the revive path under test.
    cw.check_other_agents({})

    # (d) Confirm the agent got re-briefed.
    targets = [t for t, _ in sends]
    texts = [text for _, text in sends]

    assert "orion:0.0" in targets, f"expected /clear+revive sent to orion:0.0, got: {targets}"
    assert any(s == "/clear" for s in texts), f"expected /clear keystroke; sends={texts}"
    assert any("REVIVED by watchdog" in s and "context-full" in s for s in texts), (
        f"expected REVIVED context-full message; sends={texts}"
    )
    assert any("revived orion" in m.lower() and "context-full" in m for m in slack_msgs), (
        f"expected #ceo announcement of revive; got: {slack_msgs}"
    )
