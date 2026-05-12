"""Unit tests for src.cognee.continuous_ingest — Cognee Phase 1 polling watcher.

Mocks Aiden's wrapper (src/cognee/client.add) + Supabase REST helper
(src/evo/supabase_client.sb_get). No network, no actual Cognee install.

Covers the success criteria from Elliot's dispatch:
  - watermark advance after successful ingest
  - deduplication (rows below watermark are not re-fetched / re-ingested)
  - error recovery (ingest failure does NOT advance the watermark)
  - callsign attribution (governance_events / agent_memories pass their
    callsign through as agent_id; ceo_memory defaults to 'system')
  - first-run defaults (empty state → reasonable initial watermark)
  - timestamp-order ingest (rows arrive at Cognee monotonically)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.cognee import continuous_ingest as ci


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "watermarks.json"


@pytest.fixture
def fake_add():
    """Async-mock for Aiden's cognee.add(). Records every call."""
    calls: list[dict] = []

    async def _add(content, *, org_id, app_id, agent_id, node_set=None):
        calls.append(
            {
                "content": content,
                "org_id": org_id,
                "app_id": app_id,
                "agent_id": agent_id,
                "node_set": node_set,
            }
        )

    _add.calls = calls  # type: ignore[attr-defined]
    return _add


def _patch_sb_get(monkeypatch, response_map: dict[str, list[dict]]):
    """Make sb_get(table, params) return response_map[table]. Capture last params."""
    captured: dict[str, dict] = {}

    def fake(table: str, params: dict) -> list[dict]:
        captured[table] = params
        return list(response_map.get(table, []))

    monkeypatch.setattr(ci, "sb_get", fake)
    return captured


# ─── 1. Watermark advance ──────────────────────────────────────────────


def test_watermark_advances_to_max_timestamp_after_successful_ingest(
    state_path: Path, fake_add, monkeypatch
):
    rows = [
        {"key": "k1", "value": {"x": 1}, "updated_at": "2026-05-12T03:00:00+00:00"},
        {"key": "k2", "value": {"x": 2}, "updated_at": "2026-05-12T03:05:00+00:00"},
    ]
    _patch_sb_get(monkeypatch, {"ceo_memory": rows})

    result = ci.run_once(state_path, table_filter=("ceo_memory",), add_fn=fake_add)

    assert result.ingested["ceo_memory"] == 2
    assert result.watermarks["ceo_memory"] == "2026-05-12T03:05:00+00:00"
    state = json.loads(state_path.read_text())
    assert state["ceo_memory"]["watermark"] == "2026-05-12T03:05:00+00:00"
    assert "last_run_at" in state["ceo_memory"]


# ─── 2. Deduplication / watermark filter ───────────────────────────────


def test_dedupe_uses_gt_filter_on_watermark_column(state_path: Path, fake_add, monkeypatch):
    """Rows already below the stored watermark must not be fetched —
    enforced via PostgREST `gt.<watermark>` on the watermark column."""
    state_path.write_text(
        json.dumps(
            {
                "agent_memories": {
                    "watermark": "2026-05-12T02:00:00+00:00",
                    "last_run_at": "2026-05-12T02:00:01+00:00",
                }
            }
        )
    )
    captured = _patch_sb_get(monkeypatch, {"agent_memories": []})

    ci.run_once(state_path, table_filter=("agent_memories",), add_fn=fake_add)

    assert captured["agent_memories"]["created_at"] == "gt.2026-05-12T02:00:00+00:00"
    assert captured["agent_memories"]["order"] == "created_at.asc"
    assert fake_add.calls == []


# ─── 3. Error recovery — failed ingest keeps watermark pinned ──────────


def test_ingest_failure_does_not_advance_watermark(state_path: Path, monkeypatch):
    pinned_wm = "2026-05-12T01:00:00+00:00"
    state_path.write_text(
        json.dumps({"governance_events": {"watermark": pinned_wm, "last_run_at": pinned_wm}})
    )
    rows = [
        {
            "id": "e1",
            "callsign": "aiden",
            "event_type": "RULE_FIRE",
            "event_data": {},
            "tool_name": None,
            "file_path": None,
            "timestamp": "2026-05-12T02:00:00+00:00",
            "directive_id": None,
        }
    ]
    _patch_sb_get(monkeypatch, {"governance_events": rows})

    async def boom(*_a, **_kw):
        raise RuntimeError("cognee down")

    result = ci.run_once(state_path, table_filter=("governance_events",), add_fn=boom)

    assert "governance_events" in result.errors
    assert result.errors["governance_events"].startswith("ingest:")
    state = json.loads(state_path.read_text())
    assert state["governance_events"]["watermark"] == pinned_wm, (
        "Pattern A: ingest failure must leave the watermark untouched so the "
        "next scan retries the same rows. Advancing would silently drop them."
    )


# ─── 4. Callsign attribution ───────────────────────────────────────────


def test_governance_and_agent_rows_pass_callsign_as_agent_id(
    state_path: Path, fake_add, monkeypatch
):
    _patch_sb_get(
        monkeypatch,
        {
            "governance_events": [
                {
                    "id": "g1",
                    "callsign": "max",
                    "event_type": "STEP0_OK",
                    "event_data": {},
                    "tool_name": None,
                    "file_path": None,
                    "timestamp": "2026-05-12T03:00:00+00:00",
                    "directive_id": None,
                }
            ],
            "agent_memories": [
                {
                    "id": "a1",
                    "callsign": "atlas",
                    "source_type": "daily_log",
                    "content": "shipped PR #720",
                    "tags": ["clone"],
                    "created_at": "2026-05-12T03:01:00+00:00",
                }
            ],
        },
    )

    ci.run_once(
        state_path,
        table_filter=("governance_events", "agent_memories"),
        add_fn=fake_add,
    )

    agent_ids = {c["agent_id"] for c in fake_add.calls}
    assert agent_ids == {"max", "atlas"}


