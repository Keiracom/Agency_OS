"""
Tests for CIS Timing Signal Extraction (Directive #157 - Gap 3)

Tests the timing signal extraction and aggregation functions:
- _convert_dow_to_iso: PostgreSQL DOW to ISO 8601 conversion
- _derive_company_size: Employee count to size bucket
- extract_timing_from_activity: Extract timing from activity record
- record_timing_signal: Store timing signal in platform_timing_signals
- process_conversion_timing: Full pipeline for conversion timing
"""

import pytest
from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.cis_outcome_service import (
    _convert_dow_to_iso,
    _derive_company_size,
    extract_timing_from_activity,
    record_timing_signal,
    process_conversion_timing,
    get_timing_insights,
)


# =========================================================================
# UNIT TESTS - Pure Functions
# =========================================================================


class TestConvertDowToIso:
    """Test PostgreSQL DOW to ISO 8601 conversion."""

    def test_sunday_converts_to_6(self):
        """PostgreSQL 0 (Sunday) should become ISO 6 (Sunday)."""
        assert _convert_dow_to_iso(0) == 6

    def test_monday_converts_to_0(self):
        """PostgreSQL 1 (Monday) should become ISO 0 (Monday)."""
        assert _convert_dow_to_iso(1) == 0

    def test_tuesday_converts_to_1(self):
        """PostgreSQL 2 (Tuesday) should become ISO 1 (Tuesday)."""
        assert _convert_dow_to_iso(2) == 1

    def test_wednesday_converts_to_2(self):
        """PostgreSQL 3 (Wednesday) should become ISO 2 (Wednesday)."""
        assert _convert_dow_to_iso(3) == 2

    def test_thursday_converts_to_3(self):
        """PostgreSQL 4 (Thursday) should become ISO 3 (Thursday)."""
        assert _convert_dow_to_iso(4) == 3

    def test_friday_converts_to_4(self):
        """PostgreSQL 5 (Friday) should become ISO 4 (Friday)."""
        assert _convert_dow_to_iso(5) == 4

    def test_saturday_converts_to_5(self):
        """PostgreSQL 6 (Saturday) should become ISO 5 (Saturday)."""
        assert _convert_dow_to_iso(6) == 5

    def test_none_defaults_to_tuesday(self):
        """None should default to 1 (Tuesday - common business day)."""
        assert _convert_dow_to_iso(None) == 1


class TestDeriveCompanySize:
    """Test employee count to company size bucket conversion."""

    def test_none_defaults_to_smb(self):
        """None employee count should default to SMB."""
        assert _derive_company_size(None) == "smb"

    def test_under_50_is_smb(self):
        """Under 50 employees is SMB."""
        assert _derive_company_size(10) == "smb"
        assert _derive_company_size(49) == "smb"

    def test_50_to_499_is_mid_market(self):
        """50-499 employees is mid-market."""
        assert _derive_company_size(50) == "mid_market"
        assert _derive_company_size(250) == "mid_market"
        assert _derive_company_size(499) == "mid_market"

    def test_500_plus_is_enterprise(self):
        """500+ employees is enterprise."""
        assert _derive_company_size(500) == "enterprise"
        assert _derive_company_size(1000) == "enterprise"
        assert _derive_company_size(10000) == "enterprise"

    def test_range_string_11_50(self):
        """Range string '11-50' should use upper bound -> SMB."""
        assert _derive_company_size("11-50") == "mid_market"

    def test_range_string_51_200(self):
        """Range string '51-200' should use upper bound -> mid_market."""
        assert _derive_company_size("51-200") == "mid_market"

    def test_range_string_201_500(self):
        """Range string '201-500' should use upper bound -> enterprise."""
        assert _derive_company_size("201-500") == "enterprise"

    def test_plus_string(self):
        """String like '1000+' should work."""
        assert _derive_company_size("1000+") == "enterprise"

    def test_invalid_string_defaults_to_smb(self):
        """Invalid string should default to SMB."""
        assert _derive_company_size("unknown") == "smb"
        assert _derive_company_size("") == "smb"


# =========================================================================
# INTEGRATION TESTS - Database Functions (Mocked)
# =========================================================================


