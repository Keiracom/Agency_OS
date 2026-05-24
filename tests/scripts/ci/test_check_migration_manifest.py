"""Tests for scripts/ci/check_migration_manifest.py — Agency_OS-fi4u.

Negative-path discipline per feedback_negative_path_test_before_approve:
every enforcer rule gets a synthetic-offender test that asserts the exact
exit code. Subprocess invocation pattern (tests script as CI runs it).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "scripts/ci/check_migration_manifest.py"


def _run(manifest_path: Path, *extra: str, root: Path | None = None) -> tuple[int, str, str]:
    """Subprocess-invoke the script. `root` defaults to manifest_path's parent
    so tests can use tmp_path without falling foul of the REPO_ROOT confinement.
    Production CI never passes --root."""
    if root is None and manifest_path.is_absolute():
        root = manifest_path.parent
    args = [sys.executable, str(SCRIPT), "--manifest", str(manifest_path)]
    if root is not None:
        args.extend(["--root", str(root)])
    args.extend(extra)
    cp = subprocess.run(args, capture_output=True, text=True, timeout=20, check=False)
    return cp.returncode, cp.stdout, cp.stderr


def _write(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest))


def _valid_entry(source: str = "scripts/ci/check_migration_manifest.py") -> dict:
    return {
        "source_path": source,
        "target_repo": "product",
        "target_path": source,
        "operation": "move",
        "rationale": "test",
        "active_pr_block": None,
    }


def test_valid_manifest_returns_exit_0(tmp_path):
    """Path-on-disk + valid schema + no globs → exit 0."""
    m = tmp_path / "m.json"
    _write(m, {"manifest_version": "1.0", "entries": [_valid_entry()]})
    rc, _out, err = _run(m)
    assert rc == 0, f"expected 0, got {rc}: {err}"
    assert "OK:" in err


def test_missing_manifest_returns_exit_2(tmp_path):
    """Manifest file absent → exit 2 (config error)."""
    rc, _out, err = _run(tmp_path / "absent.json")
    assert rc == 2
    assert "manifest not found" in err


def test_malformed_json_returns_exit_2(tmp_path):
    """Manifest file present but not valid JSON → exit 2."""
    m = tmp_path / "m.json"
    m.write_text("{this is not json}")
    rc, _out, err = _run(m)
    assert rc == 2
    assert "not valid JSON" in err


def test_missing_top_level_field_returns_exit_1(tmp_path):
    """Top-level missing 'entries' → exit 1."""
    m = tmp_path / "m.json"
    _write(m, {"manifest_version": "1.0"})
    rc, _out, err = _run(m)
    assert rc == 1
    assert "missing required fields" in err


def test_entry_missing_required_field_returns_exit_1(tmp_path):
    """Entry missing 'rationale' → exit 1."""
    m = tmp_path / "m.json"
    entry = _valid_entry()
    del entry["rationale"]
    _write(m, {"manifest_version": "1.0", "entries": [entry]})
    rc, _out, err = _run(m)
    assert rc == 1
    assert "missing fields" in err


def test_invalid_target_repo_returns_exit_1(tmp_path):
    """target_repo='produkt' (typo) → exit 1."""
    m = tmp_path / "m.json"
    entry = _valid_entry()
    entry["target_repo"] = "produkt"
    _write(m, {"manifest_version": "1.0", "entries": [entry]})
    rc, _out, err = _run(m)
    assert rc == 1
    assert "target_repo" in err and "produkt" in err


def test_invalid_operation_returns_exit_1(tmp_path):
    """operation='translate' → exit 1."""
    m = tmp_path / "m.json"
    entry = _valid_entry()
    entry["operation"] = "translate"
    _write(m, {"manifest_version": "1.0", "entries": [entry]})
    rc, _out, err = _run(m)
    assert rc == 1
    assert "operation" in err


def test_glob_in_source_path_returns_exit_1(tmp_path):
    """source_path='src/**/*.py' → exit 1 (enumeration discipline)."""
    m = tmp_path / "m.json"
    entry = _valid_entry()
    entry["source_path"] = "src/**/*.py"
    _write(m, {"manifest_version": "1.0", "entries": [entry]})
    rc, _out, err = _run(m)
    assert rc == 1
    assert "glob char" in err


def test_nonexistent_source_path_returns_exit_1(tmp_path):
    """source_path that doesn't exist on disk → exit 1 (path-rot)."""
    m = tmp_path / "m.json"
    entry = _valid_entry()
    entry["source_path"] = "src/dispatcher/nonexistent_ghost_module.py"
    entry["target_path"] = entry["source_path"]
    _write(m, {"manifest_version": "1.0", "entries": [entry]})
    rc, _out, err = _run(m)
    assert rc == 1
    assert "does not exist on disk" in err


