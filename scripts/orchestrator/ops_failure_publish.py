#!/usr/bin/env python3
"""ops_failure_publish.py — publish one ops-failure envelope to NATS and exit.

Called by systemd via OnFailure= on every user-scope service. Publishes a
diagnostic envelope to keiracom.ops.failure where peer_event_ceo_relay picks
it up and fans to Slack #ceo.

NATS here is CORE pub/sub (NOT jetstream) — no stream creation needed.

USAGE:
    python3 scripts/orchestrator/ops_failure_publish.py <unit>
    python3 scripts/orchestrator/ops_failure_publish.py --dry-run <unit>

    systemd passes %i (the verbatim instance name) as the positional arg.
    NB: %i not %I — %I unescapes '-' to '/', corrupting dashed unit names
    (weaviate-backup.service -> weaviate/backup.service).

EXIT: 0 on successful publish; 1 on NATS unavailable / publish error.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time

# nats-py is lazy-imported inside publish_failure() so this module remains
# collectable on CI hosts where nats-py is not in the test venv.
# Mirrors the same pattern used in supervisor_wake_publish.py (PR #1116
# anchor — top-level import nats made test uncollectable on CI).

DEFAULT_NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
DEFAULT_SUBJECT = os.environ.get("OPS_FAILURE_SUBJECT", "keiracom.ops.failure")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ops_failure_publish")


def _gather_diagnostics(unit: str) -> tuple[str, str]:
    """Run status + journal for `unit`. Returns (status_excerpt, journal_excerpt).

    Best-effort — never raises. Any subprocess error is logged and an empty
    string returned so the envelope can still be published.
    """
    status_excerpt = ""
    journal_excerpt = ""

    try:
        r = subprocess.run(
            ["systemctl", "--user", "status", unit, "--no-pager", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = r.stdout.splitlines()
        status_excerpt = "\n".join(lines[-15:]) if lines else r.stderr[:500]
    except Exception as exc:  # noqa: BLE001
        log.warning("status gather failed for %s: %s", unit, exc)

    try:
        r = subprocess.run(
            ["journalctl", "--user", "-u", unit, "-n", "12", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        journal_excerpt = r.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("journal gather failed for %s: %s", unit, exc)

    return status_excerpt, journal_excerpt


def build_envelope(unit: str, now: float | None = None) -> dict:
    """Construct the failure envelope. Pure function — testable without NATS.

    Gathers diagnostics via subprocess (best-effort). Always returns a
    publishable dict even if subprocess calls fail.
    """
    ts = now if now is not None else time.time()
    status_excerpt, journal_excerpt = _gather_diagnostics(unit)
    summary = f"{unit} entered FAILED state\n\n{status_excerpt}\n{journal_excerpt}".strip()
    return {
        "from": "ops-failure-alert",
        "kind": "ops_failure",
        "unit": unit,
        "summary": summary,
        "ts": ts,
    }


async def publish_failure(nats_url: str, subject: str, unit: str) -> int:
    """Publish one failure envelope to NATS. Returns 0 on success, 1 on failure."""
    try:
        import nats  # lazy — keeps module collectable on hosts without nats-py
    except ImportError as exc:
        log.error("ops_failure_publish: nats-py not installed; publish skipped (%s)", exc)
        return 1
    envelope = build_envelope(unit)
    payload = json.dumps(envelope).encode("utf-8")
    try:
        nc = await nats.connect(nats_url, connect_timeout=5)
    except Exception as exc:
        log.error("ops_failure_publish: NATS connect failed url=%s: %s", nats_url, exc)
        return 1
    try:
        await nc.publish(subject, payload)
        await nc.flush(timeout=5)
        log.info(
            "ops_failure_publish: published %d bytes to %s (unit=%s)", len(payload), subject, unit
        )
    except Exception as exc:
        log.error("ops_failure_publish: publish failed subject=%s: %s", subject, exc)
        await nc.close()
        return 1
    await nc.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("unit", help="Systemd unit name that entered failed state (%%i from OnFailure=)")
    p.add_argument("--nats-url", default=DEFAULT_NATS_URL, help="NATS server URL")
    p.add_argument("--subject", default=DEFAULT_SUBJECT, help="NATS subject to publish to")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the envelope JSON without publishing (smoke check)",
    )
    args = p.parse_args(argv)
    if args.dry_run:
        print(json.dumps(build_envelope(args.unit), indent=2))
        return 0
    return asyncio.run(publish_failure(args.nats_url, args.subject, args.unit))


if __name__ == "__main__":
    sys.exit(main())
