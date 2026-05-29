"""Tests for the work-loop producer bridge (Agency_OS-nkc0).

`task_event_to_message` is pure (deterministic). The publish path runs against
fakeredis with a subscriber. Payloads mirror the kei45_emit_task_event shape
(the fake PG-notify source).
"""

from __future__ import annotations

import json

import pytest
from fakeredis import aioredis

from src.keiracom_system.work_loop import bridge
from src.keiracom_system.work_loop.consumer import TASKS_CHANNEL


def _new_available(task_id: str = "T-1", claimed_by: str | None = None) -> str:
    # Mirrors kei45_emit_task_event payload (migration 20260514_kei45_tasks_realtime.sql).
    return json.dumps(
        {
            "event_type": "new_available",
            "id": task_id,
            "title": "do the thing",
            "status": "available",
            "priority": "high",
            "claimed_by": claimed_by,
            "tags": ["build"],
            "op": "INSERT",
            "at": "now",
        }
    )


# --- mapping (pure) ----------------------------------------------------


def test_maps_new_available_to_consumer_message():
    d = json.loads(bridge.task_event_to_message(_new_available("T-1", "atlas"), "fleet-1"))
    assert d["task_id"] == "T-1"
    assert d["tenant_id"] == "fleet-1"
    assert d["backend"] == bridge.DEFAULT_BACKEND  # container
    assert d["spawn_kwargs"]["callsign"] == "atlas"  # from claimed_by
    assert d["spawn_kwargs"]["task_id"] == "T-1"


def test_callsign_defaults_to_worker_when_unclaimed():
    d = json.loads(bridge.task_event_to_message(_new_available("T-2", None), "f"))
    assert d["spawn_kwargs"]["callsign"] == bridge.DEFAULT_CALLSIGN  # worker


@pytest.mark.parametrize("event_type", ["claimed", "completed", "unclaimed", "other"])
def test_non_new_available_is_skipped(event_type):
    payload = json.dumps({"event_type": event_type, "id": "T-9"})
    assert bridge.task_event_to_message(payload, "f") is None


def test_missing_id_is_skipped():
    assert bridge.task_event_to_message(json.dumps({"event_type": "new_available"}), "f") is None


def test_unparseable_payload_is_skipped():
    assert bridge.task_event_to_message("not-json{", "f") is None


def test_accepts_dict_payload_and_stringifies_id():
    d = json.loads(bridge.task_event_to_message({"event_type": "new_available", "id": 7}, "f"))
    assert d["task_id"] == "7"


# --- publish (fakeredis) ----------------------------------------------


async def test_publish_new_available_lands_on_channel():
    r = aioredis.FakeRedis(decode_responses=True)
    ps = r.pubsub()
    await ps.subscribe(TASKS_CHANNEL)
    published = await bridge.publish_task_event(r, _new_available("T-5", "orion"), "fleet-1")
    assert published is True
    got = None
    for _ in range(5):
        m = await ps.get_message(timeout=1)
        if m and m.get("type") == "message":
            got = m
            break
    assert got is not None, "published message never arrived on the channel"
    body = json.loads(got["data"])
    assert body["task_id"] == "T-5"
    assert body["tenant_id"] == "fleet-1"
    await ps.unsubscribe(TASKS_CHANNEL)
    await ps.aclose()


async def test_publish_skips_non_new_available():
    r = aioredis.FakeRedis(decode_responses=True)
    published = await bridge.publish_task_event(
        r, json.dumps({"event_type": "completed", "id": "T-6"}), "f"
    )
    assert published is False
