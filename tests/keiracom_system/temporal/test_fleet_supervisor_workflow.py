"""Tests for FleetSupervisorWorkflow + AgentStateUpdate + audit_activity.

Phase A6 first-workflow per Dave KEI-DAVE-MIGRATION-PATH.

10 cases — 3 dataclass + 4 audit-event + 3 helper.

Workflow execution against the actual Temporal runtime is covered by the
opt-in integration test (KEIRACOM_TEMPORAL_INTEGRATION=1) at the bottom of
this file — exercises signal round-trip + audit activity + query against
live PROD Temporal (45.76.114.137:7233).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("temporalio", reason="temporalio SDK required for Temporal workflow tests")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.temporal.audit_activity import (  # noqa: E402
    build_audit_event,
)
from src.keiracom_system.temporal.fleet_supervisor_workflow import (  # noqa: E402
    FLEET_SUPERVISOR_WORKFLOW_ID,
    AgentStateUpdate,
    _infer_agent_type,
)


def test_agent_state_update_dataclass_required_fields():
    """(1) AgentStateUpdate requires callsign + state; metadata defaults to empty dict."""
    u = AgentStateUpdate(callsign="orion", state="ready")
    assert u.callsign == "orion"
    assert u.state == "ready"
    assert u.metadata == {}


def test_agent_state_update_accepts_metadata():
    """(2) metadata dict accepted + retained verbatim."""
    u = AgentStateUpdate(callsign="atlas", state="starting", metadata={"task_id": "abc-123"})
    assert u.metadata == {"task_id": "abc-123"}


def test_fleet_supervisor_workflow_id_constant():
    """(3) FLEET_SUPERVISOR_WORKFLOW_ID locked — operator scripts depend on it."""
    assert FLEET_SUPERVISOR_WORKFLOW_ID == "fleet-supervisor-v1"


def test_build_audit_event_returns_contract_v1_schema():
    """(4) build_audit_event emits all 11 contract V1 schema fields."""
    event = build_audit_event(
        gate="temp.inline.audit",
        tenant_id="t1",
        agent_id="orion",
        agent_type="worker",
        tier="solo",
        outcome="pass",
        elapsed_ms=12.5,
        reason="agent_state_update",
        detail="state=ready",
    )
    required = {
        "gate",
        "workflow_id",
        "activity_id",
        "tenant_id",
        "agent_id",
        "agent_type",
        "tier",
        "outcome",
        "elapsed_ms",
        "reason",
        "detail",
        "timestamp",
    }
    assert required.issubset(event.keys()), f"missing: {required - event.keys()}"


def test_build_audit_event_workflow_and_activity_ids_default_empty():
    """(5) outside-Temporal-context defaults to empty strings (test path safe)."""
    event = build_audit_event(
        gate="temp.inline.audit",
        tenant_id="t1",
        agent_id="orion",
        agent_type="worker",
        tier="solo",
        outcome="pass",
        elapsed_ms=0.0,
        reason="x",
        detail="y",
    )
    assert event["workflow_id"] == ""
    assert event["activity_id"] == ""


def test_build_audit_event_elapsed_ms_coerced_to_float():
    """(6) caller can pass int; field is coerced to float per schema."""
    event = build_audit_event(
        gate="temp.inline.audit",
        tenant_id="t1",
        agent_id="orion",
        agent_type="worker",
        tier="solo",
        outcome="pass",
        elapsed_ms=42,
        reason="x",
        detail="y",  # int input
    )
    assert isinstance(event["elapsed_ms"], float)
    assert event["elapsed_ms"] == 42.0


def test_build_audit_event_timestamp_is_iso8601_utc():
    """(7) timestamp field is ISO-8601 UTC per contract V1."""
    from datetime import datetime

    event = build_audit_event(
        gate="temp.inline.audit",
        tenant_id="t1",
        agent_id="orion",
        agent_type="worker",
        tier="solo",
        outcome="pass",
        elapsed_ms=0.0,
        reason="x",
        detail="y",
    )
    # Parses without error + ends in +00:00 (UTC) or Z
    ts = event["timestamp"]
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None  # tz-aware
    assert ts.endswith(("+00:00", "Z"))


def test_infer_agent_type_deliberator_callsigns():
    """(8) elliot / aiden / max → deliberator."""
    assert _infer_agent_type("elliot") == "deliberator"
    assert _infer_agent_type("aiden") == "deliberator"
    assert _infer_agent_type("MAX") == "deliberator"  # case-insensitive


def test_infer_agent_type_worker_callsigns():
    """(9) orion / atlas / scout / nova / viktor → worker."""
    for cs in ("orion", "atlas", "scout", "nova", "viktor"):
        assert _infer_agent_type(cs) == "worker"


def test_infer_agent_type_unknown_defaults_to_worker():
    """(10) unknown callsigns default to worker (safe least-privileged audit attribution)."""
    assert _infer_agent_type("unknown-agent") == "worker"
    assert _infer_agent_type("ephemeral-spawn-abc-123") == "worker"


# Integration test — opt-in against live PROD Temporal
_INTEGRATION_ENABLED = os.environ.get("KEIRACOM_TEMPORAL_INTEGRATION", "").strip() == "1"


@pytest.mark.skipif(
    not _INTEGRATION_ENABLED,
    reason="KEIRACOM_TEMPORAL_INTEGRATION=1 not set — live Temporal workflow test skipped",
)
@pytest.mark.asyncio
async def test_integration_signal_round_trip_against_live_temporal():
    """(integration) start workflow on live Temporal + signal + query + shutdown.

    Requires:
      - TEMPORAL_ADDR env set (e.g. 45.76.114.137:7233)
      - A worker process running with FleetSupervisorWorkflow + emit_audit_event
        registered (start via `python -m keiracom_system.temporal.worker` in a
        separate terminal before running this test)
      - 'default' namespace exists
    """
    from src.keiracom_system.temporal.client import from_env
    from src.keiracom_system.temporal.fleet_supervisor_workflow import (
        FLEET_SUPERVISOR_WORKFLOW_ID,
        FleetSupervisorWorkflow,
    )

    client = await from_env()
    # Use a unique workflow id per test run to avoid colliding with prior smokes
    import uuid

    wf_id = f"{FLEET_SUPERVISOR_WORKFLOW_ID}-test-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        FleetSupervisorWorkflow.run,
        id=wf_id,
        task_queue="keiracom-default",
    )

    # Send 2 signals
    await handle.signal(
        "update_agent_state",
        AgentStateUpdate(callsign="orion", state="ready"),
    )
    await handle.signal(
        "update_agent_state",
        AgentStateUpdate(callsign="atlas", state="starting", metadata={"task_id": "test-1"}),
    )

    # Query counter — wait briefly for signals to land
    import asyncio

    await asyncio.sleep(2)
    count = await handle.query("get_signals_received")
    assert count == 2, f"expected 2 signals received, got {count}"

    # Query fleet state
    state = await handle.query("get_fleet_state")
    assert "orion" in state
    assert state["orion"]["state"] == "ready"
    assert "atlas" in state
    assert state["atlas"]["metadata"] == {"task_id": "test-1"}

    # Shutdown cleanly
    await handle.signal("shutdown")
    result = await handle.result()
    assert result["signals_received"] == 2
