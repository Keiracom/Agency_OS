"""Tests for gap #9 — raw ABN value written to business_universe.abn column.

Verifies three things:
1. When _match_abn returns an ABN value, _write_results SQL includes abn=$15
   with the correct value.
2. When match fails (returns None for abn), SQL uses COALESCE so existing abn
   is not clobbered.
3. abn_matched boolean still fires — no regression on existing column writes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch
import json

import pytest

from src.pipeline.free_enrichment import FreeEnrichment


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_conn() -> MagicMock:
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value=None)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    return conn


def make_fe(conn: MagicMock | None = None) -> FreeEnrichment:
    return FreeEnrichment(conn or make_conn())


def _execute_sql(conn: MagicMock) -> str:
    """Return the SQL string from the first conn.execute call."""
    assert conn.execute.called, "conn.execute was never called"
    return conn.execute.call_args[0][0]


def _execute_args(conn: MagicMock) -> tuple:
    """Return positional args passed to conn.execute (index 1 onward)."""
    return conn.execute.call_args[0][1:]


# ─── Test 1: ABN value written when match succeeds ───────────────────────────


@pytest.mark.asyncio
async def test_write_results_includes_abn_value_on_match():
    """When abn_data contains a raw ABN string, _write_results passes it as $15."""
    conn = make_conn()
    fe = make_fe(conn)

    abn_data = {
        "abn_matched": True,
        "abn": "12 345 678 901",
        "gst_registered": True,
        "entity_type": "Company",
        "registration_date": None,
    }
    website_data: dict = {
        "website_cms": None,
        "website_tech_stack": [],
        "website_tracking_codes": [],
        "website_team_names": [],
        "website_contact_emails": [],
    }
    dns_data: dict = {
        "dns_mx_provider": None,
        "dns_has_spf": False,
        "dns_has_dkim": False,
        "email_maturity": None,
    }

    await fe._write_results("bu-001", website_data, dns_data, abn_data)

    sql = _execute_sql(conn)
    args = _execute_args(conn)

    # SQL must reference the abn column with COALESCE
    assert "abn" in sql
    assert "COALESCE($15, abn)" in sql

    # $15 positional arg (index 14 in args tuple — $1 is bu_id at index 0)
    assert args[14] == "12 345 678 901"


# ─── Test 2: No clobber when match fails ─────────────────────────────────────


@pytest.mark.asyncio
async def test_write_results_coalesce_guards_existing_abn_on_no_match():
    """When abn_data has no ABN (None), COALESCE preserves the existing column value."""
    conn = make_conn()
    fe = make_fe(conn)

    abn_data = {
        "abn_matched": False,
        # abn key absent — simulates no match
    }
    website_data: dict = {
        "website_cms": None,
        "website_tech_stack": [],
        "website_tracking_codes": [],
        "website_team_names": [],
        "website_contact_emails": [],
    }
    dns_data: dict = {
        "dns_mx_provider": None,
        "dns_has_spf": False,
        "dns_has_dkim": False,
        "email_maturity": None,
    }

    await fe._write_results("bu-002", website_data, dns_data, abn_data)

    sql = _execute_sql(conn)
    args = _execute_args(conn)

    # COALESCE pattern must be present so existing value is preserved
    assert "COALESCE($15, abn)" in sql

    # $15 must be None — COALESCE(None, abn) => existing abn untouched
    assert args[14] is None


# ─── Test 3: abn_matched boolean still written — no regression ───────────────


@pytest.mark.asyncio
async def test_write_results_still_sets_abn_matched_boolean():
    """abn_matched=$10 still appears in SQL — no regression from adding abn=$15."""
    conn = make_conn()
    fe = make_fe(conn)

    abn_data = {
        "abn_matched": True,
        "abn": "98 765 432 100",
        "gst_registered": False,
        "entity_type": "Sole Trader",
        "registration_date": None,
    }
    website_data: dict = {
        "website_cms": "shopify",
        "website_tech_stack": ["react"],
        "website_tracking_codes": [],
        "website_team_names": [],
        "website_contact_emails": ["info@example.com.au"],
    }
    dns_data: dict = {
        "dns_mx_provider": "google",
        "dns_has_spf": True,
        "dns_has_dkim": True,
        "email_maturity": "professional",
    }

    await fe._write_results("bu-003", website_data, dns_data, abn_data)

    sql = _execute_sql(conn)
    args = _execute_args(conn)

    # abn_matched = $10 must still be present
    assert "abn_matched" in sql
    assert "$10" in sql
    # Positional $10 = index 9 (0-based), after bu_id at index 0
    assert args[9] is True

    # abn at $15 also correct
    assert args[14] == "98 765 432 100"


# ─── Test 4: _abn_result_from_row now includes abn key ───────────────────────


def test_abn_result_from_row_includes_abn_field():
    """_abn_result_from_row populates 'abn' from the DB row."""
    fe = make_fe()

    row = MagicMock()
    row.__getitem__ = lambda self, k: {"gst_registered": True, "entity_type": "Company"}[k]
    row.get = lambda k, default=None: {
        "abn": "11 111 111 111",
        "trading_name": "Test Trading",
        "legal_name": "Test Legal Pty Ltd",
        "registration_date": None,
    }.get(k, default)

    result = fe._abn_result_from_row(row, "Test Legal", "domain_keywords")

    assert "abn" in result
    assert result["abn"] == "11 111 111 111"
    assert result["abn_matched"] is True
