"""
Tests for CIS bridge calls in meeting_service.py and voice_post_call_processor.py
(Directive #180 — Gap identified in Directive #178 E2E audit)

CIS bridge was wired in PR #162 (Directive #177). Zero test coverage existed.

Tests cover:
- update_outreach_outcome called with 'meeting_booked' on meeting creation
- record_propensity_conversion called on meeting creation
- process_conversion_timing called on meeting creation
- CIS failure is non-blocking (try/except verified)
- Voice→CIS bridge: update_outreach_outcome called for BOOKED outcome

Patch targets:
  CISService is imported inline inside the try block:
    `from src.services.cis_service import CISService`
  process_conversion_timing is also imported inline:
    `from src.services.cis_outcome_service import process_conversion_timing`

  Patching the source module attributes works because Python resolves the
  import at call time and reads from the patched module object.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.meeting_service import MeetingService


# =========================================================================
# HELPERS
# =========================================================================


def _make_mock_session(
    als_score: int | None = 75,
    als_tier: str | None = "warm",
    touches_count: int = 3,
):
    """
    Build an AsyncMock session that returns reasonable row data for the
    queries inside MeetingService.create():
      1. touches / first_touch SELECT
      2. INSERT INTO meetings RETURNING *
      3. UPDATE leads SET meeting_booked=TRUE
      4. SELECT als_score, als_tier FROM leads  (CIS bridge)
    """
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    # Row returned by the INSERT ... RETURNING * query
    meeting_row = MagicMock()
    meeting_row.id = uuid4()
    meeting_row._mapping = {
        "id": meeting_row.id,
        "client_id": uuid4(),
        "lead_id": uuid4(),
        "scheduled_at": datetime.now(UTC),
        "duration_minutes": 30,
        "meeting_type": "discovery",
        "booked_by": "ai",
        "booking_method": "calendly",
    }

    # Row returned by touches SELECT
    touches_row = MagicMock()
    touches_row.count = touches_count
    touches_row.first_touch = datetime.now(UTC)

    # Row returned by propensity SELECT (inside CIS try block)
    prop_row = MagicMock()
    prop_row.als_score = als_score
    prop_row.als_tier = als_tier

    def _make_result(row):
        r = MagicMock()
        r.fetchone.return_value = row
        return r

    # session.execute is called in order:
    #   [0] touches query
    #   [1] INSERT meeting
    #   [2] UPDATE leads
    #   [3] SELECT als_score, als_tier (inside CIS try block)
    session.execute.side_effect = [
        _make_result(touches_row),
        _make_result(meeting_row),
        _make_result(None),
        _make_result(prop_row),
    ]

    return session, meeting_row


# =========================================================================
# MEETING SERVICE — CIS BRIDGE TESTS
# =========================================================================


class TestMeetingServiceCisBridge:
    """
    Verify that MeetingService.create() fires all three CIS bridge calls
    when a meeting is created with a converting_activity_id.
    """

    @pytest.mark.asyncio
    async def test_update_outreach_outcome_called_with_meeting_booked(self):
        """update_outreach_outcome must be called with event_type='meeting_booked'."""
        session, meeting_row = _make_mock_session()
        service = MeetingService(session)

        activity_id = uuid4()
        client_id = uuid4()
        lead_id = uuid4()

        with patch.object(service, "_push_to_crm", new=AsyncMock(return_value=None)):
            with patch("src.services.cis_service.CISService") as MockCIS:
                with patch(
                    "src.services.cis_outcome_service.process_conversion_timing",
                    new_callable=AsyncMock,
                ):
                    mock_cis = AsyncMock()
                    MockCIS.return_value = mock_cis

                    await service.create(
                        client_id=client_id,
                        lead_id=lead_id,
                        scheduled_at=datetime.now(UTC),
                        converting_activity_id=activity_id,
                        converting_channel="email",
                    )

                    mock_cis.update_outreach_outcome.assert_called_once()
                    call_kwargs = mock_cis.update_outreach_outcome.call_args.kwargs
                    assert call_kwargs["event_type"] == "meeting_booked", (
                        "update_outreach_outcome must be called with event_type='meeting_booked'"
                    )
                    assert str(call_kwargs["activity_id"]) == str(activity_id), (
                        "update_outreach_outcome must receive the converting_activity_id"
                    )

    @pytest.mark.asyncio
    async def test_process_conversion_timing_called_on_booking(self):
        """process_conversion_timing must be called with the converting_activity_id."""
        session, meeting_row = _make_mock_session()
        service = MeetingService(session)

        activity_id = uuid4()

        with patch.object(service, "_push_to_crm", new=AsyncMock(return_value=None)):
            with patch("src.services.cis_service.CISService") as MockCIS:
                with patch(
                    "src.services.cis_outcome_service.process_conversion_timing",
                    new_callable=AsyncMock,
                ) as mock_pct:
                    MockCIS.return_value = AsyncMock()

                    await service.create(
                        client_id=uuid4(),
                        lead_id=uuid4(),
                        scheduled_at=datetime.now(UTC),
                        converting_activity_id=activity_id,
                    )

                    mock_pct.assert_called_once()
                    # process_conversion_timing(session, str(activity_id))
                    positional_args = mock_pct.call_args.args
                    assert str(activity_id) in positional_args, (
                        "process_conversion_timing must receive str(converting_activity_id)"
                    )

    @pytest.mark.asyncio
    async def test_record_propensity_conversion_called_on_booking(self):
        """record_propensity_conversion must be called when lead has als_score."""
        session, meeting_row = _make_mock_session(als_score=80, als_tier="warm")
        service = MeetingService(session)

        with patch.object(service, "_push_to_crm", new=AsyncMock(return_value=None)):
            with patch("src.services.cis_service.CISService") as MockCIS:
                with patch(
                    "src.services.cis_outcome_service.process_conversion_timing",
                    new_callable=AsyncMock,
                ):
                    mock_cis = AsyncMock()
                    MockCIS.return_value = mock_cis

                    await service.create(
                        client_id=uuid4(),
                        lead_id=uuid4(),
                        scheduled_at=datetime.now(UTC),
                        converting_activity_id=uuid4(),
                        converting_channel="linkedin",
                    )

                    mock_cis.record_propensity_conversion.assert_called_once()

    @pytest.mark.asyncio
    async def test_cis_failure_does_not_block_meeting_creation(self):
        """CIS bridge failure must NOT prevent meeting from being returned."""
        session, meeting_row = _make_mock_session()
        service = MeetingService(session)

        with patch.object(service, "_push_to_crm", new=AsyncMock(return_value=None)):
            with patch("src.services.cis_service.CISService") as MockCIS:
                # Make CISService constructor raise to simulate complete CIS failure
                MockCIS.side_effect = Exception("CIS database unavailable")

                result = await service.create(
                    client_id=uuid4(),
                    lead_id=uuid4(),
                    scheduled_at=datetime.now(UTC),
                    converting_activity_id=uuid4(),
                )

                # Meeting must still be returned despite CIS failure
                assert result is not None, (
                    "Meeting creation must succeed even when CIS bridge raises Exception"
                )
                assert "id" in result, (
                    "Returned meeting dict must contain 'id' field"
                )

    @pytest.mark.asyncio
    async def test_cis_not_called_without_converting_activity_id(self):
        """
        When no converting_activity_id is provided, update_outreach_outcome
        and process_conversion_timing must NOT be called (guard clause in bridge).
        """
        session, meeting_row = _make_mock_session()
        service = MeetingService(session)

        with patch.object(service, "_push_to_crm", new=AsyncMock(return_value=None)):
            with patch("src.services.cis_service.CISService") as MockCIS:
                with patch(
                    "src.services.cis_outcome_service.process_conversion_timing",
                    new_callable=AsyncMock,
                ) as mock_pct:
                    mock_cis = AsyncMock()
                    MockCIS.return_value = mock_cis

                    await service.create(
                        client_id=uuid4(),
                        lead_id=uuid4(),
                        scheduled_at=datetime.now(UTC),
                        converting_activity_id=None,
                    )

                    mock_cis.update_outreach_outcome.assert_not_called()
                    mock_pct.assert_not_called()


# =========================================================================
# VOICE POST-CALL PROCESSOR — CIS BRIDGE TESTS
# =========================================================================


class TestVoiceCisBridge:
    """
    Verify that _write_cis_feed() fires update_outreach_outcome for BOOKED
    voice call outcomes.

    The voice → CIS bridge (Directive #177) looks up the activity via
      activities JOIN voice_calls ON provider_message_id = voice_calls.id::text
    then calls update_outreach_outcome with event_type='meeting_booked'.
    """

    @pytest.fixture
    def mock_session(self):
        """Return a minimal AsyncMock session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_voice_booked_outcome_calls_update_outreach_outcome(self, mock_session):
        """
        When a BOOKED voice call outcome is processed, update_outreach_outcome
        must be called with event_type='meeting_booked'.
        """
        from src.services.voice_post_call_processor import VoicePostCallProcessor, CallOutcome

        activity_id = uuid4()
        act_row = MagicMock()
        act_row.id = activity_id

        mock_insert_result = MagicMock()
        mock_insert_result.fetchone.return_value = None

        mock_act_result = MagicMock()
        mock_act_result.fetchone.return_value = act_row

        mock_session.execute.side_effect = [
            mock_insert_result,   # INSERT into conversion_events
            mock_act_result,      # SELECT activity for CIS voice bridge
        ]

        processor = VoicePostCallProcessor(mock_session)

        with patch("src.services.cis_service.CISService") as MockCIS:
            mock_cis = AsyncMock()
            MockCIS.return_value = mock_cis

            await processor._write_cis_feed(
                call_sid="CA_test_booked",
                outcome=CallOutcome.BOOKED,
                hook_used="hook_v1",
                propensity_score_at_call=70,
                client_id=uuid4(),
            )

            mock_cis.update_outreach_outcome.assert_called_once()
            call_kwargs = mock_cis.update_outreach_outcome.call_args.kwargs
            assert call_kwargs["event_type"] == "meeting_booked", (
                "Voice BOOKED must map to CIS event_type='meeting_booked'"
            )
            assert call_kwargs["activity_id"] == activity_id, (
                "update_outreach_outcome must receive the activity id from voice_calls join"
            )

    @pytest.mark.asyncio
    async def test_voice_non_booked_outcome_does_not_call_cis(self, mock_session):
        """
        Outcomes not in the CIS map (e.g. VOICEMAIL) must NOT trigger
        update_outreach_outcome — the if-guard must prevent it.
        """
        from src.services.voice_post_call_processor import VoicePostCallProcessor, CallOutcome

        mock_insert_result = MagicMock()
        mock_insert_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_insert_result

        processor = VoicePostCallProcessor(mock_session)

        with patch("src.services.cis_service.CISService") as MockCIS:
            mock_cis = AsyncMock()
            MockCIS.return_value = mock_cis

            await processor._write_cis_feed(
                call_sid="CA_test_voicemail",
                outcome=CallOutcome.VOICEMAIL,
                hook_used=None,
                propensity_score_at_call=None,
                client_id=None,
            )

            mock_cis.update_outreach_outcome.assert_not_called()

    @pytest.mark.asyncio
    async def test_voice_cis_failure_does_not_raise(self, mock_session):
        """
        If the CIS voice bridge raises an Exception, _write_cis_feed must
        complete without propagating the error (non-blocking pattern).
        """
        from src.services.voice_post_call_processor import VoicePostCallProcessor, CallOutcome

        mock_insert_result = MagicMock()
        mock_insert_result.fetchone.return_value = None

        mock_session.execute.side_effect = [
            mock_insert_result,       # INSERT conversion_events OK
            Exception("DB timeout"),  # Activity SELECT blows up inside CIS try block
        ]

        processor = VoicePostCallProcessor(mock_session)

        # Must not raise — CIS failure is non-blocking
        await processor._write_cis_feed(
            call_sid="CA_test_noblocking",
            outcome=CallOutcome.BOOKED,
            hook_used=None,
            propensity_score_at_call=None,
            client_id=None,
        )

    @pytest.mark.asyncio
    async def test_voice_booked_no_activity_found_skips_cis(self, mock_session):
        """
        If voice_sync_tasks hasn't created the activity yet (fetchone returns None),
        update_outreach_outcome must NOT be called — guard clause in bridge.
        """
        from src.services.voice_post_call_processor import VoicePostCallProcessor, CallOutcome

        mock_insert_result = MagicMock()
        mock_insert_result.fetchone.return_value = None

        mock_act_result = MagicMock()
        mock_act_result.fetchone.return_value = None  # No activity found yet

        mock_session.execute.side_effect = [
            mock_insert_result,   # INSERT conversion_events
            mock_act_result,      # SELECT activity → no row
        ]

        processor = VoicePostCallProcessor(mock_session)

        with patch("src.services.cis_service.CISService") as MockCIS:
            mock_cis = AsyncMock()
            MockCIS.return_value = mock_cis

            await processor._write_cis_feed(
                call_sid="CA_test_noact",
                outcome=CallOutcome.BOOKED,
                hook_used=None,
                propensity_score_at_call=None,
                client_id=uuid4(),
            )

            mock_cis.update_outreach_outcome.assert_not_called()
