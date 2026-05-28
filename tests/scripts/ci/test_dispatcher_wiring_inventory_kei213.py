"""Smoke test for scripts/ci/check_dispatcher_wiring_inventory_kei213.sh.

Mirrors PR #1221 / cutover-step-4.5-dispatcher-wiring-pr5 but for the
canonical KEI-213 dispatcher per Dave + Aiden + Viktor ratify 2026-05-27.

Positive path: guard exits 0 against live repo.
Negative path (GOV-12): guard exits non-zero when copied to non-repo dir.

bd: cutover-step-4.5-dispatcher-wiring-pr-E (KEI-213)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GUARD_PATH = REPO_ROOT / "scripts" / "ci" / "check_dispatcher_wiring_inventory_kei213.sh"


def test_guard_script_exists() -> None:
    assert GUARD_PATH.exists(), f"KEI-213 wiring inventory guard not found at {GUARD_PATH}"


def test_guard_passes_against_live_repo() -> None:
    """Positive path — guard exits 0 against current repo state."""
    result = subprocess.run(
        ["bash", str(GUARD_PATH)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"KEI-213 guard failed (exit {result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert "OK — all KEI-213 wiring preconditions present" in result.stdout


def test_guard_detects_missing_modules_when_isolated(tmp_path: Path) -> None:
    """Negative path (GOV-12) — guard MUST fail when wiring points are missing."""
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
        "KEI-213 guard MUST fail when wiring points are missing (negative-path); "
        "got exit 0 + stdout: " + result.stdout
    )
    assert "ERROR: missing wiring point" in result.stdout
    assert "FAIL" in result.stdout
