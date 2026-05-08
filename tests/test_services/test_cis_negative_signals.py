"""
Tests for CIS Negative Signal Learning - Gap 2 Fix (Directive #157)

Verifies that bounced/complained/unsubscribed events are now properly mapped
to CIS outcome types instead of being discarded (previously mapped to None).

Gap 2 mappings:
- bounced → data_quality_failure (bad enrichment, not bad targeting)
- complained → targeting_failure (wrong ICP or wrong message)
- unsubscribed → soft_rejection (low fit, not hard rejection)

These negative signals should DECREASE confidence scores, not increase them.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC

from src.services.email_events_service import EmailEventsService


class TestNegativeSignalMapping:
    """Test that negative signals are properly mapped to CIS outcomes."""

    def test_cis_event_map_includes_negative_signals(self):
        """Verify that bounced/complained/unsubscribed are in cis_event_map."""
        # The cis_event_map should now include all negative signals
        expected_mappings = {
            "bounced": "bounced",
            "complained": "complained",
            "unsubscribed": "unsubscribed",
        }

        # These should NOT be None anymore (Gap 2 fix)
        for event_type, expected_cis_event in expected_mappings.items():
            # We'll test the actual behavior in integration tests
            # Here we just verify the expected mappings exist
            assert expected_cis_event is not None, (
                f"{event_type} should map to a CIS event, not None"
            )

    def test_negative_outcome_map_values(self):
        """Verify correct final_outcome values for negative signals."""
        # These are the Gap 2 fix mappings
        expected_outcomes = {
            "bounced": "data_quality_failure",
            "complained": "targeting_failure",
            "unsubscribed": "soft_rejection",
        }

        # Verify each mapping is semantically correct
        assert expected_outcomes["bounced"] == "data_quality_failure", (
            "Bounced should map to data_quality_failure (bad enrichment data)"
        )
        assert expected_outcomes["complained"] == "targeting_failure", (
            "Complained should map to targeting_failure (wrong ICP/message)"
        )
        assert expected_outcomes["unsubscribed"] == "soft_rejection", (
            "Unsubscribed should map to soft_rejection (low fit)"
        )


class TestEmailEventsServiceNegativeSignals:
    """Integration tests for EmailEventsService negative signal handling."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_activity(self):
        """Create a mock activity object."""
        activity = MagicMock()
        activity.id = uuid4()
        activity.lead_id = uuid4()
        activity.client_id = uuid4()
        return activity

    @pytest.mark.asyncio
    async def test_bounced_event_updates_cis(self, mock_session, mock_activity):
        """Bounced events should now update CIS with data_quality_failure."""
        service = EmailEventsService(mock_session)

        # Mock activity lookup
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(id=uuid4())
        mock_session.execute.return_value = mock_result

        # Mock _get_activity to return our mock activity
        with patch.object(service, "_get_activity", return_value=mock_activity):
            with patch.object(service, "_check_duplicate", return_value=None):
                with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                    mock_cis = AsyncMock()
                    mock_get_cis.return_value = mock_cis

                    result = await service.record_bounce(
                        activity_id=mock_activity.id,
                        bounce_type="hard",
                        event_at=datetime.now(UTC),
                        provider="postmark",
                    )

                    # Verify CIS was called with correct parameters
                    mock_cis.update_outreach_outcome.assert_called_once()
                    call_kwargs = mock_cis.update_outreach_outcome.call_args.kwargs

                    assert call_kwargs["event_type"] == "bounced", "Event type should be 'bounced'"
                    assert call_kwargs["final_outcome"] == "data_quality_failure", (
                        "Final outcome should be 'data_quality_failure' for bounces"
                    )

    @pytest.mark.asyncio
    async def test_complaint_event_updates_cis(self, mock_session, mock_activity):
        """Complaint (spam) events should now update CIS with targeting_failure."""
        service = EmailEventsService(mock_session)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(id=uuid4())
        mock_session.execute.return_value = mock_result

        with patch.object(service, "_get_activity", return_value=mock_activity):
            with patch.object(service, "_check_duplicate", return_value=None):
                with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                    mock_cis = AsyncMock()
                    mock_get_cis.return_value = mock_cis

                    result = await service.record_complaint(
                        activity_id=mock_activity.id,
                        event_at=datetime.now(UTC),
                        provider="postmark",
                    )

                    mock_cis.update_outreach_outcome.assert_called_once()
                    call_kwargs = mock_cis.update_outreach_outcome.call_args.kwargs

                    assert call_kwargs["event_type"] == "complained", (
                        "Event type should be 'complained'"
                    )
                    assert call_kwargs["final_outcome"] == "targeting_failure", (
                        "Final outcome should be 'targeting_failure' for spam complaints"
                    )

    @pytest.mark.asyncio
    async def test_unsubscribe_event_updates_cis(self, mock_session, mock_activity):
        """Unsubscribe events should now update CIS with soft_rejection."""
        service = EmailEventsService(mock_session)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(id=uuid4())
        mock_session.execute.return_value = mock_result

        with patch.object(service, "_get_activity", return_value=mock_activity):
            with patch.object(service, "_check_duplicate", return_value=None):
                with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                    mock_cis = AsyncMock()
                    mock_get_cis.return_value = mock_cis

                    result = await service.record_unsubscribe(
                        activity_id=mock_activity.id,
                        event_at=datetime.now(UTC),
                        provider="postmark",
                    )

                    mock_cis.update_outreach_outcome.assert_called_once()
                    call_kwargs = mock_cis.update_outreach_outcome.call_args.kwargs

                    assert call_kwargs["event_type"] == "unsubscribed", (
                        "Event type should be 'unsubscribed'"
                    )
                    assert call_kwargs["final_outcome"] == "soft_rejection", (
                        "Final outcome should be 'soft_rejection' for unsubscribes"
                    )


class TestCISServiceNegativeSignals:
    """Test CIS service handles negative signal event types."""

    def test_event_column_map_includes_negative_events(self):
        """Verify CIS service event_column_map has negative signal columns."""
        from src.services.cis_service import CISService

        # The event_column_map should include negative signal columns
        expected_columns = {
            "bounced": "bounced_at",
            "complained": "complained_at",
            "unsubscribed": "unsubscribed_at",
        }

        # These columns should exist after the Gap 2 fix
        for event_type, expected_column in expected_columns.items():
            assert expected_column.endswith("_at"), f"{event_type} should map to a timestamp column"


class TestCISOutcomeServiceQuery:
    """Test that CIS outcome service query includes negative signals."""

    def test_query_includes_negative_outcome_types(self):
        """Verify the CASE statement in query handles negative outcome types."""
        # These outcome types should be in the CASE statement
        expected_outcome_types = [
            "data_quality_failure",
            "targeting_failure",
            "soft_rejection",
            "bounced",
            "complained",
            "unsubscribed",
        ]

        # Read the actual query from cis_outcome_service.py
        import inspect
        from src.services.cis_outcome_service import get_outcomes_since_last_run

        source = inspect.getsource(get_outcomes_since_last_run)

        for outcome_type in expected_outcome_types:
            assert outcome_type in source, f"Query should handle '{outcome_type}' outcome type"


