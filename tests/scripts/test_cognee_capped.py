"""Unit tests for scripts/orchestrator/cognee_capped.sh.

Tests use AGENCY_OS_SYSTEMD_RUN_SKIP=1 so systemd-run is never actually
invoked — the wrapper prints the resolved command and exits 0, which
lets us assert on argv shape without touching the user systemd instance.

Acceptance test (10-chunk synthetic batch) lives outside CI as a manual
runbook step — it requires real systemd-run + a deliberate OOM trigger.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "scripts" / "orchestrator" / "cognee_capped.sh"


def _run(
    args: list[str], extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["AGENCY_OS_SYSTEMD_RUN_SKIP"] = "1"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(WRAPPER), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_help_exits_zero() -> None:
    res = subprocess.run([str(WRAPPER), "--help"], check=False, capture_output=True, text=True)
    assert res.returncode == 0
    assert "cognee_capped.sh" in res.stdout
    assert "MemoryMax" in res.stdout


def test_missing_mode_exits_2() -> None:
    res = _run([])
    assert res.returncode == 2
    assert "missing mode" in res.stderr


def test_unknown_mode_exits_2() -> None:
    res = _run(["totallyfake"])
    assert res.returncode == 2
    assert "unknown mode" in res.stderr


def test_unknown_flag_exits_2() -> None:
    res = _run(["--not-a-real-flag", "ingest"])
    assert res.returncode == 2


def test_ingest_resolves_systemd_run_command() -> None:
    res = _run(["ingest", "--", "--dry-run"])
    assert res.returncode == 0, res.stderr
    lines = [ln for ln in res.stdout.splitlines() if ln]
    assert lines[0] == "systemd-run"
    assert "--user" in lines
    assert "--scope" in lines
    assert "MemoryMax=3G" in lines
    assert "MemoryAccounting=yes" in lines
    assert any(ln.endswith("cognee_ingest.py") for ln in lines)
    assert "--dry-run" in lines


def test_server_resolves_uvicorn() -> None:
    res = _run(["server"])
    assert res.returncode == 0, res.stderr
    out = res.stdout
    assert "uvicorn" in out
    assert "cognee.api.client:app" in out
    assert "--port" in out
    assert "8000" in out


def test_exec_mode_passes_arbitrary_command() -> None:
    res = _run(["exec", "--", "/bin/true", "arg1"])
    assert res.returncode == 0, res.stderr
    lines = [ln for ln in res.stdout.splitlines() if ln]
    assert "/bin/true" in lines
    assert "arg1" in lines


def test_exec_mode_requires_command() -> None:
    res = _run(["exec"])
    assert res.returncode == 2
    assert "exec mode requires" in res.stderr


def test_max_mem_override_equals_form() -> None:
    res = _run(["--max-mem=2G", "ingest"])
    assert res.returncode == 0
    assert "MemoryMax=2G" in res.stdout


def test_max_mem_override_space_form() -> None:
    res = _run(["--max-mem", "1500M", "ingest"])
    assert res.returncode == 0
    assert "MemoryMax=1500M" in res.stdout


def test_env_max_mem_override() -> None:
    res = _run(["ingest"], extra_env={"AGENCY_OS_COGNEE_CAP_MAX_MEM": "4G"})
    assert res.returncode == 0
    assert "MemoryMax=4G" in res.stdout


def test_unit_name_per_invocation() -> None:
    res = _run(["ingest"])
    out_lines = res.stdout.splitlines()
    unit_lines = [ln for ln in out_lines if ln.startswith("--unit=")]
    assert len(unit_lines) == 1
    assert unit_lines[0].startswith("--unit=cognee-ingest-")
    assert unit_lines[0].endswith(".scope")


def test_no_cap_bypass_does_not_invoke_systemd_run(tmp_path: Path) -> None:
    """--no-cap exec /bin/true should succeed without systemd-run on PATH."""
    marker = tmp_path / "marker"
    res = subprocess.run(
        [str(WRAPPER), "--no-cap", "exec", "--", "/usr/bin/touch", str(marker)],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": "/bin:/usr/bin"},  # systemd-run still on PATH but unused
    )
    assert res.returncode == 0, res.stderr
    assert marker.exists()


def test_systemd_run_missing_without_no_cap_exits_3(tmp_path: Path) -> None:
    """If systemd-run is unreachable and --no-cap is not set, exit 3."""
    env = os.environ.copy()
    env.pop("AGENCY_OS_SYSTEMD_RUN_SKIP", None)
    env["AGENCY_OS_SYSTEMD_RUN"] = str(tmp_path / "nope-systemd-run-binary")
    res = subprocess.run(
        [str(WRAPPER), "ingest"], check=False, capture_output=True, text=True, env=env
    )
    assert res.returncode == 3, f"stdout={res.stdout!r} stderr={res.stderr!r}"
    assert "not available" in res.stderr


@pytest.mark.parametrize("mode", ["ingest", "server"])
def test_both_python_modes_resolve_python_bin(mode: str) -> None:
    res = _run([mode])
    assert res.returncode == 0
    assert "python" in res.stdout.lower()
