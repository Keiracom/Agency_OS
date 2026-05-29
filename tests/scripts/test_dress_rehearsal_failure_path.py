"""Failure-path dress-rehearsal tests (Agency_OS-avii).

Viktor's chain test (Agency_OS-jb4e / #1279) is happy-path only. This adds the
FAILURE-PATH the dress rehearsal must witness, driven END-TO-END against the REAL
work-loop consumer (fakeredis — no live Valkey) plus the harness that witnesses
the crash / dead_letter runs:

  1. crash mid-task -> 5-min lease lapses -> reconcile() reclaims the slot ->
     retry counter increments -> dead-letter after 3 attempts.
  2. reconcile-miss (lease still alive / already released) -> NO orphan slot.
  3. the path STARTS at the SLACK seam (public.tasks row -> kei45 trigger ->
     keiracom:tasks:available), NOT at the Chat hop.
  4. the with-memory (recall) run MUST ASSERT recall >=1 relevant atom — a run
     that surfaces 0 atoms FAILS the gate (not just "no error").

#1310 unit-tests the individual mechanics; avii proves the integrated dress-
rehearsal failure path and binds the harness seam + spec constants to the live
consumer so an impl drift fails this gate.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from fakeredis import aioredis

from src.keiracom_system.work_loop import consumer as wl
from src.keiracom_system.work_loop.consumer import WorkLoopConsumer

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "cutover" / "full_chain_dress_rehearsal.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("_dr_failure_path", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # register before exec for dataclass annotation resolution
    spec.loader.exec_module(mod)
    return mod


m = _load_harness()

TENANT = "t-avii"


# ─── real-consumer harness (fakeredis; mirrors #1310 patterns) ────────────────


def _redis():
    return aioredis.FakeRedis(decode_responses=True)


def _ceiling(n):
    async def _f(_tenant_id):
        return n

    return _f


class _Spawner:
    """Records spawns; `result` is a bool or fn(attempt_count)->bool."""

    def __init__(self, result=True):
        self.calls: list[str] = []
        self.result = result

    async def __call__(self, task: wl.Task) -> bool:
        self.calls.append(task.task_id)
        return self.result(len(self.calls)) if callable(self.result) else self.result


def _slack_seam_message(task_id: str, tenant_id: str = TENANT, **spawn_kwargs) -> str:
    """The task message exactly as the SLACK->task-row->kei45-trigger seam
    publishes it to keiracom:tasks:available (consumer channel) — the failure
    path's origin, NOT a Chat-hop call. Shape matches consumer._parse."""
    return json.dumps(
        {
            "task_id": task_id,
            "tenant_id": tenant_id,
            "backend": "container",
            "spawn_kwargs": spawn_kwargs,
        }
    )


def _consumer(r, spawner, ceiling: int = 5, **kw) -> WorkLoopConsumer:
    return WorkLoopConsumer(valkey=r, spawn_fn=spawner, ceiling_fn=_ceiling(ceiling), **kw)


# ─── harness RunResult builders ───────────────────────────────────────────────

_GOV = {"callsign_tagged": True, "concur_count": 2, "no_linear_write": True, "claim_observed": True}


def _hop(name, *, fired=True, bypass=False, cit="C-1", score=0.8):
    return m.HopTrace(
        hop=name,
        agent=name,
        fired=fired,
        bypass_rerank=bypass,
        top_citation_id=cit,
        top_score=score,
    )


def _hops(useful: bool):
    if useful:
        return tuple(_hop(h) for h in m.HOP_AGENTS_DEFAULT)
    return tuple(_hop(h, bypass=True, cit=None, score=0.0) for h in m.HOP_AGENTS_DEFAULT)


def _run(*, mode, active=True, useful=True, recovered=True, dead_lettered=False, worker_retries=0):
    return m.RunResult(
        kei="Agency_OS-avii",
        recall_active=active,
        hop_traces=_hops(useful),
        run_mode=mode,
        pr_number=9,
        pr_merged=True,
        ci_passed=True,
        governance=dict(_GOV),
        worker_retries=worker_retries,
        recovered=recovered,
        dead_lettered=dead_lettered,
    )


def _cold_run():
    return _run(mode="cold", active=False, useful=False, worker_retries=1)


# ─── item 3 — the path STARTS at the SLACK seam, not Chat ─────────────────────


def test_failure_path_starts_at_slack_seam_not_chat():
    # The harness seed is an INSERT into public.tasks — the row the kei45 trigger
    # turns into a keiracom:tasks:available publish (the SLACK-origin leg), NOT a
    # Chat hop. The consumer subscribes to that SAME channel.
    assert "public.tasks" in m.build_seed_sql()
    assert m.TASKS_CHANNEL == wl.TASKS_CHANNEL == "keiracom:tasks:available"
    # the seam message parses as a valid task — origin is the task row, not Chat.
    task = wl._parse(_slack_seam_message("avii-slack-1"))
    assert task is not None and task.task_id == "avii-slack-1"
    # "chat" is the FIRST happy-path hop; the failure path must NOT begin there.
    assert m.HOP_AGENTS_DEFAULT[0] == "chat"


# ─── spec constants pinned to the live consumer (drift guard) ─────────────────


def test_spec_constants_match_live_consumer():
    # The avii spec names "5-min lease" and "dead-letter after 3" — pin them to
    # the live consumer so an impl drift fails this gate.
    assert wl.DEFAULT_LEASE_TTL_S == 300  # 5-minute slot lease
    assert wl.DEFAULT_MAX_ATTEMPTS == 3  # dead-letter after 3 attempts


