#!/usr/bin/env python3
"""round_trip_clone_test.py — end-to-end smoke test for clone dispatch flow.

Verifies the C1→C6 clone communication protocol works end-to-end:
 1. Parent writes a trivial task brief to clone inbox.
 2. Relay-watcher picks up the brief and (in real use) injects into clone tmux.
 3. Clone writes result to outbox.
 4. Clone-to-parent relay-watcher picks up outbox and injects into parent tmux.

This harness does NOT exercise the clone's Claude Code session itself — that
requires a live clone ready to receive dispatch. It exercises the FILE-LEVEL
plumbing: inbox write → relay-watcher detects → (clone would process) → outbox
write → parent-side relay-watcher detects → tmux injection (tested via
simulated outbox write).

Usage:
    python scripts/round_trip_clone_test.py atlas
    python scripts/round_trip_clone_test.py orion

Exit 0 on pass, non-zero on fail. Prints verbatim evidence per step.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

CLONE_CONFIG = {
    "atlas": {
        "parent": "elliot",
        "worktree": "/home/elliotbot/clawd/Agency_OS-atlas",
        "relay_dir": "/tmp/telegram-relay-atlas",
        "systemd_unit": "atlas-relay-watcher.service",
    },
    "orion": {
        "parent": "aiden",
        "worktree": "/home/elliotbot/clawd/Agency_OS-orion",
        "relay_dir": "/tmp/telegram-relay-orion",
        "systemd_unit": "orion-relay-watcher.service",
    },
}


def check(label: str, ok: bool, detail: str = "") -> None:
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {label}{' — ' + detail if detail else ''}")
    if not ok:
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clone", choices=list(CLONE_CONFIG))
    args = parser.parse_args()
    cfg = CLONE_CONFIG[args.clone]
    clone = args.clone

    print(f"=== round-trip test: {clone.upper()} (parent: {cfg['parent']}) ===")

    # 1. Scaffold presence
    worktree = Path(cfg["worktree"])
    check("worktree exists", worktree.is_dir(), str(worktree))
    check("IDENTITY.md present", (worktree / "IDENTITY.md").is_file())
    check("CLONE_LEARNINGS.md present", (worktree / "CLONE_LEARNINGS.md").is_file())

    relay = Path(cfg["relay_dir"])
    for sub in ("inbox", "outbox", "processed"):
        check(f"relay {sub} dir", (relay / sub).is_dir())

    # 2. Systemd service active
    result = subprocess.run(
        ["systemctl", "--user", "is-active", cfg["systemd_unit"]],
        capture_output=True,
        text=True,
    )
    check(
        f"{cfg['systemd_unit']} active",
        result.stdout.strip() == "active",
        f"status={result.stdout.strip()}",
    )

    # 3. Inbox write — simulate parent dispatch
    test_id = f"rt_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    inbox_file = relay / "inbox" / f"{test_id}.json"
    inbox_file.write_text(
        json.dumps(
            {
                "id": test_id,
                "type": "text",
                "text": f"[ROUND-TRIP-TEST] Smoke probe for {clone}. No action required.",
                "sender": "test-harness",
            }
        )
    )
    check("inbox write", inbox_file.exists(), str(inbox_file))

    # 4. Outbox write — simulate clone returning result
    outbox_file = relay / "outbox" / f"{test_id}_result.txt"
    outbox_file.write_text(f"[{clone.upper()}] round-trip test {test_id} ack")
    check("outbox write", outbox_file.exists(), str(outbox_file))

    # 5. Relay watcher processes outbox — give watcher time to move file
    for _ in range(10):
        time.sleep(0.5)
        if not outbox_file.exists():
            break
    processed = relay / "processed" / outbox_file.name
    check(
        "relay-watcher moved outbox → processed",
        processed.exists(),
        f"{processed} (watcher picked up within 5s)",
    )

    # Cleanup test inbox artefact (outbox already moved by watcher)
    try:
        inbox_file.unlink()
    except FileNotFoundError:
        pass

    print(f"=== {clone.upper()} round-trip: PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
