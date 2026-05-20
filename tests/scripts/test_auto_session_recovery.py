"""Tests for scripts/orchestrator/auto_session_recovery.py — KEI-35.

tmux, claude --resume, slack_relay, and the project-dir jsonl scan are all
stubbed at the module level. No real subprocess invocations.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "orchestrator" / "auto_session_recovery.py"


@pytest.fixture(scope="module")
def asr_mod():
    spec = importlib.util.spec_from_file_location("auto_session_recovery", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["auto_session_recovery"] = mod
    spec.loader.exec_module(mod)
    return mod


# detect_dead_callsigns ──────────────────────────────────────────────────────


def _stub_alive(asr_mod, monkeypatch, names: set[str]) -> None:
    monkeypatch.setattr(asr_mod, "_alive_sessions", lambda: set(names))


def test_detect_dead_all_alive(asr_mod, monkeypatch):
    _stub_alive(
        asr_mod,
        monkeypatch,
        {"elliottbot", "aiden", "maxbot", "atlas", "orion", "scout", "nova"},
    )
    assert asr_mod.detect_dead_callsigns() == []


def test_detect_dead_max_missing(asr_mod, monkeypatch):
    _stub_alive(asr_mod, monkeypatch, {"elliottbot", "aiden", "atlas", "orion", "scout", "nova"})
    # maxbot session absent → max callsign reported dead (nova alive, not flagged)
    assert asr_mod.detect_dead_callsigns() == ["max"]


def test_detect_dead_no_tmux_server(asr_mod, monkeypatch):
    _stub_alive(asr_mod, monkeypatch, set())
    # Empty alive set → all expected callsigns are dead
    assert set(asr_mod.detect_dead_callsigns()) == set(asr_mod.CALLSIGN_TO_TMUX)


# latest_session_id ──────────────────────────────────────────────────────────


def test_latest_session_id_picks_newest_jsonl(asr_mod, monkeypatch, tmp_path):
    # Build a fake project dir with two jsonls; older one has older mtime.
    proj = tmp_path / "-home-elliotbot-clawd-Agency-OS-scout"
    proj.mkdir(parents=True)
    older = proj / "aaaa-old.jsonl"
    newer = proj / "bbbb-new.jsonl"
    older.write_text("{}")
    newer.write_text("{}")
    import os as _os

    _os.utime(older, (1, 1))  # mtime far in the past
    _os.utime(newer, (10_000_000, 10_000_000))
    monkeypatch.setattr(asr_mod, "CLAUDE_PROJECTS_ROOT", tmp_path)
    assert asr_mod.latest_session_id("scout") == "bbbb-new"


def test_latest_session_id_missing_project_dir(asr_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(asr_mod, "CLAUDE_PROJECTS_ROOT", tmp_path)  # empty
    assert asr_mod.latest_session_id("scout") is None


def test_latest_session_id_unknown_callsign(asr_mod):
    assert asr_mod.latest_session_id("nobody") is None


# recover_session ────────────────────────────────────────────────────────────


def _stub_tmux(asr_mod, monkeypatch, behavior=None):
    """Stub _tmux with a callable behavior(*args) → bool. Default = always True.
    Records each call in returned list.
    """
    calls: list[tuple[str, ...]] = []

    def fake_tmux(*args: str) -> bool:
        calls.append(args)
        return behavior(*args) if behavior else True

    monkeypatch.setattr(asr_mod, "_tmux", fake_tmux)
    return calls


def test_recover_session_happy_path(asr_mod, monkeypatch):
    monkeypatch.setattr(asr_mod, "latest_session_id", lambda cs: "uuid-123")
    calls = _stub_tmux(asr_mod, monkeypatch)
    assert asr_mod.recover_session("scout") is True
    # Four steps: new-session, send-keys claude, send-keys "1", send-keys brief
    step_names = [c[0] for c in calls]
    assert step_names == ["new-session", "send-keys", "send-keys", "send-keys"]
    # Step 1 includes worktree path
    assert "/home/elliotbot/clawd/Agency_OS-scout" in calls[0]
    # Step 2 contains the claude --resume command with the session id
    assert any("claude --resume uuid-123" in part for part in calls[1])
    # Step 3 sends the "1" option selector
    assert calls[2][3] == "1"
    # Step 4 includes the auto-recovered brief banner
    assert any("AUTO-RECOVERED SESSION" in part for part in calls[3])


def test_recover_session_no_prior_session_returns_false(asr_mod, monkeypatch):
    monkeypatch.setattr(asr_mod, "latest_session_id", lambda cs: None)
    calls = _stub_tmux(asr_mod, monkeypatch)
    assert asr_mod.recover_session("scout") is False
    # Should NOT have called tmux at all if there's no session jsonl to resume
    assert calls == []


def test_recover_session_step1_failure_aborts(asr_mod, monkeypatch):
    monkeypatch.setattr(asr_mod, "latest_session_id", lambda cs: "uuid-123")
    # First _tmux call (new-session) returns False; subsequent shouldn't run
    calls = _stub_tmux(asr_mod, monkeypatch, behavior=lambda *a: False)
    assert asr_mod.recover_session("scout") is False
    assert len(calls) == 1  # only new-session attempted


# run() integration ──────────────────────────────────────────────────────────


def test_run_no_dead_sessions_is_noop(asr_mod, monkeypatch, tmp_path):
    monkeypatch.setenv("AGENCY_OS_SESSION_RECOVERY_STATE", str(tmp_path / "state.json"))
    _stub_alive(asr_mod, monkeypatch, set(asr_mod.CALLSIGN_TO_TMUX.values()))
    # If recover_session is invoked despite all-alive, fail loudly:
    monkeypatch.setattr(
        asr_mod, "recover_session", MagicMock(side_effect=AssertionError("must not run"))
    )
    assert asr_mod.run() == 0


def test_run_two_attempt_threshold_then_escalate(asr_mod, monkeypatch, tmp_path):
    """After 2 failed attempts, the next cycle should NOT retry — already escalated."""
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("AGENCY_OS_SESSION_RECOVERY_STATE", str(state_path))
    # max is dead; pre-seed state with 2 prior failures
    _stub_alive(asr_mod, monkeypatch, set(asr_mod.CALLSIGN_TO_TMUX.values()) - {"maxbot"})
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "max": {
                    "attempts": asr_mod.MAX_RECOVERY_ATTEMPTS,
                    "first_attempt_at": "2026-05-13T00:00:00+00:00",
                    "last_attempt_at": "2026-05-13T00:01:00+00:00",
                    "last_attempt_success": False,
                }
            }
        )
    )
    recover_calls: list[str] = []
    monkeypatch.setattr(asr_mod, "recover_session", lambda cs: recover_calls.append(cs) or False)
    escalations: list[tuple[str, int]] = []
    monkeypatch.setattr(asr_mod, "_escalate_to_ceo", lambda cs, n: escalations.append((cs, n)))
    asr_mod.run(now=datetime(2026, 5, 13, 0, 5, tzinfo=UTC))
    # Threshold already reached → no further recover_session call
    assert recover_calls == []
    # And no new escalation (escalation only fires ON the failing attempt)
    assert escalations == []


def test_run_first_attempt_success_clears_state_on_next_pass(asr_mod, monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("AGENCY_OS_SESSION_RECOVERY_STATE", str(state_path))
    # First call: max dead, recover succeeds.
    alive_now = set(asr_mod.CALLSIGN_TO_TMUX.values()) - {"maxbot"}

    def alive_view():
        return alive_now

    monkeypatch.setattr(asr_mod, "_alive_sessions", alive_view)
    monkeypatch.setattr(asr_mod, "recover_session", lambda cs: True)
    asr_mod.run()
    saved = json.loads(state_path.read_text())
    assert saved["max"]["attempts"] == 1
    assert saved["max"]["last_attempt_success"] is True
    # Second pass: maxbot now alive → state should clear.
    alive_now.add("maxbot")
    asr_mod.run()
    saved2 = json.loads(state_path.read_text())
    assert "max" not in saved2


def test_run_second_failure_escalates_to_ceo(asr_mod, monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("AGENCY_OS_SESSION_RECOVERY_STATE", str(state_path))
    # Pre-seed: 1 prior failed attempt for max.
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "max": {
                    "attempts": 1,
                    "first_attempt_at": "2026-05-13T00:00:00+00:00",
                    "last_attempt_at": "2026-05-13T00:01:00+00:00",
                    "last_attempt_success": False,
                }
            }
        )
    )
    _stub_alive(asr_mod, monkeypatch, set(asr_mod.CALLSIGN_TO_TMUX.values()) - {"maxbot"})
    monkeypatch.setattr(asr_mod, "recover_session", lambda cs: False)  # fails again
    escalations: list[tuple[str, int]] = []
    monkeypatch.setattr(asr_mod, "_escalate_to_ceo", lambda cs, n: escalations.append((cs, n)))
    asr_mod.run()
    # Second attempt failed → escalation expected
    assert escalations == [("max", asr_mod.MAX_RECOVERY_ATTEMPTS)]


# _project_dir_for ───────────────────────────────────────────────────────────


def test_project_dir_for_main_worktree(asr_mod):
    p = asr_mod._project_dir_for("/home/elliotbot/clawd/Agency_OS")
    assert p.name == "-home-elliotbot-clawd-Agency-OS"


def test_project_dir_for_callsign_worktree(asr_mod):
    p = asr_mod._project_dir_for("/home/elliotbot/clawd/Agency_OS-scout")
    assert p.name == "-home-elliotbot-clawd-Agency-OS-scout"
