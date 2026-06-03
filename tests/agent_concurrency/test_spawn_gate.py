"""Tests for scripts/agent_spawn_gate.py — the sync CLI / exit-hook over the
canonical concurrency_cap lib (Agency_OS-03w4).

The reservation/proof-gate semantics are proven against the async gate in
test_concurrency_cap.py. Here we prove the SYNC wrapper (used by the agent
exit-hook + ops probes) shares the exact same Lua + reservation model via
fakeredis (sync, [lua]).
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
def gate():
    module = _load_gate()
    fake = fakeredis.FakeStrictRedis(decode_responses=True, server=fakeredis.FakeServer())
    yield module, fake
    fake.flushall()


def test_orchestrator_bypasses(gate):
    module, fake = gate
    assert module.acquire("elliot", client=fake) is True
    # No slot consumed for the orchestrator.
    from src.dispatcher.concurrency_cap import HOLDERS_KEY

    assert fake.zcard(HOLDERS_KEY) == 0


def test_worker_band_capped_sync(gate):
    module, fake = gate
    from src.dispatcher.concurrency_cap import WORKER_CAP

    granted = sum(module.acquire(f"wrk{i}", client=fake) for i in range(WORKER_CAP + 3))
    assert granted == WORKER_CAP


def test_deliberators_never_starved_sync(gate):
    module, fake = gate
    from src.dispatcher.concurrency_cap import WORKER_CAP

    for i in range(WORKER_CAP + 2):
        module.acquire(f"wrk{i}", client=fake)
    assert module.acquire("aiden", client=fake) is True
    assert module.acquire("max", client=fake) is True


def test_reviewers_coreside_sync(gate):
    module, fake = gate
    assert module.acquire("orion", "spec", client=fake) is True
    assert module.acquire("atlas", "safety", client=fake) is True


def test_release_frees_slot_sync(gate):
    module, fake = gate
    from src.dispatcher.concurrency_cap import WORKER_CAP

    for i in range(WORKER_CAP):
        assert module.acquire(f"wrk{i}", client=fake) is True
    assert module.acquire("late", client=fake) is False  # queued
    module.release("wrk0", client=fake)
    assert module.acquire("late", client=fake) is True


def test_release_orchestrator_noop(gate):
    module, fake = gate
    module.release("elliot", client=fake)  # must not error
