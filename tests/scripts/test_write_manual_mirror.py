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


# ─── M11-3 — hook uses pinned venv python ──────────────────────────────────

def test_post_commit_hook_uses_venv_python():
    repo_root = Path(__file__).resolve().parent.parent.parent
    body = (repo_root / ".githooks" / "post-commit").read_text()
    assert "/home/elliotbot/clawd/venv/bin/python3" in body, (
        "hook must pin venv interpreter (M11-3)"
    )


# ─── M11-2 — shared state path ─────────────────────────────────────────────

def test_state_path_lives_under_shared_config_dir():
    """Default STATE_PATH must point at ~/.config/agency-os, not in scripts/."""
    expected = Path.home() / ".config" / "agency-os" / ".manual_mirror_state"
    assert expected == mirror.STATE_PATH


def test_load_state_migrates_legacy_path(tmp_path, monkeypatch):
    """When the shared file is missing but the legacy per-worktree file
    exists, load_state() copies it forward."""
    shared = tmp_path / "shared" / ".manual_mirror_state"
    legacy = tmp_path / "legacy" / ".manual_mirror_state"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(json.dumps({"last_fingerprint": {"sha256": "legacy-sha"}}))
    monkeypatch.setattr(mirror, "STATE_PATH", shared)
    monkeypatch.setattr(mirror, "_LEGACY_STATE_PATH", legacy)

    loaded = mirror.load_state()
    assert loaded["last_fingerprint"]["sha256"] == "legacy-sha"
    assert shared.exists()  # migrated forward
    assert json.loads(shared.read_text())["last_fingerprint"]["sha256"] == "legacy-sha"


# ─── M11-1 — hook installation + warning ───────────────────────────────────

def test_install_runs_git_config(monkeypatch):
    """--install must call `git config core.hooksPath .githooks` and
    return 0 when the hook file is present + executable."""
    calls: list[list[str]] = []

    def fake_check_call(args, cwd=None, **_):
        calls.append(args)
        return 0

    monkeypatch.setattr("subprocess.check_call", fake_check_call)
    code = mirror.main(["--install"])
    assert code == 0
    assert any(a[:3] == ["git", "config", "core.hooksPath"] for a in calls)


def test_install_returns_4_when_hook_missing(monkeypatch, tmp_path):
    """install_hook should fail loudly if .githooks/post-commit is gone."""
    monkeypatch.setattr(mirror, "REPO_ROOT", tmp_path)  # no .githooks dir
    code = mirror.install_hook()
    assert code == 4


def test_warn_when_hook_not_installed(monkeypatch, caplog, tmp_manual):
    """When core.hooksPath is unset, main() emits a single warning then
    proceeds (non-fatal)."""
    monkeypatch.setattr(mirror, "_current_hooks_path", lambda: None)
    with caplog.at_level("WARNING"), patch.object(mirror, "mirror_to_drive"):
        mirror.main([])
    assert any(
        "post-commit hook not installed" in r.message for r in caplog.records
    )


def test_no_warn_when_hook_correctly_installed(monkeypatch, caplog, tmp_manual):
    """When core.hooksPath == .githooks, no install warning is emitted."""
    monkeypatch.setattr(mirror, "_current_hooks_path", lambda: ".githooks")
    with caplog.at_level("WARNING"), patch.object(mirror, "mirror_to_drive"):
        mirror.main([])
    for r in caplog.records:
        assert "post-commit hook not installed" not in r.message
        assert "core.hooksPath = " not in r.message


def test_warn_when_hook_path_points_elsewhere(monkeypatch, caplog, tmp_manual):
    """A non-.githooks setting should produce the 'not .githooks' warning."""
    monkeypatch.setattr(mirror, "_current_hooks_path", lambda: ".husky")
    with caplog.at_level("WARNING"), patch.object(mirror, "mirror_to_drive"):
        mirror.main([])
    assert any(
        ".husky" in r.message and ".githooks" in r.message for r in caplog.records
    )
