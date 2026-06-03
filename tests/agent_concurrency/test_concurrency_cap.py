"""Proof tests for src/dispatcher/concurrency_cap.py (Agency_OS-03w4).

Runs the REAL acquire/release Lua against fakeredis (async) — no live
Valkey. These are the PROOF GATE for ceo:decision:concurrency_cap_2026-06-04:

  (a) RAM bound — the cap holds: at most GATED concurrent gated sessions,
      partitioned by reserved per-role caps that sum to GATED.
  (b) Stage-pair guard — the cap NEVER starves the 2 deliberators or the
      2 reviewers, even when workers saturate. This is the proof-gate
      NEGATIVE made impossible by the reservation partition.
  (c) Full chain completes under the cap with no role starved.

fakeredis[lua] (declared in requirements-dev.txt) supplies EVAL.
"""

from __future__ import annotations

import pytest
from fakeredis import aioredis

from src.dispatcher.concurrency_cap import (
    DELIB_CAP,
    GATED,
    N_TOTAL,
    REVIEW_CAP,
    WORKER_CAP,
    ConcurrencyDecision,
    ConcurrencyGate,
    classify,
)


def _redis():
    return aioredis.FakeRedis(decode_responses=True)


def _gate(client=None):
    return ConcurrencyGate(valkey_client=client or _redis())


async def _granted(gate, callsign, role_hint=None) -> bool:
    res = await gate.acquire(callsign=callsign, role_hint=role_hint)
    return res.decision == ConcurrencyDecision.GRANTED


# ─── Reservation partition sanity ────────────────────────────────────────────


def test_caps_partition_the_gated_band():
    """The reserved per-role caps must SUM to the gated band — this is the
    invariant that makes the stage-pair guarantee hold by construction."""
    assert DELIB_CAP + REVIEW_CAP + WORKER_CAP == GATED
    assert GATED == N_TOTAL - 1  # Elliot bypasses but is counted


def test_classify_roles():
    assert classify("elliot") == "bypass"
    assert classify("aiden") == "deliberator"
    assert classify("max") == "deliberator"
    assert classify("orion", "spec") == "reviewer"
    assert classify("atlas", "safety") == "reviewer"
    assert classify("orion", "review") == "reviewer"
    assert classify("nova") == "worker"
    assert classify("scout", None) == "worker"


# ─── Proof gate (a): the cap holds (RAM bound) ───────────────────────────────


@pytest.mark.asyncio
async def test_proof_a_orchestrator_always_bypasses():
    gate = _gate()
    # Elliot never consumes a gated slot, no matter how many times.
    for _ in range(5):
        assert await _granted(gate, "elliot")


@pytest.mark.asyncio
async def test_proof_a_worker_band_capped():
    """Workers beyond WORKER_CAP are refused (queued) — the band is hard."""
    gate = _gate()
    granted = 0
    for i in range(WORKER_CAP + 5):
        if await _granted(gate, f"worker{i}"):
            granted += 1
    assert granted == WORKER_CAP


@pytest.mark.asyncio
async def test_proof_a_total_never_exceeds_gated():
    """Saturate every role; total gated holders must never exceed GATED."""
    gate = _gate()
    # 2 deliberators + many reviewers + many workers all rush at once.
    callsigns = (
        [("aiden", None), ("max", None)]
        + [(f"rev{i}", "review") for i in range(5)]
        + [(f"wrk{i}", None) for i in range(5)]
    )
    granted = [cs for cs, hint in callsigns if await _granted(gate, cs, hint)]
    assert len(granted) <= GATED
    # And exactly the reserved partition is filled.
    assert len(granted) == DELIB_CAP + REVIEW_CAP + WORKER_CAP


# ─── Proof gate (b): stage-pairs are NEVER starved (the NEGATIVE) ─────────────


@pytest.mark.asyncio
async def test_proof_b_workers_cannot_starve_deliberators():
    """Workers saturate first; BOTH deliberators must still acquire."""
    gate = _gate()
    # Fill the worker band to its cap.
    for i in range(WORKER_CAP + 3):
        await gate.acquire(callsign=f"wrk{i}")
    # Both deliberators arrive AFTER workers saturated — must still get in.
    assert await _granted(gate, "aiden")
    assert await _granted(gate, "max")


