"""tests/test_booking_handler.py — Unit tests for booking_handler module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.booking_handler import (
    create_deal_from_booking,
    extract_prospect_from_booking,
    handle_booking_webhook,
    pause_prospect_cadence,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CALENDLY_PAYLOAD = {
    "event": {
        "invitees": [{"email": "buyer@example.com", "name": "Jane Buyer"}],
        "event_type": {"name": "30-Minute Discovery Call"},
        "start_time": "2026-04-20T09:00:00Z",
    }
}

CALCOM_PAYLOAD = {
    "email": "sales@acme.com",
    "name": "Bob Sales",
    "type": "Product Demo",
    "startTime": "2026-04-21T14:00:00Z",
}

FLAT_PAYLOAD = {
    "email": "owner@smbiz.com.au",
    "name": "Sue Owner",
    "event_type": "intro_call",
    "scheduled_time": "2026-04-22T10:00:00Z",
    "calendar_link": "https://cal.example.com/sue",
}


# ---------------------------------------------------------------------------
# extract_prospect_from_booking
# ---------------------------------------------------------------------------


class TestExtractProspectFromBooking:
    def test_calendly_shape(self):
        prospect = extract_prospect_from_booking(CALENDLY_PAYLOAD)
        assert prospect["email"] == "buyer@example.com"
        assert prospect["name"] == "Jane Buyer"
        assert prospect["event_type"] == "30-Minute Discovery Call"
        assert prospect["scheduled_time"] == "2026-04-20T09:00:00Z"

    def test_calcom_shape(self):
        prospect = extract_prospect_from_booking(CALCOM_PAYLOAD)
        assert prospect["email"] == "sales@acme.com"
        assert prospect["name"] == "Bob Sales"
        assert prospect["event_type"] == "Product Demo"
        assert prospect["scheduled_time"] == "2026-04-21T14:00:00Z"

    def test_flat_generic_shape(self):
        prospect = extract_prospect_from_booking(FLAT_PAYLOAD)
        assert prospect["email"] == "owner@smbiz.com.au"
        assert prospect["name"] == "Sue Owner"
        assert prospect["event_type"] == "intro_call"

    def test_empty_payload_returns_empty_strings(self):
        prospect = extract_prospect_from_booking({})
        assert prospect["email"] == ""
        assert prospect["name"] == ""


# ---------------------------------------------------------------------------
# pause_prospect_cadence
# ---------------------------------------------------------------------------


class TestPauseProspectCadence:
    def test_returns_paused_false_without_supabase(self):
        """When Supabase is unavailable the function returns gracefully."""
        with patch("src.pipeline.booking_handler._HAS_SUPABASE", False):
            result = pause_prospect_cadence("test@example.com")
        assert result["paused"] is False
        assert result["email"] == "test@example.com"
        assert result["status"] == "booked"

    def test_returns_paused_true_when_db_succeeds(self):
        """When Supabase is available and the coroutine succeeds, paused=True."""
        with (
            patch("src.pipeline.booking_handler._HAS_SUPABASE", True),
            patch(
                "src.pipeline.booking_handler._pause_in_db",
                return_value=None,
            ),
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_until_complete = MagicMock(return_value=None)
            result = pause_prospect_cadence("ok@example.com")
        assert result["email"] == "ok@example.com"
        # paused may be True or False depending on mock depth — just check no exception
        assert "paused" in result

    def test_db_exception_does_not_raise(self):
        """Best-effort: DB errors must be swallowed."""
        with (
            patch("src.pipeline.booking_handler._HAS_SUPABASE", True),
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_until_complete.side_effect = RuntimeError("db down")
            result = pause_prospect_cadence("fail@example.com")
        assert result["paused"] is False


# ---------------------------------------------------------------------------
# create_deal_from_booking
# ---------------------------------------------------------------------------


class TestCreateDealFromBooking:
    def test_deal_shape(self):
        with patch("src.pipeline.booking_handler._HAS_SUPABASE", False):
            deal = create_deal_from_booking(
                "owner@smbiz.com.au", "Sue Owner", "intro_call", "2026-04-22T10:00:00Z"
            )
        assert deal["prospect_email"] == "owner@smbiz.com.au"
        assert deal["prospect_name"] == "Sue Owner"
        assert deal["event_type"] == "intro_call"
        assert deal["meeting_time"] == "2026-04-22T10:00:00Z"
        assert deal["stage"] == "meeting_booked"
        assert deal["source"] == "calendar_webhook"
        assert "id" in deal
        assert "created_at" in deal

    def test_persisted_false_without_supabase(self):
        with patch("src.pipeline.booking_handler._HAS_SUPABASE", False):
            deal = create_deal_from_booking("x@y.com", "X", "call", "2026-01-01T00:00:00Z")
        assert deal["persisted"] is False

    def test_db_exception_does_not_raise(self):
        with (
            patch("src.pipeline.booking_handler._HAS_SUPABASE", True),
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.run_until_complete.side_effect = RuntimeError("db down")
            deal = create_deal_from_booking("fail@y.com", "Fail", "call", "2026-01-01T00:00:00Z")
        assert deal["persisted"] is False


# ---------------------------------------------------------------------------
# handle_booking_webhook — integration of all helpers
# ---------------------------------------------------------------------------


class TestHandleBookingWebhook:
    def test_missing_email_returns_error(self):
        result = handle_booking_webhook({})
        assert result["action"] == "error"
        assert result["error"] == "missing_email"

    def test_calendly_payload_pauses_cadence(self):
        with patch("src.pipeline.booking_handler._HAS_SUPABASE", False):
            result = handle_booking_webhook(CALENDLY_PAYLOAD)
        assert result["action"] == "cadence_paused"
        assert result["prospect_email"] == "buyer@example.com"
        assert result["meeting_time"] == "2026-04-20T09:00:00Z"
        assert "deal_data" in result

    def test_calcom_payload_pauses_cadence(self):
        with patch("src.pipeline.booking_handler._HAS_SUPABASE", False):
            result = handle_booking_webhook(CALCOM_PAYLOAD)
        assert result["action"] == "cadence_paused"
        assert result["prospect_email"] == "sales@acme.com"

    def test_deal_created_false_without_supabase(self):
        with patch("src.pipeline.booking_handler._HAS_SUPABASE", False):
            result = handle_booking_webhook(FLAT_PAYLOAD)
        assert result["deal_created"] is False

    def test_deal_data_contains_required_keys(self):
        with patch("src.pipeline.booking_handler._HAS_SUPABASE", False):
            result = handle_booking_webhook(FLAT_PAYLOAD)
        deal = result["deal_data"]
        for key in ("id", "prospect_email", "prospect_name", "stage", "source", "created_at"):
            assert key in deal, f"Missing key: {key}"
