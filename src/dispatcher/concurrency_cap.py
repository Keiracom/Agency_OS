"""concurrency_cap — dispatch-layer reservation semaphore (Agency_OS-03w4).

Ratified design: ceo:decision:concurrency_cap_2026-06-04. Fix for the
2026-06-04 ~03:02 AEST full-fleet crash — 7 persistent always-on tmux
sessions (peak ~5GB each on the OLD model) exceeded ~16GB RAM + 5.3GB
swap and OOM-exited within 2s of each other.

ENFORCEMENT LAYER: spawn/dispatch — NOT a per-service systemd setting.
A hard semaphore that QUEUES spawn requests beyond N (requeue-not-drop,
mirroring the tenant `keiracom:tenant:overflow` backpressure pattern,
Cat ceo:tier_concurrency_commercial_architecture). Wired into
src.dispatcher.main /dispatcher/spawn as a pre-spawn gate alongside the
idempotency / cost / budget gates. The legacy per-service drop-ins
(systemd/concurrency_dropin/*.conf) are RETIRED by this design.

ROLE-CLASS RESERVATION — the stage-pair guard
----------------------------------------------
N_TOTAL concurrent sessions. Elliot (orchestrator) bypasses the gate —
always live (bridge model: persistent core = orchestrator + 2
deliberators) — and consumes one of the N. The remaining gated band is
partitioned into reserved per-role caps that SUM to the gated total:

    gated   = N_TOTAL - 1          (Elliot bypasses but is counted)
    delib   = 2                    (aiden + max — dual-concur pair)
    review  = 2                    (2 parallel reviewers)
    worker  = gated - delib - review

Because the caps PARTITION the gated band, each role's slots are
physically reserved: a worker can never occupy a deliberator's or a
reviewer's slot. The 2 deliberators and the 2 reviewers can therefore
ALWAYS co-reside — no priority queue is needed, the reservation IS the
guarantee. Only workers beyond their cap overflow, and a queued worker
is safe to wait (requeue-not-drop) because by construction it cannot be
starving a higher-priority role. This is exactly the proof-gate NEGATIVE
("a cap that blocks the 2 deliberators / 2 reviewers from co-residing")
made impossible by construction.

N derivation (verbatim Opus-4.8 measurement, 2026-06-04 — see
docs/audits/concurrency_cap_rss_measurement.md):
  physical RAM 15986 MB + swap 5399 MB = 21385 MB addressable.
  per-session cgroup memory.peak under 4.8: ~0.9-1.4 GB typical, 2.6 GB
  worst observed spike (vs OLD-model 5.1 GB). Planning peak 1.5 GB
  sustained / 2.6 GB spike; infra reserve ~4 GB.
    sustained:       6 * 1.5 + 4.0 = 13.0 GB < 15.6 GB RAM        (no swap)
    worst all-spike: 6 * 2.6 + 4.0 = 19.6 GB < 20.9 GB RAM+swap   (no OOM)
    7 sessions worst-spike = 22.2 GB > 20.9 GB  <- the config that crashed
  => N_TOTAL = 6.

DI: caller passes an async Redis/Valkey client implementing `eval`. Use
src/dispatcher/valkey_pool.get_valkey_client() in production; fakes
(fakeredis[lua]) inject in tests. Fail-open on Redis transport error —
returns GRANTED + a CRITICAL alert, so a Valkey blip never freezes the
whole fleet; ops sees the alert that the cap is temporarily off.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

log = logging.getLogger(__name__)

# ── Configuration (env-overridable so ops can tune without redeploy) ──────────
N_TOTAL = int(os.environ.get("AGENT_CONCURRENCY_N_TOTAL", "6"))
DELIB_CAP = int(os.environ.get("AGENT_CONCURRENCY_DELIB_CAP", "2"))
REVIEW_CAP = int(os.environ.get("AGENT_CONCURRENCY_REVIEW_CAP", "2"))
# Elliot bypasses the gate but is counted in N_TOTAL -> gated band = N_TOTAL-1.
GATED = N_TOTAL - 1
WORKER_CAP = max(0, GATED - DELIB_CAP - REVIEW_CAP)
HOLDER_TTL_SECS = int(os.environ.get("AGENT_CONCURRENCY_TTL", "1800"))

HOLDERS_KEY = "agent:concurrency:holders"  # ZSET member=callsign score=expiry_unix
ROLES_KEY = "agent:concurrency:roles"  # HASH callsign -> role
OVERFLOW_KEY = "agent:concurrency:overflow"  # LIST FIFO of refused spawn requests

ORCHESTRATOR = "elliot"
DELIBERATORS = {"aiden", "max"}
# chain_step / role hints that mean "this spawn is a reviewer in a stage-pair".
REVIEWER_HINTS = {"reviewer", "review", "spec", "safety", "verify"}

ROLE_BYPASS = "bypass"
ROLE_DELIBERATOR = "deliberator"
ROLE_REVIEWER = "reviewer"
ROLE_WORKER = "worker"

_CAP_FOR = {
    ROLE_DELIBERATOR: DELIB_CAP,
    ROLE_REVIEWER: REVIEW_CAP,
    ROLE_WORKER: WORKER_CAP,
}

# KEYS[1]=HOLDERS_KEY (zset)  KEYS[2]=ROLES_KEY (hash)
# ARGV: callsign, role, cap, gated_total, now_unix, ttl
# Returns 1 = granted, 0 = refused (band full / global full).
ACQUIRE_LUA = """
local callsign = ARGV[1]
local role = ARGV[2]
local cap = tonumber(ARGV[3])
local gated_total = tonumber(ARGV[4])
local now = tonumber(ARGV[5])
local ttl = tonumber(ARGV[6])

