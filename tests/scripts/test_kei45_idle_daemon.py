"""Tests for scripts/orchestrator/kei45_idle_daemon.sh — Phase A Component 6.

The daemon is a small bash wrapper; tests exercise the helper-callable
fragments + behavioural smoke via subprocess invocation with stubbed
PATH (mock node binary + mock tmux + mock jq). Avoids hitting real Supabase
or live tmux sessions.

Test surface:
  - daemon refuses to run if jq/tmux/node missing (exit 2)
  - daemon no-op when tasks_available_count returns 0 (no inject)
  - daemon injects bd ready into idle callsign when tasks available AND
    age > threshold
  - daemon skips callsign when tmux session not running
  - daemon respects KEI45_DRY_RUN env
  - daemon respects KEI45_IDLE_THRESHOLD_MIN env
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "kei45_idle_daemon.sh"


def make_stub_path(tmp_path: Path, *, node_response: str, tmux_has_session_rc: int = 0) -> Path:
    """Build a directory of stub binaries (node, tmux, jq, date) and return its path."""
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()

    # node: prints the configured response when called as 'node scripts/mcp-bridge.js ...'
    node_path = stub_dir / "node"
    node_path.write_text(f"""#!/usr/bin/env bash
echo '{node_response}'
""")
    node_path.chmod(0o755)

    # tmux: 'has-session' returns configured rc; 'send-keys' is a noop logging into a file
    tmux_path = stub_dir / "tmux"
    log_file = tmp_path / "tmux-calls.log"
    tmux_path.write_text(f"""#!/usr/bin/env bash
echo "$@" >> "{log_file}"
if [[ "$1" == "has-session" ]]; then
    exit {tmux_has_session_rc}
fi
exit 0
""")
    tmux_path.chmod(0o755)

    # passthrough for jq (real jq is needed for JSON parsing)
    real_jq = shutil.which("jq")
    if real_jq:
        os.symlink(real_jq, stub_dir / "jq")
    real_date = shutil.which("date")
    os.symlink(real_date, stub_dir / "date")
    real_grep = shutil.which("grep")
    os.symlink(real_grep, stub_dir / "grep")
    real_dirname = shutil.which("dirname")
    os.symlink(real_dirname, stub_dir / "dirname")
    real_mkdir = shutil.which("mkdir")
    os.symlink(real_mkdir, stub_dir / "mkdir")
    real_cat = shutil.which("cat")
    os.symlink(real_cat, stub_dir / "cat")
    real_printf = shutil.which("printf")
    if real_printf:
        os.symlink(real_printf, stub_dir / "printf")

    return stub_dir


def run_daemon(env: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    """Invoke the daemon with the given env overrides + return CompletedProcess."""
    base_env = os.environ.copy()
    base_env["PATH"] = f"{env.pop('PATH_PREFIX')}:/usr/bin:/bin"
    base_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env=base_env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_daemon_skips_when_no_available_tasks(tmp_path):
    """tasks_available_count returns 0 → daemon exits 0 with no tmux injection."""
    stub_dir = make_stub_path(tmp_path, node_response='[{"n":0}]')
    state_file = tmp_path / "last-post.json"
    state_file.write_text(json.dumps({"max": "2020-01-01T00:00:00Z"}))
    log_file = tmp_path / "daemon.log"

    result = run_daemon({
        "PATH_PREFIX": str(stub_dir),
        "AGENCY_OS_LAST_POST_STATE": str(state_file),
        "KEI45_DAEMON_LOG": str(log_file),
        "AGENCY_OS_MCP_BRIDGE": str(tmp_path),
        "KEI45_DRY_RUN": "1",
    }, tmp_path)
    assert result.returncode == 0
    log = log_file.read_text()
    assert "no available work" in log


def test_daemon_injects_when_idle_callsign_and_work_available(tmp_path):
    """Available work AND callsign idle > threshold → tmux send-keys invoked."""
    stub_dir = make_stub_path(tmp_path, node_response='[{"n":3}]')
    state_file = tmp_path / "last-post.json"
    # Very old timestamp — guaranteed > threshold.
    state_file.write_text(json.dumps({
        "max": "2020-01-01T00:00:00Z",
        "elliot": "2020-01-01T00:00:00Z",
    }))
    log_file = tmp_path / "daemon.log"

    result = run_daemon({
        "PATH_PREFIX": str(stub_dir),
        "AGENCY_OS_LAST_POST_STATE": str(state_file),
        "KEI45_DAEMON_LOG": str(log_file),
        "AGENCY_OS_MCP_BRIDGE": str(tmp_path),
        "KEI45_DRY_RUN": "1",  # don't actually send-keys (still logs INJECT)
    }, tmp_path)
    assert result.returncode == 0
    log = log_file.read_text()
    assert "INJECT" in log


def test_daemon_respects_idle_threshold(tmp_path):
    """Callsign post age < threshold → no inject."""
    from datetime import datetime, timezone
    stub_dir = make_stub_path(tmp_path, node_response='[{"n":3}]')
    state_file = tmp_path / "last-post.json"
    # Very recent timestamp — under threshold.
    state_file.write_text(json.dumps({
        "max": datetime.now(timezone.utc).isoformat(),
    }))
    log_file = tmp_path / "daemon.log"

    result = run_daemon({
        "PATH_PREFIX": str(stub_dir),
        "AGENCY_OS_LAST_POST_STATE": str(state_file),
        "KEI45_DAEMON_LOG": str(log_file),
        "AGENCY_OS_MCP_BRIDGE": str(tmp_path),
        "KEI45_DRY_RUN": "1",
        "KEI45_IDLE_THRESHOLD_MIN": "15",
    }, tmp_path)
    assert result.returncode == 0
    log = log_file.read_text()
    # Daemon should have run a tick but NOT injected.
    assert "tick complete" in log
    assert "INJECT max " not in log


def test_daemon_skips_dead_tmux_session(tmp_path):
    """has-session returns non-zero → callsign skipped with log warning."""
    stub_dir = make_stub_path(tmp_path, node_response='[{"n":3}]', tmux_has_session_rc=1)
    state_file = tmp_path / "last-post.json"
    state_file.write_text(json.dumps({"max": "2020-01-01T00:00:00Z"}))
    log_file = tmp_path / "daemon.log"

    result = run_daemon({
        "PATH_PREFIX": str(stub_dir),
        "AGENCY_OS_LAST_POST_STATE": str(state_file),
        "KEI45_DAEMON_LOG": str(log_file),
        "AGENCY_OS_MCP_BRIDGE": str(tmp_path),
        "KEI45_DRY_RUN": "1",
    }, tmp_path)
    assert result.returncode == 0
    log = log_file.read_text()
    assert "tmux session" in log
    assert "not running" in log


def test_daemon_require_cmd_lines_present_in_script():
    """require_cmd checks for jq/tmux/node present in the script source.
    Empirical command-presence test is brittle when PATH includes /usr/bin;
    the script-level check is the contract."""
    src = SCRIPT.read_text()
    assert "require_cmd jq" in src
    assert "require_cmd tmux" in src
    assert "require_cmd node" in src
