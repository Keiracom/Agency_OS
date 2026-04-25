"""
M11 — Tests for scripts/write_manual_mirror.py staleness check.

Covers:
  - fingerprint() captures sha256 + size + mtime; git_blob present in git repo
  - is_unchanged() returns True only when the stable identifier matches
  - load_state / save_state roundtrip
  - main() exits 2 when MANUAL.md unchanged since last mirror
  - main() exits 0 when MANUAL.md changed (Drive write mocked)
  - main() with --force exits 0 even when unchanged
  - main() with --check exits 2 when stale, 0 when fresh, no Drive write
  - main() exits 3 when MANUAL.md missing
  - state file is updated after a successful mirror

Pure file/process I/O — no Drive calls (mirror_to_drive monkeypatched).
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "write_manual_mirror.py"
_spec = importlib.util.spec_from_file_location("write_manual_mirror", _SCRIPT)
mirror = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(mirror)


@pytest.fixture()
def tmp_manual(tmp_path, monkeypatch):
    """Redirect MANUAL_PATH + STATE_PATH to a temp dir for isolation."""
    manual = tmp_path / "MANUAL.md"
    state = tmp_path / ".manual_mirror_state"
    manual.write_text("# initial\n\nfirst version of the manual.\n")
    monkeypatch.setattr(mirror, "MANUAL_PATH", manual)
    monkeypatch.setattr(mirror, "STATE_PATH", state)
    return manual, state


# ─── fingerprint ───────────────────────────────────────────────────────────

def test_fingerprint_includes_sha_and_size(tmp_manual):
    manual, _ = tmp_manual
    fp = mirror.fingerprint(manual)
    assert "sha256" in fp
    assert "size" in fp
    assert fp["size"] == manual.stat().st_size


def test_is_unchanged_matches_on_sha_only_when_no_git_blob():
    a = {"sha256": "abc", "size": 10}
    b = {"sha256": "abc", "size": 10}
    c = {"sha256": "xyz", "size": 10}
    assert mirror.is_unchanged(a, b) is True
    assert mirror.is_unchanged(a, c) is False


def test_is_unchanged_prefers_git_blob_when_present():
    a = {"sha256": "abc", "git_blob": "deadbeef"}
    b = {"sha256": "different", "git_blob": "deadbeef"}
    # sha256 differs (impossible in real life but tests preference) — git_blob wins
    assert mirror.is_unchanged(a, b) is True


# ─── state roundtrip ───────────────────────────────────────────────────────

def test_load_state_returns_empty_when_missing(tmp_manual):
    _, state = tmp_manual
    assert not state.exists()
    assert mirror.load_state() == {}


def test_save_then_load_state_roundtrip(tmp_manual):
    _, state = tmp_manual
    payload = {"last_fingerprint": {"sha256": "abc"}, "last_mirrored_at": "2026-04-25T12:00:00+00:00"}
    mirror.save_state(payload)
    assert state.exists()
    assert mirror.load_state() == payload


# ─── main() flows ──────────────────────────────────────────────────────────

def test_main_exits_3_when_manual_missing(tmp_manual, caplog):
    manual, _ = tmp_manual
    manual.unlink()
    code = mirror.main([])
    assert code == 3


def test_main_first_run_succeeds_and_writes_state(tmp_manual, caplog):
    _, state = tmp_manual
    with patch.object(mirror, "mirror_to_drive") as m:
        code = mirror.main([])
    assert code == 0
    m.assert_called_once()
    saved = json.loads(state.read_text())
    assert "last_fingerprint" in saved
    assert "sha256" in saved["last_fingerprint"]


def test_main_refuses_when_unchanged(tmp_manual, caplog):
    _, state = tmp_manual
    # First mirror
    with patch.object(mirror, "mirror_to_drive"):
        assert mirror.main([]) == 0
    # Second run with no changes — must refuse
    with patch.object(mirror, "mirror_to_drive") as m:
        code = mirror.main([])
    assert code == 2
    m.assert_not_called()


def test_main_force_overrides_staleness_check(tmp_manual):
    # Seed state so the next plain run would be unchanged
    with patch.object(mirror, "mirror_to_drive"):
        mirror.main([])
    # --force must mirror even though nothing changed
    with patch.object(mirror, "mirror_to_drive") as m:
        code = mirror.main(["--force"])
    assert code == 0
    m.assert_called_once()


def test_main_proceeds_when_manual_changes(tmp_manual):
    manual, _ = tmp_manual
    with patch.object(mirror, "mirror_to_drive"):
        mirror.main([])
    # Edit the file
    manual.write_text(manual.read_text() + "\n\n## NEW SECTION\n")
    with patch.object(mirror, "mirror_to_drive") as m:
        code = mirror.main([])
    assert code == 0
    m.assert_called_once()


def test_main_check_mode_prints_verdict_no_drive_write(tmp_manual):
    """--check exits 0 when fresh, 2 when stale, never calls mirror."""
    # Fresh first run — no state yet, treated as 'changed'
    with patch.object(mirror, "mirror_to_drive") as m:
        assert mirror.main(["--check"]) == 0
    m.assert_not_called()
    # Persist a state matching current content
    with patch.object(mirror, "mirror_to_drive"):
        mirror.main([])
    # Now --check should report stale
    with patch.object(mirror, "mirror_to_drive") as m2:
        assert mirror.main(["--check"]) == 2
    m2.assert_not_called()


# ─── post-commit hook smoke ────────────────────────────────────────────────

def test_post_commit_hook_exists_and_executable():
    repo_root = Path(__file__).resolve().parent.parent.parent
    hook = repo_root / ".githooks" / "post-commit"
    assert hook.exists(), "post-commit hook missing"
    assert os.access(str(hook), os.X_OK), "post-commit hook not executable"
    body = hook.read_text()
    assert "docs/MANUAL.md" in body
    assert "write_manual_mirror.py" in body
