"""Tests for BU Stage 0 phantom queue fix (gap #11) + backlog driver unpause (gap #1).

Gap #11: backfill_domain_from_gmb task copies gmb_domain → domain so the
         existing promote_stage_0_rows task (which gates on domain IS NOT NULL)
         can advance the ~5022 GMB-discovered rows that have gmb_domain set
         but domain NULL.

Gap #1:  prefect.yaml unpauses bu-closed-loop-flow deployment (paused→false,
         active→true) since S3 ratification is complete (commit 711d38a6).
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from src.orchestration.flows.free_enrichment_flow import (
    backfill_domain_from_gmb,
    free_enrichment_flow,
)

# ---------------------------------------------------------------------------
# Gap #11 — domain backfill task
# ---------------------------------------------------------------------------


def _unwrap(task_obj):
    """Get the underlying coroutine fn from a Prefect-decorated task."""
    return task_obj.fn if hasattr(task_obj, "fn") else task_obj


class TestGap11DomainBackfill:
    @pytest.mark.asyncio
    async def test_backfill_executes_correct_sql(self):
        """Task issues UPDATE that copies gmb_domain → domain where domain IS NULL."""
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 17")
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await _unwrap(backfill_domain_from_gmb)(mock_pool)

        assert result == 17
        sql = mock_conn.execute.call_args[0][0]
        assert "UPDATE business_universe" in sql
        assert "SET domain = gmb_domain" in sql
        assert "WHERE domain IS NULL" in sql
        assert "AND gmb_domain IS NOT NULL" in sql

    @pytest.mark.asyncio
    async def test_backfill_returns_zero_when_no_rows(self):
        """No rows updated → returns 0."""
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await _unwrap(backfill_domain_from_gmb)(mock_pool)
        assert result == 0

    @pytest.mark.asyncio
    async def test_backfill_handles_unparseable_status(self):
        """Malformed UPDATE status string returns 0 instead of crashing."""
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value="GARBAGE")
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await _unwrap(backfill_domain_from_gmb)(mock_pool)
        assert result == 0

    def test_backfill_is_idempotent_via_where_filter(self):
        """SQL WHERE filter ensures already-backfilled rows aren't touched on re-run."""
        fn = _unwrap(backfill_domain_from_gmb)
        source = inspect.getsource(fn)
        # The WHERE clause must filter on domain IS NULL — running twice means
        # the second run sees no candidates (the first run set domain) so 0 rows updated.
        assert "WHERE domain IS NULL" in source
        assert "AND gmb_domain IS NOT NULL" in source

    def test_flow_calls_backfill_before_promote(self):
        """free_enrichment_flow body must call backfill BEFORE promote_stage_0_rows."""
        source = inspect.getsource(_unwrap(free_enrichment_flow))
        backfill_idx = source.find("backfill_domain_from_gmb")
        promote_idx = source.find("promote_stage_0_rows")
        assert backfill_idx > 0, "flow must call backfill_domain_from_gmb"
        assert promote_idx > 0, "flow must call promote_stage_0_rows"
        assert backfill_idx < promote_idx, (
            "backfill must be called BEFORE promote — otherwise promote's "
            "domain IS NOT NULL gate skips the rows we just backfilled"
        )


# ---------------------------------------------------------------------------
# Gap #1 — bu-closed-loop-flow deployment unpaused
# ---------------------------------------------------------------------------


class TestGap1BUClosedLoopUnpaused:
    @pytest.fixture(scope="class")
    def prefect_yaml(self):
        repo_root = Path(__file__).resolve().parents[3]
        with open(repo_root / "prefect.yaml") as f:
            return yaml.safe_load(f)

    def _find_deployment(self, prefect_yaml, name: str) -> dict:
        for dep in prefect_yaml.get("deployments", []):
            if dep.get("name") == name:
                return dep
        raise AssertionError(f"deployment '{name}' not found in prefect.yaml")

    def test_bu_closed_loop_paused_false(self, prefect_yaml):
        """gap #1 — bu-closed-loop-flow must be unpaused."""
        dep = self._find_deployment(prefect_yaml, "bu-closed-loop-flow")
        assert dep.get("paused") is False, (
            "bu-closed-loop-flow must have paused: false (S3 ratified, unpause criteria met)"
        )

    def test_bu_closed_loop_schedule_active(self, prefect_yaml):
        """gap #1 — bu-closed-loop-flow schedule must be active."""
        dep = self._find_deployment(prefect_yaml, "bu-closed-loop-flow")
        schedules = dep.get("schedules", [])
        assert schedules, "bu-closed-loop-flow must have at least one schedule"
        assert schedules[0].get("active") is True, (
            "bu-closed-loop-flow schedule[0] must have active: true"
        )
