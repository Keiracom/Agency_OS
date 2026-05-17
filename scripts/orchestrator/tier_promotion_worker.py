#!/usr/bin/env python3
"""tier_promotion_worker.py — KEI-55 daemon: sweep Staging_discoveries and apply tier expirations.

Usage:
    python3 scripts/orchestrator/tier_promotion_worker.py              # hourly daemon loop
    python3 scripts/orchestrator/tier_promotion_worker.py --once       # single sweep + exit
    python3 scripts/orchestrator/tier_promotion_worker.py --poll-interval 1800  # 30-min cadence
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from datetime import UTC, datetime
from typing import Any

from src.governance.discovery_validation import expire_stale_staging

logger = logging.getLogger("tier_promotion_worker")

DEFAULT_POLL_INTERVAL = 3600  # 1 hour — discoveries expire on 24/48/72h clock
_STOP: dict[str, bool] = {"flag": False}


def _json_line(level: str, msg: str, outcome: dict[str, Any] | None = None) -> str:
    """Build a journalctl-grep-friendly JSON log line."""
    doc: dict[str, Any] = {
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": level,
        "msg": msg,
    }
    if outcome is not None:
        doc["outcome"] = outcome
    return json.dumps(doc)


def _log(level: str, msg: str, outcome: dict[str, Any] | None = None) -> None:
    print(_json_line(level, msg, outcome), flush=True)


def _shutdown(signum: int, _frame: Any) -> None:  # noqa: ARG001
    _log("INFO", f"signal {signum} received — stopping after current sweep")
    _STOP["flag"] = True


def sweep_once() -> dict[str, int]:
    """Run a single expire_stale_staging pass. Returns the outcome dict."""
    outcome = expire_stale_staging()
    _log("INFO", "sweep complete", outcome)
    return outcome


def run(poll_interval: int, once: bool) -> int:
    """Main loop. Returns exit code."""
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    _log("INFO", "tier_promotion_worker starting", {"poll_interval_s": poll_interval, "once": once})

    try:
        sweep_once()
    except OSError as exc:
        _log("ERROR", f"Weaviate unreachable on startup — {exc}", None)
        return 1

    if once:
        _log("INFO", "tier_promotion_worker --once: exiting")
        return 0

    while not _STOP["flag"]:
        time.sleep(poll_interval)
        if _STOP["flag"]:
            break
        try:
            sweep_once()
        except OSError as exc:
            # Transient network fault — log and continue; don't crash the daemon.
            _log("WARN", f"sweep skipped — Weaviate unreachable: {exc}", None)

    _log("INFO", "tier_promotion_worker stopped cleanly")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="single sweep then exit")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=DEFAULT_POLL_INTERVAL,
        metavar="SECONDS",
        help="seconds between sweeps (default 3600)",
    )
    args = parser.parse_args(argv)
    return run(poll_interval=args.poll_interval, once=args.once)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
