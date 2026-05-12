"""state_paths.py — XDG_STATE_HOME-rooted per-callsign state directory helper.

Replaces ad-hoc `/tmp/...` state-file paths across session-store hooks +
adjacent tooling with a single shared resolver. /tmp is world-writable and
flagged by SonarCloud S5443 (publicly writable directory). XDG_STATE_HOME
($HOME/.local/state by default) is the correct location for per-user,
per-machine state that should persist across reboots but isn't user-data.

Adopted 2026-05-12 (Aiden audit + Elliot ratification) — Option A from the
PR #754 + PR #756 SonarCloud blocker analysis.

Public API:

    resolve_state_dir(callsign: str) -> Path

        Returns $XDG_STATE_HOME/agency-os/<callsign>/ as a Path. Creates the
        directory tree (mode 0o700 — owner only) on first call. Callsign is
        validated against ^[A-Za-z][A-Za-z0-9_-]*$ — empty / traversal /
        special chars raise ValueError.

Callers that previously wrote to /tmp:
    /tmp/.session_<callsign>      → resolve_state_dir(<cs>) / "session"
    /tmp/.msgidx_<callsign>       → resolve_state_dir(<cs>) / "msgidx"
    /tmp/.turn_<callsign>         → resolve_state_dir(<cs>) / "turn"
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_CALLSIGN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_APP_SUBDIR = "agency-os"


def _xdg_state_home() -> Path:
    """Resolve $XDG_STATE_HOME with the spec-mandated fallback to ~/.local/state."""
    raw = os.environ.get("XDG_STATE_HOME", "").strip()
    if raw:
        path = Path(raw).expanduser()
        if path.is_absolute():
            return path
    return Path.home() / ".local" / "state"


def resolve_state_dir(callsign: str) -> Path:
    """Return $XDG_STATE_HOME/agency-os/<callsign>/, creating it if missing.

    Args:
        callsign: agent callsign (alphanumeric, underscore, dash; must start
            with a letter). Validated against `^[A-Za-z][A-Za-z0-9_-]*$`.

    Returns:
        Absolute Path to the per-callsign state directory. Permissions 0o700
        (owner read/write/execute only) on directories created here.

    Raises:
        ValueError: callsign fails the regex (empty, contains path traversal
            segments, or has special characters).
        OSError: directory creation fails (unwritable parent, disk full,
            permission denied). NOT swallowed — callers should know.
    """
    if not _CALLSIGN_RE.fullmatch(callsign):
        raise ValueError(
            f"invalid callsign for state path: {callsign!r} (must match {_CALLSIGN_RE.pattern})"
        )
    base = _xdg_state_home() / _APP_SUBDIR / callsign
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    return base
