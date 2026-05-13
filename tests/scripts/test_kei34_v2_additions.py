"""Tests for KEI-34 v2 — 3 additions per Dave verbatim ts ~1778631000."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "elliot_polling_loop.py"
AUTO_PULL_SCRIPT = REPO_ROOT / "scripts" / "auto_pull_main.sh"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("elliot_polling_loop_v2", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["elliot_polling_loop_v2"] = m
    spec.loader.exec_module(m)
    return m


# ── Addition 1 — BS dispatch-outcome heartbeat ──────────────────────────────


def test_heartbeat_skips_when_env_unset(mod, monkeypatch):
    monkeypatch.delenv("BETTERSTACK_HB_DISPATCH_OUTCOME", raising=False)
    called: list = []

    def _fake_run(*args, **kwargs):
        called.append(args)
        return subprocess.CompletedProcess(args=[], returncode=0)

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)
    mod._emit_dispatch_outcome_heartbeat([("x", "y")], None, no_work=False)
    assert called == []


def test_heartbeat_fires_on_dispatch(mod, monkeypatch):
    monkeypatch.setenv("BETTERSTACK_HB_DISPATCH_OUTCOME", "https://hb.example/abc")
    called: list = []

    def _fake_run(args, **kwargs):
        called.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)
    mod._emit_dispatch_outcome_heartbeat([("#execution", "...")], None, no_work=False)
    assert len(called) == 1
    assert called[0][0] == "curl"


def test_heartbeat_fires_on_no_work(mod, monkeypatch):
    """no_work=True (silent skip OR is_silent()) → heartbeat fires."""
    monkeypatch.setenv("BETTERSTACK_HB_DISPATCH_OUTCOME", "https://hb.example/abc")
    called: list = []
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: called.append(a) or subprocess.CompletedProcess(args=[], returncode=0))
    mod._emit_dispatch_outcome_heartbeat([], None, no_work=True)
    assert len(called) == 1


def test_heartbeat_suppressed_when_work_exists_but_no_dispatch(mod, monkeypatch):
    """The orchestrator-discipline-gap case: bd_ready+idle but dispatches=[].
    Heartbeat must NOT fire so BS dashboard alerts."""
    monkeypatch.setenv("BETTERSTACK_HB_DISPATCH_OUTCOME", "https://hb.example/abc")
    called: list = []
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: called.append(a) or subprocess.CompletedProcess(args=[], returncode=0))
    signals = mod.CycleSignals(
        bd_ready=[{"id": "x"}],
        linear_stale=[],
        idle_agents=[],
        prefect_failures=[],
        orchestrator_idle_agents=["aiden"],
    )
    mod._emit_dispatch_outcome_heartbeat([], signals, no_work=False)
    assert called == []


# ── Addition 2 — dirty-worktree #ceo escalation (auto_pull_main.sh) ─────────


def test_dirty_worktree_ceo_alert_helper_fires_on_dirty_streak(tmp_path):
    """Bash helper test: _emit_dirty_worktree_ceo_alert fires when streak>=2 + reason matches."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    relay_log = tmp_path / "ceo_relay.log"
    helper = tmp_path / "drive.sh"
    helper.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
export AGENCY_OS_AUTO_PULL_STATE_DIR="{state_dir}"
export AGENCY_OS_DIRTY_WORKTREE_CEO_THRESHOLD=2
export AGENCY_OS_AUTO_PULL_RELAY="{tmp_path / 'shim' / 'slack_relay.py'}"
mkdir -p "{tmp_path / 'shim'}"
cat > "{tmp_path / 'shim' / 'slack_relay.py'}" <<'PY'
#!/usr/bin/env python3
import sys
open("{relay_log}", "a").write(" ".join(sys.argv[1:]) + chr(10))
PY
chmod +x "{tmp_path / 'shim' / 'slack_relay.py'}"

