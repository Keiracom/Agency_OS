"""Tests for scripts/hooks/pre_task_signal.sh (KEI-39 PreToolUse claim hook).

Verifies the six behaviours the hook contract requires:

  1. Non-trivial tool (Bash) → NATS publish fires.
  2. Trivial tool (Read) → no publish (filter passes through).
  3. Missing CALLSIGN → exit 0, no publish (fail-open).
  4. NATS binary absent → exit 0, no publish (fail-open).
  5. Two emissions within dedup window → second one suppressed.
  6. TASK_REF env var lands in the published payload.

Each test spawns the hook in a subprocess with a shimmed `nats` binary on
PATH so emissions are observable without hitting a real NATS server. Dedup
state lives under a per-test tmp dir via PRE_TASK_SIGNAL_DEDUP_DIR so tests
do not leak into each other.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "scripts" / "hooks" / "pre_task_signal.sh"


def _run_hook(
    *,
    tool_name: str,
    callsign: str | None = "nova",
    nats_available: bool = True,
    task_ref_env: str | None = None,
    dedup_dir: Path,
    dedup_seconds: int = 30,
    shim_dir: Path,
) -> tuple[int, str]:
    """Run the hook with a NATS shim. Return (exit_code, nats_log_contents)."""
    shim_dir.mkdir(parents=True, exist_ok=True)
    nats_log = dedup_dir / "nats_invocations.log"

    if nats_available:
        nats_shim = shim_dir / "nats"
        nats_shim.write_text(
            f'#!/usr/bin/env bash\necho "$@" >> "{nats_log}"\nexit 0\n'
        )
        nats_shim.chmod(0o755)

    env = os.environ.copy()
    if callsign is not None:
        env["CALLSIGN"] = callsign
    else:
        env.pop("CALLSIGN", None)
    env["PATH"] = f"{shim_dir}:/usr/bin:/bin"
    env["PRE_TASK_SIGNAL_DEDUP_DIR"] = str(dedup_dir)
    env["PRE_TASK_SIGNAL_DEDUP_SECONDS"] = str(dedup_seconds)
    if task_ref_env is not None:
        env["TASK_REF"] = task_ref_env
    else:
        env.pop("TASK_REF", None)

    payload = json.dumps({"tool_name": tool_name, "tool_input": {}})
    # noqa rationale: controlled args list, shell=False — no injection risk
    proc = subprocess.run(  # noqa: S603
        ["/bin/bash", str(HOOK)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
        cwd=str(REPO_ROOT),
    )
    log = nats_log.read_text() if nats_log.exists() else ""
    return proc.returncode, log


def test_bash_tool_emits_to_nats(tmp_path: Path) -> None:
    """Bash tool call → exactly one NATS publish to keiracom.agent.status.<callsign>."""
    rc, log = _run_hook(
        tool_name="Bash",
        dedup_dir=tmp_path / "dedup",
        shim_dir=tmp_path / "bin",
    )
    assert rc == 0
    assert "pub keiracom.agent.status.nova" in log
    assert '"state":"starting"' in log
    assert '"tool":"Bash"' in log


def test_read_tool_skips_emit(tmp_path: Path) -> None:
    """Read (trivial / read-only) → no NATS publish."""
    rc, log = _run_hook(
        tool_name="Read",
        dedup_dir=tmp_path / "dedup",
        shim_dir=tmp_path / "bin",
    )
    assert rc == 0
    assert log == ""


def test_missing_callsign_fails_open(tmp_path: Path) -> None:
    """No CALLSIGN env → exit 0, no publish."""
    rc, log = _run_hook(
        tool_name="Bash",
        callsign=None,
        dedup_dir=tmp_path / "dedup",
        shim_dir=tmp_path / "bin",
    )
    assert rc == 0
    assert log == ""


def test_nats_absent_fails_open(tmp_path: Path) -> None:
    """No nats binary on PATH → exit 0, no publish, no error."""
    rc, log = _run_hook(
        tool_name="Bash",
        nats_available=False,
        dedup_dir=tmp_path / "dedup",
        shim_dir=tmp_path / "bin",
    )
    assert rc == 0
    assert log == ""


def test_dedup_window_suppresses_second_emit(tmp_path: Path) -> None:
    """Two emits inside the dedup window → second one suppressed."""
    dedup_dir = tmp_path / "dedup"
    shim_dir = tmp_path / "bin"
    rc1, log1 = _run_hook(
        tool_name="Bash",
        task_ref_env="KEI-39",
        dedup_seconds=300,
        dedup_dir=dedup_dir,
        shim_dir=shim_dir,
    )
    rc2, log2 = _run_hook(
        tool_name="Bash",
        task_ref_env="KEI-39",
        dedup_seconds=300,
        dedup_dir=dedup_dir,
        shim_dir=shim_dir,
    )
    assert rc1 == 0 and rc2 == 0
    assert log1.count("pub keiracom.agent.status.nova") == 1
    assert log2.count("pub keiracom.agent.status.nova") == 1  # same log file, no new line


def test_task_ref_env_lands_in_payload(tmp_path: Path) -> None:
    """TASK_REF env var appears in the NATS payload."""
    rc, log = _run_hook(
        tool_name="Edit",
        task_ref_env="KEI-39",
        dedup_dir=tmp_path / "dedup",
        shim_dir=tmp_path / "bin",
    )
    assert rc == 0
    assert '"task_ref":"KEI-39"' in log
    assert '"tool":"Edit"' in log
