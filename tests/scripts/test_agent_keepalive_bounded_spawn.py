"""agent_keepalive.sh bounded-spawn discipline tests.

Dave directive 2026-05-27: every keepalive respawn starts from zero by
default; state carryover requires --preserve-context with logged justification.

Tests use KEEPALIVE_DRY=1 to capture the resolved tmux/send-keys plan without
actually spawning tmux or claude.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "agent_keepalive.sh"


def _run_keepalive(
    *args: str, override_log: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {"KEEPALIVE_DRY": "1", "PATH": "/usr/bin:/bin"}
    if override_log is not None:
        env["KEEPALIVE_OVERRIDE_LOG"] = str(override_log)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


# ---- Default — fresh context (no --continue) ------------------------------


def test_default_invokes_claude_without_continue():
    result = _run_keepalive("testsession", "testcs", "/tmp")
    assert result.returncode == 0
    # The send-keys plan should NOT include `--continue`
    assert "--continue" not in result.stdout
    # AND should include the bare claude invocation
    assert "claude --dangerously-skip-permissions" in result.stdout


# ---- --preserve-context override ------------------------------------------


def test_preserve_context_uses_claude_continue(tmp_path: Path):
    log_path = tmp_path / "override.jsonl"
    result = _run_keepalive(
        "testsession",
        "testcs",
        "/tmp",
        "--preserve-context",
        "operator recovery of stuck Atlas review",
        override_log=log_path,
    )
    assert result.returncode == 0
    assert "claude --continue --dangerously-skip-permissions" in result.stdout
    # Stderr should announce the override
    assert "--preserve-context override active" in result.stderr


def test_preserve_context_writes_jsonl_event(tmp_path: Path):
    log_path = tmp_path / "override.jsonl"
    result = _run_keepalive(
        "atlas",
        "atlas",
        "/home/elliotbot/clawd/Agency_OS-atlas",
        "--preserve-context",
        "stuck review session needs context to resume",
        override_log=log_path,
    )
    assert result.returncode == 0
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8").strip()
    event = json.loads(content)
    assert event["callsign"] == "atlas"
    assert event["session"] == "atlas"
    assert event["worktree"] == "/home/elliotbot/clawd/Agency_OS-atlas"
    assert event["justification"] == "stuck review session needs context to resume"
    assert "ts" in event
    # ISO 8601 with Z suffix
    assert event["ts"].endswith("Z")


def test_preserve_context_appends_not_overwrites(tmp_path: Path):
    """Multiple respawn cycles → multiple JSONL events appended."""
    log_path = tmp_path / "override.jsonl"
    _run_keepalive(
        "s1",
        "cs1",
        "/tmp",
        "--preserve-context",
        "first override",
        override_log=log_path,
    )
    _run_keepalive(
        "s2",
        "cs2",
        "/tmp",
        "--preserve-context",
        "second override",
        override_log=log_path,
    )
    lines = [l for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2
    events = [json.loads(line) for line in lines]
    assert events[0]["justification"] == "first override"
    assert events[1]["justification"] == "second override"


# ---- Validation — missing / empty justification ---------------------------


def test_preserve_context_without_justification_fails(tmp_path: Path):
    result = _run_keepalive(
        "testsession",
        "testcs",
        "/tmp",
        "--preserve-context",
        override_log=tmp_path / "override.jsonl",
    )
    assert result.returncode == 2
    assert "non-empty justification" in result.stderr


def test_preserve_context_with_empty_justification_fails(tmp_path: Path):
    """--preserve-context '' → fail (empty string not a real justification)."""
    result = _run_keepalive(
        "testsession",
        "testcs",
        "/tmp",
        "--preserve-context",
        "",
        override_log=tmp_path / "override.jsonl",
    )
    assert result.returncode == 2
    assert "non-empty justification" in result.stderr


# ---- Validation — unknown arg ---------------------------------------------


def test_unknown_argument_fails():
    result = _run_keepalive("testsession", "testcs", "/tmp", "--bogus-flag")
    assert result.returncode == 2
    assert "unknown argument" in result.stderr


# ---- Backwards compatibility — existing systemd-unit invocations ----------


def test_existing_three_arg_invocation_unchanged():
    """systemd units pass exactly 3 args (session callsign worktree). No --flag
    must still work — Default path is fresh-context invocation."""
    result = _run_keepalive("atlas", "atlas", "/home/elliotbot/clawd/Agency_OS-atlas")
    assert result.returncode == 0
    # Default path
    assert "--continue" not in result.stdout
    assert "claude --dangerously-skip-permissions" in result.stdout


# ---- Header doc anchor ----------------------------------------------------


def test_script_header_cites_dave_directive_2026_05_27():
    """The bounded-spawn directive anchor must be visible at the script head."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "Dave directive 2026-05-27" in text
    assert "bounded-spawn discipline" in text
    assert "--preserve-context" in text


def test_script_documents_jsonl_log_path():
    """The default JSONL log path must be discoverable in the header."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "/tmp/keepalive_override_log.jsonl" in text
