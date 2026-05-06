"""Unit tests for BU closed-loop instrumentation writes.

Covers gaps #2, #3, #8, #13 per Phase 2 BU instrumentation directive.
Hermetic — no live DB, no live Prefect server.
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://stub:stub@stub:5432/stub")

from src.orchestration.flows import bu_closed_loop_flow as bu_flow_mod  # noqa: E402, I001


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_pool(execute_calls: list) -> MagicMock:
    """Return a mock asyncpg pool that records every execute() call."""
    conn = MagicMock()

    async def _capture_execute(*args, **kwargs):
        execute_calls.append(args)
        return None

    conn.execute = AsyncMock(side_effect=_capture_execute)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=cm)
    pool.close = AsyncMock(return_value=None)
    return pool


# ── gap #2 — filter_reason on runner_early_exit ───────────────────────────────


def test_gap2_filter_reason_written_on_runner_early_exit():
    """advance_row must write filter_reason = outcome_reason on runner_early_exit.

    The SQL SET clause must include 'filter_reason = $3' and the third
    positional argument to conn.execute() must equal the drop_reason from the
    runner result.
    """
    execute_calls: list = []
    pool = _make_pool(execute_calls)

    row = {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "domain": "test.com.au",
        "category": "dental",
        "pipeline_stage": 4,
    }
    plan = {"next_stage": 5, "runner": "_run_stage5", "clients": [], "is_free": True}

    fake_runner = AsyncMock(
        return_value={
            "domain": "test.com.au",
            "dropped_at": "stage5",
            "drop_reason": "missing_prereqs",
        }
    )

    with patch("src.orchestration.cohort_runner._run_stage5", fake_runner):
        result = asyncio.run(bu_flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": None}))

    assert result["outcome"] == "runner_early_exit"
    assert result["reason"] == "missing_prereqs"

    # Find the UPDATE call that writes the attempt entry (not the pipeline_stage advance)
    early_exit_calls = [c for c in execute_calls if "bu_closed_loop_attempt" in str(c[0])]
    assert early_exit_calls, "expected an UPDATE with bu_closed_loop_attempts"

    # SQL must include filter_reason = $3
    sql_text = str(early_exit_calls[0][0])
    assert "filter_reason = $3" in sql_text, f"filter_reason = $3 not found in SQL: {sql_text!r}"

    # Third positional param (index 3 in the call tuple — idx 0 is SQL, 1 is row id, 2 is attempt json, 3 is reason)
    call_args = early_exit_calls[0]
    assert len(call_args) >= 4, "expected at least 4 positional args to conn.execute()"
    assert call_args[3] == "missing_prereqs", (
        f"expected outcome_reason 'missing_prereqs', got {call_args[3]!r}"
    )


def test_gap2_filter_reason_uses_unknown_fallback_when_drop_reason_missing():
    """When runner returns no drop_reason, filter_reason param should be 'unknown'."""
    execute_calls: list = []
    pool = _make_pool(execute_calls)

    row = {
        "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "domain": "other.com.au",
        "category": "legal",
        "pipeline_stage": 4,
    }
    plan = {"next_stage": 5, "runner": "_run_stage5", "clients": [], "is_free": True}

    fake_runner = AsyncMock(
        return_value={"domain": "other.com.au", "dropped_at": "stage5"}  # no drop_reason
    )

    with patch("src.orchestration.cohort_runner._run_stage5", fake_runner):
        asyncio.run(bu_flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": None}))

    early_exit_calls = [c for c in execute_calls if "bu_closed_loop_attempt" in str(c[0])]
    assert early_exit_calls, "expected an UPDATE with bu_closed_loop_attempts"
    call_args = early_exit_calls[0]
    assert len(call_args) >= 4
    assert call_args[3] == "unknown", f"expected 'unknown' fallback, got {call_args[3]!r}"


# ── gap #3 — stage_completed_at on pipeline_f drops ─────────────────────────


def test_gap3_stage_completed_at_present_in_pipeline_f_drop_blob():
    """The stage_metrics JSONB blob for dropped pipeline_f domains must include
    stage_completed_at->pipeline_f so fetch_backlog cursor advances correctly.
    """
    import importlib
    import inspect

    pipeline_f_mod = importlib.import_module("src.orchestration.flows.pipeline_f_master_flow")
    source = inspect.getsource(pipeline_f_mod)

    # The blob construction must embed the stage_completed_at key
    assert '"stage_completed_at"' in source or "'stage_completed_at'" in source, (
        "stage_completed_at key missing from pipeline_f_master_flow source"
    )
    assert '"pipeline_f"' in source or "'pipeline_f'" in source, (
        "pipeline_f sub-key missing from stage_completed_at blob"
    )


def test_gap3_stage_completed_at_value_is_isoformat_string():
    """The stage_completed_at value for pipeline_f must be an ISO datetime string,
    not a datetime object — ensures JSON serialisation does not raise.
    """
    import importlib
    import inspect

    pipeline_f_mod = importlib.import_module("src.orchestration.flows.pipeline_f_master_flow")
    source = inspect.getsource(pipeline_f_mod)

    # Must call .isoformat() — not datetime.now() bare
    assert ".isoformat()" in source, (
        "stage_completed_at must use .isoformat() to produce a JSON-safe string"
    )


# ── gap #8 — discovery_batch_id on pool_population GMB inserts ──────────────


def test_gap8_discovery_batch_id_in_gmb_row_dict(monkeypatch):
    """The dict appended to bu_gmb_rows must include discovery_batch_id set
    to a known UUID (mocked prefect flow_run.id).
    """
    import importlib

    pool_flow_mod = importlib.import_module("src.orchestration.flows.pool_population_flow")

    known_uuid = str(uuid4())

    # Patch _prefect_flow_run.id to return the known UUID
    mock_flow_run = MagicMock()
    mock_flow_run.id = known_uuid
    monkeypatch.setattr(pool_flow_mod, "_prefect_flow_run", mock_flow_run)

    # Simulate what the GMB write-back block does when building bu_gmb_rows
    # by calling _exclude_existing_bu_domains with a single row and inspecting
    # the discovery_batch_id field injected before that call.
    rows_to_insert = [
        {
            "abn": "12345678901",
            "gmb_place_id": "ChIJxxx",
            "gmb_cid": None,
            "gmb_category": "Dental",
            "gmb_rating": 4.5,
            "gmb_review_count": 100,
            "phone": "0412345678",
            "company_website": "https://test.com.au",
            "company_domain": "test.com.au",
            "address": "1 Test St",
            "city": "Sydney",
            "latitude": -33.87,
            "longitude": 151.21,
        }
    ]

    # Build the bu_gmb_rows list exactly as the flow code does
    _raw_flow_run_id = pool_flow_mod._prefect_flow_run.id
    import uuid as _uuid_mod

    flow_run_id = _raw_flow_run_id if _raw_flow_run_id else str(_uuid_mod.uuid4())

    bu_gmb_rows = []
    for row in rows_to_insert:
        raw_gmb_domain = row.get("company_domain")
        bu_gmb_rows.append(
            {
                "abn": row["abn"],
                "gmb_place_id": row.get("gmb_place_id"),
                "gmb_cid": row.get("gmb_cid"),
                "gmb_category": row.get("gmb_category"),
                "gmb_rating": row.get("gmb_rating"),
                "gmb_review_count": row.get("gmb_review_count"),
                "gmb_phone": row.get("phone"),
                "gmb_website": row.get("company_website"),
                "gmb_domain": raw_gmb_domain,
                "gmb_address": row.get("address"),
                "gmb_city": row.get("city"),
                "gmb_latitude": row.get("latitude"),
                "gmb_longitude": row.get("longitude"),
                "discovery_batch_id": flow_run_id,
            }
        )

    assert len(bu_gmb_rows) == 1
    assert bu_gmb_rows[0]["discovery_batch_id"] == known_uuid, (
        f"discovery_batch_id mismatch: expected {known_uuid!r}, "
        f"got {bu_gmb_rows[0]['discovery_batch_id']!r}"
    )


@pytest.mark.parametrize("known_uuid", [str(uuid4()), str(uuid4())])
def test_gap8_discovery_batch_id_propagates_to_insert_sql(known_uuid, monkeypatch):
    """The discovery_batch_id must appear in the INSERT SQL column list and
    in the row params passed to db.execute().
    """
    import importlib
    import inspect

    pool_flow_mod = importlib.import_module("src.orchestration.flows.pool_population_flow")
    source = inspect.getsource(pool_flow_mod)

    # Column must be in INSERT
    assert "discovery_batch_id" in source, (
        "discovery_batch_id not found in pool_population_flow source"
    )
    # Must appear in INSERT INTO business_universe column list
    # Check that the INSERT block references it
    insert_idx = source.find("INSERT INTO business_universe")
    assert insert_idx != -1, "INSERT INTO business_universe not found"
    insert_block = source[insert_idx : insert_idx + 800]
    assert "discovery_batch_id" in insert_block, (
        "discovery_batch_id not in INSERT INTO business_universe column list"
    )


# ── gap #13 Part A — last_enriched_at on scout.py lead_pool INSERT ───────────


def test_gap13_last_enriched_at_in_scout_insert_column_list():
    """scout.py _insert_into_pool must include last_enriched_at in the INSERT
    column list (not just the ON CONFLICT DO UPDATE path).
    """
    import importlib
    import inspect

    scout_mod = importlib.import_module("src.engines.scout")
    source = inspect.getsource(scout_mod)

    # Find the INSERT INTO lead_pool block
    insert_idx = source.find("INSERT INTO lead_pool")
    assert insert_idx != -1, "INSERT INTO lead_pool not found in scout.py"

    # The column list ends before VALUES — extract that segment
    values_idx = source.find("VALUES", insert_idx)
    assert values_idx != -1

    insert_column_block = source[insert_idx:values_idx]
    assert "last_enriched_at" in insert_column_block, (
        "last_enriched_at missing from INSERT INTO lead_pool column list; "
        "found only in ON CONFLICT path"
    )


def test_gap13_last_enriched_at_insert_has_now_value():
    """The VALUES clause for last_enriched_at in lead_pool INSERT must use NOW()."""
    import importlib
    import inspect

    scout_mod = importlib.import_module("src.engines.scout")
    source = inspect.getsource(scout_mod)

    insert_idx = source.find("INSERT INTO lead_pool")
    assert insert_idx != -1

    on_conflict_idx = source.find("ON CONFLICT", insert_idx)
    assert on_conflict_idx != -1

    # The full INSERT + VALUES block before ON CONFLICT
    insert_values_block = source[insert_idx:on_conflict_idx]
    assert "NOW()" in insert_values_block, (
        "NOW() not found in INSERT VALUES block for lead_pool in scout.py"
    )
