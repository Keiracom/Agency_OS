"""Tier-gated work-loop consumer (Agency_OS-s3ye).

Subscribes to Valkey `keiracom:tasks:available`, admits spawns under a per-tenant
ceiling via an atomic Lua INCR+compare, overflows (never drops) at the ceiling,
and releases slots on agent exit — popping the overflow to spawn the next task.

Key namespace (extends valkey_pool.py's contract):
    keiracom:tenant:active_spawns:{tenant_id}   INT   live spawn counter
    keiracom:tenant:lease:{tenant_id}:{task_id} STR   per-agent slot lease (TTL)
    keiracom:tenant:leases:{tenant_id}          SET   task_ids the counter believes live
    keiracom:tenant:overflow:{tenant_id}        LIST  tasks queued at ceiling (FIFO)
    keiracom:tasks:lock:{task_id}               STR   distributed dup-spawn lock (TTL)
    keiracom:tasks:attempts:{task_id}           INT   spawn-attempt counter (TTL)
    keiracom:tasks:deadletter                   LIST  tasks that exhausted retries

Fail-open: a malformed message dead-letters; a failed spawn requeues to overflow
until max_attempts, then dead-letters; lookup/transport errors never drop a valid
task. Crashed agents release their slot when the lease TTL lapses (reconcile()).
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from src.dispatcher.valkey_pool import get_valkey_client

logger = logging.getLogger(__name__)

TASKS_CHANNEL = "keiracom:tasks:available"
DEADLETTER_KEY = "keiracom:tasks:deadletter"
DEFAULT_DISPATCHER_URL = "http://127.0.0.1:4001"  # NOSONAR S5332 loopback (KEI-213)
DEFAULT_LEASE_TTL_S = 300  # 5 min slot lease; heartbeat renews it
LOCK_TTL_S = 300  # dup-spawn lock; renewed alongside the lease
ATTEMPTS_TTL_S = 3600
CRASH_ATTEMPTS_TTL_S = 86400  # 24h retention on crash-recovery counter
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_ALERT_THRESHOLD = 0.70  # node-level capacity alert
_TASK_RAW_PREFIX = "keiracom:tenant:task_raw"

# Dead-letter #ceo notification (Agency_OS-gl3v). A dropped task that no human
# sees destroys solo-operation trust, so every dead-letter posts to #ceo via
# Elliot's relay. Path mirrors the dispatcher's task_complete hook; spawned
# agents can't post to Slack (scrubbed env), so the relay runs CALLSIGN=elliot.
_SLACK_RELAY_SCRIPT = os.path.join(
    os.environ.get("DISPATCHER_AGENT_WORKDIR", "/home/elliotbot/clawd/Agency_OS"),
    "scripts",
    "slack_relay.py",
)
_NOTIFY_TIMEOUT_S = 15

# Atomic admission: INCR the counter iff below ceiling, take the slot lease +
# membership in one round-trip. Returns the new count, or -1 when at ceiling.
ADMIT_LUA = """
local cur = tonumber(redis.call('GET', KEYS[1]) or '0')
if cur >= tonumber(ARGV[1]) then return -1 end
local n = redis.call('INCR', KEYS[1])
redis.call('SET', KEYS[2], '1', 'EX', tonumber(ARGV[2]))
redis.call('SADD', KEYS[3], ARGV[3])
return n
"""

# Idempotent release: only DECR if the task was actually a live member (guards
# against double-release). Floors the counter at 0.
RELEASE_LUA = """
if redis.call('SREM', KEYS[3], ARGV[1]) == 0 then return 0 end
redis.call('DEL', KEYS[2])
local n = redis.call('DECR', KEYS[1])
if n < 0 then redis.call('SET', KEYS[1], '0'); n = 0 end
return 1
"""


@dataclass(frozen=True)
class Task:
    task_id: str
    tenant_id: str
    backend: str
    spawn_kwargs: dict[str, Any]
    raw: str


@dataclass(frozen=True)
class DeadLetterNotice:
    """What a dead-lettered task carries into the #ceo alert (Agency_OS-gl3v)."""

    task_id: str
    title: str
    attempts: int
    error: str  # cause / final error, already truncated to 200 chars
    raw: str


def _active_key(tenant_id: str) -> str:
    return f"keiracom:tenant:active_spawns:{tenant_id}"


def _lease_key(tenant_id: str, task_id: str) -> str:
    return f"keiracom:tenant:lease:{tenant_id}:{task_id}"