def test_ceo_memory_rows_default_agent_id_to_system(state_path: Path, fake_add, monkeypatch):
    """ceo_memory has no callsign column — every row attributes to 'system'
    so the Cognee graph still shows a clear provenance edge."""
    _patch_sb_get(
        monkeypatch,
        {"ceo_memory": [{"key": "k", "value": "v", "updated_at": "2026-05-12T03:00:00+00:00"}]},
    )

    ci.run_once(state_path, table_filter=("ceo_memory",), add_fn=fake_add)

    assert len(fake_add.calls) == 1
    assert fake_add.calls[0]["agent_id"] == "system"
    assert fake_add.calls[0]["node_set"] == ["source:ceo_memory"]


# ─── 5. First-run default watermark ────────────────────────────────────


def test_first_run_uses_lookback_default_when_state_missing(
    state_path: Path, fake_add, monkeypatch
):
    """No state file → initial watermark = NOW - lookback_seconds. Filter
    must include that timestamp via `gt.` on the watermark column."""
    captured = _patch_sb_get(monkeypatch, {"ceo_memory": []})

    before = datetime.now(UTC)
    ci.run_once(
        state_path,
        table_filter=("ceo_memory",),
        add_fn=fake_add,
        initial_lookback_seconds=10,
    )

    wm = captured["ceo_memory"]["updated_at"].removeprefix("gt.")
    parsed = datetime.fromisoformat(wm)
    delta = before - parsed
    assert timedelta(seconds=9) <= delta <= timedelta(seconds=11), (
        f"Initial watermark should be ~10s back; got delta={delta}"
    )


# ─── 6. Timestamp-order ingest ─────────────────────────────────────────


def test_rows_dispatched_in_ascending_watermark_order(state_path: Path, fake_add, monkeypatch):
    """Cognee graph consistency: rows arrive in monotonic order so each
    add() call sees the prior context already cognified. We assert both
    that the PostgREST query orders ASC AND that add() receives rows in
    that order verbatim."""
    rows = [
        {
            "id": f"a{i}",
            "callsign": "orion",
            "source_type": "daily_log",
            "content": f"row {i}",
            "tags": [],
            "created_at": f"2026-05-12T03:0{i}:00+00:00",
        }
        for i in range(3)
    ]
    captured = _patch_sb_get(monkeypatch, {"agent_memories": rows})

    ci.run_once(state_path, table_filter=("agent_memories",), add_fn=fake_add)

    assert captured["agent_memories"]["order"] == "created_at.asc"
    received_contents = [c["content"] for c in fake_add.calls]
    assert received_contents == [
        f"agent_memory[daily_log] callsign=orion tags=[] content=row {i}" for i in range(3)
    ]


# ─── 7. Fetch failure isolates one table — others still scanned ────────


def test_fetch_failure_isolates_to_one_table(state_path: Path, fake_add, monkeypatch):
    """A Supabase outage on one table must not block ingest on the others —
    matches Pattern A's "decoupled reader" requirement."""
    call_count = {"n": 0}

    def fake(table: str, params: dict) -> list[dict]:
        call_count["n"] += 1
        if table == "governance_events":
            raise RuntimeError("postgrest 503")
        return []

    monkeypatch.setattr(ci, "sb_get", fake)

    result = ci.run_once(state_path, add_fn=fake_add)

    assert "governance_events" in result.errors
    assert result.errors["governance_events"].startswith("fetch:")
    # ceo_memory + agent_memories both attempted — fetch called 3 times.
    assert call_count["n"] == 3
    # And no rows = no ingest calls.
    assert fake_add.calls == []


# ─── 8. State file persists across runs ────────────────────────────────


def test_state_persists_across_run_once_calls(state_path: Path, fake_add, monkeypatch):
    """run_once must read+write the state file so the next invocation
    picks up where the previous left off — required for cron-style usage."""
    first_rows = [{"key": "k1", "value": "v1", "updated_at": "2026-05-12T03:00:00+00:00"}]
    second_rows = [{"key": "k2", "value": "v2", "updated_at": "2026-05-12T03:10:00+00:00"}]

    # First pass
    _patch_sb_get(monkeypatch, {"ceo_memory": first_rows})
    ci.run_once(state_path, table_filter=("ceo_memory",), add_fn=fake_add)

    # Second pass — sb_get should see the new watermark from disk
    captured = _patch_sb_get(monkeypatch, {"ceo_memory": second_rows})
    ci.run_once(state_path, table_filter=("ceo_memory",), add_fn=fake_add)

    assert captured["ceo_memory"]["updated_at"] == "gt.2026-05-12T03:00:00+00:00", (
        "second run must filter strictly above first run's max"
    )
    state = json.loads(state_path.read_text())
    assert state["ceo_memory"]["watermark"] == "2026-05-12T03:10:00+00:00"


# ─── 9. Corrupt state file handled gracefully ──────────────────────────


def test_corrupt_state_file_falls_back_to_initial_watermark(
    state_path: Path, fake_add, monkeypatch
):
    state_path.write_text("{ not valid json")
    captured = _patch_sb_get(monkeypatch, {"ceo_memory": []})

    # Must not raise
    ci.run_once(state_path, table_filter=("ceo_memory",), add_fn=fake_add)

    assert captured["ceo_memory"]["updated_at"].startswith("gt.")
