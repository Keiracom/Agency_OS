"""Tests for BU stage_metrics conversion vertical recording (Gap #10)."""

from __future__ import annotations

import types
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.cis_service import CISService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(
    *,
    outcome_row=None,
    bu_row=None,
    raise_on_second_execute: Exception | None = None,
) -> AsyncMock:
    """Return a mock AsyncSession whose execute() returns controlled rows."""
    db = AsyncMock()
    db.commit = AsyncMock()

    # Build simple namespace rows
    _update_result = MagicMock()
    _update_result.fetchone.return_value = MagicMock()  # row exists -> update succeeded

    _bu_result = MagicMock()
    _bu_result.fetchone.return_value = bu_row

    call_count = 0

    async def _execute(query, params=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: UPDATE cis_outreach_outcomes
            return _update_result
        if raise_on_second_execute and call_count == 2:
            raise raise_on_second_execute
        if call_count == 2:
            # Second call: SELECT join for BU info
            return _bu_result
        # Third call: UPDATE business_universe
        return MagicMock()

    db.execute = _execute
    return db


def _bu_row(domain: str = "example.com.au", gmb_category: str | None = "Plumber"):
    row = types.SimpleNamespace()
    row.domain = domain
    row.gmb_category = gmb_category
    row.lead_id = uuid.uuid4()
    return row


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conversion_triggers_bu_update():
    """converted event → DB execute called at least 3 times (update + select + update)."""
    svc = CISService()
    activity_id = uuid.uuid4()
    bu = _bu_row()

    execute_calls = []

    update_result = MagicMock()
    update_result.fetchone.return_value = MagicMock()

    bu_result = MagicMock()
    bu_result.fetchone.return_value = bu

    db = AsyncMock()
    db.commit = AsyncMock()

    async def _execute(query, params=None):
        execute_calls.append((str(query)[:80], params))
        if len(execute_calls) == 1:
            return update_result
        if len(execute_calls) == 2:
            return bu_result
        return MagicMock()

    db.execute = _execute

    result = await svc._update_outreach_outcome_impl(db, activity_id, "converted", None)

    assert result["success"] is True
    # First execute: UPDATE cis_outreach_outcomes
    # Second execute: SELECT join
    # Third execute: UPDATE business_universe
    assert len(execute_calls) == 3


@pytest.mark.asyncio
async def test_gmb_category_is_captured():
    """Category from gmb_category column ends up in the BU UPDATE params."""
    svc = CISService()
    activity_id = uuid.uuid4()
    bu = _bu_row(domain="plumbers.com.au", gmb_category="Plumber")

    captured_params = {}

    update_result = MagicMock()
    update_result.fetchone.return_value = MagicMock()
    bu_result = MagicMock()
    bu_result.fetchone.return_value = bu
    db = AsyncMock()
    db.commit = AsyncMock()
    call_n = 0

    async def _execute(query, params=None):
        nonlocal call_n
        call_n += 1
        if call_n == 1:
            return update_result
        if call_n == 2:
            return bu_result
        # Third call = BU update — capture params
        if params:
            captured_params.update(params)
        return MagicMock()

    db.execute = _execute

    await svc._update_outreach_outcome_impl(db, activity_id, "converted", None)

    assert captured_params.get("category") == "Plumber"
    assert captured_params.get("domain") == "plumbers.com.au"


@pytest.mark.asyncio
async def test_unknown_category_defaults_to_unknown():
    """When gmb_category is None, category param should be 'unknown'."""
    svc = CISService()
    activity_id = uuid.uuid4()
    bu = _bu_row(domain="noCat.com.au", gmb_category=None)

    captured_params = {}
    update_result = MagicMock()
    update_result.fetchone.return_value = MagicMock()
    bu_result = MagicMock()
    bu_result.fetchone.return_value = bu
    db = AsyncMock()
    db.commit = AsyncMock()
    call_n = 0

    async def _execute(query, params=None):
        nonlocal call_n
        call_n += 1
        if call_n == 1:
            return update_result
        if call_n == 2:
            return bu_result
        if params:
            captured_params.update(params)
        return MagicMock()

    db.execute = _execute

    await svc._update_outreach_outcome_impl(db, activity_id, "converted", None)

    assert captured_params.get("category") == "unknown"


@pytest.mark.asyncio
async def test_non_conversion_event_skips_bu_update():
    """Non-converted events (e.g. 'opened') must NOT trigger BU update."""
    svc = CISService()
    activity_id = uuid.uuid4()

    execute_calls = []
    update_result = MagicMock()
    update_result.fetchone.return_value = MagicMock()
    db = AsyncMock()
    db.commit = AsyncMock()

    async def _execute(query, params=None):
        execute_calls.append(1)
        return update_result

    db.execute = _execute

    result = await svc._update_outreach_outcome_impl(db, activity_id, "opened", None)

    assert result["success"] is True
    # Only the one UPDATE call, no BU lookup
    assert len(execute_calls) == 1


@pytest.mark.asyncio
async def test_fail_open_on_db_error():
    """DB error in the BU update block must not break conversion recording."""
    svc = CISService()
    activity_id = uuid.uuid4()

    update_result = MagicMock()
    update_result.fetchone.return_value = MagicMock()
    db = AsyncMock()
    db.commit = AsyncMock()
    call_n = 0

    async def _execute(query, params=None):
        nonlocal call_n
        call_n += 1
        if call_n == 1:
            return update_result
        # Simulate DB error on the BU SELECT
        raise RuntimeError("simulated DB failure")

    db.execute = _execute

    result = await svc._update_outreach_outcome_impl(db, activity_id, "converted", None)

    # Must still succeed — fail-open
    assert result["success"] is True
    assert result["activity_id"] == str(activity_id)


@pytest.mark.asyncio
async def test_multiple_conversions_append_not_overwrite():
    """The SQL uses || to append — verify domain param passed correctly for two calls."""
    svc = CISService()
    domain = "repeat.com.au"
    bu = _bu_row(domain=domain, gmb_category="Electrician")

    all_domain_params = []
    update_result = MagicMock()
    update_result.fetchone.return_value = MagicMock()
    bu_result = MagicMock()
    bu_result.fetchone.return_value = bu
    db = AsyncMock()
    db.commit = AsyncMock()

    async def _make_execute():
        call_n = 0

        async def _execute(query, params=None):
            nonlocal call_n
            call_n += 1
            if call_n == 1:
                return update_result
            if call_n == 2:
                return bu_result
            if params and "domain" in params:
                all_domain_params.append(params["domain"])
            return MagicMock()

        return _execute

    for _ in range(2):
        db.execute = await _make_execute()
        await svc._update_outreach_outcome_impl(db, uuid.uuid4(), "converted", None)

    # Both conversion calls should target the same domain
    assert all_domain_params == [domain, domain]
