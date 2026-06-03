"""Unit tests for scripts/agent_spawn_gate.py (KEI Agency_OS-03w4).

Two proof gates from KEI scope:
  (a) 7 simultaneous acquires → only 2 hold slots, 5 refused
      (Elliot counts as 0 — bypasses gate at the systemd layer)
  (b) Deliberators (aiden + max) ARE NOT permanently locked out
      when both worker slots are held — workers yield to deliberator
      markers on next acquire attempt; deliberators then acquire.

Implementation: fakeredis[lua] in-process. Per
feedback_declare_test_dep_extras: fakeredis[lua] is the explicit dep
required for `EVAL` support (lupa transitive). Declared in
requirements-dev.txt with the [lua] extra.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import fakeredis
import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "agent_spawn_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("agent_spawn_gate", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def gate(monkeypatch):
    module = _load_gate()
    fake = fakeredis.FakeStrictRedis(decode_responses=True, server=fakeredis.FakeServer())
    monkeypatch.setattr(module, "_client", lambda: fake)
    yield module, fake
    fake.flushall()


def _acquire(module, callsign: str) -> int:
    """Returns 0 on slot-acquired, 1 on refused."""
    return module.acquire(callsign)


def _release(module, callsign: str) -> int:
    return module.release(callsign)


# ─── Proof gate (a) ──────────────────────────────────────────────────────────


def test_proof_gate_a_seven_starts_only_two_active(gate):
    """7 worker starts attempted, only 2 active. 5 refused."""
    module, fake = gate
    workers = ["atlas", "nova", "orion", "scout", "atlas", "nova", "orion"]
    results = [_acquire(module, w) for w in workers]
    acquired = results.count(0)
    refused = results.count(1)
    assert acquired == module.N_MAX == 2, f"expected 2 acquired, got {acquired}"
    assert refused == 5, f"expected 5 refused, got {refused}"
    assert int(fake.get(module.ACTIVE_KEY)) == 2


def test_active_counter_decrements_on_release(gate):
    module, fake = gate
    _acquire(module, "atlas")
    _acquire(module, "nova")
    assert int(fake.get(module.ACTIVE_KEY)) == 2
    _release(module, "atlas")
    assert int(fake.get(module.ACTIVE_KEY)) == 1
    _release(module, "nova")
    assert int(fake.get(module.ACTIVE_KEY)) == 0


def test_release_does_not_go_negative(gate):
    module, fake = gate
    _release(module, "atlas")
    val = fake.get(module.ACTIVE_KEY)
    assert val is None or int(val) == 0


# ─── Proof gate (b) ──────────────────────────────────────────────────────────


def test_proof_gate_b_deliberators_acquire_after_worker_yield(gate):
    """Two workers hold slots. aiden + max arrive → refused but mark
    priority list. Workers' next acquire yields (refused). Workers
    release → deliberators acquire on retry. No permanent lockout."""
    module, fake = gate
    # 1. Two workers hold slots
    assert _acquire(module, "atlas") == 0
    assert _acquire(module, "nova") == 0
    assert int(fake.get(module.ACTIVE_KEY)) == 2

    # 2. Both deliberators arrive — refused, but leave priority markers
    assert _acquire(module, "aiden") == 1
    assert _acquire(module, "max") == 1
    pending = fake.lrange(module.PRIORITY_KEY, 0, -1)
    assert "aiden" in pending and "max" in pending

    # 3. A worker that arrives now must yield (priority list non-empty)
    assert _acquire(module, "orion") == 1, "worker did not yield to deliberator marker"
    assert int(fake.get(module.ACTIVE_KEY)) == 2  # unchanged — no extra slot consumed

    # 4. Workers release; deliberators retry and acquire
    _release(module, "atlas")
    _release(module, "nova")
    assert _acquire(module, "aiden") == 0
    assert _acquire(module, "max") == 0
    assert int(fake.get(module.ACTIVE_KEY)) == 2

    # 5. Deliberator markers cleaned up on successful acquire
    pending_after = fake.lrange(module.PRIORITY_KEY, 0, -1)
    assert "aiden" not in pending_after
    assert "max" not in pending_after


def test_deliberator_marker_cleared_on_release(gate):
    """LREM in release path keeps the priority list tidy if a
    deliberator's marker was never cleared by acquire (defensive)."""
    module, fake = gate
    fake.lpush(module.PRIORITY_KEY, "aiden")
    _release(module, "aiden")
    assert "aiden" not in fake.lrange(module.PRIORITY_KEY, 0, -1)


def test_worker_does_not_yield_when_no_deliberator_pending(gate):
    """Sanity: workers acquire freely when priority list is empty."""
    module, _fake = gate
    assert _acquire(module, "atlas") == 0
    assert _acquire(module, "nova") == 0


# ─── Cap correctness ─────────────────────────────────────────────────────────


def test_ttl_set_on_active_counter(gate):
    """ACTIVE_KEY TTL set after acquire — safety net if release misses."""
    module, fake = gate
    _acquire(module, "atlas")
    ttl = fake.ttl(module.ACTIVE_KEY)
    assert 0 < ttl <= module.ACTIVE_TTL_SECS


def test_priority_ttl_set_on_marker(gate):
    """PRIORITY_KEY TTL set when deliberator marker is pushed."""
    module, fake = gate
    _acquire(module, "atlas")
    _acquire(module, "nova")
    _acquire(module, "aiden")  # refused — marker pushed
    ttl = fake.ttl(module.PRIORITY_KEY)
    assert 0 < ttl <= module.PRIORITY_TTL_SECS


def test_deliberator_acquires_when_slot_available(gate):
    """If a slot is free, a deliberator acquires directly — no need
    to wait for any worker yield."""
    module, _fake = gate
    _acquire(module, "atlas")
    assert _acquire(module, "aiden") == 0  # 2 slots, 1 used → aiden gets the 2nd


def test_third_deliberator_marker_does_not_stack_extra_slots(gate):
    """Refused acquire must not leave the counter inflated."""
    module, fake = gate
    _acquire(module, "atlas")
    _acquire(module, "nova")
    assert _acquire(module, "aiden") == 1
    assert int(fake.get(module.ACTIVE_KEY)) == 2  # NOT 3
