"""
P9 — Tests for scripts/context_fork.py.

Pure unit tests — no real transcripts, no subprocess. Confirms:
  - _validate_transcript_path: same posture as P1 governance hook
    (URL / traversal / outside-root / wrong-suffix / null-byte rejected;
     valid path under TRANSCRIPT_ROOT accepted)
  - extract_context: pulls Step 0, recent turns, file paths from
    tool_use blocks
  - extract_context isolates the LATEST Step 0 (per-directive)
  - render_brief truncates to ~max_tokens × 4 chars
  - build_forked_context returns "" on every failure path (fail-empty)
  - No subprocess invoked anywhere
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "context_fork.py"
_spec = importlib.util.spec_from_file_location("context_fork", _SCRIPT)
cf = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["context_fork"] = cf
_spec.loader.exec_module(cf)


# ─── helpers ───────────────────────────────────────────────────────────────

def _msg(role: str, text: str) -> str:
    return json.dumps({
        "message": {"role": role, "content": [{"type": "text", "text": text}]}
    })


def _tool_use(tool: str, file_path: str, key: str = "file_path") -> str:
    return json.dumps({
        "message": {
            "role": "assistant",
            "content": [{
                "type": "tool_use",
                "name": tool,
                "input": {key: file_path},
            }],
        }
    })


# ─── _validate_transcript_path ─────────────────────────────────────────────

def test_validate_rejects_url():
    for s in ("http://x/a.jsonl", "file:///etc/passwd"):
        assert cf._validate_transcript_path(s) is None


def test_validate_rejects_traversal():
    assert cf._validate_transcript_path("../../etc/passwd.jsonl") is None


def test_validate_rejects_null_byte():
    assert cf._validate_transcript_path("/tmp/x\x00y.jsonl") is None


def test_validate_rejects_outside_root(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text("{}")
    # Default TRANSCRIPT_ROOT is ~/.claude/projects — tmp_path is outside.
    assert cf._validate_transcript_path(str(p)) is None


def test_validate_rejects_wrong_suffix(monkeypatch, tmp_path):
    monkeypatch.setattr(cf, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "x.txt"
    p.write_text("{}")
    assert cf._validate_transcript_path(str(p)) is None


def test_validate_accepts_valid(monkeypatch, tmp_path):
    monkeypatch.setattr(cf, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "ok.jsonl"
    p.write_text("{}")
    assert cf._validate_transcript_path(str(p)) == p.resolve()


def test_validate_blank_or_none():
    assert cf._validate_transcript_path("") is None
    assert cf._validate_transcript_path(None) is None


# ─── extract_context ───────────────────────────────────────────────────────

def test_extract_context_pulls_step0():
    blob = "\n".join([
        _msg("user", "Build the thing"),
        _msg("assistant",
             "Objective: do X.\nScope: just the lib.\nSuccess criteria: tests pass.\nAssumptions: env present."),
    ])
    ctx = cf.extract_context(blob)
    assert ctx.step0_block is not None
    assert "Objective:" in ctx.step0_block
    assert "Scope:" in ctx.step0_block


def test_extract_context_keeps_only_last_step0():
    blob = "\n".join([
        _msg("user", "first"),
        _msg("assistant", "Objective: A\nScope: a\nSuccess criteria: a"),
        _msg("user", "second"),
        _msg("assistant", "Objective: B\nScope: b\nSuccess criteria: b\nAssumptions: b"),
    ])
    ctx = cf.extract_context(blob)
    # Last Step 0 wins
    assert "Objective: B" in ctx.step0_block


def test_extract_context_step0_none_when_too_few_markers():
    blob = "\n".join([
        _msg("user", "x"),
        _msg("assistant", "Objective: x\nScope: y"),  # only 2 markers
    ])
    ctx = cf.extract_context(blob)
    assert ctx.step0_block is None


def test_extract_context_collects_recent_turns():
    blob = "\n".join([
        _msg("user", "hi"),
        _msg("assistant", "hello"),
        _msg("user", "do it"),
        _msg("assistant", "doing"),
    ])
    ctx = cf.extract_context(blob, max_recent_turns=10)
    assert len(ctx.recent_turns) == 4
    assert ctx.recent_turns[0] == ("user", "hi")
    assert ctx.recent_turns[-1][0] == "assistant"


def test_extract_context_caps_recent_turns():
    lines = []
    for i in range(20):
        lines.append(_msg("user" if i % 2 == 0 else "assistant", f"msg-{i}"))
    ctx = cf.extract_context("\n".join(lines), max_recent_turns=5)
    assert len(ctx.recent_turns) == 5
    # Most recent kept (msg-19 last)
    assert ctx.recent_turns[-1][1] == "msg-19"


def test_extract_context_collects_active_files_from_tool_use():
    blob = "\n".join([
        _msg("user", "read it"),
        _tool_use("Read", "/abs/path/foo.py"),
        _tool_use("Edit", "/abs/path/bar.py"),
        _tool_use("Write", "/abs/path/baz.py"),
        _tool_use("NotebookEdit", "/abs/path/qux.ipynb", key="notebook_path"),
        _tool_use("Glob", "/abs/path/quux.py", key="path"),
    ])
    ctx = cf.extract_context(blob)
    assert ctx.active_files == [
        "/abs/path/foo.py", "/abs/path/bar.py",
        "/abs/path/baz.py", "/abs/path/qux.ipynb",
        "/abs/path/quux.py",
    ]


def test_extract_context_dedupes_files_preserves_order():
    blob = "\n".join([
        _tool_use("Read", "/abs/foo.py"),
        _tool_use("Read", "/abs/bar.py"),
        _tool_use("Edit", "/abs/foo.py"),  # duplicate
    ])
    ctx = cf.extract_context(blob)
    assert ctx.active_files == ["/abs/foo.py", "/abs/bar.py"]


def test_extract_context_ignores_non_file_tools():
    blob = "\n".join([
        _msg("assistant", "thinking..."),
        json.dumps({
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "name": "Bash",
                             "input": {"command": "rm -rf /"}}],
            }
        }),
    ])
    ctx = cf.extract_context(blob)
    assert ctx.active_files == []


# ─── render_brief ──────────────────────────────────────────────────────────

def test_render_brief_includes_all_three_sections():
    ctx = cf.ForkedContext(
        step0_block="Objective: x\nScope: y\nSuccess criteria: z",
        recent_turns=[("user", "do it"), ("assistant", "ok")],
        active_files=["/abs/foo.py"],
    )
    out = cf.render_brief(ctx, max_tokens=4000)
    assert "## Current directive (Step 0)" in out
    assert "Objective: x" in out
    assert "## Active files" in out
    assert "`/abs/foo.py`" in out
    assert "## Recent turns" in out
    assert "USER" in out and "ASSISTANT" in out


def test_render_brief_handles_empty_context():
    out = cf.render_brief(cf.ForkedContext(), max_tokens=4000)
    assert "_No Step 0 RESTATE found" in out
    assert "_No file-touching tool calls" in out


def test_render_brief_truncates_to_max_tokens():
    huge = "x" * 50_000
    ctx = cf.ForkedContext(
        step0_block=huge,
        recent_turns=[("user", huge), ("assistant", huge)],
        active_files=[],
    )
    out = cf.render_brief(ctx, max_tokens=200)
    # 200 tokens × 4 chars/token = 800 char ceiling; allow a small slop.
    assert len(out) <= 1_000
    assert "[truncated" in out


# ─── build_forked_context — public surface ────────────────────────────────

def test_build_returns_empty_for_invalid_path():
    assert cf.build_forked_context("/no/such/x.jsonl") == ""
    assert cf.build_forked_context("") == ""
    assert cf.build_forked_context(None) == ""


def test_build_returns_empty_for_invalid_max_tokens(monkeypatch, tmp_path):
    monkeypatch.setattr(cf, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "ok.jsonl"
    p.write_text(_msg("user", "hi"))
    assert cf.build_forked_context(str(p), max_tokens=0) == ""
    assert cf.build_forked_context(str(p), max_tokens=-1) == ""


def test_build_happy_path(monkeypatch, tmp_path):
    monkeypatch.setattr(cf, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "live.jsonl"
    p.write_text("\n".join([
        _msg("user", "do this"),
        _msg("assistant",
             "Objective: ship X\nScope: a, b\nSuccess criteria: tests pass"),
        _tool_use("Read", "/abs/foo.py"),
        _msg("assistant", "Will read foo.py"),
    ]))
    out = cf.build_forked_context(str(p), max_tokens=4000)
    assert "Objective: ship X" in out
    assert "/abs/foo.py" in out
    assert "Will read foo.py" in out


def test_build_returns_empty_when_transcript_unreadable(monkeypatch, tmp_path):
    monkeypatch.setattr(cf, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "ok.jsonl"
    p.write_text("")  # empty
    out = cf.build_forked_context(str(p))
    assert out == ""


def test_build_swallows_extraction_exceptions(monkeypatch, tmp_path):
    monkeypatch.setattr(cf, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "ok.jsonl"
    p.write_text(_msg("user", "x"))

    def boom(*_a, **_k):
        raise RuntimeError("simulated extraction crash")

    monkeypatch.setattr(cf, "extract_context", boom)
    assert cf.build_forked_context(str(p)) == ""


# ─── security guard surface ────────────────────────────────────────────────

@patch("subprocess.run")
@patch("subprocess.check_call")
@patch("subprocess.check_output")
def test_no_subprocess_calls_anywhere(check_output, check_call, run, monkeypatch, tmp_path):
    monkeypatch.setattr(cf, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "ok.jsonl"
    p.write_text(_msg("user", "x"))
    cf.build_forked_context(str(p))
    run.assert_not_called()
    check_call.assert_not_called()
    check_output.assert_not_called()


@pytest.mark.parametrize("bad", [
    "http://x/y.jsonl", "https://x/y.jsonl", "file:///x/y.jsonl",
    "../../../etc/x.jsonl", "/tmp/x\x00.jsonl",
])
def test_security_rejects_path_payloads(bad):
    assert cf.build_forked_context(bad) == ""
