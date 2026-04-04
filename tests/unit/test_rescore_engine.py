"""
Contract: tests/unit/test_rescore_engine.py
Purpose: Unit tests for RescoreEngine — promote/reject/skip logic and dry-run safety.
Layer: tests
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.rescore_engine import DEFAULT_RESCORE_THRESHOLD, RescoreEngine, RescoreResult


def _make_row(
    bu_id: str = "test-id-1",
    filter_reason: str | None = "low_score",
    gmb_rating: float = 4.2,
    gmb_review_count: int = 80,
    dfs_paid_etv: float = 200.0,
    dfs_organic_etv: float = 600.0,
) -> MagicMock:
    """Build a mock asyncpg.Record."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "id": bu_id,
        "filter_reason": filter_reason,
        "gmb_rating": gmb_rating,
        "gmb_review_count": gmb_review_count,
        "dfs_paid_etv": dfs_paid_etv,
        "dfs_organic_etv": dfs_organic_etv,
        "backlinks_count": 0,
        "updated_at": None,
        "domain": "example.com.au",
        "gmb_category": "Plumber",
        "pipeline_stage": -1,
    }[key]
    return row


@pytest.mark.asyncio
async def test_promotes_qualifying_reject():
    """Row with budget+pain score above threshold should be promoted."""
    conn = AsyncMock()
    engine = RescoreEngine(conn)
    engine._threshold = DEFAULT_RESCORE_THRESHOLD  # set directly

    # High organic_etv + good GMB rating → budget≥25, pain≥20 → combined ≥ 15
    row = _make_row(
        filter_reason="low_score",
        gmb_rating=4.2,
        gmb_review_count=80,
        dfs_organic_etv=600.0,
        dfs_paid_etv=0.0,
    )

    outcome = await engine._rescore_row(row)
    assert outcome == "promoted"


@pytest.mark.asyncio
async def test_skips_au_filter_rejects():
    """Rows with filter_reason='au_domain_filter' must always return 'skip'."""
    conn = AsyncMock()
    engine = RescoreEngine(conn)
    engine._threshold = DEFAULT_RESCORE_THRESHOLD

    row = _make_row(
        filter_reason="au_domain_filter",
        dfs_organic_etv=9999.0,  # would pass if scored
        gmb_rating=4.9,
        gmb_review_count=500,
    )

    outcome = await engine._rescore_row(row)
    assert outcome == "skip"


@pytest.mark.asyncio
async def test_dry_run_makes_no_db_writes():
    """dry_run=True must not call conn.execute for any writes."""
    conn = AsyncMock()

    # _fetch_rejects returns two rows (one promoted, one rejected)
    promoted_row = _make_row(
        bu_id="promote-me",
        filter_reason="low_score",
        gmb_rating=4.2,
        gmb_review_count=80,
        dfs_organic_etv=600.0,
    )
    rejected_row = _make_row(
        bu_id="still-bad",
        filter_reason="low_score",
        gmb_rating=0.0,
        gmb_review_count=0,
        dfs_organic_etv=0.0,
        dfs_paid_etv=0.0,
    )

    engine = RescoreEngine(conn)

    with (
        patch.object(engine, "_load_threshold", AsyncMock(return_value=DEFAULT_RESCORE_THRESHOLD)),
        patch.object(engine, "_fetch_rejects", AsyncMock(return_value=[promoted_row, rejected_row])),
    ):
        result = await engine.run(dry_run=True)

    conn.execute.assert_not_called()
    assert result.dry_run is True
    assert result.promoted + result.still_rejected >= 1


@pytest.mark.asyncio
async def test_rescore_result_counts_correct():
    """With 3 rows (1 promoted, 1 still_rejected, 1 skipped), counts must match."""
    conn = AsyncMock()

    promoted_row = _make_row(
        bu_id="r1",
        filter_reason="low_score",
        gmb_rating=4.2,
        gmb_review_count=80,
        dfs_organic_etv=600.0,
    )
    rejected_row = _make_row(
        bu_id="r2",
        filter_reason="low_score",
        gmb_rating=0.0,
        gmb_review_count=0,
        dfs_organic_etv=0.0,
        dfs_paid_etv=0.0,
    )
    skipped_row = _make_row(
        bu_id="r3",
        filter_reason="au_domain_filter",
        dfs_organic_etv=9999.0,
    )

    engine = RescoreEngine(conn)

    with (
        patch.object(engine, "_load_threshold", AsyncMock(return_value=DEFAULT_RESCORE_THRESHOLD)),
        patch.object(engine, "_fetch_rejects", AsyncMock(return_value=[promoted_row, rejected_row, skipped_row])),
    ):
        result = await engine.run(dry_run=False)

    assert result.promoted == 1
    assert result.still_rejected == 1
    assert result.skipped == 1
    assert result.total_evaluated == 3
