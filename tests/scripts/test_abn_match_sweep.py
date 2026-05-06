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
    """Build a MagicMock asyncpg pool whose acquire() returns a conn whose
    fetch() returns `rows` and fetchrow() returns the (row-shaped) match.

    2026-04-26: sweep() switched from `async with pool.acquire() as conn`
    to explicit `await pool.acquire()` + `await pool.release(conn)` so
    the retry-on-drop wrapper can re-acquire on connection drop. Mock
    pool now exposes acquire/release as AsyncMocks accordingly.
    """
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

    pool = MagicMock()
    pool.acquire = AsyncMock(return_value=conn)
    pool.release = AsyncMock(return_value=None)
    pool.close = AsyncMock(return_value=None)
    return pool, conn


def test_sweep_writes_match_when_confidence_above_threshold():
    bu_id = "00000000-0000-0000-0000-000000000001"
    rows = [
        _Row(
            id=bu_id,
            domain="example.com.au",
            state="NSW",
            legal_name="Example Pty Ltd",
            display_name=None,
        )
    ]
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
        stats = asyncio.run(
            abn_match_sweep.sweep(
                db_url="postgresql://stub",
                batch_size=10,
                min_confidence=0.7,
                dry_run=False,
                bu_ids=None,
            )
        )

    assert stats == {
        "total": 1,
        "matched": 1,
        "skipped_no_name": 0,
        "skipped_low_conf": 0,
        "errors": 0,
    }
    # _apply_match should have run an UPDATE on business_universe with the
    # production-schema columns (2026-04-26 fix): abn, abn_matched=TRUE,
    # abn_status, abr_matched_at — confirmed via live introspection.
    update_calls = [
        c for c in conn.execute.await_args_list if "UPDATE business_universe" in c.args[0]
    ]
    assert update_calls, "expected at least one BU UPDATE"
    update_sql = update_calls[0].args[0]
    assert "abn_matched     = TRUE" in update_sql
    assert "abn_status" in update_sql
    assert "abr_matched_at" in update_sql


def test_sweep_skips_low_confidence_match():
    bu_id = "00000000-0000-0000-0000-000000000002"
    rows = [
        _Row(
            id=bu_id, domain="weak.com.au", state="VIC", legal_name="Weak Match", display_name=None
        )
    ]
    match = {
        "abn": "99999999999",
        "legal_name": "X",
        "trading_name": "Y",
        "entity_type": None,
        "registration_date": None,
        "state": "VIC",
        "confidence": 0.42,  # below threshold
    }
    pool, conn = _make_pool(rows, match)

    async def _fake_create_pool(*_a, **_kw):
        return pool

    with patch.object(abn_match_sweep.asyncpg, "create_pool", _fake_create_pool):
        stats = asyncio.run(
            abn_match_sweep.sweep(
                db_url="postgresql://stub",
                batch_size=10,
                min_confidence=0.7,
                dry_run=False,
                bu_ids=None,
            )
        )

    assert stats["matched"] == 0
    assert stats["skipped_low_conf"] == 1
    # No UPDATE should have hit business_universe.
    assert not any("UPDATE business_universe" in c.args[0] for c in conn.execute.await_args_list)


def test_sweep_skips_row_with_no_resolvable_name():
    rows = [
        _Row(
            id="00000000-0000-0000-0000-000000000003",
            domain="anon.com.au",
            state="QLD",
            legal_name=None,
            display_name=None,
        )
    ]
    pool, conn = _make_pool(rows, match_row=None)

    async def _fake_create_pool(*_a, **_kw):
        return pool

    with patch.object(abn_match_sweep.asyncpg, "create_pool", _fake_create_pool):
        stats = asyncio.run(
            abn_match_sweep.sweep(
                db_url="postgresql://stub",
                batch_size=10,
                min_confidence=0.7,
                dry_run=False,
                bu_ids=None,
            )
        )

    assert stats == {
        "total": 1,
        "matched": 0,
        "skipped_no_name": 1,
        "skipped_low_conf": 0,
        "errors": 0,
    }


def test_sweep_dry_run_does_not_write():
    bu_id = "00000000-0000-0000-0000-000000000004"
    rows = [
        _Row(id=bu_id, domain="dry.com.au", state="NSW", legal_name="Dry Run", display_name=None)
    ]
    match = {
        "abn": "11111111111",
        "legal_name": "X",
        "trading_name": "Y",
        "entity_type": None,
        "registration_date": None,
        "state": "NSW",
        "confidence": 0.95,
    }
    pool, conn = _make_pool(rows, match)

    async def _fake_create_pool(*_a, **_kw):
        return pool

    with patch.object(abn_match_sweep.asyncpg, "create_pool", _fake_create_pool):
        stats = asyncio.run(
            abn_match_sweep.sweep(
                db_url="postgresql://stub",
                batch_size=10,
                min_confidence=0.7,
                dry_run=True,
                bu_ids=None,
            )
        )

    # Total counted, but no match recorded and no UPDATE executed.
    assert stats["total"] == 1
    assert stats["matched"] == 0
    assert not any("UPDATE business_universe" in c.args[0] for c in conn.execute.await_args_list)


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


