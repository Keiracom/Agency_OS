"""Tests for src/skill_gen/claude_invoke.py — subprocess wrapper."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.skill_gen.claude_invoke import RECURSION_GUARD_ENV, ClaudeNotInstalled, invoke


def _stub_runner(stdout="", stderr="", returncode=0):
    calls: list[dict] = []

    def runner(cmd, **kwargs):
        calls.append({"cmd": cmd, **kwargs})
        return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)

    return runner, calls


def test_invoke_sets_recursion_guard_env_marker():
    """CLAUDE_CODE_SKILL_GEN=1 must reach the subprocess env so session_store
    hooks early-exit and skip nested turn_logs writes.

    The earlier design relied on `--no-hooks`, which the installed claude CLI
    (v2.1.139) rejects with `error: unknown option '--no-hooks'`. The
    env-marker guard replaces it. Recorder hooks at
    .claude/hooks/session_store_{posttooluse,stop}.sh inspect this variable
    at the top of the script body and early-exit on match.
    """
    runner, calls = _stub_runner(stdout="ok")
    res = invoke(
        "hello",
        claude_bin="/fake/claude",
        runner=runner,
        parent_env={"PATH": "/usr/bin"},  # explicit so we don't depend on test host env
    )
    assert res.returncode == 0
    assert res.stdout == "ok"
    assert calls[0]["cmd"][0] == "/fake/claude"
    # The dead `--no-hooks` flag must NOT reappear; CLI v2.1.139 rejects it.
    assert "--no-hooks" not in calls[0]["cmd"]
    assert "--print" in calls[0]["cmd"]
    assert "--session-id" in calls[0]["cmd"]
    # Recursion-guard env reached the subprocess.
    env = calls[0]["env"]
    assert env[RECURSION_GUARD_ENV] == "1"
    # Parent env still merged in (PATH preserved alongside the marker).
    assert env["PATH"] == "/usr/bin"


def test_invoke_env_merges_parent_env():
    """Pre-existing env vars in parent_env must survive — we merge, not overwrite."""
    runner, calls = _stub_runner()
    invoke(
        "x",
        claude_bin="/fake/claude",
        runner=runner,
        parent_env={"PATH": "/usr/bin", "CUSTOM_KEY": "preserved"},
    )
    env = calls[0]["env"]
    assert env["CUSTOM_KEY"] == "preserved"
    assert env[RECURSION_GUARD_ENV] == "1"


def test_invoke_passes_prompt_via_stdin():
    runner, calls = _stub_runner()
    invoke("the prompt body", claude_bin="/fake/claude", runner=runner)
    assert calls[0]["input"] == "the prompt body"


def test_invoke_session_id_is_uuid_per_call():
    runner, _ = _stub_runner()
    a = invoke("x", claude_bin="/fake/claude", runner=runner)
    b = invoke("x", claude_bin="/fake/claude", runner=runner)
    assert a.session_id != b.session_id
    assert len(a.session_id) == 36  # uuid4 hex form with dashes


def test_invoke_propagates_nonzero_exit_in_result():
    runner, _ = _stub_runner(stderr="boom", returncode=7)
    res = invoke("x", claude_bin="/fake/claude", runner=runner)
    assert res.returncode == 7
    assert res.stderr == "boom"


def test_invoke_raises_when_claude_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(ClaudeNotInstalled):
        invoke("x")  # claude_bin not provided → resolution via PATH
