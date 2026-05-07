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
    """No awards AND no contracts → contract_value_aud is None.

    awarded_date now falls back to release.date when neither
    contracts.dateSigned nor awards.date is set — that's the most truthful
    timestamp the live feed gives us, so we don't drop the row.
    """
    release = _release_fixture(awards=[])
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.contract_value_aud is None
    assert event.awarded_date == "2026-04-15"


def test_parser_reads_value_from_contracts_first():
    """When both contract.value and award.value exist, contract.value
    wins — matches the live api.tenders.gov.au shape (PR #587/#588 fix)."""
    release = _release_fixture(
        contracts=[
            {
                "id": "CN-1",
                "dateSigned": "2026-04-15T00:00:00Z",
                "value": {"amount": "150000.50", "currency": "AUD"},
            }
        ],
        awards=[
            {
                "date": "2026-04-15T00:00:00Z",
                "value": {"amount": 75000, "currency": "AUD"},
            }
        ],
    )
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.contract_value_aud == 150000


def test_parser_accepts_string_amounts():
    """Live feed sends value.amount as a JSON string (e.g. '607987.88').
    Parser must coerce — not crash on the type mismatch."""
    release = _release_fixture(
        contracts=[
            {
                "id": "CN-2",
                "dateSigned": "2026-04-15T00:00:00Z",
                "value": {"amount": "607987.88", "currency": "AUD"},
            }
        ],
        awards=[],
    )
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.contract_value_aud == 607987


def test_parser_reads_abn_from_additional_identifiers():
    """Live feed puts the AU-ABN under `additionalIdentifiers` (array),
    not the spec-bare `identifier` field. Parser must walk both."""
    release = _release_fixture(
        parties=[
            {
                "name": "Hamilton Company Australia",
                "roles": ["supplier"],
                "additionalIdentifiers": [
                    {"id": "50674984886", "scheme": "AU-ABN"},
                ],
                "address": {"countryName": "AUSTRALIA"},
            },
            {"name": "Buyer", "roles": ["procuringEntity"]},
        ],
    )
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.supplier_abn is not None
    assert event.supplier_country == "AU"
    assert event.is_au_supplier() is True


def test_parser_normalises_uppercase_australia_country():
    """countryName comes through as 'AUSTRALIA' on the live feed.
    Match must be case-insensitive."""
    release = _release_fixture(
        parties=[
            {
                "name": "Acme",
                "roles": ["supplier"],
                "identifier": {"scheme": "AU-ABN", "id": "33051775556"},
                "address": {"countryName": "AUSTRALIA"},
            },
        ],
    )
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.supplier_country == "AU"


def test_parser_recognises_procuringEntity_role():
    """Live feed uses role 'procuringEntity' (OCDS extension) instead of
    the spec-bare 'buyer'. Parser must accept both for buyer-name lookup."""
    release = _release_fixture(
        parties=[
            {
                "name": "Acme Pty Ltd",
                "roles": ["supplier"],
                "identifier": {"scheme": "AU-ABN", "id": "33051775556"},
                "address": {"countryName": "AU"},
            },
            {
                "name": "Department of Defence",
                "roles": ["procuringEntity"],
            },
        ],
    )
    event = AwardEvent.from_ocds_release(release)
    assert event is not None
    assert event.agency_name == "Department of Defence"


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
async def test_fetch_awards_accepts_wide_range():
    """The legacy WAF-fronted endpoint timed out on >14-day ranges, so the
    client used to raise. api.tenders.gov.au paginates with links.next, so
    wide ranges are now valid input — validation must NOT raise."""
    client = AusTenderClient()
    # Don't actually hit the network here — patch httpx so this stays fast.
    from unittest.mock import AsyncMock, patch
    fake_response = AsyncMock()
    fake_response.raise_for_status = lambda: None
    fake_response.json = lambda: {"releases": [], "links": {}}
    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.get = AsyncMock(return_value=fake_response)
    with patch("httpx.AsyncClient", return_value=fake_client):
        result = await client.fetch_awards(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 4, 30),  # ~120 days — old code would raise
        )
    assert result == []


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


# ── Live smoke (network) ─────────────────────────────────────────────────────
# Process lesson from PR #587/#588: connector unit tests passed against the
# WAF-blocked legacy URL because every HTTP call was mocked. Mocks pass
# against any URL. We add at least one live smoke that hits the real
# api.tenders.gov.au feed — guarded by `live` marker so default `pytest`
# skips it; CI / manual verification runs `pytest -m live`.


@pytest.mark.live
@pytest.mark.asyncio
async def test_fetch_awards_live_smoke_returns_releases():
    """Hit api.tenders.gov.au for the last 7 closed days, ≥AUD 50k.

    Asserts only that the call succeeds and returns ≥1 release — the
    point is to catch URL/path/format breakage early. The number of
    releases on any given week varies; the only zero-tolerance signal
    is total breakage (URL change, WAF block, schema rename)."""
    from datetime import timedelta

    today = date.today()
    awards = await AusTenderClient().fetch_awards(
        date_from=today - timedelta(days=7),
        date_to=today - timedelta(days=1),
        value_min_aud=50_000,
    )
    assert isinstance(awards, list)
    assert len(awards) > 0, (
        "live AusTender feed returned 0 releases — "
        "URL/path/format may have regressed"
    )
    # Spot-check the payload shape so we notice if OCDS schema drifts.
    sample = awards[0]
    assert "ocid" in sample or "id" in sample
    assert "contracts" in sample or "awards" in sample
