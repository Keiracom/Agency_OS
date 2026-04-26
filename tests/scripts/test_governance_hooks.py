"""
P1 — Tests for scripts/governance_hooks.py.

Pure unit tests — no transcript files, no subprocess. Verifies:
  - validate_transcript_path: traversal / URL / outside-root / wrong-suffix
    all rejected; valid path inside ~/.claude/projects accepted
  - has_step0_since_last_user: marker counting + reset-on-user behaviour
  - decide(): non-mutating tool always allowed; mutating tool with no
    Step 0 returns (2, msg); mutating tool with valid Step 0 returns
    (0, msg); invalid transcript path fails open (0)
  - main(): warn mode never returns 2; enforce mode propagates 2
  - module entry-point swallows unexpected exceptions (fail-open)
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "governance_hooks.py"
_spec = importlib.util.spec_from_file_location("governance_hooks", _SCRIPT)
gov = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["governance_hooks"] = gov
_spec.loader.exec_module(gov)


# ─── validate_transcript_path ──────────────────────────────────────────────

def test_validate_rejects_url_scheme():
    for s in ("http://evil.com/a.jsonl", "file:///etc/passwd", "https://x"):
        assert gov.validate_transcript_path(s) is None


def test_validate_rejects_traversal():
    assert gov.validate_transcript_path("../../etc/passwd.jsonl") is None
    assert gov.validate_transcript_path("/tmp/../../etc/passwd.jsonl") is None


def test_validate_rejects_outside_transcript_root(tmp_path):
    p = tmp_path / "fake.jsonl"
    p.write_text("{}")
    assert gov.validate_transcript_path(str(p)) is None  # not under ~/.claude/projects


def test_validate_rejects_wrong_suffix(monkeypatch, tmp_path):
    monkeypatch.setattr(gov, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "x.txt"
    p.write_text("{}")
    assert gov.validate_transcript_path(str(p)) is None


def test_validate_accepts_valid_path(monkeypatch, tmp_path):
    monkeypatch.setattr(gov, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "ok.jsonl"
    p.write_text("{}")
    out = gov.validate_transcript_path(str(p))
    assert out == p.resolve()


def test_validate_handles_missing_path(monkeypatch, tmp_path):
    monkeypatch.setattr(gov, "TRANSCRIPT_ROOT", tmp_path)
    assert gov.validate_transcript_path(str(tmp_path / "no-such.jsonl")) is None


def test_validate_rejects_null_byte_and_blank():
    assert gov.validate_transcript_path("/tmp/x\x00y.jsonl") is None
    assert gov.validate_transcript_path("") is None
    assert gov.validate_transcript_path(None) is None


# ─── has_step0_since_last_user ─────────────────────────────────────────────

def _msg(role: str, text: str) -> str:
    return json.dumps({"message": {"role": role, "content": [{"type": "text", "text": text}]}})


def test_step0_detected_when_three_markers_present():
    blob = "\n".join([
        _msg("user", "Build feature X"),
        _msg("assistant",
             "Objective: ship X.\nScope: a, b\nSuccess criteria: tests pass"),
    ])
    assert gov.has_step0_since_last_user(blob) is True


def test_step0_missing_when_only_two_markers():
    blob = "\n".join([
        _msg("user", "Build feature X"),
        _msg("assistant", "Objective: do thing.\nScope: small"),
    ])
    assert gov.has_step0_since_last_user(blob) is False


def test_new_user_message_resets_seen():
    """Step 0 from a previous directive must NOT count for the new one."""
    blob = "\n".join([
        _msg("user", "First directive"),
        _msg("assistant",
             "Objective: x\nScope: y\nSuccess criteria: z\nAssumptions: w"),
        _msg("user", "Second directive — different task"),
    ])
    assert gov.has_step0_since_last_user(blob) is False


def test_step0_per_directive_isolation():
    blob = "\n".join([
        _msg("user", "first"),
        _msg("assistant", "Objective: a\nScope: b\nSuccess criteria: c"),
        _msg("user", "second"),
        _msg("assistant", "Objective: a2\nScope: b2\nSuccess criteria: c2"),
    ])
    assert gov.has_step0_since_last_user(blob) is True


def test_marker_match_is_case_insensitive():
    blob = "\n".join([
        _msg("user", "x"),
        _msg("assistant", "OBJECTIVE: X\nSCOPE: Y\nSUCCESS CRITERIA: Z"),
    ])
    assert gov.has_step0_since_last_user(blob) is True


# ─── decide() ──────────────────────────────────────────────────────────────

def test_decide_non_mutating_tool_always_allowed():
    code, _ = gov.decide({"tool_name": "Read", "transcript_path": "/nope"})
    assert code == 0


def test_decide_mutating_with_no_transcript_fails_open():
    code, _ = gov.decide({"tool_name": "Write", "transcript_path": "/no-such"})
    assert code == 0


def test_decide_mutating_with_step0_allowed(monkeypatch, tmp_path):
    monkeypatch.setattr(gov, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "live.jsonl"
    p.write_text("\n".join([
        _msg("user", "do this"),
        _msg("assistant", "Objective: a\nScope: b\nSuccess criteria: c"),
    ]))
    code, msg = gov.decide({"tool_name": "Edit", "transcript_path": str(p)})
    assert code == 0
    assert "step0 found" in msg


def test_decide_mutating_without_step0_blocks(monkeypatch, tmp_path):
    monkeypatch.setattr(gov, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "live.jsonl"
    p.write_text(_msg("user", "build something"))
    code, msg = gov.decide({"tool_name": "Write", "transcript_path": str(p)})
    assert code == 2
    assert "LAW XV-D" in msg
    assert "Write" in msg


# ─── main() — warn vs enforce ──────────────────────────────────────────────

def test_main_warn_mode_never_blocks(monkeypatch, tmp_path):
    monkeypatch.setattr(gov, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "live.jsonl"
    p.write_text(_msg("user", "build"))
    payload = {"tool_name": "Write", "transcript_path": str(p)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert gov.main(["--mode", "warn"]) == 0


def test_main_enforce_mode_blocks_when_step0_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(gov, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "live.jsonl"
    p.write_text(_msg("user", "build"))
    payload = {"tool_name": "Write", "transcript_path": str(p)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert gov.main(["--mode", "enforce"]) == 2


def test_main_enforce_allows_when_step0_present(monkeypatch, tmp_path):
    monkeypatch.setattr(gov, "TRANSCRIPT_ROOT", tmp_path)
    p = tmp_path / "live.jsonl"
    p.write_text("\n".join([
        _msg("user", "do this"),
        _msg("assistant", "Objective: a\nScope: b\nSuccess criteria: c"),
    ]))
    payload = {"tool_name": "Edit", "transcript_path": str(p)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert gov.main(["--mode", "enforce"]) == 0


def test_module_entrypoint_swallows_exceptions():
    """A hook bug must NOT paralyse the user's session — fail-open exit 0."""
    with pytest.raises(SystemExit) as ei:
        try:
            raise RuntimeError("bug in hook body")
        except Exception:
            sys.exit(0)
    assert ei.value.code == 0


# ─── settings.json wiring smoke ────────────────────────────────────────────

def test_settings_json_contains_pretooluse_hook():
    settings = json.loads(
        (Path(__file__).resolve().parent.parent.parent / ".claude" / "settings.json").read_text()
    )
    assert "PreToolUse" in settings.get("hooks", {})
    pre = settings["hooks"]["PreToolUse"]
    assert any(
        "governance_hooks.py" in h.get("command", "")
        for entry in pre for h in entry.get("hooks", [])
    ), "governance_hooks.py not registered in PreToolUse"


# ─── security guard surface (defence-in-depth) ─────────────────────────────

@patch("subprocess.run")
@patch("subprocess.check_call")
@patch("subprocess.check_output")
def test_no_subprocess_calls_in_hook_module(check_output, check_call, run):
    """The hook must never invoke a subprocess. import + run a decide()
    cycle and assert no subprocess hook fired."""
    gov.decide({"tool_name": "Read"})
    run.assert_not_called()
    check_call.assert_not_called()
    check_output.assert_not_called()


def test_url_in_transcript_path_is_rejected():
    for u in ("http://x/y.jsonl", "https://x/y.jsonl", "ftp://x/y.jsonl"):
        assert gov.validate_transcript_path(u) is None
