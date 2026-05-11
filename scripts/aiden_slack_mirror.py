#!/usr/bin/env python3
"""aiden_slack_mirror.py — DUAL_POST dispatch for AIDEN-SLACK-MIGRATION-001.

Watches Aiden's TG outbox dir (/tmp/telegram-relay-aiden/outbox/) and
mirrors each outgoing message to Slack via slack_relay.py. This is the
"DUAL_POST" half of the dispatch layer: TG outbox writes continue to
fire normally (Elliot's TG relay watcher handles them); this service
posts a parallel copy to Slack.

Cutover plan (post-smoke, separate dispatch): switch to SLACK_ONLY by
disabling Aiden's TG outbox watcher OR by setting SLACK_ONLY=true and
making this service write a sentinel that the TG watcher respects.

Env:
    DUAL_POST            (default false) — if "true", this service runs
                          the mirror. If false, exits 0 immediately
                          (smoke gate).
    SLACK_BOT_TOKEN      (required when DUAL_POST=true)
    SLACK_DEFAULT_CHANNEL (optional, default #execution)

Revert path: `systemctl --user stop aiden-slack-mirror.service` or unset
DUAL_POST in EnvironmentFile and restart.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

CALLSIGN = "aiden"
OUTBOX = Path(f"/tmp/telegram-relay-{CALLSIGN}/outbox")
PROCESSED_MARKER_DIR = Path(f"/tmp/aiden-slack-mirror-processed")
SLACK_RELAY = Path(__file__).resolve().parent / "slack_relay.py"

DUAL_POST = os.environ.get("DUAL_POST", "false").lower() == "true"
POLL_INTERVAL = float(os.environ.get("MIRROR_POLL_SECONDS", "2"))


def already_processed(filename: str) -> bool:
    return (PROCESSED_MARKER_DIR / filename).exists()


def mark_processed(filename: str) -> None:
    (PROCESSED_MARKER_DIR / filename).touch()


def post_to_slack(text: str) -> bool:
    """Invoke slack_relay.py with the message body. Returns True on success."""
    try:
        result = subprocess.run(
            ["python3", str(SLACK_RELAY), "-g", text],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            print(f"slack_relay failed: {result.stderr.strip()}", file=sys.stderr, flush=True)
            return False
        return True
    except subprocess.TimeoutExpired:
        print("slack_relay timeout", file=sys.stderr, flush=True)
        return False


def process_outbox_file(path: Path) -> None:
    """Read a single outbox JSON file and mirror its text to Slack."""
    if already_processed(path.name):
        return
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"skip {path.name}: {e}", file=sys.stderr, flush=True)
        mark_processed(path.name)  # avoid retry loop on malformed files
        return
    text = payload.get("text") or ""
    if not text:
        mark_processed(path.name)
        return
    if post_to_slack(text):
        mark_processed(path.name)
        print(f"mirrored {path.name} -> Slack", flush=True)


def main() -> int:
    if not DUAL_POST:
        print("DUAL_POST=false — mirror service no-op, exiting", flush=True)
        return 0
    PROCESSED_MARKER_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    print(f"DUAL_POST=true — watching {OUTBOX} every {POLL_INTERVAL}s", flush=True)
    # On boot, mark all CURRENT outbox files as processed (don't replay history).
    for existing in OUTBOX.glob("*.json"):
        mark_processed(existing.name)
    while True:
        for path in sorted(OUTBOX.glob("*.json")):
            process_outbox_file(path)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
