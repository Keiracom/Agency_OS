"""Integration test for the atom-store-discipline CI guard.

Verifies BOTH:
  - Positive path: guard passes on the current repo tree.
  - Negative path (per feedback_negative_path_test_before_approve): a
    synthetic offender file inside src/keiracom_system/ outside the
    atomization module triggers a non-zero exit.

Mirrors the test pattern from tests/keiracom_system/cache/
test_no_raw_valkey_outside_client.py (PR #1173).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GUARD = REPO_ROOT / "scripts" / "ci" / "check_no_raw_atom_store_outside_module.sh"


def _run_guard(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(GUARD)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_guard_passes_on_clean_tree():
    """Positive path — current repo (PR introducing this test) is clean."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    result = _run_guard(REPO_ROOT)
    assert result.returncode == 0, f"guard failed on clean tree: {result.stdout}\n{result.stderr}"
    assert "no raw atom-store SQL outside atomization module" in result.stdout


def test_guard_fails_on_insert_outside_module(tmp_path: Path):
    """`INSERT INTO keiracom_atoms` outside atomization/ MUST fail."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    scope_dir = tmp_path / "src" / "keiracom_system" / "leaky"
    scope_dir.mkdir(parents=True)
    (scope_dir / "leak.py").write_text(
        'cursor.execute("INSERT INTO keiracom_atoms VALUES (...)")\n'
    )
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_no_raw_atom_store_outside_module.sh")
    result = _run_guard(tmp_path)
    assert result.returncode != 0
    assert "FAIL (atom-store-discipline)" in result.stdout
    assert "leak.py" in result.stdout


def test_guard_fails_on_select_outside_module(tmp_path: Path):
    """`FROM keiracom_atoms` SELECT clause outside atomization/ MUST fail."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    scope_dir = tmp_path / "src" / "keiracom_system" / "reader"
    scope_dir.mkdir(parents=True)
    (scope_dir / "leak_read.py").write_text(
        'cursor.execute("SELECT atom_id FROM keiracom_atoms WHERE tenant_id = %s", tid)\n'
    )
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_no_raw_atom_store_outside_module.sh")
    result = _run_guard(tmp_path)
    assert result.returncode != 0
    assert "leak_read.py" in result.stdout


def test_guard_fails_on_supersession_edges_outside_module(tmp_path: Path):
    """`UPDATE keiracom_atom_supersession_edges` outside atomization/ MUST fail.

    Tests that the guard's pattern matches the suffix tables (supersession_edges
    + atomizer_jobs) not just the base keiracom_atoms table.
    """
    if not GUARD.exists():
        pytest.skip("guard script not present")
    scope_dir = tmp_path / "src" / "keiracom_system" / "leaky_edges"
    scope_dir.mkdir(parents=True)
    (scope_dir / "leak.py").write_text(
        'db.execute("UPDATE keiracom_atom_supersession_edges SET confidence = 0")\n'
    )
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_no_raw_atom_store_outside_module.sh")
    result = _run_guard(tmp_path)
    assert result.returncode != 0


def test_guard_exempts_atomization_module(tmp_path: Path):
    """src/keiracom_system/atomization/ is the canonical module owner — exempt."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    cache_dir = tmp_path / "src" / "keiracom_system" / "atomization"
    cache_dir.mkdir(parents=True)
    (cache_dir / "atom_store.py").write_text(
        'cursor.execute("INSERT INTO keiracom_atoms VALUES (...)")\n'
    )
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_no_raw_atom_store_outside_module.sh")
    result = _run_guard(tmp_path)
    assert result.returncode == 0, (
        f"guard should exempt atomization/; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_guard_inactive_when_scope_missing(tmp_path: Path):
    """Empty repo (no src/keiracom_system/) — guard exits 0 with `inactive` message."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_no_raw_atom_store_outside_module.sh")
    result = _run_guard(tmp_path)
    assert result.returncode == 0
    assert "guard inactive" in result.stdout