SKIP_ALERT_THRESHOLD=3
STATE_DIR="$AGENCY_OS_AUTO_PULL_STATE_DIR"
RELAY="$AGENCY_OS_AUTO_PULL_RELAY"
DIRTY_WORKTREE_CEO_THRESHOLD="$AGENCY_OS_DIRTY_WORKTREE_CEO_THRESHOLD"
mkdir -p "$STATE_DIR"
source <(sed -n '/^_state_path()/,/^for wt in/p' "{AUTO_PULL_SCRIPT}" | sed '/^for wt in/d')
WT="/tmp/test-wt"
_handle_skip "$WT" "working tree dirty"
_handle_skip "$WT" "working tree dirty"
_handle_skip "$WT" "working tree dirty"
"""
    )
    helper.chmod(0o755)
    result = subprocess.run(  # noqa: S603
        ["/bin/bash", str(helper)], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    relay_lines = relay_log.read_text().splitlines() if relay_log.exists() else []
    ceo_lines = [line for line in relay_lines if "-c ceo" in line]
    assert len(ceo_lines) == 1, f"expected one #ceo alert, got {ceo_lines!r}"
    assert "DIRTY WORKTREE STALE CODE" in ceo_lines[0]


def test_dirty_worktree_ceo_alert_skips_non_dirty_reason(tmp_path):
    """Non-dirty SKIP reasons (on feature branch, etc.) don't fire #ceo alert."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    relay_log = tmp_path / "relay.log"
    helper = tmp_path / "drive.sh"
    helper.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
export AGENCY_OS_AUTO_PULL_STATE_DIR="{state_dir}"
export AGENCY_OS_DIRTY_WORKTREE_CEO_THRESHOLD=2
export AGENCY_OS_AUTO_PULL_RELAY="{tmp_path / 'shim' / 'slack_relay.py'}"
mkdir -p "{tmp_path / 'shim'}"
cat > "{tmp_path / 'shim' / 'slack_relay.py'}" <<'PY'
#!/usr/bin/env python3
import sys
open("{relay_log}", "a").write(" ".join(sys.argv[1:]) + chr(10))
PY
chmod +x "{tmp_path / 'shim' / 'slack_relay.py'}"

SKIP_ALERT_THRESHOLD=3
STATE_DIR="$AGENCY_OS_AUTO_PULL_STATE_DIR"
RELAY="$AGENCY_OS_AUTO_PULL_RELAY"
DIRTY_WORKTREE_CEO_THRESHOLD="$AGENCY_OS_DIRTY_WORKTREE_CEO_THRESHOLD"
mkdir -p "$STATE_DIR"
source <(sed -n '/^_state_path()/,/^for wt in/p' "{AUTO_PULL_SCRIPT}" | sed '/^for wt in/d')
WT="/tmp/test-wt"
_handle_skip "$WT" "on feature/branch (only auto-pull when on main)"
_handle_skip "$WT" "on feature/branch (only auto-pull when on main)"
"""
    )
    helper.chmod(0o755)
    result = subprocess.run(["/bin/bash", str(helper)], capture_output=True, text=True, timeout=10)  # noqa: S603
    assert result.returncode == 0, result.stderr
    relay_lines = relay_log.read_text().splitlines() if relay_log.exists() else []
    ceo_lines = [line for line in relay_lines if "-c ceo" in line]
    assert ceo_lines == [], f"expected NO #ceo alert for non-dirty reason, got {ceo_lines!r}"


# ── Addition 3 — subprocess-aware idle detection ────────────────────────────


def test_descendant_pids_returns_list(mod):
    """_descendant_pids returns a list (smoke test — actual content depends on
    runtime process tree)."""
    descendants = mod._descendant_pids(1)  # PID 1 has many descendants on Linux
    assert isinstance(descendants, list)


def test_descendant_pids_invalid_pid_returns_empty(mod):
    """Invalid/unknown pid returns empty list (no children)."""
    # PID 999999 unlikely to exist
    assert mod._descendant_pids(999999) == []


def test_agent_has_active_subprocess_unknown_callsign_false(mod):
    """Callsign not in CALLSIGN_TO_TMUX → False (conservative)."""
    assert mod._agent_has_active_subprocess("unknown_callsign") is False


def test_poll_orchestrator_idle_filters_active_subprocess(mod, monkeypatch):
    """If timestamp-idle says aiden is idle but _agent_has_active_subprocess
    says aiden has a running subprocess, aiden gets filtered out."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")

    async def _fake_async():
        return ["aiden", "max"]

    # Stub the inner async _q via asyncio.run injection — simulate timestamp-idle returns [aiden, max].
    # Easier: stub poll_orchestrator_idle_agents's internal asyncio call via monkeypatching asyncio.run.
    import asyncio

    monkeypatch.setattr(asyncio, "run", lambda coro: ["aiden", "max"] if hasattr(coro, "__await__") else [])
    # Stub _agent_has_active_subprocess: aiden busy, max idle.
    monkeypatch.setattr(mod, "_agent_has_active_subprocess", lambda cs: cs == "aiden")
    # asyncpg import check inside the function — make sure it's importable.
    pytest.importorskip("asyncpg")
    out = mod.poll_orchestrator_idle_agents()
    assert "aiden" not in out
    assert "max" in out
