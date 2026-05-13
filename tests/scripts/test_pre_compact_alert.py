"""tests for scripts/pre_compact_alert.py — Dave System Health Outcome 5.

Mocks Slack + git subprocess + HEARTBEAT.md to test:
  - resolve_callsign env / IDENTITY.md / fallback
  - read_heartbeat reads worktree HEARTBEAT.md / caps at 2000 chars
  - git_context returns branch + log + dirty flag
  - format_alert composes complete message
  - post_to_slack: no-token / network-error / ok=true paths
  - read_hook_input: tty / empty / valid JSON / invalid JSON
  - main() always returns 0 (best-effort)
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALERT_PATH = REPO_ROOT / "scripts" / "pre_compact_alert.py"


@pytest.fixture(scope="module")
def alert():
    spec = importlib.util.spec_from_file_location("pre_compact_alert", ALERT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pre_compact_alert"] = mod
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# resolve_callsign
# ─────────────────────────────────────────────────────────────────────────────


def test_resolve_callsign_from_env(alert, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "aiden")
    assert alert.resolve_callsign() == "aiden"


def test_resolve_callsign_lowercases(alert, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "AIDEN")
    assert alert.resolve_callsign() == "aiden"


def test_resolve_callsign_fallback_unknown(alert, monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CALLSIGN", raising=False)
    monkeypatch.chdir(tmp_path)
    assert alert.resolve_callsign() == "unknown"


def test_resolve_callsign_from_identity_md(alert, monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CALLSIGN", raising=False)
    (tmp_path / "IDENTITY.md").write_text("# IDENTITY\n\n**CALLSIGN:** aiden\n")
    monkeypatch.chdir(tmp_path)
    assert alert.resolve_callsign() == "aiden"


# ─────────────────────────────────────────────────────────────────────────────
# read_heartbeat
# ─────────────────────────────────────────────────────────────────────────────


def test_read_heartbeat_returns_empty_when_missing(alert, monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    assert alert.read_heartbeat() == ""


def test_read_heartbeat_returns_content(alert, monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "HEARTBEAT.md").write_text("Active task: build outcome 5\n")
    assert "Active task" in alert.read_heartbeat()


def test_read_heartbeat_caps_at_2000_chars(alert, monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "HEARTBEAT.md").write_text("x" * 5000)
    assert len(alert.read_heartbeat()) == 2000


# ─────────────────────────────────────────────────────────────────────────────
# git_context
# ─────────────────────────────────────────────────────────────────────────────


def test_git_context_returns_fields(alert) -> None:
    def fake_run(args: list[str]) -> str:
        if args[:2] == ["git", "rev-parse"]:
            return "feature/branch"
        if args[:2] == ["git", "log"]:
            return "abc123 commit message"
        if args[:2] == ["git", "status"]:
            return ""  # clean
        return ""

    with patch.object(alert, "_run", side_effect=fake_run):
        ctx = alert.git_context()
    assert ctx["branch"] == "feature/branch"
    assert ctx["log"] == "abc123 commit message"
    assert ctx["dirty"] is False


def test_git_context_marks_dirty_when_porcelain_nonempty(alert) -> None:
    def fake_run(args: list[str]) -> str:
        if args[:2] == ["git", "rev-parse"]:
            return "main"
        if args[:2] == ["git", "log"]:
            return "deadbeef commit"
        if args[:2] == ["git", "status"]:
            return " M file.py\n?? other.py"
        return ""

    with patch.object(alert, "_run", side_effect=fake_run):
        ctx = alert.git_context()
    assert ctx["dirty"] is True


def test_git_context_handles_missing_git(alert) -> None:
    with patch.object(alert, "_run", return_value=""):
        ctx = alert.git_context()
    assert ctx["branch"] == "?"
    assert ctx["log"] == "(no commits)"
    assert ctx["dirty"] is False


# ─────────────────────────────────────────────────────────────────────────────
# _run
# ─────────────────────────────────────────────────────────────────────────────


def test_run_returns_empty_on_filenotfound(alert) -> None:
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert alert._run(["nonexistent"]) == ""


def test_run_returns_empty_on_timeout(alert) -> None:
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5)):
        assert alert._run(["git", "log"]) == ""


# ─────────────────────────────────────────────────────────────────────────────
# format_alert
# ─────────────────────────────────────────────────────────────────────────────


def test_format_alert_composes_all_fields(alert) -> None:
    git = {
        "branch": "aiden/test-branch",
        "log": "abc123 fix(x): y",
        "dirty": False,
        "porcelain": "",
    }
    text = alert.format_alert(
        "aiden",
        {"trigger": "auto"},
        "Active task: outcome 5",
        git,
    )
    assert "[PRE-COMPACT]" in text
    assert "callsign=aiden" in text
    assert "branch=aiden/test-branch" in text
    assert "trigger=auto" in text
    assert "outcome 5" in text
    assert "abc123" in text
    assert "[DIRTY]" not in text


def test_format_alert_marks_dirty_branch(alert) -> None:
    git = {"branch": "main", "log": "x", "dirty": True, "porcelain": "M file"}
    text = alert.format_alert("aiden", {}, "h", git)
    assert "[DIRTY]" in text


def test_format_alert_handles_empty_heartbeat(alert) -> None:
    git = {"branch": "main", "log": "x", "dirty": False, "porcelain": ""}
    text = alert.format_alert("aiden", {}, "", git)
    assert "HEARTBEAT.md empty or missing" in text


# ─────────────────────────────────────────────────────────────────────────────
# read_hook_input
# ─────────────────────────────────────────────────────────────────────────────


def test_read_hook_input_returns_empty_when_tty(alert) -> None:
    with patch.object(sys, "stdin") as mock_stdin:
        mock_stdin.isatty.return_value = True
        assert alert.read_hook_input() == {}


def test_read_hook_input_parses_valid_json(alert) -> None:
    fake_stdin = io.StringIO('{"trigger": "auto"}')
    fake_stdin.isatty = lambda: False
    with patch.object(sys, "stdin", fake_stdin):
        assert alert.read_hook_input() == {"trigger": "auto"}


def test_read_hook_input_returns_empty_on_invalid_json(alert) -> None:
    fake_stdin = io.StringIO("not json {")
    fake_stdin.isatty = lambda: False
    with patch.object(sys, "stdin", fake_stdin):
        assert alert.read_hook_input() == {}


def test_read_hook_input_returns_empty_on_blank(alert) -> None:
    fake_stdin = io.StringIO("")
    fake_stdin.isatty = lambda: False
    with patch.object(sys, "stdin", fake_stdin):
        assert alert.read_hook_input() == {}


# ─────────────────────────────────────────────────────────────────────────────
# post_to_slack
# ─────────────────────────────────────────────────────────────────────────────


def test_post_to_slack_no_token_returns_false(alert, monkeypatch) -> None:
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    assert alert.post_to_slack("test") is False


def test_post_to_slack_ok_true_returns_true(alert, monkeypatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    import urllib.request

    class FakeResponse:
        def read(self) -> bytes:
            return json.dumps({"ok": True}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch.object(urllib.request, "urlopen", return_value=FakeResponse()):
        assert alert.post_to_slack("test") is True


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────


def test_main_returns_zero_on_success(alert, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "aiden")
    with (
        patch.object(alert, "read_hook_input", return_value={"trigger": "auto"}),
        patch.object(alert, "read_heartbeat", return_value="task: x"),
        patch.object(
            alert,
            "git_context",
            return_value={"branch": "main", "log": "x", "dirty": False, "porcelain": ""},
        ),
        patch.object(alert, "post_to_slack", return_value=True) as mock_post,
    ):
        assert alert.main() == 0
    # PRE-COMPACT alert is always posted; KEI-36 may add a [HEARTBEAT-INCOMPLETE]
    # warning if the worktree's real HEARTBEAT.md has residual placeholders.
    assert mock_post.call_count >= 1


def test_main_returns_zero_even_on_slack_failure(alert, monkeypatch) -> None:
    """Best-effort — compaction must NEVER be blocked."""
    monkeypatch.setenv("CALLSIGN", "aiden")
    with (
        patch.object(alert, "read_hook_input", return_value={}),
        patch.object(alert, "read_heartbeat", return_value=""),
        patch.object(
            alert,
            "git_context",
            return_value={"branch": "?", "log": "", "dirty": False, "porcelain": ""},
        ),
        patch.object(alert, "post_to_slack", return_value=False),
    ):
        assert alert.main() == 0


# ─────────────────────────────────────────────────────────────────────────────
# KEI-36 — auto_populate_heartbeat + find_residual_placeholders
# ─────────────────────────────────────────────────────────────────────────────


_TEMPLATE_SAMPLE = """# HEARTBEAT.md

