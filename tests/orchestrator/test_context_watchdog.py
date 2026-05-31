"""Unit tests for scripts.orchestrator.context_watchdog — three Dave-identified
fixes (2026-05-30):

  Fix A — permission-prompt detection in is_stuck().
  Fix B — post-revive verification + escalation in check_other_agents().
  Fix C — richer revive_agent() prompt that includes last_task when known.

Pattern: monkeypatch the side-effecting seams (pane_capture, send_pane,
slack_ceo) so no real tmux / Slack is reached. Out of scope per the dispatch:
restart_elliot / wake_idle_elliot (Elliot-side, unchanged).

Note: the dispatch named tests/session_resumption/test_watchdog.py as the
existing file to extend, but that file tests a different module
(src.session_resumption.watchdog — clear/sb_get/mark_stuck). These tests live
in tests/orchestrator/ to colocate with the module under test.
"""

from __future__ import annotations

import importlib
import time

import pytest


@pytest.fixture
def cw():
    """Fresh import of scripts.orchestrator.context_watchdog per test so
    monkeypatched module-level attrs don't bleed between tests."""
    mod = importlib.import_module("scripts.orchestrator.context_watchdog")
    return importlib.reload(mod)


# ---------------------------------------------------------------------------
# Fix A — is_stuck() detects permission-prompt stalls
# ---------------------------------------------------------------------------


def test_is_stuck_returns_true_for_double_chevron_prompt(cw):
    """Claude permission prompt: '⏵⏵' indicator (skip-permissions mode trigger)."""
    assert cw.is_stuck("waiting on tool call\n⏵⏵ Approve?") is True


def test_is_stuck_returns_true_for_bypass_permiss_hint(cw):
    """Claude permission prompt: 'bypass permiss' substring."""
    assert cw.is_stuck("Press tab to bypass permissions") is True


def test_is_stuck_returns_true_when_allow_and_deny_both_present(cw):
    """Generic permission dialog: both 'Allow' and 'Deny' buttons visible."""
    assert cw.is_stuck("Run command? [Allow] [Deny]") is True


def test_is_stuck_false_when_only_allow_or_only_deny(cw):
    """Defensive — incidental 'Allow' or 'Deny' alone is not a permission prompt."""
    assert cw.is_stuck("DENY: access refused") is False  # no 'Allow'
    assert cw.is_stuck("allowlist updated") is False  # 'allow' lowercase doesn't match 'Allow'


def test_is_stuck_still_detects_existing_error_indicators(cw):
    """Regression: pre-existing indicators still fire after the prompt-detection patch."""
    for token in ("Error:", "APIError:", "ConnectionError", "TimeoutError", "Traceback"):
        assert cw.is_stuck(f"...some output...\n{token} something") is True


def test_is_stuck_false_for_normal_pane(cw):
    """A working pane (no prompts, no errors) → not stuck."""
    assert cw.is_stuck("> running task\nstep 3/5 complete") is False


# ---------------------------------------------------------------------------
# Fix C — revive_agent prompt includes last_task when known
# ---------------------------------------------------------------------------


def test_revive_agent_includes_last_task_when_provided(cw, monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        cw, "send_pane", lambda target, text, delay=1.5: sent.append((target, text))
    )
    monkeypatch.setattr(cw, "slack_ceo", lambda _msg: None)

    cw.revive_agent("aiden", "aiden:0.0", "error-detected", last_task="KEI-99: chain consumer")

    bodies = [t for _tg, t in sent]
    assert "/clear" in bodies[0]
    assert "Last task: KEI-99: chain consumer" in bodies[1]
    assert "Read IDENTITY.md, resume that task" in bodies[1]


def test_revive_agent_falls_back_to_bd_ready_when_last_task_blank(cw, monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        cw, "send_pane", lambda target, text, delay=1.5: sent.append((target, text))
    )
    monkeypatch.setattr(cw, "slack_ceo", lambda _msg: None)

    cw.revive_agent("aiden", "aiden:0.0", "error-detected")  # default last_task=""

    body = sent[1][1]
    assert "Last task:" not in body
    assert "check bd ready" in body


# ---------------------------------------------------------------------------
# Fix B — check_other_agents tracks revive_sent + verifies on next cycle
# ---------------------------------------------------------------------------


def _stub_one_agent(cw, monkeypatch, *, pane_text: str):
    """Reduce AGENTS to a single test agent + stub pane_capture to return pane_text."""
    monkeypatch.setattr(cw, "AGENTS", {"aiden": "aiden:0.0"})
    monkeypatch.setattr(cw, "pane_capture", lambda _target: pane_text)
    monkeypatch.setattr(cw, "send_pane", lambda *a, **kw: None)
    monkeypatch.setattr(cw, "slack_ceo", lambda _msg: None)