def test_select_unmatched_bus_applies_W1_filter_on_display_name():
    """Option W1 regression test (2026-04-26 dual-concur, dispatch dispatched
    after the v4 pre-launch halt revealed all 8501 unmatched rows have
    legal_name=NULL): _select_unmatched_bus must include the pre-filter
    clauses on DISPLAY_NAME (the actual name source for unmatched GMB-sourced
    rows). Filter skips:
      - NULL display_name
      - display_name shorter than 12 trimmed chars
      - display_name with no Latin letters (e.g., CJK, Cyrillic)
      - display_name matching common-word stopword set that triggers GIN
        trigram bitmap blowout (home/store/shop/page/index/services/world/
        center/online/business/company/group)
    Eliminates the slow-tail dead-time region observed in v3.

    Catches the v4 ordering/column bug (filter applied to wrong column).
    """
    captured_sql: list[str] = []

    conn = MagicMock()

    async def _capture_fetch(sql, *args, **kwargs):
        captured_sql.append(sql)
        return []

    conn.fetch = AsyncMock(side_effect=_capture_fetch)

    # Default branch — no bu_ids.
    asyncio.run(
        abn_match_sweep._select_unmatched_bus(
            conn,
            batch_size=10,
            bu_ids=None,
        )
    )
    # bu_ids branch.
    asyncio.run(
        abn_match_sweep._select_unmatched_bus(
            conn,
            batch_size=10,
            bu_ids=["00000000-0000-0000-0000-000000000001"],
        )
    )

    assert len(captured_sql) == 2
    for sql in captured_sql:
        assert "abn_matched IS NOT TRUE" in sql
        # W1 filter is on display_name, not legal_name (per v4 pre-launch
        # finding that all unmatched rows have legal_name=NULL).
        assert "display_name IS NOT NULL" in sql
        assert "length(trim(display_name)) >= 12" in sql
        assert "display_name ~ '[a-zA-Z]'" in sql
        # Stopword negative-match clause (case-insensitive regex).
        assert "display_name !~*" in sql
        # Spot-check a few stopwords from the set.
        assert "home" in sql
        assert "company" in sql
        assert "services" in sql
        # Defense against accidental regression to legal_name column.
        assert "legal_name IS NOT NULL" not in sql
        assert "length(trim(legal_name))" not in sql


def test_statement_timeout_is_set_AFTER_initial_bulk_fetch():
    """Cat-B v2 regression test (2026-04-26): SET statement_timeout='30s'
    must NOT fire before the initial _select_unmatched_bus bulk fetch.

    Why: the bulk fetch is a seq scan over business_universe (no index
    on `abn_matched IS NOT TRUE`) and routinely exceeds 30s on production.
    My v1 fix bundled the SET into _init_session which ran BEFORE the
    bulk fetch — crashed in 4 minutes with QueryCanceledError, zero
    rows processed (see outbox task_error_2026-04-26T12-35Z_abn_sweep_v2.json).

    This test enforces the ordering invariant: ANY 'SET statement_timeout'
    statement issued by sweep() must come AFTER the first conn.fetch() call.
    """
    bu_id = "00000000-0000-0000-0000-000000000099"
    rows = [
        _Row(
            id=bu_id,
            domain="ordering.com.au",
            state="NSW",
            legal_name="Ordering Test",
            display_name=None,
        )
    ]
    pool, conn = _make_pool(rows, match_row=None)  # no match → SKIP low_conf

    # Capture the call order across both fetch and execute on the conn mock.
    call_order: list[str] = []
    original_fetch = conn.fetch
    original_execute = conn.execute

    async def _record_fetch(*args, **kwargs):
        call_order.append(f"fetch:{(args[0] if args else '')[:200]!r}")
        return await original_fetch(*args, **kwargs)

    async def _record_execute(*args, **kwargs):
        call_order.append(f"execute:{(args[0] if args else '')[:200]!r}")
        return await original_execute(*args, **kwargs)

    conn.fetch = AsyncMock(side_effect=_record_fetch)
    conn.execute = AsyncMock(side_effect=_record_execute)

    async def _fake_create_pool(*_a, **_kw):
        return pool

    with patch.object(abn_match_sweep.asyncpg, "create_pool", _fake_create_pool):
        asyncio.run(
            abn_match_sweep.sweep(
                db_url="postgresql://stub",
                batch_size=10,
                min_confidence=0.7,
                dry_run=False,
                bu_ids=None,
            )
        )

    # Find indexes of the first bulk fetch and the first statement_timeout SET.
    bulk_fetch_idx = next(
        (
            i
            for i, c in enumerate(call_order)
            if c.startswith("fetch:") and "business_universe" in c
        ),
        None,
    )
    timeout_set_idx = next(
        (
            i
            for i, c in enumerate(call_order)
            if c.startswith("execute:") and "statement_timeout" in c
        ),
        None,
    )
    assert bulk_fetch_idx is not None, (
        f"Expected a fetch against business_universe; saw {call_order}"
    )
    assert timeout_set_idx is not None, f"Expected a SET statement_timeout call; saw {call_order}"
    assert bulk_fetch_idx < timeout_set_idx, (
        "ORDERING VIOLATION: SET statement_timeout fired BEFORE the initial "
        f"bulk fetch.\n  bulk_fetch_idx={bulk_fetch_idx}\n  "
        f"timeout_set_idx={timeout_set_idx}\n  call_order={call_order}"
    )
