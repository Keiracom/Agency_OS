"""tests/pipeline/test_austender_discovery.py — unit tests for AusTender → BU writer.

Mocks asyncpg connection + AusTenderClient. No live DB / network.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.austender_client import AwardEvent
from src.pipeline.austender_discovery import (
    IngestResult,
    _build_jsonb_payload,
    ingest_award_event,
    run_ingest,
    yesterday_aest,
)


def _au_event(
    *,
    contract_id: str = "ocds-au-CN1",
    abn: str = "33 051 775 556",
    name: str = "Pymble Dental Pty Ltd",
    value: int | None = 75000,
) -> AwardEvent:
    return AwardEvent(
        contract_id=contract_id,
        supplier_abn=abn,
        supplier_name=name,
        supplier_country="AU",
        contract_value_aud=value,
        awarded_date="2026-04-15",
        agency_name="Department of Health",
        classification_id="85101701",
    )


# ── _build_jsonb_payload ──────────────────────────────────────────────────────


def test_build_jsonb_payload_extracts_all_fields():
    event = _au_event()
    payload = _build_jsonb_payload(event)
    assert payload == {
        "contract_id": "ocds-au-CN1",
        "contract_value_aud": 75000,
        "awarded_date": "2026-04-15",
        "agency_name": "Department of Health",
        "classification_id": "85101701",
    }


def test_build_jsonb_payload_handles_none_fields():
    event = AwardEvent(
        contract_id="ocds-au-CN2",
        supplier_abn="33 051 775 556",
        supplier_name=None,
        supplier_country="AU",
        contract_value_aud=None,
        awarded_date=None,
        agency_name=None,
        classification_id=None,
    )
    payload = _build_jsonb_payload(event)
    assert payload["contract_id"] == "ocds-au-CN2"
    assert payload["contract_value_aud"] is None
    assert payload["awarded_date"] is None


# ── ingest_award_event ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ingest_dry_run_returns_none():
    """Dry-run path makes no DB calls and returns None."""
    conn = MagicMock()
    conn.fetchval = AsyncMock()
    conn.fetchrow = AsyncMock()

    result = await ingest_award_event(_au_event(), conn, "batch-1", dry_run=True)
    assert result is None
    conn.fetchval.assert_not_called()
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_skips_non_au_supplier():
    """Non-AU supplier event is filtered (returns None) without DB calls."""
    event = AwardEvent(
        contract_id="ocds-foreign-1",
        supplier_abn=None,  # missing ABN → not AU
        supplier_name="Foreign Vendor",
        supplier_country="US",
        contract_value_aud=100000,
        awarded_date="2026-04-15",
        agency_name="DoH",
        classification_id=None,
    )
    conn = MagicMock()
    conn.fetchval = AsyncMock()
    conn.fetchrow = AsyncMock()

    result = await ingest_award_event(event, conn, "batch-1", dry_run=False)
    assert result is None
    conn.fetchval.assert_not_called()
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_existing_row_takes_update_path():
    """Existing BU row matched by ABN → UPDATE returns id; no INSERT."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value="existing-bu-uuid")
    conn.fetchrow = AsyncMock()

    result = await ingest_award_event(_au_event(), conn, "batch-1", dry_run=False)
    assert result == ("existing-bu-uuid", False)  # was_inserted=False
    conn.fetchval.assert_awaited_once()
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_new_row_takes_insert_path():
    """No existing row (UPDATE returns None) → INSERT path."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=None)  # UPDATE matched 0 rows
    conn.fetchrow = AsyncMock(
        return_value={"id": "new-bu-uuid", "inserted": True}
    )

    result = await ingest_award_event(_au_event(), conn, "batch-1", dry_run=False)
    assert result == ("new-bu-uuid", True)
    conn.fetchval.assert_awaited_once()
    conn.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_insert_returning_handles_conflict_path():
    """INSERT ... ON CONFLICT DO UPDATE — xmax!=0 means conflict, was_inserted=False."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=None)
    conn.fetchrow = AsyncMock(
        return_value={"id": "conflict-bu-uuid", "inserted": False}
    )

    result = await ingest_award_event(_au_event(), conn, "batch-1", dry_run=False)
    assert result == ("conflict-bu-uuid", False)


