"""Tests for src/skill_gen/generator.py — orchestrator + PR opener.

Post Gemini pivot (2026-05-12): the LLM injection point is `client_factory`
(forwarded to gemini_invoke.invoke), not `claude_runner`. Tests build a
stub google.genai.Client substitute and pass its factory.
"""

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


def _gemini_client_factory(text: str):
    """Build a google.genai.Client substitute that returns `text` from
    generate_content."""

    class _Models:
        def generate_content(self, *, model, contents):
            return SimpleNamespace(
                text=text,
                usage_metadata=SimpleNamespace(prompt_token_count=100, candidates_token_count=20),
            )

    class _Client:
        def __init__(self, _api_key):
            self.models = _Models()

    return lambda api_key: _Client(api_key)


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


def test_write_skill_creates_dir_and_file(tmp_path: Path):
    skill_path = write_skill(tmp_path, "demo-skill", _SKILL_BODY)
    assert skill_path == tmp_path / "skills" / "demo-skill" / "SKILL.md"
    assert skill_path.read_text() == _SKILL_BODY


def test_write_skill_refuses_overwrite_by_default(tmp_path: Path):
    write_skill(tmp_path, "demo-skill", "first")
    with pytest.raises(FileExistsError):
        write_skill(tmp_path, "demo-skill", "second")
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


def test_generate_end_to_end_with_stubs(tmp_path: Path, monkeypatch):
    """Full pipeline: stubbed extractor + stubbed Gemini client + stubbed gh."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")

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
        client_factory=_gemini_client_factory(_SKILL_BODY),
        pr_runner=pr_runner,
        extractor_overrides=extractor_overrides,
    )
    assert res.skill_name == "read-pattern"
    assert res.skill_path.read_text() == _SKILL_BODY
    assert res.pr_url == "https://github.com/x/y/pull/42"
    assert "[ATLAS] feat(skills): auto-generated from dir-#42" in pr_calls["cmd"]
    # Token usage from the stubbed response surfaced on GenerateResult.
    assert res.llm.prompt_tokens == 100
    assert res.llm.output_tokens == 20
    assert res.llm.model.startswith("gemini-")


def test_generate_raises_on_empty_gemini_response(tmp_path: Path, monkeypatch):
    """If Gemini returns empty text we refuse to write an empty SKILL.md.

    The RuntimeError must surface the model name + token usage so callers
    can diagnose (e.g. content-filter rejection, prompt-too-large, etc.).
    """
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")

    extractor_overrides = {
        "fetch_turns": lambda *a: [],
        "fetch_turn_logs": lambda *a: [],
        "fetch_turn_files": lambda *a: [],
        "fetch_user_messages": lambda *a: [],
    }
    with pytest.raises(RuntimeError, match="Gemini returned empty text"):
        generate(
            repo_root=tmp_path,
            session_id="s1",
            start_ts="t0",
            end_ts="t1",
            directive_ref="r",
            client_factory=_gemini_client_factory(""),
            pr_runner=lambda *a, **kw: SimpleNamespace(stdout="", stderr="", returncode=0),
            extractor_overrides=extractor_overrides,
        )
