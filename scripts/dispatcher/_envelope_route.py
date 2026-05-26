"""Envelope-type router for the ephemeral-agent dispatcher.

Reads the `type` field on an inbox envelope and routes to the right handler:

- `task_dispatch`           → spawn path (compose A+B+C+D+E + run claude)
- `decision_response`       → resume-spawn path (compose A+B+D+E + resume_ctx)
- `paused_pending_decision` → log + skip (paused_tasks persistence is §7
                              piece 2, separate KEI)
- unknown type              → quarantine (move to inbox/quarantine/)

Per PR #1140 §5 (resume-spawn protocol) + my PR #1181 envelope schema
(src/relay/envelope_schema.py defines the 4 type literals). This module
is the dispatcher-side consumer of that schema.

bd: Agency_OS-8416
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# The 4 known envelope types — local mirror of envelope_schema.KNOWN_ENVELOPE_TYPES
# so this module stays import-resilient if the schema module is unavailable at
# runtime (defence-in-depth: schema is authoritative; this list is the
# router's claim about which it can route).
ROUTABLE_TYPES: frozenset[str] = frozenset(
    {
        "task_dispatch",
        "decision_response",
        "paused_pending_decision",
    }
)


class RouteAction:
    """Marker constants for the action a route returns."""

    SPAWN = "spawn"
    RESUME = "resume"
    LOG_PAUSED = "log_paused"
    QUARANTINE = "quarantine"


def route_envelope(
    envelope: Mapping[str, Any],
    *,
    claimed_path: Path,
    quarantine_dir: Path,
) -> tuple[str, Mapping[str, Any] | None]:
    """Decide what to do with a claimed inbox envelope.

    Returns `(action, resume_context)`. `resume_context` is None except on
    the RESUME path (carries the decoded envelope for the composer).
    """
    type_value = envelope.get("type")

    if type_value == "task_dispatch":
        return RouteAction.SPAWN, None

    if type_value == "decision_response":
        return RouteAction.RESUME, envelope

    if type_value == "paused_pending_decision":
        log.info(
            "paused_pending_decision received id=%s task_ref=%s — log+skip "
            "(paused_tasks persistence is §7 piece 2, separate KEI)",
            envelope.get("id"),
            envelope.get("task_ref"),
        )
        return RouteAction.LOG_PAUSED, None

    # Unknown / missing type → quarantine
    quarantine_envelope(claimed_path, quarantine_dir, reason=f"unknown type={type_value!r}")
    return RouteAction.QUARANTINE, None


def quarantine_envelope(
    claimed_path: Path,
    quarantine_dir: Path,
    *,
    reason: str,
    mover: Callable[[str, str], Any] = shutil.move,
) -> Path:
    """Move a claimed envelope to inbox/quarantine/ with a sidecar reason file.

    `mover` is injectable so tests can substitute a fake (the default
    shutil.move handles cross-filesystem moves which os.rename does not).
    """
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    dest = quarantine_dir / claimed_path.name
    mover(str(claimed_path), str(dest))
    (dest.with_suffix(dest.suffix + ".reason")).write_text(reason, encoding="utf-8")
    log.warning("quarantined %s → %s: %s", claimed_path.name, dest, reason)
    return dest