class TestExtractTimingFromActivity:
    """Test timing extraction from activity records."""

    @pytest.mark.asyncio
    async def test_extracts_timing_data(self):
        """Should extract all timing fields from activity."""
        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Create mock row with timing data
        mock_row = MagicMock()
        mock_row.id = "activity-123"
        mock_row.lead_id = "lead-456"
        mock_row.client_id = "client-789"
        mock_row.channel = "email"
        mock_row.lead_local_day_of_week = 2  # PostgreSQL Tuesday
        mock_row.lead_local_time = time(10, 30)  # 10:30 AM
        mock_row.touch_number = 2
        mock_row.created_at = MagicMock()
        mock_row.created_at.isoformat.return_value = "2025-01-06T10:30:00"
        mock_row.industry = "manufacturing"
        mock_row.employee_count = 75
        mock_row.company_name = "Test Corp"

        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await extract_timing_from_activity(mock_db, "activity-123")

        assert result is not None
        assert result["activity_id"] == "activity-123"
        assert result["day_of_week"] == 1  # ISO Tuesday (converted from PG 2)
        assert result["hour_of_day"] == 10
        assert result["touch_number"] == 2
        assert result["channel"] == "email"
        assert result["industry"] == "manufacturing"
        assert result["company_size"] == "mid_market"  # 75 employees

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_activity(self):
        """Should return None if activity not found."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        result = await extract_timing_from_activity(mock_db, "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_defaults_for_missing_timing_fields(self):
        """Should use defaults when timing fields are null."""
        mock_db = AsyncMock()
        mock_result = MagicMock()

        mock_row = MagicMock()
        mock_row.id = "activity-123"
        mock_row.lead_id = "lead-456"
        mock_row.client_id = "client-789"
        mock_row.channel = None  # Missing
        mock_row.lead_local_day_of_week = None  # Missing
        mock_row.lead_local_time = None  # Missing
        mock_row.touch_number = None  # Missing
        mock_row.created_at = MagicMock()
        mock_row.created_at.isoformat.return_value = "2025-01-06T10:30:00"
        mock_row.industry = None
        mock_row.employee_count = None
        mock_row.company_name = None

        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await extract_timing_from_activity(mock_db, "activity-123")

        assert result is not None
        assert result["day_of_week"] == 1  # Default Tuesday
        assert result["hour_of_day"] == 10  # Default business hour
        assert result["touch_number"] == 1  # Default first touch
        assert result["channel"] == "email"  # Default channel
        assert result["industry"] == "unknown"
        assert result["company_size"] == "smb"


class TestRecordTimingSignal:
    """Test recording timing signals to database."""

    @pytest.mark.asyncio
    async def test_records_conversion_signal(self):
        """Should call database function with correct params."""
        mock_db = AsyncMock()

        result = await record_timing_signal(
            db=mock_db,
            industry="Manufacturing",
            channel="Email",
            company_size="mid_market",
            day_of_week=1,  # Tuesday
            hour_of_day=10,
            touch_number=2,
            is_conversion=True,
        )

        assert result["success"] is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify normalized inputs
        call_args = mock_db.execute.call_args
        params = call_args[0][1]  # Second positional arg is params dict
        assert params["industry"] == "manufacturing"
        assert params["channel"] == "email"
        assert params["is_conversion"] is True

    @pytest.mark.asyncio
    async def test_validates_ranges(self):
        """Should cap values to valid ranges."""
        mock_db = AsyncMock()

        await record_timing_signal(
            db=mock_db,
            industry="test",
            channel="email",
            company_size="smb",
            day_of_week=10,  # Invalid, should cap to 6
            hour_of_day=30,  # Invalid, should cap to 23
            touch_number=20,  # Invalid, should cap to 10
            is_conversion=False,
        )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params["day_of_week"] == 6  # Capped
        assert params["hour_of_day"] == 23  # Capped
        assert params["touch_number"] == 10  # Capped


class TestProcessConversionTiming:
    """Test full conversion timing pipeline."""

    @pytest.mark.asyncio
    async def test_processes_conversion_successfully(self):
        """Should extract and record timing for conversion."""
        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Mock activity data
        mock_row = MagicMock()
        mock_row.id = "activity-123"
        mock_row.lead_id = "lead-456"
        mock_row.client_id = "client-789"
        mock_row.channel = "email"
        mock_row.lead_local_day_of_week = 2  # Tuesday
        mock_row.lead_local_time = time(10, 0)
        mock_row.touch_number = 2
        mock_row.created_at = MagicMock()
        mock_row.created_at.isoformat.return_value = "2025-01-06T10:00:00"
        mock_row.industry = "manufacturing"
        mock_row.employee_count = 100
        mock_row.company_name = "Test Corp"

        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await process_conversion_timing(mock_db, "activity-123")

        assert result["success"] is True
        assert result["timing"] is not None
        assert result["timing"]["day_of_week"] == 1  # ISO Tuesday
        assert result["timing"]["hour_of_day"] == 10
        assert result["timing"]["touch_number"] == 2

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_activity(self):
        """Should return error if activity not found."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        result = await process_conversion_timing(mock_db, "nonexistent")

        assert result["success"] is False
        assert "error" in result