def test_check_other_agents_sets_revive_sent_after_reviving(cw, monkeypatch):
    """is_stuck pane → revive fires → state[name_revive_sent] set to ~now."""
    _stub_one_agent(cw, monkeypatch, pane_text="...\n⏵⏵ Allow?")
    before = time.time()
    state = cw.check_other_agents({})
    after = time.time()

    assert "aiden_revive_sent" in state
    assert before <= state["aiden_revive_sent"] <= after
    # last_hash captured + last_change stamped
    assert "aiden_last_hash" in state
    assert "aiden_last_change" in state


def test_check_other_agents_escalates_on_unchanged_pane_after_timeout(cw, monkeypatch):
    """Next cycle: revive_sent expired AND pane hash unchanged → escalate to #ceo,
    reset revive_sent. Does NOT re-fire revive."""
    ceo_msgs: list[str] = []
    send_calls: list = []
    pane_text = "stuck pane (unchanged since last cycle)"
    monkeypatch.setattr(cw, "AGENTS", {"aiden": "aiden:0.0"})
    monkeypatch.setattr(cw, "pane_capture", lambda _t: pane_text)
    monkeypatch.setattr(cw, "send_pane", lambda *a, **kw: send_calls.append(a))
    monkeypatch.setattr(cw, "slack_ceo", lambda msg: ceo_msgs.append(msg))

    prior_hash = cw.pane_hash(pane_text)  # same pane → same hash
    state = {
        "aiden_last_hash": prior_hash,
        "aiden_last_change": time.time() - cw.WAKE_TIMEOUT_SEC - 60,
        "aiden_revive_sent": time.time() - cw.WAKE_TIMEOUT_SEC - 60,  # expired
    }
    out = cw.check_other_agents(state)

    # Escalation fired with the canonical FAILED message
    assert any("revive FAILED" in m for m in ceo_msgs), ceo_msgs
    assert any("aiden" in m for m in ceo_msgs)
    # revive_sent reset to avoid spam loop
    assert out["aiden_revive_sent"] == 0
    # No new /clear or wake (didn't re-fire revive)
    assert send_calls == []


def test_check_other_agents_no_re_revive_while_in_flight(cw, monkeypatch):
    """revive_sent is set + within timeout → skip everything (no escalation, no re-revive),
    even if pane currently looks stuck."""
    ceo_msgs: list[str] = []
    send_calls: list = []
    pane_text = "still hung\n⏵⏵ Allow?"
    monkeypatch.setattr(cw, "AGENTS", {"aiden": "aiden:0.0"})
    monkeypatch.setattr(cw, "pane_capture", lambda _t: pane_text)
    monkeypatch.setattr(cw, "send_pane", lambda *a, **kw: send_calls.append(a))
    monkeypatch.setattr(cw, "slack_ceo", lambda msg: ceo_msgs.append(msg))

    prior_hash = cw.pane_hash(pane_text)
    state = {
        "aiden_last_hash": prior_hash,
        "aiden_revive_sent": time.time() - 30,  # only 30s ago, within WAKE_TIMEOUT_SEC=600
    }
    out = cw.check_other_agents(state)

    # No escalation, no new revive
    assert ceo_msgs == []
    assert send_calls == []
    # revive_sent preserved (still in-flight)
    assert out["aiden_revive_sent"] == state["aiden_revive_sent"]


def test_check_other_agents_clears_revive_sent_when_pane_changes(cw, monkeypatch):
    """Pane hash MOVED between cycles → revive worked → clear revive_sent flag.
    No escalation, no re-revive."""
    ceo_msgs: list[str] = []
    monkeypatch.setattr(cw, "AGENTS", {"aiden": "aiden:0.0"})
    monkeypatch.setattr(cw, "pane_capture", lambda _t: "NEW pane content after revive\nworking now")
    monkeypatch.setattr(cw, "send_pane", lambda *a, **kw: None)
    monkeypatch.setattr(cw, "slack_ceo", lambda msg: ceo_msgs.append(msg))

    state = {
        "aiden_last_hash": "old-hash-from-stuck-pane",
        "aiden_revive_sent": time.time() - 30,  # still recent — would normally skip
    }
    out = cw.check_other_agents(state)

    # Hash moved → revive_sent cleared
    assert out["aiden_revive_sent"] == 0
    # Hash updated to the new pane
    assert out["aiden_last_hash"] != "old-hash-from-stuck-pane"
    # No escalation (revive succeeded)
    assert ceo_msgs == []


def test_check_other_agents_passes_last_task_to_revive(cw, monkeypatch):
    """When state carries f'{name}_last_task', revive_agent receives it."""
    received: dict = {}

    def fake_revive(name, target, reason, last_task=""):
        received["name"] = name
        received["reason"] = reason
        received["last_task"] = last_task

    monkeypatch.setattr(cw, "AGENTS", {"aiden": "aiden:0.0"})
    monkeypatch.setattr(cw, "pane_capture", lambda _t: "Traceback (most recent call):\n...")
    monkeypatch.setattr(cw, "revive_agent", fake_revive)

    cw.check_other_agents({"aiden_last_task": "KEI-42: wire foo"})
    assert received == {
        "name": "aiden",
        "reason": "error-detected",
        "last_task": "KEI-42: wire foo",
    }
