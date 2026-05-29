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


async def _noop_notify(_notice: wl.DeadLetterNotice) -> None:
    """Default test notify — keeps dead-letter tests off the live Slack relay."""
    return None


class _Notifier:
    """Records dead-letter notices for assertion."""

    def __init__(self) -> None:
        self.notices: list[wl.DeadLetterNotice] = []

    async def __call__(self, notice: wl.DeadLetterNotice) -> None:
        self.notices.append(notice)


def _consumer(r, spawner, ceiling: int, **kw) -> WorkLoopConsumer:
    kw.setdefault("notify_fn", _noop_notify)  # never shell out to slack_relay in tests
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


# --- dead-letter #ceo notification (Agency_OS-gl3v) -------------------


async def test_dead_letter_notifies_ceo_with_task_context():
    """Retry-exhaustion dead-letter fires a notice carrying id, title, attempts, error."""
    r, spawner = _redis(), _Spawner(result=False)  # every spawn fails
    notifier = _Notifier()
    c = _consumer(r, spawner, ceiling=5, notify_fn=notifier)
    await c.process_task(_msg("flaky", title="Refill domain pool"))
    assert len(notifier.notices) == 1
    n = notifier.notices[0]
    assert n.task_id == "flaky"
    assert n.title == "Refill domain pool"  # pulled from spawn_kwargs.title
    assert n.attempts == 3  # exhausted max_attempts
    assert "3 attempts" in n.error  # final cause carried, ≤200 chars


async def test_malformed_dead_letter_notifies_ceo():
    """A malformed (silently-dropped) task also alerts #ceo — attempts=0."""
    r, spawner = _redis(), _Spawner()
    notifier = _Notifier()
    c = _consumer(r, spawner, ceiling=5, notify_fn=notifier)
    assert await c.process_task("not-json{") == "deadletter:malformed"
    assert len(notifier.notices) == 1
    n = notifier.notices[0]
    assert n.task_id == "unknown"
    assert n.attempts == 0
    assert n.error == "malformed"


async def test_dead_letter_notification_is_fail_open():
    """A notifier that raises must NOT block the dead-letter side effects."""

    async def _boom(_notice: wl.DeadLetterNotice) -> None:
        raise RuntimeError("slack down")

    r, spawner = _redis(), _Spawner(result=False)
    c = _consumer(r, spawner, ceiling=5, notify_fn=_boom)
    await c.process_task(_msg("flaky"))  # must not raise despite notifier blowing up
    assert await r.lrange(wl.DEADLETTER_KEY, 0, -1) == [_msg("flaky")]  # dead-letter still happened
    assert await r.get(wl._active_key("t1")) == "0"  # slot still released


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


# --- crash recovery (Agency_OS-avii) -----------------------------------


async def test_reconcile_requeues_crashed_task():
    """When lease expires, reconcile re-publishes the task to the channel."""
    r, spawner = _redis(), _Spawner()
    c = _consumer(r, spawner, ceiling=1)
    await c.process_task(_msg("task-1"))
    assert await r.get(wl._active_key("t1")) == "1"
    # Simulate crash: delete the lease key (TTL expiry)
    await r.delete(wl._lease_key("t1", "task-1"))
    # Verify task_raw was stored
    assert await r.get(wl._task_raw_key("t1", "task-1")) is not None
    # Stub out the notify helpers so no HTTP calls are made
    async def _noop_retry(_task_id: str) -> None:
        pass

    c._notify_crash_retry = _noop_retry
    # Reconcile should reclaim + re-queue via publish
    published: list[tuple[str, str]] = []
    original_publish = r.publish

    async def _capture_publish(channel: str, data: str) -> int:
        published.append((channel, data))
        return await original_publish(channel, data)

    r.publish = _capture_publish
    reclaimed = await c.reconcile("t1")
    assert reclaimed == 1
    assert await r.get(wl._active_key("t1")) == "0"
    assert len(published) == 1
    assert published[0][0] == wl.TASKS_CHANNEL
    # crash_attempts counter should be 1
    assert int(await r.get("keiracom:tasks:crash_attempts:task-1")) == 1


async def test_reconcile_dead_letters_after_max_attempts():
    """After max_attempts crashes, task goes to dead-letter."""
    r = _redis()
    notified: list[str] = []

    async def fake_notify_dl(task_id: str) -> None:
        notified.append(task_id)

    async def fake_notify_retry(_task_id: str) -> None:
        pass

    c = WorkLoopConsumer(valkey=r, spawn_fn=_Spawner(), ceiling_fn=_ceiling(5), max_attempts=3)
    c._notify_dead_letter = fake_notify_dl
    c._notify_crash_retry = fake_notify_retry
    # Pre-set crash attempts to 2 (next crash = 3 = max)
    await r.set("keiracom:tasks:crash_attempts:task-x", "2")
    await r.set(wl._task_raw_key("t1", "task-x"), _msg("task-x"))
    await c._handle_crashed_task("task-x", _msg("task-x"))
    # Should be dead-lettered
    dl = await r.lrange(wl.DEADLETTER_KEY, 0, -1)
    assert len(dl) == 1
    assert "task-x" in dl[0]
    assert notified == ["task-x"]
    # crash_attempts key should be deleted
    assert await r.exists("keiracom:tasks:crash_attempts:task-x") == 0


async def test_release_slot_deletes_task_raw():
    """release_slot cleans up the task_raw key."""
    r = _redis()
    c = WorkLoopConsumer(valkey=r, spawn_fn=_Spawner(), ceiling_fn=_ceiling(2))
    await c.process_task(_msg("task-1"))
    assert await r.exists(wl._task_raw_key("t1", "task-1")) == 1
    await c.release_slot("t1", "task-1")
    assert await r.exists(wl._task_raw_key("t1", "task-1")) == 0


async def test_reconcile_no_orphan_on_raw_miss():
    """If task_raw is missing (reconcile-miss), no orphaned slot is left."""
    r = _redis()
    c = WorkLoopConsumer(valkey=r, spawn_fn=_Spawner(), ceiling_fn=_ceiling(2))
    await c.process_task(_msg("task-1"))
    # Simulate lease expiry AND missing task_raw (e.g. DEL race)
    await r.delete(wl._lease_key("t1", "task-1"))
    await r.delete(wl._task_raw_key("t1", "task-1"))
    reclaimed = await c.reconcile("t1")
    assert reclaimed == 1
    assert await r.get(wl._active_key("t1")) == "0"
    # Nothing dead-lettered since raw was missing
    assert await r.llen(wl.DEADLETTER_KEY) == 0


# --- capacity alert ----------------------------------------------------


async def test_capacity_alert_fires_at_70_percent(caplog):
    r, spawner = _redis(), _Spawner()
    c = _consumer(r, spawner, ceiling=10)
    with caplog.at_level(logging.WARNING, logger="src.keiracom_system.work_loop.consumer"):
        for i in range(7):  # 7/10 == 70%
            await c.process_task(_msg(f"task-{i}"))
    assert any("WORK-LOOP CAPACITY ALERT" in rec.message for rec in caplog.records)
