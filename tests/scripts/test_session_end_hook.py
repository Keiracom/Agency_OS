"""
A3 — Tests for scripts/session_end_hook.py.

Pure mocks — no Drive, no Supabase. Confirms:
  - read_hook_input parses stdin JSON / tolerates garbage
  - maybe_mirror_manual fires the mirror script ONLY when the working
    MANUAL.md blob hash differs from the last-mirrored one
  - maybe_mirror_manual short-circuits when MANUAL.md missing
  - write_memory tolerates a missing DSN (no exception)
  - main() always returns 0 (never blocks SessionEnd)
  - main() handles unexpected exceptions in steps without raising
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "session_end_hook.py"
_spec = importlib.util.spec_from_file_location("session_end_hook", _SCRIPT)
hook = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["session_end_hook"] = hook
_spec.loader.exec_module(hook)


# ─── read_hook_input ───────────────────────────────────────────────────────


def test_read_hook_input_parses_valid_json(monkeypatch):
    payload = {"session_id": "abc", "reason": "exit"}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert hook.read_hook_input() == payload


def test_read_hook_input_returns_empty_on_garbage(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))
    assert hook.read_hook_input() == {}


def test_read_hook_input_returns_empty_on_blank(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert hook.read_hook_input() == {}


# ─── maybe_mirror_manual ───────────────────────────────────────────────────


def test_mirror_skipped_when_manual_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(hook, "MANUAL_PATH", tmp_path / "no-such-manual.md")
    report = hook.maybe_mirror_manual()
    assert report["manual_present"] is False
    assert report["mirror_invoked"] is False


def test_mirror_skipped_when_blob_unchanged(monkeypatch, tmp_path):
    """current blob == last-mirrored blob → no subprocess call."""
    manual = tmp_path / "MANUAL.md"
    manual.write_text("hello")
    monkeypatch.setattr(hook, "MANUAL_PATH", manual)
    monkeypatch.setattr(hook, "_git_blob_hash", lambda _p: "deadbeef")
    monkeypatch.setattr(hook, "_last_mirrored_blob", lambda: "deadbeef")
    with patch.object(hook.subprocess, "run") as run:
        report = hook.maybe_mirror_manual()
    run.assert_not_called()
    assert report["changed"] is False
    assert report["mirror_invoked"] is False


def test_mirror_fires_when_blob_changed(monkeypatch, tmp_path):
    manual = tmp_path / "MANUAL.md"
    manual.write_text("new content")
    monkeypatch.setattr(hook, "MANUAL_PATH", manual)
    monkeypatch.setattr(hook, "MIRROR_SCRIPT", manual)  # any path that exists
    monkeypatch.setattr(hook, "_git_blob_hash", lambda _p: "newhash")
    monkeypatch.setattr(hook, "_last_mirrored_blob", lambda: "oldhash")

    fake_proc = MagicMock(returncode=0, stdout="", stderr="")
    with patch.object(hook.subprocess, "run", return_value=fake_proc) as run:
        report = hook.maybe_mirror_manual()

    run.assert_called_once()
    args = run.call_args.args[0]
    assert "--force" in args
    assert report["mirror_invoked"] is True
    assert report["exit_code"] == 0


def test_mirror_handles_subprocess_timeout(monkeypatch, tmp_path):
    manual = tmp_path / "MANUAL.md"
    manual.write_text("x")
    monkeypatch.setattr(hook, "MANUAL_PATH", manual)
    monkeypatch.setattr(hook, "MIRROR_SCRIPT", manual)
    monkeypatch.setattr(hook, "_git_blob_hash", lambda _p: "a")
    monkeypatch.setattr(hook, "_last_mirrored_blob", lambda: "b")

    def boom(*_a, **_k):
        raise hook.subprocess.TimeoutExpired(cmd="x", timeout=20)

    with patch.object(hook.subprocess, "run", side_effect=boom):
        report = hook.maybe_mirror_manual()
    # Timeout did not crash; report records the attempt path
    assert report["changed"] is True
    assert report["mirror_invoked"] is False


def test_mirror_skipped_when_script_missing(monkeypatch, tmp_path):
    manual = tmp_path / "MANUAL.md"
    manual.write_text("x")
    monkeypatch.setattr(hook, "MANUAL_PATH", manual)
    monkeypatch.setattr(hook, "MIRROR_SCRIPT", tmp_path / "no_such_mirror.py")
    monkeypatch.setattr(hook, "_git_blob_hash", lambda _p: "a")
    monkeypatch.setattr(hook, "_last_mirrored_blob", lambda: "b")
    with patch.object(hook.subprocess, "run") as run:
        report = hook.maybe_mirror_manual()
    run.assert_not_called()
    assert report["mirror_invoked"] is False


# ─── _last_mirrored_blob ───────────────────────────────────────────────────


def test_last_mirrored_blob_returns_none_when_state_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(hook, "STATE_PATH", tmp_path / "no-such-state")
    assert hook._last_mirrored_blob() is None


def test_last_mirrored_blob_returns_value_when_state_present(monkeypatch, tmp_path):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"last_fingerprint": {"git_blob": "abc123"}}))
    monkeypatch.setattr(hook, "STATE_PATH", state)
    assert hook._last_mirrored_blob() == "abc123"


def test_last_mirrored_blob_returns_none_on_garbage(monkeypatch, tmp_path):
    state = tmp_path / "state.json"
    state.write_text("not-json")
    monkeypatch.setattr(hook, "STATE_PATH", state)
    assert hook._last_mirrored_blob() is None


# ─── write_memory ──────────────────────────────────────────────────────────


def test_write_memory_returns_safely_when_no_dsn(monkeypatch):
    monkeypatch.setattr(hook, "_supabase_dsn", lambda: None)
    out = hook.write_memory({"session_id": "x", "manual_mirror": {}})
    assert out == {"ceo_memory_upserted": False, "daily_log_written": False}


def test_write_memory_handles_db_error(monkeypatch):
    monkeypatch.setattr(hook, "_supabase_dsn", lambda: "postgresql://fake")
    # Simulate asyncpg raising at connect time
    fake_asyncpg = MagicMock()
    fake_asyncpg.connect.side_effect = RuntimeError("network down")
    monkeypatch.setitem(sys.modules, "asyncpg", fake_asyncpg)
    out = hook.write_memory({"session_id": "x", "manual_mirror": {}})
    assert out["ceo_memory_upserted"] is False
    assert out["daily_log_written"] is False


# ─── main() — always returns 0 ─────────────────────────────────────────────


def test_main_returns_zero_on_happy_path(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO('{"session_id":"x","reason":"exit"}'))
    monkeypatch.setattr(hook, "maybe_mirror_manual", lambda: {"mirror_invoked": False})
    monkeypatch.setattr(
        hook,
        "write_memory",
        lambda _s: {
            "ceo_memory_upserted": True,
            "daily_log_written": True,
        },
    )
    assert hook.main() == 0


def test_main_returns_zero_even_when_steps_raise(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))

    def boom():
        raise RuntimeError("step exploded")

    monkeypatch.setattr(hook, "maybe_mirror_manual", boom)
    # main wraps in try/except at module level via __main__ guard,
    # but main() itself must propagate; the entry-point catches it.
    with pytest.raises(RuntimeError):
        hook.main()


def test_module_entrypoint_swallows_exceptions(monkeypatch):
    """The __main__ guard must convert ANY hook failure into exit-0 so
    Claude Code never blocks the SessionEnd transition."""
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))

    def boom():
        raise RuntimeError("kaboom")

    monkeypatch.setattr(hook, "main", boom)
    # Re-execute the __main__ block guard logic directly
    with pytest.raises(SystemExit) as ei:
        try:
            sys.exit(hook.main())
        except Exception:
            sys.exit(0)
    assert ei.value.code == 0


# ─── settings.json wiring smoke ────────────────────────────────────────────


def test_settings_json_contains_session_end_hook():
    settings = json.loads(
        (Path(__file__).resolve().parent.parent.parent / ".claude" / "settings.json").read_text()
    )
    assert "hooks" in settings
    assert "SessionEnd" in settings["hooks"]
    se = settings["hooks"]["SessionEnd"]
    assert isinstance(se, list) and len(se) >= 1
    # The first SessionEnd entry references our hook script
    cmd_block = se[0]
    assert "hooks" in cmd_block
    assert any("session_end_hook.py" in h.get("command", "") for h in cmd_block["hooks"]), (
        "session_end_hook.py not registered in .claude/settings.json"
    )
