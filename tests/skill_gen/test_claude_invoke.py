"""Tests for src/skill_gen/claude_invoke.py — subprocess wrapper."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.skill_gen.claude_invoke import ClaudeNotInstalled, invoke


def _stub_runner(stdout="", stderr="", returncode=0):
    calls: list[dict] = []

    def runner(cmd, **kwargs):
        calls.append({"cmd": cmd, **kwargs})
        return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)

    return runner, calls


def test_invoke_passes_no_hooks_flag():
    runner, calls = _stub_runner(stdout="ok")
    res = invoke("hello", claude_bin="/fake/claude", runner=runner)
    assert res.returncode == 0
    assert res.stdout == "ok"
    assert calls[0]["cmd"][0] == "/fake/claude"
    assert "--no-hooks" in calls[0]["cmd"]
    assert "--print" in calls[0]["cmd"]
    assert "--session-id" in calls[0]["cmd"]


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
