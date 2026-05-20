"""Tests for scripts/auto_pull_main.sh — peak-window staleness alerting.

Verifies the SKIP-streak counter + alert-on-threshold logic added per Scout's
peak-window diagnosis (f42cc4d4). The script's main pull loop hits real git,
which we don't exercise here — we drive the streak-counter helpers via env
overrides and assert state-file behaviour.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "auto_pull_main.sh"


def _run_script(tmp_path: Path, relay_log: Path | None = None) -> subprocess.CompletedProcess:
    """Run auto_pull_main.sh against a sandboxed state-dir + stubbed relay."""
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir(exist_ok=True)
    state_dir = tmp_path / "state"
    state_dir.mkdir(exist_ok=True)
    # Stub relay: writes calling args to relay_log if provided.
    if relay_log is not None:
        relay = shim_dir / "slack_relay.py"
        relay.write_text(
            f"#!/usr/bin/env python3\nimport sys\nopen('{relay_log}', 'a').write(' '.join(sys.argv[1:]) + chr(10))\n"
        )
        relay.chmod(0o755)
    else:
        relay = shim_dir / "slack_relay.py"
        relay.write_text("#!/usr/bin/env python3\n")
        relay.chmod(0o755)
    env = os.environ.copy()
    env["AGENCY_OS_AUTO_PULL_STATE_DIR"] = str(state_dir)
    env["AGENCY_OS_AUTO_PULL_RELAY"] = str(relay)
    env["AGENCY_OS_AUTO_PULL_SKIP_THRESHOLD"] = "3"
    return subprocess.run(  # noqa: S603 — controlled args, no shell
        ["/bin/bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _streak_file(tmp_path: Path, worktree: str) -> Path:
    basename = worktree.replace("/", "_").lstrip("_")
    return tmp_path / "state" / f"auto-pull-main.{basename}.skip-streak"


# State-machine via direct shell invocation of the helpers ───────────────────


def test_streak_increments_then_resets(tmp_path: Path) -> None:
    """Source the script's helpers + verify _streak_inc / _streak_reset
    behaviour against a sandboxed state dir. No real worktree touched."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    helper = tmp_path / "drive.sh"
    helper.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
export AGENCY_OS_AUTO_PULL_STATE_DIR="{state_dir}"
export AGENCY_OS_AUTO_PULL_SKIP_THRESHOLD=3
export AGENCY_OS_AUTO_PULL_RELAY="/dev/null"
# Source only the helper functions by extracting the top of the script.
SKIP_ALERT_THRESHOLD="${{AGENCY_OS_AUTO_PULL_SKIP_THRESHOLD:-3}}"
STATE_DIR="${{AGENCY_OS_AUTO_PULL_STATE_DIR}}"
RELAY="${{AGENCY_OS_AUTO_PULL_RELAY}}"
mkdir -p "$STATE_DIR"
source <(sed -n '/^_state_path()/,/^for wt in/p' "{SCRIPT}" | sed '/^for wt in/d')
WT="/tmp/test-worktree"
_streak_inc "$WT"; _streak_inc "$WT"
echo "after-2:$(_streak_get "$WT")"
_streak_reset "$WT"
echo "after-reset:$(_streak_get "$WT")"
"""
    )
    helper.chmod(0o755)
    result = subprocess.run(  # noqa: S603
        ["/bin/bash", str(helper)], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    assert "after-2:2" in result.stdout
    assert "after-reset:0" in result.stdout


def test_alert_fires_at_threshold(tmp_path: Path) -> None:
    """When streak reaches threshold, the relay shim is called exactly once
    per streak — repeat-suppressed via .alerted flag."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    relay_log = tmp_path / "relay.log"
    helper = tmp_path / "drive.sh"
    helper.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
export AGENCY_OS_AUTO_PULL_STATE_DIR="{state_dir}"
export AGENCY_OS_AUTO_PULL_SKIP_THRESHOLD=3
export AGENCY_OS_AUTO_PULL_RELAY="{tmp_path / 'shim' / 'slack_relay.py'}"
mkdir -p "{tmp_path / 'shim'}"
cat > "{tmp_path / 'shim' / 'slack_relay.py'}" <<'PY'
#!/usr/bin/env python3
import sys
open("{relay_log}", "a").write(" ".join(sys.argv[1:]) + chr(10))
PY
chmod +x "{tmp_path / 'shim' / 'slack_relay.py'}"
mkdir -p "/home/elliotbot/clawd/venv/bin" 2>/dev/null || true
SKIP_ALERT_THRESHOLD="${{AGENCY_OS_AUTO_PULL_SKIP_THRESHOLD:-3}}"
STATE_DIR="${{AGENCY_OS_AUTO_PULL_STATE_DIR}}"
RELAY="${{AGENCY_OS_AUTO_PULL_RELAY}}"
mkdir -p "$STATE_DIR"
source <(sed -n '/^_state_path()/,/^for wt in/p' "{SCRIPT}" | sed '/^for wt in/d')
WT="/tmp/test-worktree"
_handle_skip "$WT" "working tree dirty"
_handle_skip "$WT" "working tree dirty"
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
    # Streak now 5; .alerted + .alerted_ceo flags prevent repeat-emit.
    # Two distinct alerts fire (KEI-34 v2 Addition 2):
    #   1. DIRTY WORKTREE STALE CODE → #ceo at streak >= 2 (one-shot).
    #   2. auto-pull-main staleness → #execution at streak >= 3 (one-shot).
    relay_lines = relay_log.read_text().splitlines() if relay_log.exists() else []
    assert len(relay_lines) == 2, f"expected two relay calls, got {relay_lines!r}"
    dirty_line = next((l for l in relay_lines if "DIRTY WORKTREE STALE CODE" in l), None)
    staleness_line = next((l for l in relay_lines if "auto-pull-main staleness" in l), None)
    assert dirty_line is not None, f"missing #ceo dirty-worktree alert in {relay_lines!r}"
    assert staleness_line is not None, f"missing #execution staleness alert in {relay_lines!r}"
    assert "3 consecutive cycles" in staleness_line


def test_alert_resets_after_success(tmp_path: Path) -> None:
    """After _streak_reset, a new SKIP run rebuilds the counter from 0."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    helper = tmp_path / "drive.sh"
    helper.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
export AGENCY_OS_AUTO_PULL_STATE_DIR="{state_dir}"
export AGENCY_OS_AUTO_PULL_SKIP_THRESHOLD=3
export AGENCY_OS_AUTO_PULL_RELAY="/dev/null"
SKIP_ALERT_THRESHOLD="${{AGENCY_OS_AUTO_PULL_SKIP_THRESHOLD:-3}}"
STATE_DIR="${{AGENCY_OS_AUTO_PULL_STATE_DIR}}"
RELAY="${{AGENCY_OS_AUTO_PULL_RELAY}}"
mkdir -p "$STATE_DIR"
source <(sed -n '/^_state_path()/,/^for wt in/p' "{SCRIPT}" | sed '/^for wt in/d')
WT="/tmp/test-wt"
_streak_inc "$WT"; _streak_inc "$WT"; _streak_inc "$WT"
echo "before-reset:$(_streak_get "$WT")"
_streak_reset "$WT"
echo "after-reset:$(_streak_get "$WT")"
_streak_inc "$WT"
echo "after-new-inc:$(_streak_get "$WT")"
"""
    )
    helper.chmod(0o755)
    result = subprocess.run(  # noqa: S603
        ["/bin/bash", str(helper)], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    assert "before-reset:3" in result.stdout
    assert "after-reset:0" in result.stdout
    assert "after-new-inc:1" in result.stdout
