"""Tests for src/orchestration/flows/free_enrichment_flow.py.

Hermetic — mocks asyncpg pool + FreeEnrichment.run(). Verifies:
  - promote_stage_0_rows issues an UPDATE that targets pipeline_stage IS NULL
    OR pipeline_stage = 0 (and NO other rows).
  - Returns the integer count parsed from the asyncpg "UPDATE N" status.
  - free_enrichment_flow performs the two-phase sweep when promote_stage_0=True.
  - free_enrichment_flow skips the promote step when promote_stage_0=False.
  - Summary surfaces both promoted and enrichment stats.
"""
from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


os.environ.setdefault("DATABASE_URL", "postgresql://stub:stub@stub:5432/stub")

from src.orchestration.flows import free_enrichment_flow as fe_flow_mod  # noqa: E402


def _make_pool(execute_return: str = "UPDATE 17") -> tuple[MagicMock, MagicMock]:
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=execute_return)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=cm)
    pool.close = AsyncMock(return_value=None)
    return pool, conn


# ── promote_stage_0_rows unit tests ─────────────────────────────────────────

def test_promote_stage_0_rows_targets_null_and_zero_only():
    pool, conn = _make_pool("UPDATE 42")
    promoted = asyncio.run(fe_flow_mod.promote_stage_0_rows.fn(pool))

    assert promoted == 42
    sql = conn.execute.await_args.args[0]
    # WHERE clause must specifically target NULL or 0.
    assert "pipeline_stage IS NULL" in sql
    assert "pipeline_stage = 0" in sql
    # SET clause must promote to 1.
    assert "SET pipeline_stage = 1" in sql
    # Must NOT touch other stages.
    assert "pipeline_stage = 2" not in sql
    assert "pipeline_stage > 0" not in sql


def test_promote_stage_0_rows_returns_zero_on_unparseable_update_response():
    pool, conn = _make_pool("not-a-real-update-status")
    promoted = asyncio.run(fe_flow_mod.promote_stage_0_rows.fn(pool))
    assert promoted == 0


# ── free_enrichment_flow end-to-end tests ───────────────────────────────────

def test_flow_runs_two_phases_when_promote_enabled():
    """promote_stage_0=True → both promote + enrich tasks run."""
    pool, conn = _make_pool("UPDATE 100")
    fake_enrich = AsyncMock(return_value={
        "total": 100, "completed": 80, "abn_matched": 60,
        "abn_unmatched": 20, "dns_skipped": 5, "spider_failed": 2, "errors": [],
    })

    with patch.object(fe_flow_mod, "_open_pool", AsyncMock(return_value=pool)), \
         patch.object(fe_flow_mod.run_free_enrichment, "fn", fake_enrich):
        summary = asyncio.run(fe_flow_mod.free_enrichment_flow.fn(
            limit=100, promote_stage_0=True,
        ))

    assert summary["promoted"] == 100
    assert summary["enrichment"]["total"] == 100
    assert summary["enrichment"]["completed"] == 80
    assert summary["promote_stage_0"] is True
    assert summary["limit"] == 100
    fake_enrich.assert_awaited_once_with(100)


def test_flow_skips_promote_when_disabled():
    """promote_stage_0=False → only enrich runs, promoted stays 0, no UPDATE issued."""
    pool, conn = _make_pool("UPDATE 999")  # would be 999 if promote ran
    fake_enrich = AsyncMock(return_value={"total": 0, "completed": 0,
                                          "abn_matched": 0, "abn_unmatched": 0,
                                          "dns_skipped": 0, "spider_failed": 0,
                                          "errors": []})

    with patch.object(fe_flow_mod, "_open_pool", AsyncMock(return_value=pool)), \
         patch.object(fe_flow_mod.run_free_enrichment, "fn", fake_enrich):
        summary = asyncio.run(fe_flow_mod.free_enrichment_flow.fn(
            limit=50, promote_stage_0=False,
        ))

    assert summary["promoted"] == 0
    assert summary["promote_stage_0"] is False
    # Connection.execute should NOT have been called for promote.
    conn.execute.assert_not_called()
    fake_enrich.assert_awaited_once_with(50)


def test_flow_summary_carries_run_start_and_limit():
    pool, _ = _make_pool("UPDATE 0")
    fake_enrich = AsyncMock(return_value={"total": 0})

    with patch.object(fe_flow_mod, "_open_pool", AsyncMock(return_value=pool)), \
         patch.object(fe_flow_mod.run_free_enrichment, "fn", fake_enrich):
        summary = asyncio.run(fe_flow_mod.free_enrichment_flow.fn(limit=200))

    assert "run_start_ts" in summary
    assert summary["limit"] == 200
