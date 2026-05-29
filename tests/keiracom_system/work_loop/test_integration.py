"""Tests for the work-loop dispatcher integration (Agency_OS-innu).

release_on_exit + reconcile_loop are driven against a fakeredis-backed real
WorkLoopConsumer (injected via set_consumer) so the slot accounting is exercised
end-to-end. Fail-open paths use a consumer stub that raises.
"""

from __future__ import annotations

import json

import pytest
from fakeredis import aioredis

from src.keiracom_system.work_loop import consumer as wl
from src.keiracom_system.work_loop import integration as integ
from src.keiracom_system.work_loop.consumer import WorkLoopConsumer


@pytest.fixture(autouse=True)
def _reset_singleton():
    yield
    integ.set_consumer(None)


def _ceiling(n: int):
    async def _f(_t: str) -> int:
        return n

    return _f


class _Spawner:
    def __init__(self):
        self.calls: list[str] = []

    async def __call__(self, task: wl.Task) -> bool:
        self.calls.append(task.task_id)
        return True


def _msg(task_id: str, tenant_id: str = "tnt") -> str:
    return json.dumps(
        {"task_id": task_id, "tenant_id": tenant_id, "backend": "container", "spawn_kwargs": {}}
    )


def _fakeredis_consumer(spawner) -> WorkLoopConsumer:
    return WorkLoopConsumer(
        valkey=aioredis.FakeRedis(decode_responses=True), spawn_fn=spawner, ceiling_fn=_ceiling(1)
    )


async def test_release_on_exit_frees_slot_and_pops_overflow():
    spawner = _Spawner()
    c = _fakeredis_consumer(spawner)
    integ.set_consumer(c)
    await c.process_task(_msg("k1"))  # spawned (ceiling 1)
    await c.process_task(_msg("k2"))  # overflowed
    await integ.release_on_exit("tnt", "k1")  # dispatcher exit hook
    assert spawner.calls == ["k1", "k2"]  # next popped + spawned
    assert await c._r.get(wl._active_key("tnt")) == "1"


async def test_release_on_exit_is_failopen():
    class _Boom:
        async def release_slot(self, *_a):
            raise RuntimeError("valkey down")

    integ.set_consumer(_Boom())
    await integ.release_on_exit("tnt", "k1")  # must not raise


async def test_reconcile_loop_one_iteration_reclaims_expired_lease():
    spawner = _Spawner()
    c = _fakeredis_consumer(spawner)
    integ.set_consumer(c)
    await c.process_task(_msg("crashed"))
    await c._r.delete(wl._lease_key("tnt", "crashed"))  # lease lapsed (no heartbeat)
    await integ.reconcile_loop(interval_s=0, iterations=1)
    assert await c._r.get(wl._active_key("tnt")) == "0"  # reclaimed


async def test_reconcile_loop_is_failopen():
    class _Boom:
        async def reconcile_all(self):
            raise RuntimeError("scan failed")

    integ.set_consumer(_Boom())
    await integ.reconcile_loop(interval_s=0, iterations=1)  # must not raise


async def test_reconcile_all_scans_multiple_tenants():
    spawner = _Spawner()
    c = WorkLoopConsumer(
        valkey=aioredis.FakeRedis(decode_responses=True), spawn_fn=spawner, ceiling_fn=_ceiling(5)
    )
    await c.process_task(_msg("a1", "tenant-A"))
    await c.process_task(_msg("b1", "tenant-B"))
    await c._r.delete(wl._lease_key("tenant-A", "a1"))
    await c._r.delete(wl._lease_key("tenant-B", "b1"))
    reclaimed = await c.reconcile_all()
    assert reclaimed == 2  # both tenants swept via SCAN