def _leases_set(tenant_id: str) -> str:
    return f"keiracom:tenant:leases:{tenant_id}"


def _overflow_key(tenant_id: str) -> str:
    return f"keiracom:tenant:overflow:{tenant_id}"


def _lock_key(task_id: str) -> str:
    return f"keiracom:tasks:lock:{task_id}"


def _attempts_key(task_id: str) -> str:
    return f"keiracom:tasks:attempts:{task_id}"


def _task_raw_key(tenant_id: str, task_id: str) -> str:
    """Key that stores the original task message for crash-recovery re-queue."""
    return f"{_TASK_RAW_PREFIX}:{tenant_id}:{task_id}"


def _parse(raw: str) -> Task | None:
    try:
        d = json.loads(raw)
        task_id, tenant_id = str(d["task_id"]), str(d["tenant_id"])
        if not task_id or not tenant_id:
            return None
        return Task(
            task_id=task_id,
            tenant_id=tenant_id,
            backend=str(d.get("backend", "container")),
            spawn_kwargs=dict(d.get("spawn_kwargs") or {}),
            raw=raw,
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def _extract_id_title(raw: str) -> tuple[str, str]:
    """Best-effort task_id + title from a (possibly malformed) message.

    Title lives in spawn_kwargs.title (bridge.task_event_to_message). Falls back
    to a top-level title, then to placeholders — never raises, so a malformed
    message still produces a human-readable notice.
    """
    try:
        d = json.loads(raw)
        task_id = str(d.get("task_id") or "unknown")
        spawn_kwargs = d.get("spawn_kwargs") if isinstance(d.get("spawn_kwargs"), dict) else {}
        title = str(spawn_kwargs.get("title") or d.get("title") or "(no title in message)")
        return task_id, title
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return "unknown", "(unparseable task message)"


SpawnFn = Callable[[Task], Awaitable[bool]]
CeilingFn = Callable[[str], Awaitable[int]]
NotifyFn = Callable[[DeadLetterNotice], Awaitable[None]]


class WorkLoopConsumer:
    """Drives the tier-gated spawn loop. All external seams are injectable."""

    def __init__(
        self,
        *,
        valkey: Any = None,
        spawn_fn: SpawnFn | None = None,
        ceiling_fn: CeilingFn | None = None,
        notify_fn: NotifyFn | None = None,
        dispatcher_url: str = DEFAULT_DISPATCHER_URL,
        lease_ttl_s: int = DEFAULT_LEASE_TTL_S,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        alert_threshold: float = DEFAULT_ALERT_THRESHOLD,
    ):
        self._r = valkey or get_valkey_client()
        self._spawn_fn = spawn_fn or self._default_spawn
        self._ceiling_fn = ceiling_fn
        self._notify_fn = notify_fn or self._default_notify
        self._dispatcher_url = dispatcher_url.rstrip("/")
        self._lease_ttl_s = lease_ttl_s
        self._max_attempts = max_attempts
        self._alert_threshold = alert_threshold

    async def _ceiling(self, tenant_id: str) -> int:
        if self._ceiling_fn is not None:
            return await self._ceiling_fn(tenant_id)
        from src.keiracom_system.work_loop import ceilings

        return await ceilings.get_ceiling(tenant_id)

    async def _default_spawn(self, task: Task) -> bool:
        """POST /dispatcher/spawn. True on 2xx; False (never raises) otherwise."""
        import httpx

        body = {
            "backend": task.backend,
            "key": task.task_id,  # unique supervisor registry key
            "spawn_kwargs": {
                **task.spawn_kwargs,
                "task_id": task.task_id,
                "tenant_id": task.tenant_id,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self._dispatcher_url}/dispatcher/spawn", json=body)
            return 200 <= resp.status_code < 300
        except Exception:  # noqa: BLE001 — transport failure is a failed attempt, not a crash
            logger.warning("work-loop: spawn POST failed for task=%s", task.task_id, exc_info=True)
            return False

    async def _admit(self, task: Task, ceiling: int) -> int:
        result = int(
            await self._r.eval(
                ADMIT_LUA,
                3,
                _active_key(task.tenant_id),
                _lease_key(task.tenant_id, task.task_id),
                _leases_set(task.tenant_id),
                ceiling,
                self._lease_ttl_s,
                task.task_id,
            )
        )
        if result >= 0:
            # TTL matches CRASH_ATTEMPTS_TTL_S — safety net against leaked keys on permanent failure.
            await self._r.set(
                _task_raw_key(task.tenant_id, task.task_id), task.raw, ex=CRASH_ATTEMPTS_TTL_S
            )
        return result

    async def _maybe_alert(self, tenant_id: str, count: int, ceiling: int) -> None:
        if ceiling > 0 and count / ceiling >= self._alert_threshold:
            logger.warning(
                "[WORK-LOOP CAPACITY ALERT] tenant=%s at %d/%d (%.0f%%) — >= %.0f%% threshold",
                tenant_id,
                count,
                ceiling,
                100 * count / ceiling,
                100 * self._alert_threshold,
            )

    async def _dead_letter(self, raw: str, reason: str, *, attempts: int = 0) -> None:
        logger.error("work-loop: dead-lettering task (%s): %s", reason, raw[:200])
        await self._r.rpush(DEADLETTER_KEY, raw)
        # Agency_OS-gl3v: alert #ceo so a dropped task is never silent. Fail-open
        # — the dead-letter itself must complete even if notification raises.
        task_id, title = _extract_id_title(raw)
        notice = DeadLetterNotice(
            task_id=task_id, title=title, attempts=attempts, error=reason[:200], raw=raw
        )
        try:
            await self._notify_fn(notice)
        except Exception:  # noqa: BLE001 — a notification failure must NEVER block dead-letter
            logger.warning(
                "work-loop: dead-letter notification raised for task=%s", task_id, exc_info=True
            )

    async def _default_notify(self, notice: DeadLetterNotice) -> None:
        """Post a dead-letter alert to #ceo via slack_relay.py (CALLSIGN=elliot).

        Fail-open: a non-zero relay exit or any exception is logged, never
        raised. `-c ceo` targets #ceo explicitly (not the env default channel,
        which #execution-drops). Mirrors the dispatcher task_complete hook.
        """
        msg = (
            f"🪦 [WORK-LOOP] Task dead-lettered after {notice.attempts} attempt(s) — "
            f"ID: {notice.task_id} · what: {notice.title} · error: {notice.error}"
        )
        try:
            import subprocess
            import sys

            result = subprocess.run(
                [sys.executable, _SLACK_RELAY_SCRIPT, "-c", "ceo", msg],
                capture_output=True,
                text=True,
                timeout=_NOTIFY_TIMEOUT_S,
                env={**os.environ, "CALLSIGN": "elliot"},
                check=False,
            )
            if result.returncode != 0:
                logger.warning(
                    "work-loop: dead-letter slack_relay rc=%d stderr=%r",
                    result.returncode,
                    result.stderr[:200],
                )
        except Exception:  # noqa: BLE001 — notification must never block dead-letter
            logger.warning(
                "work-loop: dead-letter slack_relay raised for task=%s",
                notice.task_id,
                exc_info=True,
            )

    async def process_task(self, raw: str) -> str:
        """Process one task message. Returns a status string for observability."""
        task = _parse(raw)
        if task is None:
            await self._dead_letter(raw, "malformed")
            return "deadletter:malformed"
        # Distributed lock — one live spawn per task_id across consumer instances.
        if not await self._r.set(_lock_key(task.task_id), "1", nx=True, ex=LOCK_TTL_S):
            return "duplicate:locked"
        ceiling = await self._ceiling(task.tenant_id)
        admitted = await self._admit(task, ceiling)
        if admitted < 0:
            await self._r.delete(_lock_key(task.task_id))  # not spawned → free the lock
            await self._r.rpush(_overflow_key(task.tenant_id), raw)  # never drop
            return "overflow"
        await self._maybe_alert(task.tenant_id, admitted, ceiling)
        if await self._spawn_with_attempts(task):
            return "spawned"  # lock + lease held until exit
        await self.release_slot(task.tenant_id, task.task_id)
        return "spawn_failed"

    async def _spawn_with_attempts(self, task: Task) -> bool:
        attempts = int(await self._r.incr(_attempts_key(task.task_id)))
        await self._r.expire(_attempts_key(task.task_id), ATTEMPTS_TTL_S)
        ok = await self._spawn_fn(task)
        if ok:
            await self._r.delete(_attempts_key(task.task_id))
            return True
        if attempts >= self._max_attempts:
            await self._dead_letter(
                task.raw,
                f"spawn failed after {attempts} attempts (max={self._max_attempts})",
                attempts=attempts,
            )
            await self._r.delete(_attempts_key(task.task_id))
        else:
            await self._r.rpush(_overflow_key(task.tenant_id), task.raw)  # requeue, never drop
        return False

    async def release_slot(self, tenant_id: str, task_id: str) -> None:
        """exit_cycle callback: free the slot, drop the lock, spawn the next queued task."""
        await self._r.eval(
            RELEASE_LUA,
            3,
            _active_key(tenant_id),
            _lease_key(tenant_id, task_id),
            _leases_set(tenant_id),
            task_id,
        )
        await self._r.delete(_lock_key(task_id))
        await self._r.delete(_task_raw_key(tenant_id, task_id))  # clean up raw message
        nxt = await self._r.lpop(_overflow_key(tenant_id))
        if nxt is not None:
            await self.process_task(nxt)

    async def renew_lease(self, tenant_id: str, task_id: str) -> None:
        """Heartbeat: refresh the slot lease + lock TTL so a live agent keeps its slot."""
        await self._r.expire(_lease_key(tenant_id, task_id), self._lease_ttl_s)
        await self._r.expire(_lock_key(task_id), LOCK_TTL_S)

    async def reconcile(self, tenant_id: str) -> int:
        """Crash recovery: release slots whose lease TTL lapsed (no heartbeat).

        For each expired lease, the original task message is re-queued (up to
        max_attempts) or dead-lettered. Returns the number of slots reclaimed.
        Run periodically per active tenant.
        """
        reclaimed = 0
        for task_id in await self._r.smembers(_leases_set(tenant_id)):
            if not await self._r.exists(_lease_key(tenant_id, task_id)):
                raw = await self._r.get(_task_raw_key(tenant_id, task_id))
                await self.release_slot(tenant_id, task_id)
                reclaimed += 1
                if raw:
                    await self._handle_crashed_task(task_id, raw)
        return reclaimed

    async def _handle_crashed_task(self, task_id: str, raw: str) -> None:
        """Re-queue or dead-letter a task whose agent crashed (lease expired)."""
        crash_key = f"keiracom:tasks:crash_attempts:{task_id}"
        attempts = int(await self._r.incr(crash_key))
        await self._r.expire(crash_key, CRASH_ATTEMPTS_TTL_S)
        if attempts >= self._max_attempts:
            await self._dead_letter(raw, f"crash_max_attempts={attempts}")
            await self._r.delete(crash_key)
            await self._notify_dead_letter(task_id)
        else:
            logger.info(
                "work-loop: crash recovery requeue task=%s attempt=%d/%d",
                task_id,
                attempts,
                self._max_attempts,
            )
            await self._notify_crash_retry(task_id)
            await self._r.publish(TASKS_CHANNEL, raw)

    async def _notify_dead_letter(self, task_id: str) -> None:
        """POST /dispatcher/task_dead_letter to mark DB row. Fail-open."""
        import httpx  # noqa: PLC0415

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self._dispatcher_url}/dispatcher/task_dead_letter",
                    json={"task_id": task_id},
                )
        except Exception:  # noqa: BLE001
            logger.warning(
                "work-loop: task_dead_letter notify failed for task=%s",
                task_id,
                exc_info=True,
            )

    async def _notify_crash_retry(self, task_id: str) -> None:
        """POST /dispatcher/task_crash_retry to increment retry_count in DB. Fail-open."""
        import httpx  # noqa: PLC0415

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self._dispatcher_url}/dispatcher/task_crash_retry",
                    json={"task_id": task_id},
                )
        except Exception:  # noqa: BLE001
            logger.warning(
                "work-loop: task_crash_retry notify failed for task=%s",
                task_id,
                exc_info=True,
            )

    async def reconcile_all(self) -> int:
        """Reconcile every tenant with a live counter (SCAN). Returns total reclaimed.

        Drives the periodic crash-recovery sweep without a caller-maintained
        tenant list: the `active_spawns:{tenant}` keys ARE the active-tenant set.
        """
        total = 0
        seen: set[str] = set()
        async for key in self._r.scan_iter(match=f"{_active_key('')}*"):
            tenant_id = key.rsplit(":", 1)[-1]
            if tenant_id and tenant_id not in seen:
                seen.add(tenant_id)
                total += await self.reconcile(tenant_id)
        return total

    async def run(self) -> None:  # pragma: no cover — long-running loop, exercised via process_task
        """Subscribe to the tasks channel and process messages until cancelled."""
        pubsub = self._r.pubsub()
        await pubsub.subscribe(TASKS_CHANNEL)
        logger.info("work-loop consumer subscribed to %s", TASKS_CHANNEL)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                await self.process_task(message["data"])
            except Exception:  # noqa: BLE001 — one bad message never kills the loop
                logger.exception("work-loop: process_task crashed; continuing")
