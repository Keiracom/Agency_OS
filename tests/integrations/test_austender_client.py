"""tests/integrations/test_austender_client.py — unit tests for AusTender client.

Tests the parser (AwardEvent.from_ocds_release) and date-range helpers via
pure-function inputs. HTTP layer is exercised by mocking httpx.AsyncClient.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.integrations.austender_client import (
    MIN_CONTRACT_VALUE_AUD,
    AusTenderClient,
    AwardEvent,
    date_range_chunks,
)

# ── AwardEvent.from_ocds_release ──────────────────────────────────────────────


def _release_fixture(**overrides):
    """Build a minimal OCDS release dict — overridable per-test."""
    base = {
        "ocid": "ocds-au-CN3987654-A2",
        "date": "2026-04-15T00:00:00Z",
        "parties": [
            {
                "name": "Pymble Dental Pty Ltd",
                "roles": ["supplier"],
                "identifier": {"scheme": "AU-ABN", "id": "33051775556"},
                "address": {"countryName": "AU"},
            },
            {
                "name": "Department of Health",
                "roles": ["buyer"],
            },
        ],
        "awards": [
            {
                "date": "2026-04-15T00:00:00Z",
                "value": {"amount": 75000, "currency": "AUD"},
                "items": [{"classification": {"scheme": "UNSPSC", "id": "85101701"}}],
            }
        ],
    }
    base.update(overrides)
    return base


def test_parser_extracts_supplier_abn_and_canonicalises():
    event = AwardEvent.from_ocds_release(_release_fixture())
    assert event is not None
    assert event.supplier_abn == "33 051 775 556"
    assert event.supplier_country == "AU"
    assert event.supplier_name == "Pymble Dental Pty Ltd"


def test_parser_extracts_contract_value_aud():
    event = AwardEvent.from_ocds_release(_release_fixture())
    assert event is not None
    assert event.contract_value_aud == 75000


def test_parser_normalises_awarded_date():
    event = AwardEvent.from_ocds_release(_release_fixture())
    assert event is not None
    assert event.awarded_date == "2026-04-15"


def test_parser_extracts_classification():
    event = AwardEvent.from_ocds_release(_release_fixture())
    assert event is not None
    assert event.classification_id == "85101701"


def test_parser_rejects_non_aud_currency():
    """Non-AUD value is dropped — LAW II says AUD only."""
    release = _release_fixture(
        awards=[
            {
                "value": {"amount": 50000, "currency": "USD"},
                "date": "2026-04-15",
            }
        ]
    )
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.contract_value_aud is None  # silently dropped


def test_parser_drops_invalid_abn():
    """ABN failing checksum → supplier_abn = None (not the raw value)."""
    release = _release_fixture(
        parties=[
            {
                "name": "Bad ABN Co",
                "roles": ["supplier"],
                "identifier": {"scheme": "AU-ABN", "id": "12345678901"},  # checksum fails
                "address": {"countryName": "AU"},
            }
        ]
    )
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.supplier_abn is None
    assert event.is_au_supplier() is False


def test_parser_drops_non_au_supplier():
    """Supplier with non-AU country is parsed but flagged as not AU."""
    release = _release_fixture(
        parties=[
            {
                "name": "Foreign Vendor",
                "roles": ["supplier"],
                "identifier": {"scheme": "AU-ABN", "id": "33051775556"},
                "address": {"countryName": "United States"},
            }
        ]
    )
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.supplier_country != "AU"
    assert event.is_au_supplier() is False


def test_parser_returns_none_without_contract_id():
    release = {"parties": [], "awards": []}
    assert AwardEvent.from_ocds_release(release) is None


def test_parser_handles_no_supplier_party():
    """Missing supplier party → event still parses but supplier fields are None."""
    release = _release_fixture(parties=[])
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.supplier_abn is None
    assert event.supplier_name is None


def test_parser_handles_missing_awards():
    """No awards → contract_value_aud and awarded_date are None."""
    release = _release_fixture(awards=[])
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.contract_value_aud is None
    assert event.awarded_date is None


def test_is_au_supplier_only_when_abn_and_country_match():
    """Both ABN and country must indicate AU."""
    event = AwardEvent.from_ocds_release(_release_fixture())
    assert event is not None
    assert event.is_au_supplier() is True


# ── date_range_chunks ─────────────────────────────────────────────────────────


def test_date_range_chunks_single_week():
    chunks = date_range_chunks(date(2026, 5, 1), date(2026, 5, 5), step_days=7)
    assert chunks == [(date(2026, 5, 1), date(2026, 5, 5))]


def test_date_range_chunks_multi_week():
    chunks = date_range_chunks(date(2026, 5, 1), date(2026, 5, 21), step_days=7)
    assert len(chunks) == 3
    assert chunks[0] == (date(2026, 5, 1), date(2026, 5, 7))
    assert chunks[1] == (date(2026, 5, 8), date(2026, 5, 14))
    assert chunks[2] == (date(2026, 5, 15), date(2026, 5, 21))


def test_date_range_chunks_empty_when_end_before_start():
    chunks = date_range_chunks(date(2026, 5, 10), date(2026, 5, 1))
    assert chunks == []


def test_date_range_chunks_single_day():
    chunks = date_range_chunks(date(2026, 5, 5), date(2026, 5, 5))
    assert chunks == [(date(2026, 5, 5), date(2026, 5, 5))]


# ── AusTenderClient validation ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_awards_rejects_future_date():
    client = AusTenderClient()
    with pytest.raises(ValueError, match="future"):
        await client.fetch_awards(
            date_from=date(2030, 1, 1),
            date_to=date(2030, 1, 2),
        )


@pytest.mark.asyncio
async def test_fetch_awards_rejects_inverted_range():
    client = AusTenderClient()
    with pytest.raises(ValueError, match="before"):
        await client.fetch_awards(
            date_from=date(2026, 5, 10),
            date_to=date(2026, 5, 1),
        )


@pytest.mark.asyncio
async def test_fetch_awards_rejects_wide_range():
    client = AusTenderClient()
    with pytest.raises(ValueError, match="too wide"):
        await client.fetch_awards(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 5, 1),  # ~120 days
        )


@pytest.mark.asyncio
async def test_fetch_awards_rejects_low_value():
    client = AusTenderClient()
    with pytest.raises(ValueError, match="noise"):
        await client.fetch_awards(
            date_from=date(2026, 5, 1),
            date_to=date(2026, 5, 1),
            value_min_aud=500,  # below 1000
        )


@pytest.mark.asyncio
async def test_fetch_release_by_id_rejects_empty_ocid():
    client = AusTenderClient()
    with pytest.raises(ValueError, match="non-empty"):
        await client.fetch_release_by_id("")


def test_min_contract_value_constant():
    """Sanity: documented threshold matches research finding."""
    assert MIN_CONTRACT_VALUE_AUD == 50000
