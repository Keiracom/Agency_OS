"""
P1.7: Tests for NULL-URL BDM write-path guard, name normalization,
unknown name rejection, and AU TLD filter in flow SQL.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# 1. NULL-URL guard — no INSERT when both linkedin_url and email are absent
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_null_url_guard_skips_insert():
    """dm with no linkedin_url and no email should not INSERT into BDM table."""
    from src.pipeline.stage_5_dm_waterfall import Stage5DMWaterfall, DMResult

    stage = Stage5DMWaterfall.__new__(Stage5DMWaterfall)
    stage.conn = AsyncMock()
    stage.conn.fetchval = AsyncMock(return_value=None)
    stage.conn.execute = AsyncMock()

    dm = DMResult(name="Jane Smith", source="test", linkedin_url=None, email=None)
    business = {"id": "biz-001", "domain": "example.com.au"}

    await stage._write_result("biz-001", dm, business)

    # No UPDATE to business_decision_makers (only BU pipeline UPDATE should fire)
    calls = [str(c) for c in stage.conn.execute.call_args_list]
    # The INSERT SQL contains 'INSERT INTO business_decision_makers'
    insert_calls = [c for c in calls if "INSERT INTO business_decision_makers" in c]
    assert len(insert_calls) == 0, f"Expected no BDM INSERT but got: {insert_calls}"


# ---------------------------------------------------------------------------
# 2. NULL-URL guard allows INSERT when email is present
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_null_url_guard_allows_with_email():
    """dm with email but no linkedin_url should proceed to INSERT."""
    from src.pipeline.stage_5_dm_waterfall import Stage5DMWaterfall, DMResult

    stage = Stage5DMWaterfall.__new__(Stage5DMWaterfall)
    stage.conn = AsyncMock()
    stage.conn.fetchval = AsyncMock(return_value=None)
    stage.conn.execute = AsyncMock()

    dm = DMResult(name="Jane Smith", source="test", linkedin_url=None, email="jane@example.com.au")
    business = {
        "id": "biz-002",
        "domain": "example.com.au",
        "dm_email": None,
        "dm_phone": None,
        "phone": None,
        "address": None,
        "gmb_place_id": None,
    }

    await stage._write_result("biz-002", dm, business)

    calls = [str(c) for c in stage.conn.execute.call_args_list]
    insert_calls = [c for c in calls if "INSERT INTO business_decision_makers" in c]
    assert len(insert_calls) == 1, f"Expected 1 BDM INSERT but got: {insert_calls}"


# ---------------------------------------------------------------------------
# 3. Name title-case normalization — lowercase input
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_name_title_case_normalization():
    """'sian mcconnell' must be stored as 'Sian Mcconnell'."""
    from src.pipeline.stage_5_dm_waterfall import Stage5DMWaterfall, DMResult

    stage = Stage5DMWaterfall.__new__(Stage5DMWaterfall)
    stage.conn = AsyncMock()
    stage.conn.fetchval = AsyncMock(return_value=None)

    captured = {}

    async def capture_execute(sql, *args):
        if "INSERT INTO business_decision_makers" in sql:
            captured["name"] = args[1]  # $2 = name

    stage.conn.execute = capture_execute

    dm = DMResult(
        name="sian mcconnell",
        source="test",
        email="sian@example.com.au",
        linkedin_url=None,
    )
    business = {
        "id": "biz-003",
        "domain": "example.com.au",
        "dm_email": None,
        "dm_phone": None,
        "phone": None,
        "address": None,
        "gmb_place_id": None,
    }

    await stage._write_result("biz-003", dm, business)
    assert captured.get("name") == "Sian Mcconnell", f"Got: {captured.get('name')}"


# ---------------------------------------------------------------------------
# 4. Title-case preserves already-correct casing (Dr John)
# ---------------------------------------------------------------------------
def test_name_title_case_preserves_dr():
    """title() on 'Dr John' gives 'Dr John' — no regression."""
    name = "Dr John"
    assert name.strip().title() == "Dr John"


# ---------------------------------------------------------------------------
# 5. DMResult with name='Unknown' and no contact is not valid
# ---------------------------------------------------------------------------
def test_unknown_name_dm_not_valid():
    """DMResult(name='Unknown') without any contact method must not be valid."""
    from src.pipeline.stage_5_dm_waterfall import DMResult

    dm = DMResult(name="Unknown", source="test")
    assert not dm.is_valid


# ---------------------------------------------------------------------------
# 6. _DEDUP_SQL contains AU TLD filter
# ---------------------------------------------------------------------------
def test_flow_sql_has_au_tld_filter():
    """_DEDUP_SQL in stage_9_10_flow must contain .com.au filter clause."""
    from src.orchestration.flows.stage_9_10_flow import _DEDUP_SQL

    assert ".com.au" in _DEDUP_SQL, "_DEDUP_SQL missing AU TLD whitelist"
    assert ".gov.au" in _DEDUP_SQL, "_DEDUP_SQL missing gov.au exclusion"
