"""Integration-style test for the cache-discipline CI guard (CB-10).

Verifies BOTH:
  - Positive path: the guard passes on the current repo tree.
  - Negative path (per feedback_negative_path_test_before_approve): a
    synthetic offender file inside src/keiracom_system/ outside the cache
    module triggers a non-zero exit.

The shell script is the source of truth; this test exercises it via subprocess
so a future refactor of the script doesn't silently break the discipline.

Pattern shape: import-detection (mirrors boundary-matrix-v1 guard (b)). Direct
call-site detection (e.g. `client.set(...)`) would require flow analysis;
chokepoint is at the import barrier.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GUARD = REPO_ROOT / "scripts" / "ci" / "check_no_raw_valkey_outside_client.sh"


def _run_guard(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(GUARD)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_guard_passes_on_clean_tree():
    """Positive path — current repo state is clean (PR-introducing-this-test)."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    result = _run_guard(REPO_ROOT)
    assert result.returncode == 0, f"guard failed on clean tree: {result.stdout}\n{result.stderr}"
    assert "no raw redis/valkey imports outside cache module" in result.stdout


def test_guard_fails_on_synthetic_import_offender(tmp_path: Path):
    """Negative path — synthetic `import redis` outside cache/ MUST fail."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    scope_dir = tmp_path / "src" / "keiracom_system" / "leaky"
    scope_dir.mkdir(parents=True)
    (scope_dir / "leak.py").write_text(
        "import redis\nclient = redis.Redis()\nclient.set('raw-key', 'value')\n"
    )
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_no_raw_valkey_outside_client.sh")
    result = _run_guard(tmp_path)
    assert result.returncode != 0, (
        f"guard should have failed on synthetic offender; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "FAIL (cache-discipline)" in result.stdout
    assert "leak.py" in result.stdout


def test_guard_fails_on_from_redis_import(tmp_path: Path):
    """`from redis import X` should also fail."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    scope_dir = tmp_path / "src" / "keiracom_system" / "leaky"
    scope_dir.mkdir(parents=True)
    (scope_dir / "leak.py").write_text("from redis import Redis\n")
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_no_raw_valkey_outside_client.sh")
    result = _run_guard(tmp_path)
    assert result.returncode != 0
    assert "FAIL (cache-discipline)" in result.stdout


def test_guard_fails_on_valkey_import(tmp_path: Path):
    """`import valkey` (the other client lib) MUST also fail outside cache/."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    scope_dir = tmp_path / "src" / "keiracom_system" / "leaky"
    scope_dir.mkdir(parents=True)
    (scope_dir / "leak.py").write_text("import valkey\n")
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_no_raw_valkey_outside_client.sh")
    result = _run_guard(tmp_path)
    assert result.returncode != 0


def test_guard_exempts_cache_module(tmp_path: Path):
    """ValkeyClient is the canonical owner; cache/ imports of redis are exempt."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    cache_dir = tmp_path / "src" / "keiracom_system" / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "valkey_client.py").write_text("import redis\n")
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_no_raw_valkey_outside_client.sh")
    result = _run_guard(tmp_path)
    assert result.returncode == 0, (
        f"guard should exempt cache/; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_guard_inactive_when_scope_missing(tmp_path: Path):
    """Empty repo (no src/keiracom_system/) — guard exits 0 with `inactive` message."""
    if not GUARD.exists():
        pytest.skip("guard script not present")
    scripts_dir = tmp_path / "scripts" / "ci"
    scripts_dir.mkdir(parents=True)
    shutil.copy(GUARD, scripts_dir / "check_no_raw_valkey_outside_client.sh")
    result = _run_guard(tmp_path)
    assert result.returncode == 0
    assert "guard inactive" in result.stdout
