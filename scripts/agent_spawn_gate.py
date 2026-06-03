#!/usr/bin/env python3
"""Agent concurrency spawn-gate — Redis semaphore (KEI Agency_OS-03w4).

Wired into systemd via ExecStartPre/ExecStopPost on each non-Elliot
*-agent.service drop-in (systemd/concurrency_dropin/<callsign>.conf).
Elliot's service has no drop-in; Elliot bypasses the gate.

Hard global ceiling: N_MAX=2 non-Elliot concurrent sessions. Elliot is
always-on, so total = 3 with Elliot.

Priority semantics (KEI: "Deliberator priority queue prevents chain
deadlock"). Implemented at the Redis atomic level rather than via
in-process BLPOP-wait, because ExecStartPre cannot block on a long
queue without holding systemd state hostage:

  Lua acquire (Worker):
    1. If a deliberator marker is present in the priority list,
       refuse (worker yields). Returns 0.
    2. Otherwise INCR active_sessions. If > N_MAX, DECR + return 0.
    3. Else SETEX TTL on the counter (300s safety). Return 1.

  Lua acquire (Deliberator):
    1. INCR active_sessions. If <= N_MAX: SETEX + cleanup own marker
       (LREM) + return 1.
    2. Else DECR + LPUSH own callsign to priority list (TTL via
       EXPIRE 60s on the list key) + return 0. Systemd retries
       (Restart=always, RestartSec=10) until a slot frees and the
       deliberator wins it on next attempt.

  Lua release: DECR active_sessions; LREM own callsign from list.

The deliberator marker yields slots from workers within RestartSec of
arrival, which satisfies proof gate (b) without true in-process queue
waits.

Lua atomicity prevents TOCTOU between INCR and the cap check.

Exit codes:
  0  acquire succeeded / release succeeded
  1  acquire refused (over cap or yielding to deliberator)
  2  redis unreachable or argument error
"""

from __future__ import annotations

import argparse
import os
import sys

import redis

# Hard global ceiling. Non-Elliot active sessions. KEI Agency_OS-03w4.
N_MAX = 2

ACTIVE_KEY = "agent:concurrency:active_sessions"
PRIORITY_KEY = "agent:concurrency:deliberator_priority"
ACTIVE_TTL_SECS = 300
PRIORITY_TTL_SECS = 60

DELIBERATORS = {"aiden", "max"}

# KEYS[1] = ACTIVE_KEY, KEYS[2] = PRIORITY_KEY
# ARGV[1] = callsign, ARGV[2] = is_deliberator ("1"/"0"),
# ARGV[3] = n_max,    ARGV[4] = active_ttl, ARGV[5] = priority_ttl
_ACQUIRE_LUA = """
local is_deliberator = ARGV[2] == "1"
local n_max = tonumber(ARGV[3])
local active_ttl = tonumber(ARGV[4])
local priority_ttl = tonumber(ARGV[5])
local callsign = ARGV[1]

if not is_deliberator then
  local pending = redis.call("LLEN", KEYS[2])
  if pending > 0 then
    return 0
  end
end

local count = redis.call("INCR", KEYS[1])
if count > n_max then
  redis.call("DECR", KEYS[1])
  if is_deliberator then
    redis.call("LPUSH", KEYS[2], callsign)
    redis.call("EXPIRE", KEYS[2], priority_ttl)
  end
  return 0
end

redis.call("EXPIRE", KEYS[1], active_ttl)
if is_deliberator then
  redis.call("LREM", KEYS[2], 0, callsign)
end
return 1
"""

# KEYS[1] = ACTIVE_KEY, KEYS[2] = PRIORITY_KEY
# ARGV[1] = callsign
_RELEASE_LUA = """
local count = redis.call("GET", KEYS[1])
if count and tonumber(count) > 0 then
  redis.call("DECR", KEYS[1])
end
redis.call("LREM", KEYS[2], 0, ARGV[1])
return 1
"""


def _client() -> redis.Redis:
    url = os.environ.get("REDIS_URL")
    if not url:
        print("agent_spawn_gate: REDIS_URL not set", file=sys.stderr)
        sys.exit(2)
    return redis.from_url(url, decode_responses=True)


def acquire(callsign: str) -> int:
    client = _client()
    is_deliberator = "1" if callsign in DELIBERATORS else "0"
    script = client.register_script(_ACQUIRE_LUA)
    got = script(
        keys=[ACTIVE_KEY, PRIORITY_KEY],
        args=[callsign, is_deliberator, N_MAX, ACTIVE_TTL_SECS, PRIORITY_TTL_SECS],
    )
    if int(got) == 1:
        print(f"agent_spawn_gate: {callsign} acquired slot")
        return 0
    print(f"agent_spawn_gate: {callsign} refused (over cap or yielding)", file=sys.stderr)
    return 1


def release(callsign: str) -> int:
    client = _client()
    script = client.register_script(_RELEASE_LUA)
    script(keys=[ACTIVE_KEY, PRIORITY_KEY], args=[callsign])
    print(f"agent_spawn_gate: {callsign} released slot")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="agent_spawn_gate")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--acquire", action="store_true")
    group.add_argument("--release", action="store_true")
    parser.add_argument("--callsign", required=True)
    args = parser.parse_args()
    callsign = args.callsign.lower()
    if callsign == "elliot":
        print("agent_spawn_gate: elliot bypasses cap", file=sys.stderr)
        return 0
    if args.acquire:
        return acquire(callsign)
    return release(callsign)


if __name__ == "__main__":
    sys.exit(main())
