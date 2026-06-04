#!/usr/bin/env python3
"""Agent concurrency spawn-gate — sync CLI / exit-hook over the canonical lib.

The authoritative implementation lives in src/dispatcher/concurrency_cap.py
and is wired into the live dispatcher (src.dispatcher.main /dispatcher/spawn)
as a pre-spawn gate. This script is the SYNC entry-point for:

  * the agent exit-hook  (`--release --callsign <cs>` on session exit), and
  * ops / manual probes   (`--acquire --callsign <cs> [--role <hint>]`).

It shares the exact Lua + reservation constants from the lib, so there is a
single source of truth. Enforcement is the dispatch layer — this is NOT a
per-service systemd setting (the legacy systemd/concurrency_dropin/*.conf
drop-ins are retired by ceo:decision:concurrency_cap_2026-06-04).

Exit codes:
  0  acquire granted / release ok
  1  acquire refused — caller must QUEUE (requeue-not-drop)
  2  redis unreachable or argument error
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import redis

# Run-as-script path shim: put repo root on sys.path so `src` imports resolve.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.dispatcher.concurrency_cap import (  # noqa: E402 — after path shim
    _CAP_FOR,
    ACQUIRE_LUA,
    GATED,
    HOLDER_TTL_SECS,
    HOLDERS_KEY,
    RELEASE_LUA,
    ROLE_BYPASS,
    ROLES_KEY,
    classify,
)


def _client() -> redis.Redis:
    url = os.environ.get("REDIS_URL")
    if not url:
        print("agent_spawn_gate: REDIS_URL not set", file=sys.stderr)
        sys.exit(2)
    return redis.from_url(url, decode_responses=True)


def acquire(
    callsign: str, role_hint: str | None = None, *, client: redis.Redis | None = None
) -> bool:
    """Sync acquire. Returns True = granted, False = refused (queue)."""
    role = classify(callsign, role_hint)
    if role == ROLE_BYPASS:
        return True
    client = client or _client()
    got = int(
        client.eval(
            ACQUIRE_LUA,
            2,
            HOLDERS_KEY,
            ROLES_KEY,
            callsign.lower(),
            role,
            _CAP_FOR[role],
            GATED,
            int(time.time()),
            HOLDER_TTL_SECS,
        )
    )
    return got == 1


def release(callsign: str, *, client: redis.Redis | None = None) -> None:
    if callsign.lower() == "elliot":
        return
    client = client or _client()
    client.eval(RELEASE_LUA, 2, HOLDERS_KEY, ROLES_KEY, callsign.lower())


def main() -> int:
    parser = argparse.ArgumentParser(prog="agent_spawn_gate")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--acquire", action="store_true")
    group.add_argument("--release", action="store_true")
    parser.add_argument("--callsign", required=True)
    parser.add_argument("--role", default=None, help="chain-step / role hint")
    args = parser.parse_args()
    callsign = args.callsign.lower()

    if args.release:
        release(callsign)
        print(f"agent_spawn_gate: {callsign} released")
        return 0

    if acquire(callsign, args.role):
        print(f"agent_spawn_gate: {callsign} acquired ({classify(callsign, args.role)})")
        return 0
    print(f"agent_spawn_gate: {callsign} REFUSED — band full, queue", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
