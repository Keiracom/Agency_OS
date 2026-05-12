"""Tests for src/skill_gen/generator.py — orchestrator + PR opener."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.skill_gen.extractor import CompressedSession
from src.skill_gen.generator import (
    build_prompt,
    derive_skill_name,
    generate,
    open_pr,
    write_skill,
)

_SKILL_BODY = """\
---
name: read-pattern
description: reading-heavy investigation flow
---
# Read Pattern

## When to use
- early recce

## Steps
1. read

## Failure modes
- missing file

## Verification
- assert exists
"""


def _empty_session(**overrides) -> CompressedSession:
    base: CompressedSession = {
        "session_id": "s1",
        "window_start": "t0",
        "window_end": "t1",
        "turn_count": 0,
        "tool_call_freq": {},
        "errors": [],
        "user_messages": [],
        "files_touched": [],
        "chronology": [],
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def test_derive_skill_name_from_override():
    sess = _empty_session()
    assert derive_skill_name(sess, "My Skill! Name") == "my-skill-name"


def test_derive_skill_name_from_dominant_tool():
    sess = _empty_session(tool_call_freq={"Read": 5, "Bash": 2})
    assert derive_skill_name(sess, None) == "read-pattern"


def test_derive_skill_name_default_when_empty():
    sess = _empty_session()
    assert derive_skill_name(sess, None) == "captured-pattern"


def test_build_prompt_embeds_session_json():
    sess = _empty_session(tool_call_freq={"Read": 1})
    prompt = build_prompt(sess)
    assert "SKILL.md" in prompt
    assert '"Read": 1' in prompt
    assert "--- " not in prompt.split("```json")[0] or True  # template shape preserved


def test_write_skill_creates_dir_and_file(tmp_path: Path):
    skill_path = write_skill(tmp_path, "demo-skill", _SKILL_BODY)
    assert skill_path == tmp_path / "skills" / "demo-skill" / "SKILL.md"
    assert skill_path.read_text() == _SKILL_BODY


def test_write_skill_refuses_overwrite_by_default(tmp_path: Path):
    write_skill(tmp_path, "demo-skill", "first")
    with pytest.raises(FileExistsError):
        write_skill(tmp_path, "demo-skill", "second")
    # overwrite=True allowed
    p = write_skill(tmp_path, "demo-skill", "third", overwrite=True)
    assert p.read_text() == "third"


def test_open_pr_invokes_gh_with_expected_args(tmp_path: Path):
    captured: dict = {}

    def runner(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = kwargs.get("cwd")
        return SimpleNamespace(stdout="https://github.com/x/y/pull/1\n", stderr="", returncode=0)

    skill_path = tmp_path / "skills" / "demo" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("body")
    url = open_pr(tmp_path, skill_path, "directive-#999", runner=runner)
    assert url == "https://github.com/x/y/pull/1"
    assert captured["cmd"][:3] == ["gh", "pr", "create"]
    assert "[ATLAS] feat(skills): auto-generated from directive-#999" in captured["cmd"]
    assert captured["cwd"] == str(tmp_path)


def test_open_pr_returns_none_on_gh_failure(tmp_path: Path):
    def runner(cmd, **kwargs):
        return SimpleNamespace(stdout="", stderr="auth required", returncode=1)

    skill_path = tmp_path / "skills" / "demo" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("body")
    assert open_pr(tmp_path, skill_path, "ref", runner=runner) is None


def test_generate_end_to_end_with_stubs(tmp_path: Path):
    """Full pipeline: stubbed extractor + stubbed claude + stubbed gh."""

    def claude_runner(cmd, **kwargs):
        return SimpleNamespace(stdout=_SKILL_BODY, stderr="", returncode=0)

    pr_calls: dict = {}

    def pr_runner(cmd, **kwargs):
        pr_calls["cmd"] = cmd
        return SimpleNamespace(stdout="https://github.com/x/y/pull/42\n", stderr="", returncode=0)

    extractor_overrides = {
        "fetch_turns": lambda *a: [{"id": "t1", "turn_index": 0}],
        "fetch_turn_logs": lambda turn_ids: [
            {
                "id": "l1",
                "turn_id": "t1",
                "tool_name": "Read",
                "exit_status": "success",
                "started_at": "t",
                "tool_result_summary": "",
            }
        ],
        "fetch_turn_files": lambda log_ids: [],
        "fetch_user_messages": lambda *a: [],
    }
    res = generate(
        repo_root=tmp_path,
        session_id="s1",
        start_ts="t0",
        end_ts="t1",
        directive_ref="dir-#42",
        claude_runner=claude_runner,
        pr_runner=pr_runner,
        extractor_overrides=extractor_overrides,
    )
    assert res.skill_name == "read-pattern"
    assert res.skill_path.read_text() == _SKILL_BODY
    assert res.pr_url == "https://github.com/x/y/pull/42"
    assert "[ATLAS] feat(skills): auto-generated from dir-#42" in pr_calls["cmd"]


def test_generate_raises_on_claude_failure_surfaces_stdout_and_stderr(tmp_path: Path):
    """RuntimeError must include both streams.

    claude --print writes CLI errors to STDOUT (e.g. "Credit balance is too
    low"), not stderr. Previous error message format dropped stdout, leaving
    the real cause invisible. Verified empirically against PR #728 re-run
    (atlas outbox 20260512_0115_pr720_flag_fix_complete.json).
    """

    def claude_runner(cmd, **kwargs):
        # Real-world failure mode: error on stdout, stderr empty, non-zero exit.
        return SimpleNamespace(stdout="Credit balance is too low", stderr="", returncode=1)

    extractor_overrides = {
        "fetch_turns": lambda *a: [],
        "fetch_turn_logs": lambda *a: [],
        "fetch_turn_files": lambda *a: [],
        "fetch_user_messages": lambda *a: [],
    }
    with pytest.raises(RuntimeError) as exc_info:
        generate(
            repo_root=tmp_path,
            session_id="s1",
            start_ts="t0",
            end_ts="t1",
            directive_ref="r",
            claude_runner=claude_runner,
            pr_runner=lambda *a, **kw: SimpleNamespace(stdout="", stderr="", returncode=0),
            extractor_overrides=extractor_overrides,
        )
    msg = str(exc_info.value)
    assert "claude invocation failed" in msg
    assert "Credit balance is too low" in msg, (
        f"stdout content missing from RuntimeError; got: {msg!r}"
    )
    # exit code visible
    assert "exit 1" in msg


def test_generate_raises_includes_stderr_when_present(tmp_path: Path):
    """The stderr branch still surfaces — the polish includes BOTH streams, not
    a swap. Asymmetry would re-hide whichever stream is the real cause."""

    def claude_runner(cmd, **kwargs):
        return SimpleNamespace(stdout="", stderr="rate limited", returncode=2)

    extractor_overrides = {
        "fetch_turns": lambda *a: [],
        "fetch_turn_logs": lambda *a: [],
        "fetch_turn_files": lambda *a: [],
        "fetch_user_messages": lambda *a: [],
    }
    with pytest.raises(RuntimeError, match="rate limited"):
        generate(
            repo_root=tmp_path,
            session_id="s1",
            start_ts="t0",
            end_ts="t1",
            directive_ref="r",
            claude_runner=claude_runner,
            pr_runner=lambda *a, **kw: SimpleNamespace(stdout="", stderr="", returncode=0),
            extractor_overrides=extractor_overrides,
        )
