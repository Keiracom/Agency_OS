"""Unit tests for scripts.orchestrator.context_watchdog — Dave-identified fixes:

  Fix A (2026-05-30) — permission-prompt detection.
  Fix B (2026-05-30) — post-revive verification + escalation in check_other_agents().
  Fix C (2026-05-30) — richer revive_agent() prompt that includes last_task when known.
  Permission-vs-stall split (2026-06-01) — is_permission_prompt /
    is_genuinely_stuck handled by separate code paths; permission prompts
    auto-approve (read-only + dual-concur merges) or escalate, never /clear.

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
# Permission-vs-stall split (2026-06-01): ⏵⏵ + 'bypass permiss' moved out of
# is_stuck() into is_permission_prompt(). is_genuinely_stuck() keeps the real
# failure indicators + the Allow/Deny dialog pattern.
# ---------------------------------------------------------------------------


def test_is_permission_prompt_returns_true_for_double_chevron(cw):
    """Claude permission prompt: '⏵⏵' indicator (skip-permissions mode trigger)."""
    assert cw.is_permission_prompt("waiting on tool call\n⏵⏵ Approve?") is True


def test_is_permission_prompt_returns_true_for_bypass_permiss_hint(cw):
    """Claude permission prompt: 'bypass permiss' substring."""
    assert cw.is_permission_prompt("Press tab to bypass permissions") is True


def test_is_permission_prompt_false_for_normal_pane(cw):
    """Pane with no permission tokens → not a permission prompt."""
    assert cw.is_permission_prompt("> running task\nstep 3/5 complete") is False


def test_is_genuinely_stuck_does_not_fire_on_chevron(cw):
    """⏵⏵ is a permission prompt, NOT a genuine stall — kept off /clear path."""
    assert cw.is_genuinely_stuck("waiting on tool call\n⏵⏵ Approve?") is False


def test_is_genuinely_stuck_does_not_fire_on_bypass_permiss(cw):
    """'bypass permiss' is a permission prompt, NOT a genuine stall."""
    assert cw.is_genuinely_stuck("Press tab to bypass permissions") is False


def test_is_genuinely_stuck_returns_true_when_allow_and_deny_both_present(cw):
    """Generic Allow/Deny dialog stays on the stall path per dispatch verbatim."""
    assert cw.is_genuinely_stuck("Run command? [Allow] [Deny]") is True


def test_is_genuinely_stuck_false_when_only_allow_or_only_deny(cw):
    """Defensive — incidental 'Allow' or 'Deny' alone is not a stall signal."""
    assert cw.is_genuinely_stuck("DENY: access refused") is False  # no 'Allow'
    assert cw.is_genuinely_stuck("allowlist updated") is False  # case-sensitive


def test_is_genuinely_stuck_still_detects_existing_error_indicators(cw):
    """Regression: pre-existing indicators still fire on the genuine-stall path."""
    for token in ("Error:", "APIError:", "ConnectionError", "TimeoutError", "Traceback"):
        assert cw.is_genuinely_stuck(f"...some output...\n{token} something") is True


def test_is_genuinely_stuck_false_for_normal_pane(cw):
    """A working pane (no prompts, no errors) → not stuck."""
    assert cw.is_genuinely_stuck("> running task\nstep 3/5 complete") is False


# ---------------------------------------------------------------------------
# Fix C — revive_agent prompt includes last_task when known
# ---------------------------------------------------------------------------


def test_revive_agent_includes_last_task_when_provided(cw, monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        cw, "safe_send", lambda target, text, **kw: sent.append((target, text)) or True
    )
    monkeypatch.setattr(cw, "wait_for_prompt", lambda target, timeout=30.0: True)
    monkeypatch.setattr(cw, "slack_ceo", lambda _msg: None)

    cw.revive_agent("aiden", "aiden:0.0", "error-detected", last_task="KEI-99: chain consumer")

    bodies = [t for _tg, t in sent]
    assert "/clear" in bodies[0]
    assert "Last task: KEI-99: chain consumer" in bodies[1]
    assert "Read IDENTITY.md" in bodies[1]


def test_revive_agent_falls_back_to_bd_ready_when_last_task_blank(cw, monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        cw, "safe_send", lambda target, text, **kw: sent.append((target, text)) or True
    )
    monkeypatch.setattr(cw, "wait_for_prompt", lambda target, timeout=30.0: True)
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
    """is_genuinely_stuck pane → revive fires → state[name_revive_sent] set to ~now.

    Post-2026-06-01 split: ⏵⏵ panes now go to handle_permission_prompt (no /clear);
    only real-failure panes (Error:/Traceback/etc.) take the revive path.
    """
    _stub_one_agent(cw, monkeypatch, pane_text="Error: chain consumer crashed")
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


# ---------------------------------------------------------------------------
# record_agent_task — dispatch-time feed for Fix C
# ---------------------------------------------------------------------------


def test_record_agent_task_writes_last_task_into_state_file(cw, tmp_path, monkeypatch):
    """record_agent_task persists `{name}_last_task` into the watchdog state
    file. A subsequent load_state() round-trip returns the same value."""
    state_file = tmp_path / "watchdog-state.json"
    monkeypatch.setattr(cw, "WATCHDOG_STATE_FILE", state_file)

    cw.record_agent_task("orion", "PR #1373 — wire last_task feed")

    persisted = cw.load_state()
    assert persisted["orion_last_task"] == "PR #1373 — wire last_task feed"


def test_record_agent_task_preserves_other_state_keys(cw, tmp_path, monkeypatch):
    """Writing one agent's last_task must not clobber unrelated state keys
    (e.g. another agent's revive_sent timestamp)."""
    state_file = tmp_path / "watchdog-state.json"
    monkeypatch.setattr(cw, "WATCHDOG_STATE_FILE", state_file)
    cw.save_state({"atlas_revive_sent": 123.45, "atlas_last_task": "old-atlas-task"})

    cw.record_agent_task("orion", "orion task")

    out = cw.load_state()
    assert out["atlas_revive_sent"] == 123.45
    assert out["atlas_last_task"] == "old-atlas-task"
    assert out["orion_last_task"] == "orion task"


def test_record_agent_task_squashes_newlines_and_caps_length(cw, tmp_path, monkeypatch):
    """Multi-line briefs collapse to one tmux-safe line; >240 chars truncated."""
    state_file = tmp_path / "watchdog-state.json"
    monkeypatch.setattr(cw, "WATCHDOG_STATE_FILE", state_file)

    long_brief = "Task header\n\nLine two with detail.\n" + ("x" * 500)
    cw.record_agent_task("scout", long_brief)

    stored = cw.load_state()["scout_last_task"]
    assert "\n" not in stored
    assert len(stored) == 240
    assert stored.startswith("Task header Line two with detail.")


def test_record_agent_task_no_op_on_blank_inputs(cw, tmp_path, monkeypatch):
    """Empty name OR empty task → return without touching state file."""
    state_file = tmp_path / "watchdog-state.json"
    monkeypatch.setattr(cw, "WATCHDOG_STATE_FILE", state_file)

    cw.record_agent_task("", "real task")
    cw.record_agent_task("orion", "")
    assert not state_file.exists()


def test_record_then_revive_uses_persisted_last_task(cw, tmp_path, monkeypatch):
    """End-to-end Fix C wire: record_agent_task → check_other_agents picks up
    the persisted last_task and passes it into revive_agent."""
    state_file = tmp_path / "watchdog-state.json"
    monkeypatch.setattr(cw, "WATCHDOG_STATE_FILE", state_file)

    cw.record_agent_task("aiden", "KEI-77: rebase PR after #1371")

    received: dict = {}

    def fake_revive(name, target, reason, last_task=""):
        received["last_task"] = last_task

    monkeypatch.setattr(cw, "AGENTS", {"aiden": "aiden:0.0"})
    monkeypatch.setattr(cw, "pane_capture", lambda _t: "...\nError: oh no")
    monkeypatch.setattr(cw, "revive_agent", fake_revive)

    cw.check_other_agents(cw.load_state())
    assert received["last_task"] == "KEI-77: rebase PR after #1371"


# ---------------------------------------------------------------------------
# Permission-vs-stall split (2026-06-01): handle_permission_prompt dispatch
# ---------------------------------------------------------------------------


def _perm_pane(tool_call: str, pr: int | None = None) -> str:
    """Build a synthetic pane: tool-call line + ⏵⏵ marker (+ optional PR status)."""
    parts = [f"● {tool_call}", "⏵⏵ Approve?"]
    if pr is not None:
        parts.append(f"· PR #{pr} · orion/feature ·")
    return "\n".join(parts)


def test_permission_prompt_does_not_trigger_clear(cw, monkeypatch):
    """check_other_agents must take the permission-prompt path, NOT revive_agent."""
    revive_calls: list = []
    monkeypatch.setattr(cw, "AGENTS", {"aiden": "aiden:0.0"})
    monkeypatch.setattr(cw, "pane_capture", lambda _t: _perm_pane("Bash(git log)"))
    monkeypatch.setattr(cw, "revive_agent", lambda *a, **kw: revive_calls.append(a))
    monkeypatch.setattr(cw, "send_tab", lambda _t: None)
    monkeypatch.setattr(cw, "slack_ceo", lambda _m: None)

    cw.check_other_agents({})
    assert revive_calls == []


def test_auto_approve_sends_tab_for_git_log(cw, monkeypatch):
    """git log is in AUTO_APPROVE_PATTERNS → Tab keystroke, no Slack escalation."""
    tabs: list[str] = []
    slack: list[str] = []
    monkeypatch.setattr(cw, "send_tab", lambda t: tabs.append(t))
    monkeypatch.setattr(cw, "slack_ceo", lambda m: slack.append(m))

    pane = _perm_pane("Bash(git log --oneline -5)")
    cw.handle_permission_prompt("aiden", "aiden:0.0", pane, {})

    assert tabs == ["aiden:0.0"]
    assert slack == []


def test_auto_approve_sends_tab_for_gh_pr_view(cw, monkeypatch):
    """gh pr view is in AUTO_APPROVE_PATTERNS → Tab keystroke."""
    tabs: list[str] = []
    monkeypatch.setattr(cw, "send_tab", lambda t: tabs.append(t))
    monkeypatch.setattr(cw, "slack_ceo", lambda _m: None)

    pane = _perm_pane("Bash(gh pr view 1375 --json comments)")
    cw.handle_permission_prompt("orion", "orion:0.0", pane, {})

    assert tabs == ["orion:0.0"]


def test_unknown_tool_escalates_not_clears(cw, monkeypatch):
    """Unknown tool → slack_ceo called; send_tab / revive_agent NOT called."""
    tabs: list[str] = []
    slack: list[str] = []
    monkeypatch.setattr(cw, "send_tab", lambda t: tabs.append(t))
    monkeypatch.setattr(cw, "slack_ceo", lambda m: slack.append(m))
    monkeypatch.setattr(cw, "revive_agent", lambda *a, **kw: pytest.fail("revive_agent must not run"))

    pane = _perm_pane("Bash(rm -rf /tmp/foo)")
    state = cw.handle_permission_prompt("aiden", "aiden:0.0", pane, {})

    assert tabs == []
    assert len(slack) == 1
    assert "needs permission" in slack[0]
    assert "rm -rf /tmp/foo" in slack[0]
    assert state["aiden_escalated_at"] > 0


def test_escalation_anti_spam(cw, monkeypatch):
    """Two cycles within 5 min for same unknown tool → slack_ceo called only once."""
    slack: list[str] = []
    monkeypatch.setattr(cw, "send_tab", lambda _t: None)
    monkeypatch.setattr(cw, "slack_ceo", lambda m: slack.append(m))

    pane = _perm_pane("Bash(unknown-binary --foo)")
    state = cw.handle_permission_prompt("aiden", "aiden:0.0", pane, {})
    assert len(slack) == 1

    # Second cycle right after — escalated_at is now within the cooldown window.
    state = cw.handle_permission_prompt("aiden", "aiden:0.0", pane, state)
    assert len(slack) == 1, "anti-spam cooldown should suppress the second escalation"


def test_merge_with_dual_concur_auto_approves(cw, monkeypatch):
    """gh pr merge + 2+ REVIEW:approve in PR comments → Tab keystroke."""
    tabs: list[str] = []
    slack: list[str] = []
    monkeypatch.setattr(cw, "send_tab", lambda t: tabs.append(t))
    monkeypatch.setattr(cw, "slack_ceo", lambda m: slack.append(m))

    class _R:
        returncode = 0
        stdout = "[REVIEW:approve:aiden] looks good\n[REVIEW:approve:max] LGTM\n"

    monkeypatch.setattr(cw.subprocess, "run", lambda *a, **kw: _R())

    pane = _perm_pane("Bash(gh pr merge 1375 --squash --admin)", pr=1375)
    cw.handle_permission_prompt("elliot", "elliottbot:0.0", pane, {})

    assert tabs == ["elliottbot:0.0"]
    assert slack == []
