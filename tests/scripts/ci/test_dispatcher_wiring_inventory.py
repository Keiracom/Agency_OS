"""Smoke test for scripts/ci/check_dispatcher_wiring_inventory.sh.

Runs the CI guard against the live repo. Passes if the guard exits 0 (all
wiring points present); fails with the guard's stderr if any wiring point
is missing.

This makes the wiring-inventory check available to pytest as well as CI,
so local pre-commit / IDE test runs catch missing wiring before push.

bd: cutover-step-4.5-dispatcher-wiring-pr5
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GUARD_PATH = REPO_ROOT / "scripts" / "ci" / "check_dispatcher_wiring_inventory.sh"


def test_guard_script_exists() -> None:
    assert GUARD_PATH.exists(), f"wiring inventory guard not found at {GUARD_PATH}"


def test_guard_passes_against_live_repo() -> None:
    """Run the CI guard against current repo state; assert exit 0."""
    result = subprocess.run(
        ["bash", str(GUARD_PATH)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"wiring inventory guard failed (exit {result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert "OK — all 9 launch-blocker wiring points present" in result.stdout


def test_guard_detects_missing_modules_when_isolated(tmp_path: Path) -> None:
    """Negative-path: when guard is COPIED to a non-repo dir, it MUST fail.

    The guard resolves REPO_ROOT via `BASH_SOURCE`, so a copy in tmp_path
    resolves REPO_ROOT to tmp_path/.. — which has no modules. The guard
    must exit non-zero with explicit ERROR messages naming the missing
    wiring points.

    This is the canonical "gates as code not comments" verification per
    GOV-12 — proves the guard actually fails when wiring points are missing.
    """
    temp_guard = tmp_path / "guard.sh"
    temp_guard.write_text(GUARD_PATH.read_text())
    temp_guard.chmod(0o755)

    result = subprocess.run(
        ["bash", str(temp_guard)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode != 0, (
        "guard MUST fail when wiring points are missing (negative-path); "
        "got exit 0 + stdout: " + result.stdout
    )
    assert "ERROR: missing wiring point" in result.stdout
    assert "FAIL" in result.stdout