-- 1. Reap expired holders (release-miss safety net).
local stale = redis.call("ZRANGEBYSCORE", KEYS[1], "-inf", now)
for _, cs in ipairs(stale) do
  redis.call("ZREM", KEYS[1], cs)
  redis.call("HDEL", KEYS[2], cs)
end

-- 2. Idempotent re-acquire: already holding -> just refresh the lease.
if redis.call("ZSCORE", KEYS[1], callsign) then
  redis.call("ZADD", KEYS[1], now + ttl, callsign)
  return 1
end

-- 3. Count current holders, total and for this role.
local total = redis.call("ZCARD", KEYS[1])
local role_count = 0
local roles = redis.call("HGETALL", KEYS[2])
for i = 2, #roles, 2 do
  if roles[i] == role then role_count = role_count + 1 end
end

-- 4. Reservation check: role band first (the stage-pair guard), then the
--    global gated ceiling as a defensive backstop.
if role_count >= cap then return 0 end
if total >= gated_total then return 0 end

-- 5. Grant: lease the slot.
redis.call("ZADD", KEYS[1], now + ttl, callsign)
redis.call("HSET", KEYS[2], callsign, role)
return 1
"""

# KEYS[1]=HOLDERS_KEY  KEYS[2]=ROLES_KEY  ARGV[1]=callsign
RELEASE_LUA = """
redis.call("ZREM", KEYS[1], ARGV[1])
redis.call("HDEL", KEYS[2], ARGV[1])
return 1
"""


class ConcurrencyDecision(Enum):
    GRANTED = "granted"
    QUEUE = "queue"  # band/ceiling full -> caller requeues (requeue-not-drop)


@dataclass(frozen=True, kw_only=True)
class ConcurrencyResult:
    decision: ConcurrencyDecision
    callsign: str
    role: str
    reason: str

    @property
    def granted(self) -> bool:
        return self.decision == ConcurrencyDecision.GRANTED


class _RedisProtocol(Protocol):
    """Subset of redis.asyncio.Redis we depend on: Lua eval."""

    def eval(self, script: str, numkeys: int, *keys_and_args: Any) -> Awaitable[Any]: ...


LogEmitter = Callable[[dict[str, Any]], None]


def classify(callsign: str, role_hint: str | None = None) -> str:
    """Map (callsign, optional chain-step/role hint) -> reservation class."""
    cs = callsign.lower()
    if cs == ORCHESTRATOR:
        return ROLE_BYPASS
    if cs in DELIBERATORS:
        return ROLE_DELIBERATOR
    if role_hint and role_hint.strip().lower() in REVIEWER_HINTS:
        return ROLE_REVIEWER
    return ROLE_WORKER


def _default_log_emitter(payload: dict[str, Any]) -> None:
    log.info("concurrency-cap: %s", payload)


class ConcurrencyGate:
    """Dispatcher pre-spawn concurrency cap with role-class reservation.

    Caller invokes `acquire(...)` BEFORE every spawn. GRANTED -> proceed;
    QUEUE -> the spawn would exceed the role's reserved band, so requeue the
    request (requeue-not-drop). `release(...)` is called from the
    terminate/reaper path on session exit (TTL is the safety net if missed).
    """

    def __init__(
        self,
        *,
        valkey_client: _RedisProtocol,
        ttl_seconds: int = HOLDER_TTL_SECS,
        log_emitter: LogEmitter | None = None,
        now_provider: Callable[[], float] | None = None,
    ) -> None:
        self._client = valkey_client
        self._ttl = ttl_seconds
        self._log = log_emitter or _default_log_emitter
        self._now = now_provider or time.time

    async def acquire(self, *, callsign: str, role_hint: str | None = None) -> ConcurrencyResult:
        role = classify(callsign, role_hint)
        if role == ROLE_BYPASS:
            return ConcurrencyResult(
                decision=ConcurrencyDecision.GRANTED,
                callsign=callsign,
                role=role,
                reason="orchestrator bypasses cap (always live)",
            )
        cap = _CAP_FOR[role]
        now = int(self._now())
        try:
            granted = int(
                await self._client.eval(
                    ACQUIRE_LUA,
                    2,
                    HOLDERS_KEY,
                    ROLES_KEY,
                    callsign.lower(),
                    role,
                    cap,
                    GATED,
                    now,
                    self._ttl,
                )
            )
        except Exception:  # noqa: BLE001 — fail-open per design (see module docstring)
            log.exception("concurrency-cap: Valkey eval failed; failing OPEN (cap off)")
            self._emit(
                {
                    "kind": "concurrency_cap_fail_open",
                    "severity": "critical",
                    "callsign": callsign,
                    "role": role,
                    "reason": "valkey unreachable — cap temporarily OFF",
                }
            )
            return ConcurrencyResult(
                decision=ConcurrencyDecision.GRANTED,
                callsign=callsign,
                role=role,
                reason="valkey unreachable — fail-open GRANTED",
            )
        if granted == 1:
            return ConcurrencyResult(
                decision=ConcurrencyDecision.GRANTED,
                callsign=callsign,
                role=role,
                reason=f"{role} slot acquired",
            )
        self._emit(
            {
                "kind": "concurrency_cap_queue",
                "callsign": callsign,
                "role": role,
                "cap": cap,
                "reason": "role band full — requeue (requeue-not-drop)",
            }
        )
        return ConcurrencyResult(
            decision=ConcurrencyDecision.QUEUE,
            callsign=callsign,
            role=role,
            reason=f"{role} band full (cap={cap}) — requeue",
        )

    async def release(self, *, callsign: str) -> None:
        if callsign.lower() == ORCHESTRATOR:
            return
        try:
            await self._client.eval(RELEASE_LUA, 2, HOLDERS_KEY, ROLES_KEY, callsign.lower())
        except Exception:  # noqa: BLE001 — release failure is non-fatal (TTL reaps it)
            log.exception("concurrency-cap: release eval failed for %s (TTL will reap)", callsign)

    def _emit(self, payload: dict[str, Any]) -> None:
        try:
            self._log(payload)
        except Exception:  # noqa: BLE001 — telemetry never blocks
            log.exception("concurrency-cap: log emit failed (non-blocking)")


__all__ = [
    "ACQUIRE_LUA",
    "DELIB_CAP",
    "GATED",
    "N_TOTAL",
    "RELEASE_LUA",
    "REVIEW_CAP",
    "WORKER_CAP",
    "ConcurrencyDecision",
    "ConcurrencyGate",
    "ConcurrencyResult",
    "classify",
]
