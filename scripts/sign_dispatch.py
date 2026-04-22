#!/usr/bin/env python3
"""Sign a dispatch payload and write it to a clone inbox.

Helper for parent bots (or any authorised writer) to create HMAC-signed
dispatch files that pass verification at the inbox relay-watcher.

Usage:
    python scripts/sign_dispatch.py --target atlas --type task_dispatch \\
        --from elliot --brief "fix H1 persistence" \\
        [--max-task-minutes 30] [--task-ref B4P2-T1]

Requires INBOX_HMAC_SECRET in env (auto-loaded from ~/.config/agency-os/.env).

Exit 0 on success, prints the written path. Exit 2 on missing secret or
unknown target.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from security.inbox_hmac import sign  # noqa: E402


VALID_TARGETS = {
    "atlas": "/tmp/telegram-relay-atlas/inbox",
    "orion": "/tmp/telegram-relay-orion/inbox",
}


def _load_env(env_path: str) -> None:
    if not os.path.exists(env_path):
        return
    for line in Path(env_path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    _load_env("/home/elliotbot/.config/agency-os/.env")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=list(VALID_TARGETS))
    parser.add_argument("--type", default="task_dispatch")
    parser.add_argument("--from", dest="sender", required=True)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--max-task-minutes", type=int, default=30)
    parser.add_argument("--task-ref", default=None)
    args = parser.parse_args()

    if not os.environ.get("INBOX_HMAC_SECRET"):
        print("ERROR: INBOX_HMAC_SECRET not set in env (expected in ~/.config/agency-os/.env)", file=sys.stderr)
        return 2

    task_ref = args.task_ref or f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    payload = {
        "id": task_ref,
        "type": args.type,
        "from": args.sender,
        "target": args.target,
        "brief": args.brief,
        "max_task_minutes": args.max_task_minutes,
        "created_at": int(time.time()),
    }
    signed = sign(payload)

    inbox = Path(VALID_TARGETS[args.target])
    inbox.mkdir(parents=True, exist_ok=True)
    out_path = inbox / f"{task_ref}.json"
    out_path.write_text(json.dumps(signed))

    print(str(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
