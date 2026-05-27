"""Integration test for the Composer-isolation CI guard.

Verifies the negative-path probe fires correctly + the positive-path
(no Composer in tree) returns the inert message. Mirrors the pattern from
tests/keiracom_system/cache/test_no_raw_valkey_outside_client.py (PR #1173)
and tests/keiracom_system/atomization/test_atom_store_ci_guard.py
(PR #1185).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GUARD = REPO_ROOT / "scripts" / "ci" / "check_composer_output_never_reaches_agent_reasoning.sh"


def _run_guard(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(GUARD)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_guard_inert_when_composer_not_present(tmp_path: Path):
    """No src/keiracom_system/ directory → guard exits 0 with 'inactive' message.

    This is the current state of main (PR #1189 not yet merged), so the
    real-tree run also hits this path.
    """
    if not GUARD.exists():
        pytest.skip("guard script not present")
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_composer_output_never_reaches_agent_reasoning.sh")
    result = _run_guard(tmp_path)
    assert result.returncode == 0
    assert "guard inactive" in result.stdout


def test_guard_inert_when_composer_file_missing(tmp_path: Path):
    """src/keiracom_system/ exists but no composer.py → guard inert."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    (tmp_path / "src" / "keiracom_system" / "atomization").mkdir(parents=True)
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_composer_output_never_reaches_agent_reasoning.sh")
    result = _run_guard(tmp_path)
    assert result.returncode == 0
    assert "guard inert" in result.stdout


def test_guard_passes_on_clean_tree_with_composer(tmp_path: Path):
    """Composer present, no offenders → guard exits 0 with clean message."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    atom_dir = tmp_path / "src" / "keiracom_system" / "atomization"
    atom_dir.mkdir(parents=True)
    (atom_dir / "composer.py").write_text("# stub")
    (atom_dir / "__init__.py").write_text(
        "from src.keiracom_system.atomization.composer import Composer"
    )
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_composer_output_never_reaches_agent_reasoning.sh")
    result = _run_guard(tmp_path)
    assert result.returncode == 0
    assert "no Composer imports outside endpoints/" in result.stdout


def test_guard_fails_on_composer_import_in_agent_reasoning_module(tmp_path: Path):
    """Synthetic offender: importing Composer outside endpoints/ MUST fail."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    atom_dir = tmp_path / "src" / "keiracom_system" / "atomization"
    atom_dir.mkdir(parents=True)
    (atom_dir / "composer.py").write_text("# stub")
    leaky_dir = tmp_path / "src" / "keiracom_system" / "agent_reasoning"
    leaky_dir.mkdir(parents=True)
    (leaky_dir / "leaky.py").write_text(
        "from src.keiracom_system.atomization.composer import Composer\n"
    )
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_composer_output_never_reaches_agent_reasoning.sh")
    result = _run_guard(tmp_path)
    assert result.returncode != 0
    assert "FAIL (composer-isolation)" in result.stdout
    assert "agent_reasoning/leaky.py" in result.stdout


def test_guard_fails_on_composed_output_import(tmp_path: Path):
    """Importing ComposedOutput (the type) outside endpoints/ MUST also fail."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    atom_dir = tmp_path / "src" / "keiracom_system" / "atomization"
    atom_dir.mkdir(parents=True)
    (atom_dir / "composer.py").write_text("# stub")
    leaky_dir = tmp_path / "src" / "keiracom_system" / "rogue_module"
    leaky_dir.mkdir(parents=True)
    (leaky_dir / "rogue.py").write_text(
        "from src.keiracom_system.atomization import ComposedOutput\n"
    )
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_composer_output_never_reaches_agent_reasoning.sh")
    result = _run_guard(tmp_path)
    assert result.returncode != 0


def test_guard_exempts_endpoints_directory(tmp_path: Path):
    """src/keiracom_system/endpoints/ is the canonical home — importers exempt."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    atom_dir = tmp_path / "src" / "keiracom_system" / "atomization"
    atom_dir.mkdir(parents=True)
    (atom_dir / "composer.py").write_text("# stub")
    endpoints_dir = tmp_path / "src" / "keiracom_system" / "endpoints"
    endpoints_dir.mkdir(parents=True)
    (endpoints_dir / "chat_reply.py").write_text(
        "from src.keiracom_system.atomization.composer import Composer\n"
    )
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_composer_output_never_reaches_agent_reasoning.sh")
    result = _run_guard(tmp_path)
    assert result.returncode == 0, (
        f"guard should exempt endpoints/; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_guard_exempts_init_module(tmp_path: Path):
    """__init__.py re-export of Composer is the canonical surface."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    atom_dir = tmp_path / "src" / "keiracom_system" / "atomization"
    atom_dir.mkdir(parents=True)
    (atom_dir / "composer.py").write_text("# stub")
    (atom_dir / "__init__.py").write_text(
        "from src.keiracom_system.atomization.composer import Composer, ComposedOutput\n"
    )
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_composer_output_never_reaches_agent_reasoning.sh")
    result = _run_guard(tmp_path)
    assert result.returncode == 0