# ── run_ingest ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_ingest_aggregates_counters():
    """End-to-end: client returns 3 releases (1 AU/valid, 1 non-AU, 1 low-value) → counters reflect."""
    # Build mock client returning 3 OCDS releases
    valid_release = {
        "ocid": "ocds-au-CN1",
        "parties": [
            {
                "name": "Pymble Dental Pty Ltd",
                "roles": ["supplier"],
                "identifier": {"scheme": "AU-ABN", "id": "33051775556"},
                "address": {"countryName": "AU"},
            }
        ],
        "awards": [
            {"value": {"amount": 75000, "currency": "AUD"}, "date": "2026-04-15"}
        ],
    }
    non_au_release = {
        "ocid": "ocds-foreign-1",
        "parties": [
            {
                "name": "US Vendor",
                "roles": ["supplier"],
                "identifier": {"scheme": "AU-ABN", "id": "33051775556"},
                "address": {"countryName": "United States"},
            }
        ],
        "awards": [
            {"value": {"amount": 100000, "currency": "AUD"}, "date": "2026-04-15"}
        ],
    }
    low_value_release = {
        "ocid": "ocds-au-CN2",
        "parties": [
            {
                "name": "Tiny Co Pty Ltd",
                "roles": ["supplier"],
                "identifier": {"scheme": "AU-ABN", "id": "33051775556"},
                "address": {"countryName": "AU"},
            }
        ],
        "awards": [
            {"value": {"amount": 10000, "currency": "AUD"}, "date": "2026-04-15"}
        ],
    }

    mock_client = MagicMock()
    mock_client.fetch_awards = AsyncMock(
        return_value=[valid_release, non_au_release, low_value_release]
    )

    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value="existing-uuid")
    conn.fetchrow = AsyncMock()

    result = await run_ingest(
        date_from=date(2026, 4, 15),
        date_to=date(2026, 4, 15),
        conn=conn,
        value_min_aud=50000,
        dry_run=False,
        client=mock_client,
    )

    assert result.fetched == 3
    assert result.parsed == 3
    assert result.filtered_non_au == 1
    assert result.filtered_low_value == 1
    assert result.updated == 1  # the valid one matched existing row
    assert result.inserted == 0
    assert result.errors == 0


@pytest.mark.asyncio
async def test_run_ingest_handles_client_failure():
    """Client raises → errors counter increments, no parse attempted."""
    mock_client = MagicMock()
    mock_client.fetch_awards = AsyncMock(side_effect=Exception("OCDS timeout"))

    conn = MagicMock()
    result = await run_ingest(
        date_from=date(2026, 4, 15),
        date_to=date(2026, 4, 15),
        conn=conn,
        dry_run=False,
        client=mock_client,
    )
    assert result.errors == 1
    assert result.fetched == 0
    assert result.parsed == 0


@pytest.mark.asyncio
async def test_run_ingest_chunks_wide_range():
    """20-day range chunks into 3 weekly fetches."""
    mock_client = MagicMock()
    mock_client.fetch_awards = AsyncMock(return_value=[])

    conn = MagicMock()
    await run_ingest(
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 20),
        conn=conn,
        dry_run=False,
        client=mock_client,
    )
    # 1-7, 8-14, 15-20 → 3 chunks
    assert mock_client.fetch_awards.await_count == 3


@pytest.mark.asyncio
async def test_run_ingest_dry_run_no_db_calls():
    """Dry run path should not touch the DB connection."""
    valid_release = {
        "ocid": "ocds-au-CN1",
        "parties": [
            {
                "name": "Pymble Dental",
                "roles": ["supplier"],
                "identifier": {"scheme": "AU-ABN", "id": "33051775556"},
                "address": {"countryName": "AU"},
            }
        ],
        "awards": [
            {"value": {"amount": 75000, "currency": "AUD"}, "date": "2026-04-15"}
        ],
    }
    mock_client = MagicMock()
    mock_client.fetch_awards = AsyncMock(return_value=[valid_release])

    conn = MagicMock()
    conn.fetchval = AsyncMock()
    conn.fetchrow = AsyncMock()

    result = await run_ingest(
        date_from=date(2026, 4, 15),
        date_to=date(2026, 4, 15),
        conn=conn,
        dry_run=True,
        client=mock_client,
    )
    # Counters reflect parse but not write
    assert result.parsed == 1
    assert result.inserted == 0
    assert result.updated == 0
    conn.fetchval.assert_not_called()
    conn.fetchrow.assert_not_called()


# ── yesterday_aest ────────────────────────────────────────────────────────────


def test_yesterday_aest_returns_date():
    """yesterday_aest is a date in the past, never today or future."""
    y = yesterday_aest()
    assert isinstance(y, date)
    assert y < date.today() + __import__("datetime").timedelta(days=1)


# ── IngestResult str ──────────────────────────────────────────────────────────


def test_ingest_result_str_includes_all_counters():
    r = IngestResult(fetched=10, parsed=8, filtered_non_au=2, filtered_low_value=1, inserted=3, updated=2, errors=0)
    s = str(r)
    assert "fetched=10" in s
    assert "parsed=8" in s
    assert "non_au_filtered=2" in s
    assert "low_value_filtered=1" in s
    assert "inserted=3" in s
    assert "updated=2" in s
    assert "errors=0" in s
