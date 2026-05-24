#!/usr/bin/env python3
"""supervisor_wake_publish.py — periodic elliot-supervisor wake-up via NATS.

Meta-orchestration: closes the restart gap by waking elliot every 5 minutes
so the supervise routine (running inside elliot's tmux pane) can:
  - check bd ready queue + dispatch idle workers
  - merge completed dual-concurred PRs
  - relay agent positions to #ceo via Slack relay (elliot-only outbound)

This script publishes ONE envelope to keiracom.elliot.inbox and exits.
The existing elliot-nats-inbox-bridge.service subscribes to that subject,
writes the message to /tmp/telegram-relay-elliot/inbox/, the inbox watcher
injects it into the elliottbot tmux pane → elliot wakes up + acts.

NATS subject naming convention: per ceo:comm_architecture canonical key
(2026-05-24). keiracom.elliot.inbox is the all-agents → Elliot funnel.

Per Dave directive 2026-05-24 via Viktor: 'the purpose of the wake is to
supervise them'. This is the minimal mechanism — single periodic NATS
publish — that delivers the wake-up. The supervise routine itself lives
inside elliot's tmux pane and is NOT this script's concern.

USAGE:
    python3 scripts/orchestrator/supervisor_wake_publish.py
    python3 scripts/orchestrator/supervisor_wake_publish.py --dry-run
    python3 scripts/orchestrator/supervisor_wake_publish.py --subject keiracom.elliot.inbox

EXIT: 0 on successful publish; 1 on NATS unavailable / publish error
(systemd Restart=on-failure will retry; the timer will catch the next cycle).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time

# nats-py is lazy-imported inside publish_wake() so this module remains
# collectable on CI hosts where nats-py is not in the test venv. CI
# regression caught 2026-05-24: top-level `import nats` made the test
# file uncollectable (test imports this module → ImportError cascades →
# pytest collection error → 3 consecutive main CI failures + PR #1116
# inherit-blocked). Fix per Elliot dispatch: lazy-import only on the
# live-publish path.

DEFAULT_NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
DEFAULT_SUBJECT = os.environ.get("SUPERVISOR_WAKE_SUBJECT", "keiracom.elliot.inbox")
WAKE_KIND = "supervise_check"
WAKE_FROM = "supervisor-wake"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("supervisor_wake")


def build_envelope(now: float | None = None) -> dict:
    """Construct the wake envelope. Pure function — easy to test."""
    ts = now if now is not None else time.time()
    return {
        "from": WAKE_FROM,
        "kind": WAKE_KIND,
        "summary": (
            "[SUPERVISE-WAKE] periodic fleet supervision check — check bd ready / "
            "inbox status / PR review queue / take action."
        ),
        "ts": ts,
    }


async def publish_wake(nats_url: str, subject: str) -> int:
    """Publish one envelope to NATS. Returns 0 on success, 1 on failure."""
    try:
        import nats  # lazy — keeps module collectable on hosts without nats-py
    except ImportError as exc:
        log.error("supervisor_wake: nats-py not installed; publish skipped (%s)", exc)
        return 1
    envelope = build_envelope()
    payload = json.dumps(envelope).encode("utf-8")
    try:
        nc = await nats.connect(nats_url, connect_timeout=5)
    except Exception as exc:
        log.error("supervisor_wake: NATS connect failed url=%s: %s", nats_url, exc)
        return 1
    try:
        await nc.publish(subject, payload)
        await nc.flush(timeout=5)
        log.info("supervisor_wake: published %d bytes to %s", len(payload), subject)
    except Exception as exc:
        log.error("supervisor_wake: publish failed subject=%s: %s", subject, exc)
        await nc.close()
        return 1
    await nc.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--nats-url", default=DEFAULT_NATS_URL, help="NATS server URL")
    p.add_argument("--subject", default=DEFAULT_SUBJECT, help="NATS subject to publish to")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the envelope JSON without publishing (smoke check)",
    )
    args = p.parse_args(argv)
    if args.dry_run:
        print(json.dumps(build_envelope(), indent=2))
        return 0
    return asyncio.run(publish_wake(args.nats_url, args.subject))


if __name__ == "__main__":
    sys.exit(main())
