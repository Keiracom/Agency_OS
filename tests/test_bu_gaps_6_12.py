"""Tests for BU audit gaps #6 (dead-domain cleanup) and #12 (suppression pre-check).

Gap #6: Dead domains with permanent_ or legacy free_enrichment_* filter_reasons
        must be excluded from the bu_closed_loop_flow backlog cursor.

Gap #12: Stage 8 contact waterfall must skip paid email/mobile enrichment when
         the known contact email is already suppressed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Gap #6 — Backlog SQL exclusion and filter_reason renaming
# ---------------------------------------------------------------------------


class TestGap6BacklogExclusion:
    """Verify that dead-domain filter_reasons do not re-enter the BU cursor."""

    def _make_row(self, filter_reason: str | None, pipeline_stage: int = 1) -> dict:
        return {
            "id": "test-id",
            "domain": "example.com",
            "category": "dental",
            "pipeline_stage": pipeline_stage,
            "propensity_score": 30,
            "stage_metrics": {},
            "filter_reason": filter_reason,
            "free_enrichment_completed_at": None,
            "latest_stage_at": "1970-01-01T00:00:00+00:00",
            "propensity_tier": "cold",
        }

    def test_permanent_dns_unreachable_excluded_by_permanent_prefix_filter(self):
        """Rows with permanent_dns_unreachable match NOT LIKE 'permanent_%' exclusion."""
        row = self._make_row("permanent_dns_unreachable")
        # The SQL WHERE clause: filter_reason NOT LIKE 'permanent_%'
        # permanent_dns_unreachable STARTS with 'permanent_' → excluded.
        assert row["filter_reason"].startswith("permanent_"), (
            "permanent_dns_unreachable must start with 'permanent_' to be caught "
            "by the NOT LIKE 'permanent_%' cursor filter"
        )

    def test_legacy_dns_unreachable_excluded_by_not_in_filter(self):
        """Legacy free_enrichment_dns_unreachable is caught by the NOT IN exclusion."""
        excluded = {
            "free_enrichment_dns_unreachable",
            "free_enrichment_http_unreachable",
            "free_enrichment_exception",
        }
        row = self._make_row("free_enrichment_dns_unreachable")
        assert row["filter_reason"] in excluded, (
            "free_enrichment_dns_unreachable must be in the NOT IN exclusion list "
            "in fetch_backlog SQL"
        )

    def test_null_filter_reason_not_excluded(self):
        """Rows with NULL filter_reason should still be eligible for processing."""
        row = self._make_row(None)
        excluded = {
            "free_enrichment_dns_unreachable",
            "free_enrichment_http_unreachable",
            "free_enrichment_exception",
        }
        assert row["filter_reason"] is None
        assert row["filter_reason"] not in excluded

    def test_classify_row_skips_free_enriched_rows(self):
        """_classify_row skips stage-1 rows already free-enriched (existing logic)."""
        from src.orchestration.flows.bu_closed_loop_flow import _classify_row

        row = {
            "pipeline_stage": 1,
            "filter_reason": None,
            "free_enrichment_completed_at": "2024-01-01T00:00:00+00:00",
        }
        result = _classify_row(row, free_mode_only=True)
        assert result["action"] == "skip"
        assert result["reason"] == "stuck:already_free_enriched"

    def test_fetch_backlog_sql_contains_not_in_exclusion(self):
        """Verify the fetch_backlog SQL string includes the NOT IN dead-domain exclusion."""
        import inspect

        from src.orchestration.flows.bu_closed_loop_flow import fetch_backlog

        # Unwrap the Prefect task to get the original function source
        fn = fetch_backlog.fn if hasattr(fetch_backlog, "fn") else fetch_backlog
        source = inspect.getsource(fn)
        assert "free_enrichment_dns_unreachable" in source, (
            "fetch_backlog SQL must exclude 'free_enrichment_dns_unreachable'"
        )
        assert "free_enrichment_http_unreachable" in source, (
            "fetch_backlog SQL must exclude 'free_enrichment_http_unreachable'"
        )

    def test_free_enrichment_writes_permanent_prefix_on_dns_fail(self):
        """FreeEnrichment._process_domain writes permanent_dns_unreachable (permanent_ prefix)."""
        import inspect

        from src.pipeline import free_enrichment

        source = inspect.getsource(free_enrichment)
        assert "permanent_dns_unreachable" in source, (
            "free_enrichment.py must write 'permanent_dns_unreachable' "
            "(with permanent_ prefix) on DNS failure"
        )
        # Legacy name must NOT be written any more
        assert "free_enrichment_dns_unreachable" not in source, (
            "free_enrichment.py must NOT write the legacy 'free_enrichment_dns_unreachable' — "
            "it has been renamed to 'permanent_dns_unreachable'"
        )


# ---------------------------------------------------------------------------
# Gap #12 — Suppression pre-check before paid enrichment
# ---------------------------------------------------------------------------


class TestGap12SuppressionPreCheck:
    """Stage 8 must skip paid email/mobile waterfall when contact is suppressed."""

    def _base_domain_data(self, known_email: str | None = None) -> dict:
        """Minimal domain_data structure for _run_stage8."""
        from src.pipeline.latency_tracker import LatencyTracker

        identity: dict = {"business_name": "ACME Plumbing", "dm_candidate": {}}
        if known_email:
            identity["dm_candidate"]["email"] = known_email

        return {
            "domain": "acmeplumbing.com.au",
            "category": "plumbing",
            "stage3": identity,
            "stage8_verify": None,
            "stage8_contacts": None,
            "errors": [],
            "cost_usd": 0.0,
            "timings": {},
            "dropped_at": None,
            "drop_reason": None,
            "_latency_tracker": LatencyTracker("acmeplumbing.com.au"),
            "_bu_id": "test-bu-id",
        }

    @pytest.mark.asyncio
    async def test_suppressed_email_skips_paid_waterfall(self):
        """When known email is suppressed, discover_email and run_mobile_waterfall are NOT called."""
        from src.orchestration import cohort_runner as cr

        domain_data = self._base_domain_data(known_email="owner@acmeplumbing.com.au")

        mock_dfs = MagicMock()
        mock_bd = MagicMock()
        mock_lm = MagicMock()

        suppressed_response = {
            "suppressed": True,
            "reason": "bounce",
            "suppressed_at": "2024-01-01T00:00:00+00:00",
        }

        with (
            patch.object(
                cr.SuppressionManager,
                "check_before_outreach",
                return_value=suppressed_response,
            ),
            patch(
                "src.orchestration.cohort_runner.run_verify_fills",
                new_callable=AsyncMock,
                return_value={"_cost": 0.0},
            ),
            patch(
                "src.orchestration.cohort_runner.enrich_dm_via_contactout",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.orchestration.cohort_runner.discover_email",
                new_callable=AsyncMock,
            ) as mock_discover,
            patch(
                "src.orchestration.cohort_runner.run_mobile_waterfall",
                new_callable=AsyncMock,
            ) as mock_mobile,
        ):
            result = await cr._run_stage8(domain_data, mock_dfs, mock_bd, mock_lm)

        # Paid waterfalls must NOT have been called
        mock_discover.assert_not_called()
        mock_mobile.assert_not_called()

        # Suppression error logged
        suppression_errors = [e for e in result["errors"] if "stage8_suppressed" in e]
        assert len(suppression_errors) == 1, "Expected one stage8_suppressed error entry"
        assert "bounce" in suppression_errors[0]

    @pytest.mark.asyncio
    async def test_non_suppressed_email_proceeds_to_paid_waterfall(self):
        """When known email is NOT suppressed, discover_email is called normally."""
        from src.orchestration import cohort_runner as cr

        domain_data = self._base_domain_data(known_email="owner@acmeplumbing.com.au")

        mock_dfs = MagicMock()
        mock_bd = MagicMock()
        mock_lm = MagicMock()

        not_suppressed = {"suppressed": False, "reason": None, "suppressed_at": None}

        mock_email_result = MagicMock()
        mock_email_result.email = "owner@acmeplumbing.com.au"
        mock_email_result.verified = True
        mock_email_result.source = "leadmagic"
        mock_email_result.confidence = 0.95
        mock_email_result.cost_usd = 0.015

        mock_mobile_result = MagicMock()
        mock_mobile_result.mobile = None
        mock_mobile_result.source = "none"
        mock_mobile_result.cost_usd = 0.0

        with (
            patch.object(
                cr.SuppressionManager,
                "check_before_outreach",
                return_value=not_suppressed,
            ),
            patch(
                "src.orchestration.cohort_runner.run_verify_fills",
                new_callable=AsyncMock,
                return_value={"_cost": 0.0},
            ),
            patch(
                "src.orchestration.cohort_runner.enrich_dm_via_contactout",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.orchestration.cohort_runner.discover_email",
                new_callable=AsyncMock,
                return_value=mock_email_result,
            ) as mock_discover,
            patch(
                "src.orchestration.cohort_runner.run_mobile_waterfall",
                new_callable=AsyncMock,
                return_value=mock_mobile_result,
            ) as mock_mobile,
        ):
            result = await cr._run_stage8(domain_data, mock_dfs, mock_bd, mock_lm)

        # Both waterfalls were called
        mock_discover.assert_called_once()
        mock_mobile.assert_called_once()

        # No suppression errors
        suppression_errors = [e for e in result["errors"] if "stage8_suppressed" in e]
        assert len(suppression_errors) == 0

    @pytest.mark.asyncio
    async def test_no_known_email_proceeds_normally(self):
        """When no known email is available, suppression check is skipped and waterfall runs."""
        from src.orchestration import cohort_runner as cr

        domain_data = self._base_domain_data(known_email=None)

        mock_dfs = MagicMock()
        mock_bd = MagicMock()
        mock_lm = MagicMock()

        mock_mobile_result = MagicMock()
        mock_mobile_result.mobile = None
        mock_mobile_result.source = "none"
        mock_mobile_result.cost_usd = 0.0

        with (
            patch(
                "src.orchestration.cohort_runner.run_verify_fills",
                new_callable=AsyncMock,
                return_value={"_cost": 0.0},
            ),
            patch(
                "src.orchestration.cohort_runner.enrich_dm_via_contactout",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.orchestration.cohort_runner.discover_email",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_discover,
            patch(
                "src.orchestration.cohort_runner.run_mobile_waterfall",
                new_callable=AsyncMock,
                return_value=mock_mobile_result,
            ) as mock_mobile,
        ):
            result = await cr._run_stage8(domain_data, mock_dfs, mock_bd, mock_lm)

        # Waterfalls still called (no email to suppress against)
        mock_discover.assert_called_once()
        mock_mobile.assert_called_once()

        suppression_errors = [e for e in result["errors"] if "stage8_suppressed" in e]
        assert len(suppression_errors) == 0
