# tests/test_stage5_email_enrichment.py
# PURPOSE: Tests for src/pipeline/stage5_email_enrichment.py
# DIRECTIVE: #251 — all mocks, no live API calls, no live DB

import uuid
import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.pipeline.stage5_email_enrichment import Stage5EmailEnrichment, LEADMAGIC_EMAIL_COST_AUD


# ============================================================
# HELPERS
# ============================================================

def make_db(fetch_rows):
    """Create a mock DB that returns given rows from fetch()."""
    db = MagicMock()
    db.fetch = AsyncMock(return_value=fetch_rows)
    db.execute = AsyncMock(return_value=None)
    return db


def make_row(**kwargs):
    """Build a mock row dict with defaults."""
    defaults = {
        "id": uuid.uuid4(),
        "display_name": "Acme Corp",
        "domain": "acme.com",
        "dm_linkedin_url": None,
        "dm_source": None,
        "dm_name": None,
        "propensity_score": 0.75,
    }
    defaults.update(kwargs)
    return defaults


# ============================================================
# TEST 1: LinkedIn path — email found
# ============================================================

@pytest.mark.asyncio
async def test_linkedin_path_attempts_email():
    """Row with dm_linkedin_url: stage5 calls _find_email_by_linkedin and marks email_found."""
    row = make_row(
        dm_linkedin_url="https://linkedin.com/in/john-doe",
        dm_name="John Doe",
        domain="example.com",
        display_name="Acme",
        dm_source="dfs_serp",
    )
    db = make_db([row])
    client = MagicMock()

    stage5 = Stage5EmailEnrichment(leadmagic_client=client, db=db)

    linkedin_return = {"email": "john@example.com", "verified": True, "confidence": 90}
    with patch.object(stage5, "_find_email_by_linkedin", new=AsyncMock(return_value=linkedin_return)):
        result = await stage5.run(batch_size=1)

    assert result["attempted"] == 1
    assert result["email_found"] == 1

    # Verify db.execute called with email_found status
    call_args_list = db.execute.call_args_list
    sql_calls = [str(call) for call in call_args_list]
    assert any("email_found" in s for s in sql_calls), (
        f"Expected 'email_found' in db.execute calls, got: {sql_calls}"
    )


# ============================================================
# TEST 2: Domain fallback path — email found
# ============================================================

@pytest.mark.asyncio
async def test_domain_fallback_path():
    """Row without dm_linkedin_url but with domain: uses _find_email_by_domain."""
    row = make_row(
        dm_linkedin_url=None,
        domain="example.com",
        dm_name="Jane Smith",
    )
    db = make_db([row])
    client = MagicMock()

    stage5 = Stage5EmailEnrichment(leadmagic_client=client, db=db)

    domain_return = {"email": "jane@example.com", "verified": False, "confidence": 65}
    with patch.object(stage5, "_find_email_by_domain", new=AsyncMock(return_value=domain_return)):
        result = await stage5.run(batch_size=1)

    assert result["email_found"] == 1
    assert result["attempted"] == 1


# ============================================================
# TEST 3: No path — skipped
# ============================================================

@pytest.mark.asyncio
async def test_no_path_skipped():
    """Row with neither dm_linkedin_url nor domain: skipped_no_path incremented."""
    row = make_row(
        dm_linkedin_url=None,
        domain=None,
        dm_name="Unknown Person",
    )
    db = make_db([row])
    client = MagicMock()

    stage5 = Stage5EmailEnrichment(leadmagic_client=client, db=db)
    result = await stage5.run(batch_size=1)

    assert result["skipped_no_path"] == 1
    assert result["attempted"] == 0

    call_args_list = db.execute.call_args_list
    sql_calls = [str(call) for call in call_args_list]
    assert any("email_no_path" in s for s in sql_calls), (
        f"Expected 'email_no_path' in db.execute calls, got: {sql_calls}"
    )


# ============================================================
# TEST 4: Spend cap stops enrichment
# ============================================================

@pytest.mark.asyncio
async def test_spend_cap_stops_enrichment():
    """daily_spend_cap_aud=0.005 (< $0.015): all rows hit spend cap, attempted=0."""
    rows = [
        make_row(dm_linkedin_url="https://linkedin.com/in/a", dm_name="Alice B", domain="a.com"),
        make_row(dm_linkedin_url="https://linkedin.com/in/b", dm_name="Bob C", domain="b.com"),
    ]
    db = make_db(rows)
    client = MagicMock()

    stage5 = Stage5EmailEnrichment(leadmagic_client=client, db=db)
    result = await stage5.run(batch_size=2, daily_spend_cap_aud=0.005)

    assert result["attempted"] == 0

    # All rows should be marked email_skipped_spend_cap
    call_args_list = db.execute.call_args_list
    sql_calls = [str(call) for call in call_args_list]
    assert any("email_skipped_spend_cap" in s for s in sql_calls)


# ============================================================
# TEST 5: Cost accumulates correctly
# ============================================================

@pytest.mark.asyncio
async def test_enrichment_cost_accumulates():
    """3 rows found via linkedin path: total cost = 3 * $0.015."""
    rows = [
        make_row(
            dm_linkedin_url=f"https://linkedin.com/in/person{i}",
            dm_name=f"Person{i} Last",
            domain="example.com",
        )
        for i in range(3)
    ]
    db = make_db(rows)
    client = MagicMock()

    stage5 = Stage5EmailEnrichment(leadmagic_client=client, db=db)

    email_return = {"email": "person@example.com", "verified": True, "confidence": 85}
    with patch.object(stage5, "_find_email_by_linkedin", new=AsyncMock(return_value=email_return)):
        result = await stage5.run(batch_size=3, daily_spend_cap_aud=15.0)

    assert result["cost_aud"] == pytest.approx(3 * float(LEADMAGIC_EMAIL_COST_AUD), abs=0.001)
    assert result["email_found"] == 3