@pytest.mark.asyncio
async def test_proof_b_workers_cannot_starve_reviewers():
    """Workers saturate first; 2 parallel reviewers must still co-reside."""
    gate = _gate()
    for i in range(WORKER_CAP + 3):
        await gate.acquire(callsign=f"wrk{i}")
    assert await _granted(gate, "orion", "spec")
    assert await _granted(gate, "atlas", "safety")


@pytest.mark.asyncio
async def test_proof_b_deliberators_and_reviewers_coreside():
    """The 2 deliberators AND the 2 reviewers all hold slots simultaneously —
    the exact co-residency the proof gate demands, regardless of order."""
    gate = _gate()
    assert await _granted(gate, "orion", "review")  # reviewer first
    assert await _granted(gate, "aiden")  # deliberator
    assert await _granted(gate, "atlas", "review")  # reviewer
    assert await _granted(gate, "max")  # deliberator
    # All four reserved holders are live at once.


# ─── Proof gate (c): full chain completes under the cap ──────────────────────


@pytest.mark.asyncio
async def test_proof_c_full_chain_completes_no_role_starved():
    """Simulate the v1 chain under the cap: worker builds, then the dual-concur
    deliberators + the 2 parallel reviewers all run. No role is ever starved."""
    gate = _gate()
    # Stage: worker builds.
    assert await _granted(gate, "nova")  # worker slot
    # Stage: dual-concur — both deliberators must be reachable.
    assert await _granted(gate, "aiden")
    assert await _granted(gate, "max")
    # Stage: parallel review — both reviewers must co-reside.
    assert await _granted(gate, "orion", "spec")
    assert await _granted(gate, "atlas", "safety")
    # Chain complete: 1 worker + 2 deliberators + 2 reviewers = 5 = GATED.
    # A second worker now correctly QUEUES (requeue-not-drop), not starving
    # anyone above it.
    res = await gate.acquire(callsign="scout")
    assert res.decision == ConcurrencyDecision.QUEUE


# ─── Release frees the band; queued worker then acquires ─────────────────────


@pytest.mark.asyncio
async def test_release_frees_slot_for_queued_worker():
    gate = _gate()
    for i in range(WORKER_CAP):
        assert await _granted(gate, f"wrk{i}")
    # Next worker queues.
    assert (await gate.acquire(callsign="late")).decision == ConcurrencyDecision.QUEUE
    # Release one held worker → the queued worker can now acquire.
    await gate.release(callsign="wrk0")
    assert await _granted(gate, "late")


@pytest.mark.asyncio
async def test_idempotent_reacquire_does_not_double_count():
    """Re-acquiring while already holding refreshes the lease, no extra slot."""
    gate = _gate()
    assert await _granted(gate, "aiden")
    assert await _granted(gate, "aiden")  # same holder — idempotent
    # max (the other deliberator) must still fit.
    assert await _granted(gate, "max")


@pytest.mark.asyncio
async def test_release_is_idempotent_and_safe_when_not_held():
    gate = _gate()
    await gate.release(callsign="ghost")  # never held — must not error
    assert await _granted(gate, "nova")


# ─── TTL reap: a missed release is reclaimed ─────────────────────────────────


@pytest.mark.asyncio
async def test_expired_holder_is_reaped_on_next_acquire():
    """A holder whose lease expired (release missed) is reaped so its slot is
    reclaimed on the next acquire — the safety net behind release()."""
    clock = {"t": 1000}
    client = _redis()
    gate = ConcurrencyGate(valkey_client=client, ttl_seconds=10, now_provider=lambda: clock["t"])
    # Fill worker band at t=1000 (expires at 1010).
    for i in range(WORKER_CAP):
        assert await _granted(gate, f"wrk{i}")
    assert (await gate.acquire(callsign="late")).decision == ConcurrencyDecision.QUEUE
    # Advance past the lease — the stale worker is reaped on next acquire.
    clock["t"] = 2000
    assert await _granted(gate, "late")


# ─── Fail-open on Valkey error ───────────────────────────────────────────────


class _BrokenRedis:
    async def eval(self, *_a, **_k):
        raise ConnectionError("valkey down")


@pytest.mark.asyncio
async def test_fail_open_grants_on_valkey_error():
    """A Valkey blip must NOT freeze the fleet — fail-open GRANTED + alert."""
    alerts: list[dict] = []
    gate = ConcurrencyGate(valkey_client=_BrokenRedis(), log_emitter=alerts.append)
    res = await gate.acquire(callsign="nova")
    assert res.decision == ConcurrencyDecision.GRANTED
    assert any(a.get("kind") == "concurrency_cap_fail_open" for a in alerts)
