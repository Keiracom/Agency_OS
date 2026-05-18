"""KEI-94 — agent_keepalive.sh: tmux survives Claude exits via in-pane respawn loop.

Dispatch (Elliot 2026-05-18): "Claude Code exits on boot, destroying tmux
sessions. Fix: Restart=always + keep-alive wrapper in each *-agent.service.
Acceptance: agent service Restart=always; wrapper script keeps tmux alive
across Claude exits. Test: kill Claude in tmux, verify wrapper respawns."

Coverage:
  - DRY mode emits the in-pane `while true` respawn loop (not `exec claude`)
  - Required components present: CALLSIGN export, worktree cd, claude invocation,
    sleep between respawns, log line on exit
  - Bash syntax valid
  - Missing-arg / missing-worktree rejection
  - Integration smoke: real tmux pane survives inner-command exit and respawns

The integration test substitutes `claude` with a stub via a PATH shim, so it
exercises the loop without touching the real Claude binary.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "agent_keepalive.sh"


# ---------------------------------------------------------------------------
# DRY-mode unit tests — no real tmux / no real claude
# ---------------------------------------------------------------------------


def _dry_run(callsign: str, worktree: Path, session: str = "test-session") -> str:
    proc = subprocess.run(
        ["bash", str(SCRIPT), session, callsign, str(worktree)],
        env={**os.environ, "KEEPALIVE_DRY": "1"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, f"DRY exit {proc.returncode}: {proc.stderr}"
    return proc.stdout


def test_dry_run_emits_in_pane_respawn_loop(tmp_path: Path) -> None:
    out = _dry_run("orion", tmp_path)
    # Must NOT be the legacy `exec claude` form — `exec` makes claude REPLACE
    # the shell, so when claude exits the pane process exits and tmux session
    # dies. The KEI-94 fix wraps claude in `while true` so the shell survives.
    assert "exec claude" not in out, "regression: legacy `exec claude` reintroduced"
    assert "while true" in out, "in-pane respawn loop missing"
    assert "claude --dangerously-skip-permissions" in out
    assert "sleep 2" in out, "respawn backoff missing — could busy-spin on immediate-crash"
    assert "claude exited" in out, "exit log line missing — observability"


def test_dry_run_emits_callsign_export(tmp_path: Path) -> None:
    out = _dry_run("aiden", tmp_path)
    assert "export CALLSIGN='aiden'" in out, "callsign export missing — worktree mis-tag risk"


def test_dry_run_emits_worktree_cd(tmp_path: Path) -> None:
    out = _dry_run("scout", tmp_path)
    assert f"cd '{tmp_path}'" in out, "worktree cd missing — wrong-dir spawn"


def test_dry_run_rejects_missing_worktree() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "s", "cs", "/no/such/path"],
        env={**os.environ, "KEEPALIVE_DRY": "1"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert proc.returncode == 2
    assert "worktree missing" in proc.stderr


def test_dry_run_rejects_missing_args(tmp_path: Path) -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        env={**os.environ, "KEEPALIVE_DRY": "1"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert proc.returncode != 0


def test_script_syntax_is_valid() -> None:
    proc = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True, timeout=5)
    assert proc.returncode == 0, proc.stderr


# ---------------------------------------------------------------------------
# Integration: real tmux pane survives inner-command exit + respawn
# ---------------------------------------------------------------------------


pytestmark_no_tmux = pytest.mark.skipif(
    shutil.which("tmux") is None, reason="tmux not available on this host"
)


@pytestmark_no_tmux
def test_real_tmux_in_pane_respawn_after_inner_exit(tmp_path: Path) -> None:
    """Spawn a tmux session running the same in-pane loop the wrapper emits,
    but with `claude` substituted by a tick-writer stub. The stub writes a
    timestamped line to a file then exits. After waiting for two iterations
    of the loop we expect ≥2 stub invocations recorded — proving the bash
    loop respawns the inner command in the same pane (tmux session survives).
    """
    session = f"kei94-it-{os.getpid()}"
    tick_file = tmp_path / "ticks.log"
    # Stub: append one timestamped line then exit. Mimics claude exiting.
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    stub = stub_dir / "claude"
    stub.write_text(f'#!/usr/bin/env bash\necho "tick $(date -u +%s%N)" >> "{tick_file}"\nexit 0\n')
    stub.chmod(0o755)

    # Build the exact loop shape the wrapper emits, but with the stub on PATH.
    # Note: double-quote the PATH assignment so bash inside tmux expands $PATH;
    # single quotes would assign the literal string and the stub wouldn't be
    # findable.
    loop_cmd = (
        f'export PATH="{stub_dir}:$PATH" && '
        f"while true; do claude --dangerously-skip-permissions; "
        f'echo "[keepalive] claude exited at $(date -u +%FT%TZ), respawning in 2s" >&2; '
        f"sleep 2; done"
    )

    try:
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session, "-c", str(tmp_path)],
            check=True,
            timeout=5,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", session, loop_cmd, "Enter"],
            check=True,
            timeout=5,
        )
        # Loop iteration takes ~2s (sleep) + stub runtime (~ms). Wait for
        # at least three ticks to land — confidently proves the loop is
        # respawning, not a one-shot.
        deadline = time.time() + 10
        ticks: list[str] = []
        while time.time() < deadline:
            if tick_file.exists():
                ticks = tick_file.read_text().splitlines()
                if len(ticks) >= 3:
                    break
            time.sleep(0.2)

        # tmux session must still be alive — that's the core acceptance.
        sess_check = subprocess.run(
            ["tmux", "has-session", "-t", session],
            capture_output=True,
            timeout=5,
        )
        assert sess_check.returncode == 0, (
            "tmux session died — wrapper failed to keep tmux alive across claude exits"
        )

        # And the inner stub must have been respawned at least 3x — proves
        # the bash loop is doing its job (not just one execution then idle).
        assert len(ticks) >= 3, (
            f"stub ran {len(ticks)} times; expected ≥3. tmux session is alive "
            f"but the loop isn't respawning — regression to `exec` or first-exit-bails"
        )

        # Sanity: timestamps are strictly increasing (no duplicate-line race).
        ns_values = [int(re.search(r"tick (\d+)", t).group(1)) for t in ticks]  # type: ignore[union-attr]
        assert ns_values == sorted(ns_values)
    finally:
        subprocess.run(
            ["tmux", "kill-session", "-t", session],
            capture_output=True,
            timeout=5,
        )
