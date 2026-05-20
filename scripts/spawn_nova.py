"""spawn_nova.py — Nova engineer-clone spawn entrypoint (KEI-185).

Delegates the actual session lifecycle to `src.fleet.session_manager.SessionManager`
(KEI-184, Orion). This module is the named spawn handler the fleet supervisor v2
calls when it determines Nova should come online (engineer overflow path).

The CLI is the operator-facing form: `python -m scripts.spawn_nova --dry-run`
prints the resolved spawn plan without firing it. Useful before the
SessionManager landing PR (KEI-184) merges, since dry-run mode never imports it.

Until KEI-184 lands, `--force` returns exit 2 with a clear missing-dep message
rather than ImportError stacktrace — the flip-on order is enforced at runtime.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

NOVA_CALLSIGN = "nova"
NOVA_WORKTREE = "/home/elliotbot/clawd/Agency_OS-nova"
NOVA_TMUX_SESSION = "nova:0"
NOVA_SERVICE = "nova-agent"


@dataclass(frozen=True)
class NovaSpawnPlan:
    callsign: str = NOVA_CALLSIGN
    worktree: str = NOVA_WORKTREE
    tmux_session: str = NOVA_TMUX_SESSION
    service: str = NOVA_SERVICE


def plan() -> NovaSpawnPlan:
    return NovaSpawnPlan()


def spawn(*, dry_run: bool = False) -> int:
    """Spawn Nova via SessionManager (KEI-184). Returns 0 on success, non-zero
    on failure. `dry_run=True` skips the SessionManager call and returns 0
    after logging the plan — safe to run pre-KEI-184-merge.
    """
    p = plan()
    logger.info(
        "nova spawn plan: callsign=%s worktree=%s tmux=%s service=%s",
        p.callsign,
        p.worktree,
        p.tmux_session,
        p.service,
    )
    if dry_run:
        logger.info("dry-run mode — SessionManager NOT invoked")
        return 0
    try:
        from src.fleet.session_manager import (
            SessionManager,  # type: ignore[import-not-found]  # noqa: PLC0415
        )
    except ImportError:
        logger.error(
            "SessionManager not importable — KEI-184 (Orion PR #1004) must "
            "merge before Nova can spawn. Re-run with --dry-run to validate "
            "the plan without invoking SessionManager."
        )
        return 2
    sm = SessionManager()
    sm.spawn(
        callsign=p.callsign,
        worktree=p.worktree,
        tmux_session=p.tmux_session,
        service=p.service,
    )
    logger.info("nova spawn dispatched via SessionManager")
    return 0


def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="spawn_nova", description=__doc__)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the spawn plan without invoking SessionManager.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Invoke SessionManager even if KEI-184 not yet merged (will exit 2 on ImportError).",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _build_argparser().parse_args(argv)
    if not args.dry_run and not args.force:
        logger.error("refusing to invoke SessionManager without --force or --dry-run")
        return 2
    return spawn(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
