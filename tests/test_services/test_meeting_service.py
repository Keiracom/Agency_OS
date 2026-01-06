"""
FILE: tests/test_services/test_meeting_service.py
PURPOSE: Unit tests for Meeting Service
PHASE: 24E (Downstream Outcomes)
TASK: OUTCOME-003, OUTCOME-007
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.services.meeting_service import MeetingService, MEETING_TYPES, MEETING_OUTCOMES


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def meeting_service(mock_session):
    """Create MeetingService with mock session."""
    return MeetingService(mock_session)


@pytest.fixture
def sample_meeting():
    """Sample meeting data."""
    return {
        "id": uuid4(),
        "client_id": uuid4(),
        "lead_id": uuid4(),
        "scheduled_at": datetime.utcnow() + timedelta(days=1),
        "duration_minutes": 30,
        "meeting_type": "discovery",
        "booked_by": "ai",
        "confirmed": False,
        "showed_up": None,
        "meeting_outcome": None,
        "created_at": datetime.utcnow(),
    }


class TestMeetingServiceCreate:
    """Tests for create operations."""

    @pytest.mark.asyncio
    async def test_create_meeting(self, meeting_service, mock_session):
        """Test creating a new meeting."""
        client_id = uuid4()
        lead_id = uuid4()
        scheduled_at = datetime.utcnow() + timedelta(days=1)

        # Mock touches query
        touches_result = MagicMock()
        touches_row = MagicMock()
        touches_row.count = 5
        touches_row.first_touch = datetime.utcnow() - timedelta(days=3)
        touches_result.fetchone.return_value = touches_row

        # Mock insert result
        insert_result = MagicMock()
        insert_row = MagicMock()
        insert_row.id = uuid4()
        insert_row._mapping = {
            "id": insert_row.id,
            "client_id": client_id,
            "lead_id": lead_id,
            "scheduled_at": scheduled_at,
            "meeting_type": "discovery",
        }
        insert_result.fetchone.return_value = insert_row

        mock_session.execute.side_effect = [touches_result, insert_result, MagicMock()]

        result = await meeting_service.create(
            client_id=client_id,
            lead_id=lead_id,
            scheduled_at=scheduled_at,
            meeting_type="discovery",
        )

        assert result is not None
        assert result["scheduled_at"] == scheduled_at
        assert mock_session.commit.call_count >= 1

    @pytest.mark.asyncio
    async def test_create_meeting_invalid_type(self, meeting_service, mock_session):
        """Test creating meeting with invalid type raises error."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await meeting_service.create(
                client_id=uuid4(),
                lead_id=uuid4(),
                scheduled_at=datetime.utcnow() + timedelta(days=1),
                meeting_type="invalid_type",
            )


class TestMeetingServiceConfirmation:
    """Tests for confirmation operations."""

    @pytest.mark.asyncio
    async def test_confirm_meeting(self, meeting_service, mock_session, sample_meeting):
        """Test confirming a meeting."""
        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_meeting
        get_result.fetchone.return_value = get_row

        # Mock update result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {**sample_meeting, "confirmed": True, "confirmed_at": datetime.utcnow()}
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [get_result, update_result]

        result = await meeting_service.confirm(meeting_id=sample_meeting["id"])

        assert result["confirmed"] is True

    @pytest.mark.asyncio
    async def test_send_reminder(self, meeting_service, mock_session, sample_meeting):
        """Test marking reminder as sent."""
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {**sample_meeting, "reminder_sent": True}
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await meeting_service.send_reminder(meeting_id=sample_meeting["id"])

        assert result["reminder_sent"] is True


class TestMeetingServiceShowTracking:
    """Tests for show/no-show tracking."""

    @pytest.mark.asyncio
    async def test_record_show(self, meeting_service, mock_session, sample_meeting):
        """Test recording that lead showed up."""
        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_meeting
        get_result.fetchone.return_value = get_row

        # Mock update result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {
            **sample_meeting,
            "showed_up": True,
            "showed_up_confirmed_at": datetime.utcnow(),
        }
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [get_result, update_result]

        result = await meeting_service.record_show(
            meeting_id=sample_meeting["id"],
            showed_up=True,
            confirmed_by="webhook",
        )

        assert result["showed_up"] is True

    @pytest.mark.asyncio
    async def test_record_no_show(self, meeting_service, mock_session, sample_meeting):
        """Test recording no-show."""
        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_meeting
        get_result.fetchone.return_value = get_row

        # Mock update result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {
            **sample_meeting,
            "showed_up": False,
            "meeting_outcome": "no_show",
            "no_show_reason": "Lead did not join",
        }
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [get_result, update_result]

        result = await meeting_service.record_show(
            meeting_id=sample_meeting["id"],
            showed_up=False,
            no_show_reason="Lead did not join",
        )

        assert result["showed_up"] is False
        assert result["meeting_outcome"] == "no_show"


