"""Tests for the tier-gated work-loop consumer.

Runs the REAL admit/release Lua against fakeredis (async) — no live Valkey. The
spawn POST + ceiling lookup are injected (a recording spawner + a fixed ceiling).
"""

from __future__ import annotations

import json
import logging

from fakeredis import aioredis

from src.keiracom_system.work_loop import consumer as wl
from src.keiracom_system.work_loop.consumer import WorkLoopConsumer


def _redis():
    return aioredis.FakeRedis(decode_responses=True)


def _ceiling(n: int):
    async def _f(_tenant_id: str) -> int:
        return n

    return _f


class _Spawner:
    """Records spawn calls; `result` is a bool or fn(attempt_count)->bool."""

    def __init__(self, result=True):
        self.calls: list[str] = []
        self.result = result

    async def __call__(self, task: wl.Task) -> bool:
        self.calls.append(task.task_id)
        return self.result(len(self.calls)) if callable(self.result) else self.result


def _msg(task_id: str, tenant_id: str = "t1", **spawn_kwargs) -> str:
    return json.dumps(
        {
            "task_id": task_id,
            "tenant_id": tenant_id,
            "backend": "container",
            "spawn_kwargs": spawn_kwargs,
        }
    )


def _consumer(r, spawner, ceiling: int, **kw) -> WorkLoopConsumer:
    return WorkLoopConsumer(valkey=r, spawn_fn=spawner, ceiling_fn=_ceiling(ceiling), **kw)


# --- admission + ceiling ----------------------------------------------


async def test_admit_under_ceiling_spawns():
    r, spawner = _redis(), _Spawner()
    c = _consumer(r, spawner, ceiling=2)
    assert await c.process_task(_msg("task-1")) == "spawned"
    assert spawner.calls == ["task-1"]
    assert await r.get(wl._active_key("t1")) == "1"
    assert await r.exists(wl._lease_key("t1", "task-1")) == 1


async def test_at_ceiling_overflows_and_does_not_spawn():
    r, spawner = _redis(), _Spawner()
    c = _consumer(r, spawner, ceiling=1)
    assert await c.process_task(_msg("task-1")) == "spawned"
    assert await c.process_task(_msg("task-2")) == "overflow"
    assert spawner.calls == ["task-1"]  # task-2 never spawned
    assert await r.lrange(wl._overflow_key("t1"), 0, -1) == [_msg("task-2")]
    assert await r.get(wl._active_key("t1")) == "1"


async def test_release_pops_overflow_and_spawns_next():
    r, spawner = _redis(), _Spawner()
    c = _consumer(r, spawner, ceiling=1)
    await c.process_task(_msg("task-1"))
    await c.process_task(_msg("task-2"))  # overflowed
    await c.release_slot("t1", "task-1")  # exit_cycle callback
    assert spawner.calls == ["task-1", "task-2"]  # next popped + spawned
    assert await r.get(wl._active_key("t1")) == "1"  # one slot freed, one re-taken
    assert await r.llen(wl._overflow_key("t1")) == 0


async def test_atomic_admit_respects_ceiling_exactly():
    r = _redis()
    c = _consumer(r, _Spawner(), ceiling=3)
    results = [await c._admit(wl._parse(_msg(f"t{i}")), 3) for i in range(4)]
    assert results == [1, 2, 3, -1]  # 4th rejected at ceiling


# --- distributed lock --------------------------------------------------


async def test_duplicate_task_id_is_locked_out():
    r, spawner = _redis(), _Spawner()
    c = _consumer(r, spawner, ceiling=5)
    assert await c.process_task(_msg("dup")) == "spawned"
    assert await c.process_task(_msg("dup")) == "duplicate:locked"
    assert spawner.calls == ["dup"]  # spawned exactly once


# --- dead-letter + requeue --------------------------------------------


async def test_dead_letter_after_three_failed_spawns():
    r, spawner = _redis(), _Spawner(result=False)  # every spawn fails
    c = _consumer(r, spawner, ceiling=5)
    await c.process_task(_msg("flaky"))
    assert spawner.calls == ["flaky", "flaky", "flaky"]  # 3 attempts via requeue+pop
    assert await r.lrange(wl.DEADLETTER_KEY, 0, -1) == [_msg("flaky")]
    assert await r.get(wl._active_key("t1")) == "0"  # slot released
    assert await r.llen(wl._overflow_key("t1")) == 0


async def test_malformed_message_dead_letters_without_spawn():
    r, spawner = _redis(), _Spawner()
    c = _consumer(r, spawner, ceiling=5)
    assert await c.process_task("not-json{") == "deadletter:malformed"
    assert spawner.calls == []
    assert await r.lrange(wl.DEADLETTER_KEY, 0, -1) == ["not-json{"]


# --- crash recovery (lease TTL) ---------------------------------------


async def test_reconcile_releases_expired_lease():
    r, spawner = _redis(), _Spawner()
    c = _consumer(r, spawner, ceiling=5)
    await c.process_task(_msg("crashed"))
    await r.delete(wl._lease_key("t1", "crashed"))  # simulate TTL lapse (no heartbeat)
    reclaimed = await c.reconcile("t1")
    assert reclaimed == 1
    assert await r.get(wl._active_key("t1")) == "0"  # slot reclaimed


async def test_renew_lease_keeps_slot_alive():
    r = _redis()
    c = _consumer(r, _Spawner(), ceiling=5, lease_ttl_s=120)
    await c.process_task(_msg("live"))
    await c.renew_lease("t1", "live")
    ttl = await r.ttl(wl._lease_key("t1", "live"))
    assert ttl > 0  # lease still leased after heartbeat


# --- capacity alert ----------------------------------------------------


async def test_capacity_alert_fires_at_70_percent(caplog):
    r, spawner = _redis(), _Spawner()
    c = _consumer(r, spawner, ceiling=10)
    with caplog.at_level(logging.WARNING, logger="src.keiracom_system.work_loop.consumer"):
        for i in range(7):  # 7/10 == 70%
            await c.process_task(_msg(f"task-{i}"))
    assert any("WORK-LOOP CAPACITY ALERT" in rec.message for rec in caplog.records)