def test_empty_entries_returns_exit_0(tmp_path):
    """Empty manifest (entries: []) → exit 0 (no violations to fail)."""
    m = tmp_path / "m.json"
    _write(m, {"manifest_version": "1.0", "entries": []})
    rc, _out, err = _run(m)
    assert rc == 0
    assert "OK:" in err


def test_report_mode_never_enforces(tmp_path):
    """Even with violations, --report exits 0 and prints counts."""
    m = tmp_path / "m.json"
    entry = _valid_entry()
    entry["target_repo"] = "produkt"  # invalid
    _write(m, {"manifest_version": "1.0", "entries": [entry]})
    rc, _out, err = _run(m, "--report")
    assert rc == 0
    assert "manifest entries: 1" in err
    assert "violation:" in err


def test_seed_manifest_on_disk_validates(tmp_path):
    """The real seed manifest at docs/migration/migrated_manifest_seed.json
    parses + every entry validates against the schema + every source_path
    exists on origin/main. Locks the artefact against silent regression."""
    seed = REPO_ROOT / "docs/migration/migrated_manifest_seed.json"
    if not seed.exists():
        pytest.skip("seed manifest absent (running before artefact lands)")
    rc, _out, err = _run(seed)
    assert rc == 0, f"seed manifest validation failed: {err}"


# _safe_resolve negative-path tests — pythonsecurity:S2083 path-injection guard.
# Same shape as PR #1119's _safe_resolve tests. Loads the module via importlib
# so we can call the helper directly without spawning subprocesses.


def _load_enforcer_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "cmm", REPO_ROOT / "scripts/ci/check_migration_manifest.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_safe_resolve_accepts_in_root_paths(tmp_path):
    """In-root path resolves cleanly."""
    mod = _load_enforcer_module()
    inside = tmp_path / "manifest.json"
    inside.write_text("{}")
    resolved = mod._safe_resolve(str(inside), tmp_path)
    assert resolved == inside.resolve()


def test_safe_resolve_accepts_relative_paths(tmp_path):
    """Relative path inside root resolves cleanly."""
    mod = _load_enforcer_module()
    resolved = mod._safe_resolve("subdir/manifest.json", tmp_path)
    assert resolved == (tmp_path / "subdir/manifest.json").resolve()


def test_safe_resolve_rejects_absolute_escape(tmp_path):
    """Absolute path outside root → ValueError (S2083 guard)."""
    mod = _load_enforcer_module()
    with pytest.raises(ValueError, match="escapes confinement root"):
        mod._safe_resolve("/etc/passwd", tmp_path)


def test_safe_resolve_rejects_dotdot_escape(tmp_path):
    """Relative ..-escape outside root → ValueError."""
    mod = _load_enforcer_module()
    with pytest.raises(ValueError, match="escapes confinement root"):
        mod._safe_resolve("../../../../etc/passwd", tmp_path)


def test_safe_resolve_rejects_home_expansion(tmp_path):
    """~/foo home-expansion → ValueError (fail-fast string check)."""
    mod = _load_enforcer_module()
    with pytest.raises(ValueError, match="home-expansion forbidden"):
        mod._safe_resolve("~/.ssh/id_rsa", tmp_path)


def test_safe_resolve_rejects_null_byte(tmp_path):
    """Null byte in path → ValueError (control-character guard)."""
    mod = _load_enforcer_module()
    with pytest.raises(ValueError, match="control characters"):
        mod._safe_resolve("manifest.json\x00.evil", tmp_path)


def test_safe_resolve_rejects_empty(tmp_path):
    """Empty string → ValueError."""
    mod = _load_enforcer_module()
    with pytest.raises(ValueError, match="non-empty"):
        mod._safe_resolve("", tmp_path)


def test_main_rejects_manifest_escape_with_exit_2(tmp_path):
    """End-to-end: --manifest /etc/passwd against --root tmp_path → exit 2
    (config error). The path-confinement guard rejects any path outside
    the configured root regardless of caller intent."""
    # Use tmp_path as root so the manifest path /etc/passwd is empirically
    # outside it; if --root defaulted to REPO_ROOT we'd still get exit 2
    # but for different reasons.
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--manifest", "/etc/passwd", "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert cp.returncode == 2
    assert "escapes confinement root" in cp.stderr or "ERROR:" in cp.stderr