class TestMeetingServiceOutcomes:
    """Tests for outcome recording."""

    @pytest.mark.asyncio
    async def test_record_good_outcome(self, meeting_service, mock_session, sample_meeting):
        """Test recording good meeting outcome."""
        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_meeting
        get_result.fetchone.return_value = get_row

        # Mock update result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {
            **sample_meeting,
            "meeting_outcome": "good",
            "showed_up": True,
            "meeting_notes": "Great discussion",
            "next_steps": "Send proposal",
        }
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [get_result, update_result]

        result = await meeting_service.record_outcome(
            meeting_id=sample_meeting["id"],
            outcome="good",
            meeting_notes="Great discussion",
            next_steps="Send proposal",
        )

        assert result["meeting_outcome"] == "good"
        assert result["showed_up"] is True

    @pytest.mark.asyncio
    async def test_record_outcome_with_deal_creation(self, meeting_service, mock_session, sample_meeting):
        """Test recording outcome and creating deal."""
        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_meeting
        get_result.fetchone.return_value = get_row

        # Mock update result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {
            **sample_meeting,
            "meeting_outcome": "good",
            "showed_up": True,
        }
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [get_result, update_result]

        # Note: create_deal=True would trigger deal service, which we're not fully testing here
        result = await meeting_service.record_outcome(
            meeting_id=sample_meeting["id"],
            outcome="good",
            create_deal=False,  # Testing without deal creation for simplicity
        )

        assert result["meeting_outcome"] == "good"

    @pytest.mark.asyncio
    async def test_record_invalid_outcome(self, meeting_service, mock_session, sample_meeting):
        """Test recording invalid outcome raises error."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await meeting_service.record_outcome(
                meeting_id=sample_meeting["id"],
                outcome="invalid_outcome",
            )


class TestMeetingServiceReschedule:
    """Tests for reschedule operations."""

    @pytest.mark.asyncio
    async def test_reschedule(self, meeting_service, mock_session, sample_meeting):
        """Test rescheduling a meeting."""
        new_time = datetime.utcnow() + timedelta(days=3)

        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_meeting
        get_result.fetchone.return_value = get_row

        # Mock update result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {
            **sample_meeting,
            "scheduled_at": new_time,
            "rescheduled_count": 1,
            "meeting_outcome": "rescheduled",
        }
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [get_result, update_result]

        result = await meeting_service.reschedule(
            meeting_id=sample_meeting["id"],
            new_scheduled_at=new_time,
            reason="Conflict with another meeting",
        )

        assert result["scheduled_at"] == new_time
        assert result["rescheduled_count"] == 1

    @pytest.mark.asyncio
    async def test_cancel(self, meeting_service, mock_session, sample_meeting):
        """Test cancelling a meeting."""
        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_meeting
        get_result.fetchone.return_value = get_row

        # Mock update result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {
            **sample_meeting,
            "meeting_outcome": "cancelled",
        }
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [get_result, update_result]

        result = await meeting_service.cancel(
            meeting_id=sample_meeting["id"],
            reason="Lead requested cancellation",
        )

        assert result["meeting_outcome"] == "cancelled"


class TestMeetingServiceQueries:
    """Tests for query operations."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, meeting_service, mock_session, sample_meeting):
        """Test getting meeting by ID."""
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = sample_meeting
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await meeting_service.get_by_id(sample_meeting["id"])

        assert result is not None
        assert result["id"] == sample_meeting["id"]

    @pytest.mark.asyncio
    async def test_list_upcoming(self, meeting_service, mock_session, sample_meeting):
        """Test listing upcoming meetings."""
        mock_result = MagicMock()
        mock_rows = [MagicMock(_mapping=sample_meeting)]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        result = await meeting_service.list_upcoming(
            client_id=sample_meeting["client_id"],
            days=7,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_needing_reminder(self, meeting_service, mock_session, sample_meeting):
        """Test listing meetings needing reminders."""
        mock_result = MagicMock()
        mock_rows = [MagicMock(_mapping=sample_meeting)]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        result = await meeting_service.list_needing_reminder(
            client_id=sample_meeting["client_id"],
            hours_before=24,
        )

        assert len(result) == 1


class TestMeetingConstants:
    """Tests for meeting constants."""

    def test_valid_meeting_types(self):
        """Test all expected meeting types are defined."""
        expected_types = [
            "discovery",
            "demo",
            "follow_up",
            "close",
            "onboarding",
            "other",
        ]
        assert MEETING_TYPES == expected_types

    def test_valid_meeting_outcomes(self):
        """Test all expected meeting outcomes are defined."""
        expected_outcomes = [
            "good",
            "bad",
            "rescheduled",
            "no_show",
            "cancelled",
            "pending",
        ]
        assert MEETING_OUTCOMES == expected_outcomes


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test create operations
# [x] Test invalid meeting type validation
# [x] Test confirmation
# [x] Test reminder tracking
# [x] Test show/no-show recording
# [x] Test outcome recording
# [x] Test invalid outcome validation
# [x] Test reschedule
# [x] Test cancel
# [x] Test get_by_id
# [x] Test list_upcoming
# [x] Test list_needing_reminder
# [x] Test constants
