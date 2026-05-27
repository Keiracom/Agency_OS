#!/usr/bin/env python3
"""dispatcher_main — per-callsign ephemeral-agent dispatcher entrypoint.

Invoked by Scout's systemd template (PR #1180):
    keiracom-dispatcher@<callsign>.service
      ExecStart=/usr/bin/python3 -B scripts/dispatcher/dispatcher_main.py --callsign %i

Watches /tmp/telegram-relay-<callsign>/inbox/, atomically claims each
envelope, routes by type, composes A+B+C+D+E (or A+B+D+E+resume) via
src.relay.spawn_composer, and either logs (Stage 1 default) or spawns
`claude` (Stage 2 via DISPATCHER_MODE=spawn).

Stop conditions:
- SIGTERM / SIGINT: graceful drain (finish current claim, then exit 0).
  Scout's systemd template handles restart-on-failure separately.

bd: Agency_OS-8416
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any

from scripts.dispatcher import _budget_gate, _envelope_route, _inbox_loop, _spawn

log = logging.getLogger("dispatcher_main")

DEFAULT_INBOX_ROOT = Path("/tmp")
DEFAULT_REPO_ROOT = Path("/home/elliotbot/clawd/Agency_OS")


def main(
    argv: list[str] | None = None,
    *,
    db_factory: Any = None,
    budget_gate: Any = None,
) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    inbox_root = Path(args.inbox_root)
    repo_root = Path(args.repo_root)
    inbox_dir = inbox_root / f"telegram-relay-{args.callsign}" / "inbox"
    processing_dir = inbox_dir.parent / "processing"
    quarantine_dir = inbox_dir.parent / "quarantine"

    mode = os.environ.get("DISPATCHER_MODE", _spawn.MODE_NOOP)
    poll_seconds = float(os.environ.get("DISPATCHER_POLL_SECONDS", "2.0"))

    db = (db_factory or _build_default_db)()

    log.info(
        "dispatcher start callsign=%s mode=%s inbox_dir=%s poll_seconds=%.1f",
        args.callsign,
        mode,
        inbox_dir,
        poll_seconds,
    )

    stop_flag = {"requested": False}

    def _on_signal(signum: int, _frame: Any) -> None:
        log.info("signal %d received — draining", signum)
        stop_flag["requested"] = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    for claimed, envelope in _inbox_loop.iter_claimed_envelopes(
        inbox_dir,
        processing_dir=processing_dir,
        poll_seconds=poll_seconds,
        stop_after=args.stop_after,
    ):
        if stop_flag["requested"]:
            log.info("drain complete — exiting after current claim")
            return 0
        action, resume_ctx = _envelope_route.route_envelope(
            envelope,
            claimed_path=claimed,
            quarantine_dir=quarantine_dir,
        )
        if action in (
            _envelope_route.RouteAction.QUARANTINE,
            _envelope_route.RouteAction.LOG_PAUSED,
        ):
            continue
        budget_action, budget_result = _budget_gate.evaluate(envelope, budget_gate=budget_gate)
        if budget_action == _budget_gate.BudgetAction.SKIP_SPAWN:
            log.info(
                "budget gate skipped spawn from=%s type=%s decision=%s spend_aud=%.2f budget_aud=%.2f",
                envelope.get("from"),
                envelope.get("type"),
                budget_result.decision.value if budget_result else None,
                budget_result.current_day_spend_aud if budget_result else 0.0,
                budget_result.daily_budget_aud if budget_result else 0.0,
            )
            continue
        _spawn.handle_envelope(
            callsign=args.callsign,
            db=db,
            repo_root=repo_root,
            inbox_root=inbox_root,
            mode=mode,
            resume_context=resume_ctx,
        )
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--callsign", required=True, help="callsign for this dispatcher")
    parser.add_argument("--inbox-root", default=str(DEFAULT_INBOX_ROOT))
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--stop-after",
        type=int,
        default=None,
        help="bound the inbox-watch loop (None = run forever; used by tests)",
    )
    return parser.parse_args(argv)


def _build_default_db() -> Any:
    """Lazy-import psycopg + connect to DATABASE_URL.

    Kept out of module import so unit tests can pass a fake db_factory
    without requiring psycopg.
    """
    import psycopg  # noqa: PLC0415 — deferred import is intentional

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL env var required for dispatcher main")
    return psycopg.connect(dsn).cursor()


if __name__ == "__main__":
    sys.exit(main())