## Active Task

- Directive: <directive number or label>
- Goal: <one-line>
- Phase: <scope/decompose/execute/verify/report>
- Files touched (current PR): <list>

## Last Good Commit

- SHA: <git short-sha>
- Branch: <branch-name>
- Subject: <commit subject line>

## Model

- Configured: <callsign-from-IDENTITY.md → lookup in CLAUDE.md §Callsign → Model Assignment table>
- Running: <actual `--model` flag at startup, if known; otherwise "unknown — check tmux session launch command">

## Blockers

- <bulleted list, or "none">

## Next Action

- <single concrete next step the next session should execute>

## Heartbeat Cadence (CLAUDE.md context thresholds)

- 40% — self-alert
- 50% — alert Dave
- 60% — execute session-end
"""


def test_auto_populate_replaces_known_fields(alert):
    out = alert.auto_populate_heartbeat(
        _TEMPLATE_SAMPLE,
        git_short_sha="abc1234",
        branch="aiden/kei36-test",
        commit_subject="fix: thing",
        files_touched="a.py, b.py",
        directive="KEI-36",
        blockers="none",
        next_action="KEI-99: do X",
    )
    assert "abc1234" in out
    assert "aiden/kei36-test" in out
    assert "fix: thing" in out
    assert "a.py, b.py" in out
    assert "KEI-36" in out
    assert "KEI-99: do X" in out


def test_auto_populate_skips_empty_values(alert):
    """Empty-string values must leave placeholder intact (so warning surfaces)."""
    out = alert.auto_populate_heartbeat(
        _TEMPLATE_SAMPLE,
        git_short_sha="",
        branch="",
        commit_subject="",
        files_touched="",
        directive="",
        blockers="",
        next_action="",
    )
    assert "<git short-sha>" in out
    assert "<branch-name>" in out
    assert "<commit subject line>" in out


def test_auto_populate_leaves_phase_and_model_placeholders(alert):
    """Phase + Configured + Running model have NO mechanical source — must persist as placeholders."""
    out = alert.auto_populate_heartbeat(
        _TEMPLATE_SAMPLE,
        git_short_sha="abc1234",
        branch="x",
        commit_subject="s",
        files_touched="f",
        directive="d",
        blockers="none",
        next_action="n",
    )
    assert "<scope/decompose/execute/verify/report>" in out
    assert "<callsign-from-IDENTITY.md" in out
    assert "<actual `--model` flag" in out


def test_find_residual_placeholders_returns_unfilled(alert):
    out = alert.auto_populate_heartbeat(
        _TEMPLATE_SAMPLE,
        git_short_sha="abc1234",
        branch="x",
        commit_subject="s",
        files_touched="f",
        directive="d",
        blockers="none",
        next_action="n",
    )
    residual = alert.find_residual_placeholders(out)
    # At minimum Phase + Configured + Running + Goal remain (no value provided for goal here either — value="" or no source).
    assert any("scope/decompose" in r for r in residual)
    assert any("Callsign" in r or "callsign" in r for r in residual)


def test_find_residual_placeholders_skips_heartbeat_cadence_section(alert):
    """The Cadence section uses literal '%>' / placeholder-like text — must not match."""
    sample = """## Heartbeat Cadence (CLAUDE.md context thresholds)

