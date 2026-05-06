"""SQL spot-check fixtures for layer_3_bulk_filter filter_reason population.

Verifies that every drop branch in Layer3BulkFilter.run() writes a *specific*
filter_reason to business_universe (BU Closed-Loop S1 acceptance gate).

We do NOT hit a real DB; we mock asyncpg.Connection and assert that the SQL
UPDATE issued for each drop branch carries the expected filter_reason value.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.pipeline.layer_3_bulk_filter import Layer3BulkFilter


def _make_conn(stage1_rows: list[dict]) -> MagicMock:
    """Build a mock asyncpg conn for Layer3 happy-path/drop-path tests."""
    conn = MagicMock()
    # _run() executes UPDATE for no_domain advancement, then SELECT, then per-row UPDATEs.
    conn.execute = AsyncMock(return_value="UPDATE 0")
    conn.fetch = AsyncMock(return_value=stage1_rows)
    return conn


def _make_signal_config():
    """Return a stand-in config object with default thresholds."""
    cfg = MagicMock()
    cfg.enrichment_gates = {}  # use defaults
    return cfg


def _patch_signal_repo(monkeypatch):
    repo = MagicMock()
    repo.get_config = AsyncMock(return_value=_make_signal_config())
    monkeypatch.setattr(
        "src.pipeline.layer_3_bulk_filter.SignalConfigRepository",
        lambda conn: repo,
    )


def _captured_filter_reasons(conn: MagicMock) -> list[str]:
    """Pull the filter_reason argument from every UPDATE call that wrote one."""
    reasons: list[str] = []
    for call in conn.execute.await_args_list:
        sql = call.args[0] if call.args else ""
        if "filter_reason" not in sql:
            continue
        if "pipeline_stage = -1" in sql or "pipeline_stage = 2" in sql:
            # drop / pass branch — second positional arg is filter_reason
            if len(call.args) >= 3:
                reasons.append(call.args[2])
        else:
            # batch-error marker branch — second positional arg is reason
            if len(call.args) >= 3:
                reasons.append(call.args[2])
    return reasons


@pytest.mark.asyncio
async def test_layer3_drop_below_threshold_writes_specific_filter_reason(monkeypatch):
    """Threshold-fail drop branch writes a *specific* reason naming which
    threshold(s) failed (not the old generic 'bulk_metrics_below_threshold')."""
    bu_id = "11111111-1111-1111-1111-111111111111"
    rows = [{"id": bu_id, "domain": "weak.com.au"}]
    conn = _make_conn(rows)

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(
        return_value=[
            # Returned by DFS, but every metric is below threshold → drop.
            {
                "domain": "weak.com.au",
                "organic_etv": 0.0,
                "paid_etv": 0.0,
                "backlinks_count": 0,
                "domain_rank": 0,
            },
        ]
    )

    _patch_signal_repo(monkeypatch)
    engine = Layer3BulkFilter(conn, dfs)
    stats = await engine.run("dental")
    assert stats.rejected == 1

    reasons = _captured_filter_reasons(conn)
    assert reasons, "expected at least one filter_reason write on drop"
    matched = [r for r in reasons if r.startswith("bulk_metrics_below_threshold:")]
    assert matched, f"expected specific below_threshold reason; got {reasons}"
    # Specific axes must appear so analytics can group by failure type.
    assert "organic_etv" in matched[0]
    assert "paid_etv" in matched[0]
    assert "backlinks" in matched[0]


@pytest.mark.asyncio
async def test_layer3_missing_from_response_uses_distinct_reason(monkeypatch):
    """Domain absent from DFS bulk response → distinct reason, not the
    generic threshold reason."""
    bu_id = "22222222-2222-2222-2222-222222222222"
    rows = [{"id": bu_id, "domain": "ghost.com.au"}]
    conn = _make_conn(rows)

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(return_value=[])  # ghost domain not returned

    _patch_signal_repo(monkeypatch)
    engine = Layer3BulkFilter(conn, dfs)
    stats = await engine.run("dental")
    assert stats.rejected == 1

    reasons = _captured_filter_reasons(conn)
    assert "bulk_metrics_missing_from_response" in reasons


@pytest.mark.asyncio
async def test_layer3_batch_error_writes_marker_filter_reason(monkeypatch):
    """DFS bulk-call exception writes a batch-error marker on every domain in
    the failed batch (pipeline_stage stays at 1 — these are not drops)."""
    rows = [
        {"id": "33333333-3333-3333-3333-333333333333", "domain": "a.com.au"},
        {"id": "44444444-4444-4444-4444-444444444444", "domain": "b.com.au"},
    ]
    conn = _make_conn(rows)

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(side_effect=RuntimeError("DFS down"))

    _patch_signal_repo(monkeypatch)
    engine = Layer3BulkFilter(conn, dfs)
    stats = await engine.run("dental")
    assert stats.errors  # batch error logged in stats

    reasons = _captured_filter_reasons(conn)
    matched = [r for r in reasons if r.startswith("bulk_metrics_batch_error:")]
    assert len(matched) >= 2, f"expected batch-error marker per domain; got {reasons}"
    assert "RuntimeError" in matched[0]