# ─── item 1a — crash -> lease lapse -> reconcile reclaims -> loop resumes ──────


async def test_crash_recovery_reclaims_slot_and_loop_resumes():
    r, spawner = _redis(), _Spawner(result=True)
    c = _consumer(r, spawner, ceiling=1)
    # START AT SLACK SEAM: tasks arrive on keiracom:tasks:available.
    assert await c.process_task(_slack_seam_message("avii-crash")) == "spawned"
    await c.process_task(_slack_seam_message("avii-next"))  # overflowed at ceiling 1
    assert spawner.calls == ["avii-crash"]
    assert await r.exists(wl._lease_key(TENANT, "avii-crash")) == 1
    # CRASH mid-task: no heartbeat -> the 5-min lease TTL lapses (simulated).
    await r.delete(wl._lease_key(TENANT, "avii-crash"))
    # RECONCILE reclaims the orphaned slot AND release pops overflow -> loop resumes.
    assert await c.reconcile(TENANT) == 1
    assert spawner.calls == ["avii-crash", "avii-next"]  # queued task now spawns
    assert await r.get(wl._active_key(TENANT)) == "1"  # one live (the resumed task), not orphaned


# ─── item 1b — retry counter increments -> dead-letter after 3 attempts ───────


async def test_retry_increments_then_dead_letters_after_three_attempts():
    r, spawner = _redis(), _Spawner(result=False)  # every spawn attempt fails
    c = _consumer(r, spawner, ceiling=5)
    # START AT SLACK SEAM.
    await c.process_task(_slack_seam_message("avii-flaky"))
    # retry counter increments via requeue+pop until max_attempts (3), then DLQ.
    assert spawner.calls == ["avii-flaky", "avii-flaky", "avii-flaky"]
    assert await r.lrange(wl.DEADLETTER_KEY, 0, -1) == [_slack_seam_message("avii-flaky")]
    assert await r.get(wl._active_key(TENANT)) == "0"  # slot released, not orphaned
    assert await r.llen(wl._overflow_key(TENANT)) == 0  # nothing stranded
    assert await r.exists(wl._attempts_key("avii-flaky")) == 0  # attempts counter cleaned up
    # the harness witnesses a dead_letter run as routed (P4) — not a hang.
    assert m.classify_failure_path(_run(mode="dead_letter", dead_lettered=True)) is None


# ─── item 2 — reconcile-miss -> NO orphan locked slot ─────────────────────────


async def test_reconcile_miss_when_lease_alive_leaves_no_orphan():
    r, spawner = _redis(), _Spawner(result=True)
    c = _consumer(r, spawner, ceiling=5)
    await c.process_task(_slack_seam_message("avii-live"))
    # lease still ALIVE (agent heartbeating) -> reconcile must reclaim NOTHING.
    assert await r.exists(wl._lease_key(TENANT, "avii-live")) == 1
    assert await c.reconcile(TENANT) == 0  # reconcile-miss
    assert await r.get(wl._active_key(TENANT)) == "1"  # slot intact, no spurious reclaim
    assert await r.exists(wl._lock_key("avii-live")) == 1  # lock not orphaned/dropped


async def test_double_release_is_idempotent_no_negative_counter():
    r, spawner = _redis(), _Spawner(result=True)
    c = _consumer(r, spawner, ceiling=5)
    await c.process_task(_slack_seam_message("avii-once"))
    await c.release_slot(TENANT, "avii-once")  # clean exit
    assert await r.get(wl._active_key(TENANT)) == "0"
    # a reconcile/release racing the same already-freed task must NOT drive the
    # counter negative or leave an orphan (RELEASE_LUA SREM guard).
    await c.release_slot(TENANT, "avii-once")
    assert await r.get(wl._active_key(TENANT)) == "0"  # floored, never negative
    assert await c.reconcile(TENANT) == 0  # nothing left to reclaim


# ─── item 4 — with-memory run MUST assert recall >=1 atom (else FAIL) ─────────


def test_with_memory_run_fails_when_recall_returns_zero_atoms():
    # recall-active arm where every hop fired but bypassed / surfaced nothing.
    barren = _run(mode="recall", active=True, useful=False)
    ok, n = m.assert_recall_returned_atom(barren)
    assert ok is False and n == 0
    out = m.evaluate_gate(barren, _cold_run())
    assert out.passed is False
    assert any("0 relevant atoms" in r for r in out.reasons)  # FAIL, not silent pass


def test_with_memory_run_passes_when_recall_returns_atom():
    ok, n = m.assert_recall_returned_atom(_run(mode="recall", useful=True))
    assert ok is True and n >= 1


# ─── harness failure-path classifier (ties §9 modes to observed runs) ─────────


def test_classify_failure_path_flags_unrecovered_crash():
    assert m.classify_failure_path(_run(mode="crash", recovered=False)) == "crash_unrecovered"
    assert m.classify_failure_path(_run(mode="crash", recovered=True)) is None
    assert "crash_unrecovered" in m.FAILURE_MODES


def test_classify_failure_path_flags_not_dead_lettered():
    assert (
        m.classify_failure_path(_run(mode="dead_letter", dead_lettered=False))
        == "not_dead_lettered"
    )
    assert m.classify_failure_path(_run(mode="dead_letter", dead_lettered=True)) is None
    assert "not_dead_lettered" in m.FAILURE_MODES


def test_classify_failure_path_ignores_non_failure_runs():
    assert m.classify_failure_path(_run(mode="cold", active=False, useful=False)) is None
    assert m.classify_failure_path(_run(mode="recall")) is None