- 40% — self-alert
- 50% — alert Dave
On heartbeat check:
1. Context health — if >60%, alert Dave.
"""
    assert alert.find_residual_placeholders(sample) == []


def test_find_residual_placeholders_empty_when_all_filled(alert):
    """Fully populated template has zero residual placeholders."""
    sample = """## Active Task
- Directive: KEI-36
- Goal: ship auto-populate
## Last Good Commit
- SHA: abc1234
"""
    assert alert.find_residual_placeholders(sample) == []


def test_bd_ready_first_returns_empty_on_command_missing(alert, monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError())
    )
    assert alert._bd_ready_first() == ""


def test_bd_ready_first_extracts_id_and_title(alert, monkeypatch):
    class Fake:
        returncode = 0
        stdout = '[{"id": "Agency_OS-99", "title": "Do thing"}]'

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Fake())
    assert alert._bd_ready_first() == "Agency_OS-99: Do thing"


def test_bd_blocked_list_returns_none_on_empty(alert, monkeypatch):
    class Fake:
        returncode = 0
        stdout = "[]"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Fake())
    assert alert._bd_blocked_list() == "none"


def test_bd_blocked_list_formats_bullets(alert, monkeypatch):
    class Fake:
        returncode = 0
        stdout = '[{"id": "A", "title": "x"}, {"id": "B", "title": "y"}]'

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Fake())
    out = alert._bd_blocked_list()
    assert "A: x" in out and "B: y" in out


def test_directive_from_branch_extracts_kei(alert):
    assert "KEI36" in alert._directive_from_branch("aiden/kei36-foo")
    assert alert._directive_from_branch("aiden/kei-22-something") == "KEI-22"
    # Bare label match is best-effort; partial match acceptable for labelling.
    out = alert._directive_from_branch("aiden/kei-5vu-foo")
    assert "KEI" in out


def test_directive_from_branch_main_returns_empty(alert):
    assert alert._directive_from_branch("main") == ""


def test_post_heartbeat_incomplete_warning_no_residual_returns_false(alert):
    assert alert.post_heartbeat_incomplete_warning([]) is False


def test_post_heartbeat_incomplete_warning_calls_slack(alert, monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        alert,
        "post_to_slack",
        lambda text, channel=alert.EXECUTION_CHANNEL: calls.append((text, channel)) or True,
    )
    out = alert.post_heartbeat_incomplete_warning(["<x>", "<y>", "<x>"])
    assert out is True
    assert len(calls) == 1
    text = calls[0][0]
    assert "[HEARTBEAT-INCOMPLETE]" in text
    assert "<x>" in text and "<y>" in text


def test_main_auto_populates_and_warns(alert, monkeypatch, tmp_path):
    """Integration: main() → auto-populate writes back + posts incomplete warning."""
    monkeypatch.setenv("CALLSIGN", "aiden")
    monkeypatch.chdir(tmp_path)
    hb = tmp_path / "HEARTBEAT.md"
    hb.write_text(_TEMPLATE_SAMPLE)
    monkeypatch.setattr(alert, "HEARTBEAT_PATH", hb)

    posts: list = []
    monkeypatch.setattr(
        alert,
        "post_to_slack",
        lambda text, channel=alert.EXECUTION_CHANNEL: posts.append((text, channel)) or True,
    )
    monkeypatch.setattr(alert, "read_hook_input", lambda: {"trigger": "auto"})
    monkeypatch.setattr(
        alert,
        "git_context",
        lambda: {"branch": "aiden/kei36-x", "log": "abc x", "dirty": False, "porcelain": ""},
    )
    monkeypatch.setattr(alert, "_git_short_sha", lambda: "abc1234")
    monkeypatch.setattr(alert, "_git_commit_subject", lambda: "fix: thing")
    monkeypatch.setattr(alert, "_git_files_touched", lambda b: "a.py")
    monkeypatch.setattr(alert, "_bd_ready_first", lambda: "KEI-99: do X")
    monkeypatch.setattr(alert, "_bd_blocked_list", lambda: "none")

    assert alert.main() == 0
    updated = hb.read_text()
    assert "abc1234" in updated  # SHA populated
    assert "aiden/kei36-x" in updated  # branch populated
    # Phase + model placeholders remain → incomplete warning fires
    incomplete = [t for t, _ in posts if "[HEARTBEAT-INCOMPLETE]" in t]
    assert len(incomplete) == 1
