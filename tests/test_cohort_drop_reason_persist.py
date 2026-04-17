"""
Tests for cohort_runner drop_reason → rejection_reason persistence.

Verifies:
1. DROP_REASON_TO_REJECTION mapping covers all drop_reason strings used in cohort_runner
2. _persist_drop_reason writes to Supabase (mocked) with correct ENUM value and rejection_phase
3. _persist_drop_reason is best-effort — Supabase failure does not raise
4. Domains without a lead row are handled gracefully (no exception)
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.orchestration.cohort_runner import DROP_REASON_TO_REJECTION, _persist_drop_reason

# ---------------------------------------------------------------------------
# Known drop_reason prefixes used in cohort_runner gate points
# ---------------------------------------------------------------------------

KNOWN_DROP_REASON_PREFIXES = [
    "stage3_exception",
    "stage3_failed",
    "enterprise_or_chain",
    "no_dm_found",
    "score_exception",
    "viability",
    "score_below_gate",
]

# Valid rejection_reason ENUM values from migrations 027 + 028
VALID_REJECTION_REASONS = {
    # Sales/outreach rejections (migration 027)
    "timing_not_now",
    "budget_constraints",
    "using_competitor",
    "not_decision_maker",
    "no_need",
    "bad_experience",
    "too_busy",
    "not_interested_generic",
    "do_not_contact",
    "wrong_contact",
    "company_policy",
    "other",
    # Pipeline quality drops (migration 028)
    "enterprise_or_chain",
    "no_dm_found",
    "score_below_gate",
    "stage_failed",
    "viability",
}


class TestDropReasonMapping:
    """Verify the mapping dict covers all known drop_reason prefixes."""

    def test_all_prefixes_covered(self):
        """Every drop_reason prefix used in cohort_runner must be in the mapping."""
        missing = [p for p in KNOWN_DROP_REASON_PREFIXES if p not in DROP_REASON_TO_REJECTION]
        assert not missing, f"Unmapped drop_reason prefixes: {missing}"

    def test_all_values_are_valid_enum(self):
        """Every mapped value must be a valid rejection_reason ENUM string."""
        invalid = {
            key: val
            for key, val in DROP_REASON_TO_REJECTION.items()
            if val not in VALID_REJECTION_REASONS
        }
        assert not invalid, f"Invalid ENUM values in mapping: {invalid}"

    def test_no_extra_unmapped_keys(self):
        """Mapping should not silently have keys that differ from known prefixes — catch typos."""
        extra = [k for k in DROP_REASON_TO_REJECTION if k not in KNOWN_DROP_REASON_PREFIXES]
        assert not extra, f"Unexpected keys in DROP_REASON_TO_REJECTION (typo?): {extra}"


class TestPersistDropReason:
    """Verify _persist_drop_reason behaviour with mocked Supabase."""

    def _make_mock_sb(self):
        """Return a mock Supabase async client."""
        execute_mock = AsyncMock(return_value=MagicMock(data=[]))
        is_mock = MagicMock(return_value=MagicMock(execute=execute_mock))
        eq_mock = MagicMock(return_value=MagicMock(is_=is_mock))
        update_mock = MagicMock(return_value=MagicMock(eq=eq_mock))
        table_mock = MagicMock(return_value=MagicMock(update=update_mock))
        sb = MagicMock()
        sb.table = table_mock
        return sb, execute_mock

    @pytest.mark.asyncio
    async def test_writes_correct_rejection_reason(self):
        """enterprise_or_chain drop → rejection_reason='enterprise_or_chain', rejection_phase='pipeline' written to leads."""
        sb, execute_mock = self._make_mock_sb()
        update_mock = sb.table.return_value.update
        domain_data = {
            "domain": "example.com.au",
            "drop_reason": "enterprise_or_chain",
        }
        with patch(
            "src.orchestration.cohort_runner._get_supabase",
            new=AsyncMock(return_value=sb),
        ):
            await _persist_drop_reason(domain_data)

        sb.table.assert_called_once_with("leads")
        update_mock.assert_called_once_with(
            {"rejection_reason": "enterprise_or_chain", "rejection_phase": "pipeline"}
        )
        execute_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_prefixed_drop_reason_mapped_correctly(self):
        """stage3_exception: <detail> → key extraction works, maps to 'stage_failed'."""
        sb, execute_mock = self._make_mock_sb()
        update_mock = sb.table.return_value.update
        domain_data = {
            "domain": "example.com.au",
            "drop_reason": "stage3_exception: TimeoutError('foo')",
        }
        with patch(
            "src.orchestration.cohort_runner._get_supabase",
            new=AsyncMock(return_value=sb),
        ):
            await _persist_drop_reason(domain_data)

        update_mock.assert_called_once_with(
            {"rejection_reason": "stage_failed", "rejection_phase": "pipeline"}
        )
        execute_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_supabase_failure_does_not_raise(self):
        """Best-effort: Supabase error must be swallowed, not propagated."""
        domain_data = {
            "domain": "example.com.au",
            "drop_reason": "no_dm_found",
        }
        with patch(
            "src.orchestration.cohort_runner._get_supabase",
            new=AsyncMock(side_effect=RuntimeError("connection refused")),
        ):
            # Must not raise
            await _persist_drop_reason(domain_data)

    @pytest.mark.asyncio
    async def test_noop_when_no_domain(self):
        """If domain is empty, function returns immediately without touching Supabase."""
        domain_data = {"domain": "", "drop_reason": "no_dm_found"}
        with patch(
            "src.orchestration.cohort_runner._get_supabase",
            new=AsyncMock(),
        ) as mock_client:
            await _persist_drop_reason(domain_data)
        mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_noop_when_no_drop_reason(self):
        """If drop_reason is empty, function returns immediately."""
        domain_data = {"domain": "example.com.au", "drop_reason": ""}
        with patch(
            "src.orchestration.cohort_runner._get_supabase",
            new=AsyncMock(),
        ) as mock_client:
            await _persist_drop_reason(domain_data)
        mock_client.assert_not_called()
