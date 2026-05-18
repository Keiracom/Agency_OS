"""KEI-69 — fallback poller must cover all 7 fleet sessions.

Acceptance per dispatch: poller reports state for all 7 sessions
(elliot + atlas + orion + scout + nova + aiden + max).

Guards against future regressions where adding a new clone forgets to wire
the poller, session-recovery, or workspace maps.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
POLLING = REPO_ROOT / "scripts" / "orchestrator" / "elliot_polling_loop.py"
RECOVERY = REPO_ROOT / "scripts" / "orchestrator" / "auto_session_recovery.py"

EXPECTED_FLEET = frozenset({"elliot", "aiden", "max", "atlas", "orion", "scout", "nova"})
EXPECTED_CLONES = frozenset({"atlas", "orion", "scout", "nova"})


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_polling_callsign_to_tmux_covers_7_sessions():
    """elliot_polling_loop.CALLSIGN_TO_TMUX includes nova and totals 7."""
    mod = _load("elliot_polling_loop", POLLING)
    assert set(mod.CALLSIGN_TO_TMUX.keys()) == EXPECTED_FLEET
    assert len(mod.CALLSIGN_TO_TMUX) == 7
    assert mod.CALLSIGN_TO_TMUX["nova"] == "nova"


def test_polling_clones_tuple_includes_nova():
    mod = _load("elliot_polling_loop", POLLING)
    assert set(mod.CLONES) == EXPECTED_CLONES
    assert "nova" in mod.CLONES


def test_polling_inbox_paths_covers_all_clones():
    mod = _load("elliot_polling_loop", POLLING)
    assert set(mod.INBOX_PATHS.keys()) == EXPECTED_CLONES
    # NOSONAR S5443 — string-equality assertion, not a filesystem write. The
    # /tmp inbox path is the systemd-relay convention asserted against
    # elliot_polling_loop.INBOX_PATHS (which itself carries NOSONAR S5443).
    assert mod.INBOX_PATHS["nova"] == "/tmp/telegram-relay-nova/inbox"  # NOSONAR S5443


def test_recovery_callsign_to_tmux_covers_7_sessions():
    mod = _load("auto_session_recovery", RECOVERY)
    assert set(mod.CALLSIGN_TO_TMUX.keys()) == EXPECTED_FLEET
    assert mod.CALLSIGN_TO_TMUX["nova"] == "nova"


def test_recovery_callsign_to_worktree_covers_7_sessions():
    mod = _load("auto_session_recovery", RECOVERY)
    assert set(mod.CALLSIGN_TO_WORKTREE.keys()) == EXPECTED_FLEET
    assert mod.CALLSIGN_TO_WORKTREE["nova"].endswith("/Agency_OS-nova")


def test_polling_and_recovery_tmux_maps_agree():
    """Both modules must agree on tmux session names — drift = silent misroute."""
    poll = _load("elliot_polling_loop", POLLING)
    rec = _load("auto_session_recovery", RECOVERY)
    assert poll.CALLSIGN_TO_TMUX == rec.CALLSIGN_TO_TMUX
