"""Unit tests for scripts/abn_match_sweep.py.

These tests mock asyncpg so the suite stays hermetic — no DB needed.
Logic under test:
  - _resolve_search_name() picks the best available name from the BU row.
  - sweep() (via mocked pool) writes abn / abn_matched / abn_status_code
    when match confidence >= threshold and dry_run=False.
  - Low-confidence matches are skipped.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Load the script as a module under the name `abn_match_sweep` without
# requiring scripts/ to be a package. spec_from_file_location keeps test
# isolation from production import paths.
_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "abn_match_sweep.py"
_spec = importlib.util.spec_from_file_location("abn_match_sweep", _SCRIPT_PATH)
abn_match_sweep = importlib.util.module_from_spec(_spec)
sys.modules["abn_match_sweep"] = abn_match_sweep
_spec.loader.exec_module(abn_match_sweep)


# ── _resolve_search_name ────────────────────────────────────────────────────

class _Row(dict):
    """asyncpg.Record-like dict with .get() semantics used by the sweep code."""


def test_resolve_search_name_prefers_legal_name():
    """2026-04-26 production-schema fix: legal_name -> display_name fallback chain.
    trading_name / abr_trading_name dropped — neither exists on production BU."""
    row = _Row(legal_name="ABC Pty Ltd", display_name="abc.com.au")
    assert abn_match_sweep._resolve_search_name(row) == "ABC Pty Ltd"


def test_resolve_search_name_falls_back_to_display_name():
    row = _Row(legal_name=None, display_name="example.com.au")
    assert abn_match_sweep._resolve_search_name(row) == "example.com.au"


def test_resolve_search_name_returns_none_when_empty():
    row = _Row(legal_name=None, display_name=None)
    assert abn_match_sweep._resolve_search_name(row) is None


# ── sweep() — happy path with mocked pool ──────────────────────────────────

def _make_pool(rows: list[_Row], match_row: dict | None) -> MagicMock:
    """Build a MagicMock asyncpg pool whose acquire() yields a conn whose
    fetch() returns `rows` and fetchrow() returns the (row-shaped) match."""
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=rows)
    if match_row is None:
        conn.fetchrow = AsyncMock(return_value=None)
    else:
        # asyncpg.Record-like — supports __getitem__
        rec = MagicMock()
        rec.__getitem__.side_effect = lambda key: match_row[key]
        conn.fetchrow = AsyncMock(return_value=rec)
    conn.execute = AsyncMock(return_value="UPDATE 1")

    pool_cm = MagicMock()
    pool_cm.__aenter__ = AsyncMock(return_value=conn)
    pool_cm.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=pool_cm)
    pool.close = AsyncMock(return_value=None)
    return pool, conn


def test_sweep_writes_match_when_confidence_above_threshold():
    bu_id = "00000000-0000-0000-0000-000000000001"
    rows = [_Row(id=bu_id, domain="example.com.au", state="NSW",
                 legal_name="Example Pty Ltd", display_name=None)]
    match = {
        "abn": "12345678901",
        "legal_name": "Example Pty Ltd",
        "trading_name": "Example Dental",
        "entity_type": "Company",
        "registration_date": None,
        "state": "NSW",
        "confidence": 0.92,
    }
    pool, conn = _make_pool(rows, match)

    async def _fake_create_pool(*_a, **_kw):
        return pool

    with patch.object(abn_match_sweep.asyncpg, "create_pool", _fake_create_pool):
        stats = asyncio.run(abn_match_sweep.sweep(
            db_url="postgresql://stub",
            batch_size=10,
            min_confidence=0.7,
            dry_run=False,
            bu_ids=None,
        ))

    assert stats == {"total": 1, "matched": 1, "skipped_no_name": 0,
                     "skipped_low_conf": 0, "errors": 0}
    # _apply_match should have run an UPDATE on business_universe with the
    # production-schema columns (2026-04-26 fix): abn, abn_matched=TRUE,
    # abn_status, abr_matched_at — confirmed via live introspection.
    update_calls = [c for c in conn.execute.await_args_list
                    if "UPDATE business_universe" in c.args[0]]
    assert update_calls, "expected at least one BU UPDATE"
    update_sql = update_calls[0].args[0]
    assert "abn_matched     = TRUE" in update_sql
    assert "abn_status" in update_sql
    assert "abr_matched_at" in update_sql


def test_sweep_skips_low_confidence_match():
    bu_id = "00000000-0000-0000-0000-000000000002"
    rows = [_Row(id=bu_id, domain="weak.com.au", state="VIC",
                 legal_name="Weak Match", display_name=None)]
    match = {
        "abn": "99999999999", "legal_name": "X", "trading_name": "Y",
        "entity_type": None, "registration_date": None, "state": "VIC",
        "confidence": 0.42,  # below threshold
    }
    pool, conn = _make_pool(rows, match)

    async def _fake_create_pool(*_a, **_kw):
        return pool

    with patch.object(abn_match_sweep.asyncpg, "create_pool", _fake_create_pool):
        stats = asyncio.run(abn_match_sweep.sweep(
            db_url="postgresql://stub",
            batch_size=10,
            min_confidence=0.7,
            dry_run=False,
            bu_ids=None,
        ))

    assert stats["matched"] == 0
    assert stats["skipped_low_conf"] == 1
    # No UPDATE should have hit business_universe.
    assert not any("UPDATE business_universe" in c.args[0]
                   for c in conn.execute.await_args_list)


def test_sweep_skips_row_with_no_resolvable_name():
    rows = [_Row(id="00000000-0000-0000-0000-000000000003",
                 domain="anon.com.au", state="QLD",
                 legal_name=None, display_name=None)]
    pool, conn = _make_pool(rows, match_row=None)

    async def _fake_create_pool(*_a, **_kw):
        return pool

    with patch.object(abn_match_sweep.asyncpg, "create_pool", _fake_create_pool):
        stats = asyncio.run(abn_match_sweep.sweep(
            db_url="postgresql://stub",
            batch_size=10,
            min_confidence=0.7,
            dry_run=False,
            bu_ids=None,
        ))

    assert stats == {"total": 1, "matched": 0, "skipped_no_name": 1,
                     "skipped_low_conf": 0, "errors": 0}


def test_sweep_dry_run_does_not_write():
    bu_id = "00000000-0000-0000-0000-000000000004"
    rows = [_Row(id=bu_id, domain="dry.com.au", state="NSW",
                 legal_name="Dry Run", display_name=None)]
    match = {
        "abn": "11111111111", "legal_name": "X", "trading_name": "Y",
        "entity_type": None, "registration_date": None, "state": "NSW",
        "confidence": 0.95,
    }
    pool, conn = _make_pool(rows, match)

    async def _fake_create_pool(*_a, **_kw):
        return pool

    with patch.object(abn_match_sweep.asyncpg, "create_pool", _fake_create_pool):
        stats = asyncio.run(abn_match_sweep.sweep(
            db_url="postgresql://stub",
            batch_size=10,
            min_confidence=0.7,
            dry_run=True,
            bu_ids=None,
        ))

    # Total counted, but no match recorded and no UPDATE executed.
    assert stats["total"] == 1
    assert stats["matched"] == 0
    assert not any("UPDATE business_universe" in c.args[0]
                   for c in conn.execute.await_args_list)


def test_resolve_db_url_normalises_sqlalchemy_form(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pw@host:5432/db",
    )
    assert abn_match_sweep._resolve_db_url() == "postgresql://user:pw@host:5432/db"


def test_resolve_db_url_raises_when_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(SystemExit):
        abn_match_sweep._resolve_db_url()