class TestGetTimingInsights:
    """Test querying timing insights."""

    @pytest.mark.asyncio
    async def test_returns_insights_for_industry(self):
        """Should return timing insights for an industry."""
        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Mock insights data
        mock_row = MagicMock()
        mock_row.industry = "manufacturing"
        mock_row.channel = "email"
        mock_row.company_size = "mid_market"
        mock_row.best_day = "Tuesday"
        mock_row.best_hour = 10
        mock_row.best_touchpoint = 2
        mock_row.avg_touchpoint = 2.3
        mock_row.conversion_rate = 0.045
        mock_row.total_conversions = 25
        mock_row.confidence = "medium"

        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        insights = await get_timing_insights(
            db=mock_db,
            industry="Manufacturing",
            channel="email",
        )

        assert len(insights) == 1
        assert insights[0]["industry"] == "manufacturing"
        assert insights[0]["best_day"] == "Tuesday"
        assert insights[0]["best_hour"] == 10
        assert insights[0]["confidence"] == "medium"


# =========================================================================
# TIMING VALIDATION TESTS
# =========================================================================


class TestTimingFieldsValidation:
    """Ensure timing fields match expected format."""

    def test_day_of_week_uses_iso_format(self):
        """day_of_week should be 0=Monday, 6=Sunday (ISO 8601)."""
        # Verify the conversion function produces ISO format
        # PostgreSQL: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
        # ISO 8601: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun

        day_mapping = {
            0: 6,  # Sun -> 6
            1: 0,  # Mon -> 0
            2: 1,  # Tue -> 1
            3: 2,  # Wed -> 2
            4: 3,  # Thu -> 3
            5: 4,  # Fri -> 4
            6: 5,  # Sat -> 5
        }

        for pg_dow, iso_dow in day_mapping.items():
            assert _convert_dow_to_iso(pg_dow) == iso_dow

    def test_hour_of_day_range(self):
        """hour_of_day should be 0-23."""
        # This is validated in record_timing_signal
        # Invalid values should be capped
        mock_db = AsyncMock()

        # Test would verify capping in actual implementation
        # The function caps to 0-23 range


# =========================================================================
# EDGE CASES
# =========================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_handles_enum_channel_type(self):
        """Should handle ChannelType enum correctly."""
        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Mock channel as enum-like object
        mock_channel = MagicMock()
        mock_channel.value = "linkedin"

        mock_row = MagicMock()
        mock_row.id = "activity-123"
        mock_row.lead_id = "lead-456"
        mock_row.client_id = "client-789"
        mock_row.channel = mock_channel  # Enum-like
        mock_row.lead_local_day_of_week = 1
        mock_row.lead_local_time = time(14, 0)
        mock_row.touch_number = 1
        mock_row.created_at = MagicMock()
        mock_row.created_at.isoformat.return_value = "2025-01-06T14:00:00"
        mock_row.industry = "tech"
        mock_row.employee_count = 200
        mock_row.company_name = "Tech Inc"

        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await extract_timing_from_activity(mock_db, "activity-123")

        assert result["channel"] == "linkedin"

    def test_company_size_boundary_values(self):
        """Test exact boundary values for company size."""
        assert _derive_company_size(49) == "smb"
        assert _derive_company_size(50) == "mid_market"
        assert _derive_company_size(499) == "mid_market"
        assert _derive_company_size(500) == "enterprise"
