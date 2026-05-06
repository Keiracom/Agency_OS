"""tests/integration/test_governance_hooks_live.py — live Supabase tests
for the Aiden-scope governance hooks.

GOV-PHASE1-COMPREHENSIVE-FIX-AIDEN-SCOPE — D7.

Marked `pytest.mark.integration` — default `pytest` skips them; CI/manual
runs must use `pytest -m integration`. The conftest auto-skips if
SUPABASE_URL or SUPABASE_SERVICE_KEY is absent.

Three smoke tests:
  1. governance_events insert via the same MCP path the recorder hook uses
  2. coordinator_claims insert + check_conflict() detection + release
  3. frozen_artifacts insert + is_frozen() detection
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest


pytestmark = pytest.mark.integration


def _supabase_client():
    """Build a service-role client. Call inside tests after env is verified."""
    from supabase import create_client  # type: ignore

    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )


def test_governance_event_emit_round_trip(cleanup_rows):
    """governance_event_emit() inserts a row that we can SELECT back."""
    from src.governance._mcp_helpers import governance_event_emit

    callsign = "test-aiden-integration"
    event_type = f"integration_smoke_{uuid.uuid4().hex[:8]}"
    ok = governance_event_emit(
        callsign=callsign,
        event_type=event_type,
        event_data={"smoke": True},
        tool_name="tests.integration.governance_hooks_live",
    )
    assert ok is True

    client = _supabase_client()
    response = client.table("governance_events").select("*").eq("event_type", event_type).execute()
    rows = getattr(response, "data", None) or []
    assert len(rows) == 1, f"expected 1 row, got {len(rows)}"
    assert rows[0]["callsign"] == callsign
    assert rows[0]["event_data"]["smoke"] is True
    cleanup_rows.append(("governance_events", "event_type", event_type))


def test_coordinator_claim_conflict_and_release(cleanup_rows):
    """A peer claim on the same target_path is detected by check_conflict()."""
    from src.governance.coordinator import (
        check_conflict,
        claim,
        list_active_claims,
        release,
    )

    target = f"__integration_target__/{uuid.uuid4().hex[:8]}"
    client = _supabase_client()
    rec = claim(
        callsign="peer-bot",
        action="shared-file-edit",
        target_path=target,
        client=client,
    )
    cleanup_rows.append(("coordinator_claims", "id", rec.id))

    conflict = check_conflict(
        callsign="self-bot",
        target_path=target,
        client=client,
    )
    assert conflict is not None, "expected conflict for peer-claimed target"
    assert conflict["callsign"] == "peer-bot"
    assert conflict["target_path"] == target

    same_callsign = check_conflict(
        callsign="peer-bot",
        target_path=target,
        client=client,
    )
    assert same_callsign is None, "expected no conflict for self-callsign"

    assert release(rec.id, client=client) is True
    remaining = list_active_claims(target_path=target, client=client)
    assert remaining == []


def test_frozen_artifact_round_trip(cleanup_rows):
    """freeze_artifact + is_frozen + unfreeze round-trip on a synthetic path."""
    from src.governance.freeze import (
        freeze_artifact,
        is_frozen,
        unfreeze_artifact,
    )

    path = f"__integration_freeze__/{uuid.uuid4().hex[:8]}.txt"
    cleanup_rows.append(("frozen_artifacts", "artifact_path", path))

    row = freeze_artifact(
        path,
        frozen_by="integration-test",
        reason="smoke",
    )
    assert row.get("artifact_path") == path
    assert is_frozen(path) is True

    unfreeze_artifact(path)
    assert is_frozen(path) is False
