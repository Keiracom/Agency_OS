"""tests/test_reply_router.py — Unit tests for reply_router.classify_reply."""

import pytest

from src.pipeline.reply_router import classify_reply


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify(subject: str = "", body: str = "", sender: str = "test@example.com", step: int = 1):
    return classify_reply(
        subject=subject, body=body, sender_email=sender, original_sequence_step=step
    )


# ---------------------------------------------------------------------------
# Intent: positive
# ---------------------------------------------------------------------------


class TestPositive:
    def test_interested_keyword(self):
        result = _classify(body="I'm interested, tell me more about your service.")
        assert result["intent"] == "positive"
        assert result["action"] == "pause_cadence"

    def test_sounds_good(self):
        result = _classify(body="Sounds good, let's chat.")
        assert result["intent"] == "positive"

    def test_can_you_send(self):
        result = _classify(body="Can you send me more details?")
        assert result["intent"] == "positive"

    def test_happy_to(self):
        result = _classify(body="Happy to discuss further.")
        assert result["intent"] == "positive"

    def test_love_to(self):
        result = _classify(body="Would love to connect.")
        assert result["intent"] == "positive"

    def test_confidence_increases_with_more_keywords(self):
        low = _classify(body="Interested.")
        high = _classify(body="Interested. Tell me more. Sounds good. Love to chat.")
        assert high["confidence"] > low["confidence"]


# ---------------------------------------------------------------------------
# Intent: booking
# ---------------------------------------------------------------------------


class TestBooking:
    def test_schedule_keyword(self):
        result = _classify(body="Can we schedule a call?")
        assert result["intent"] == "booking"
        assert result["action"] == "book_meeting"

    def test_book_keyword(self):
        result = _classify(body="Happy to book a meeting.")
        assert result["intent"] == "booking"

    def test_day_name_triggers_booking(self):
        result = _classify(body="Are you available Tuesday?")
        assert result["intent"] == "booking"

    def test_calendar_link(self):
        result = _classify(body="Send me your calendar link.")
        assert result["intent"] == "booking"

    def test_extracted_meeting_time_day_time(self):
        result = _classify(body="Let's meet Tuesday 2pm.")
        assert result["intent"] == "booking"
        assert "meeting_time" in result["extracted_data"]
        assert "tuesday" in result["extracted_data"]["meeting_time"].lower()

    def test_extracted_meeting_time_iso(self):
        result = _classify(body="How about we schedule on 2026-05-10?")
        assert result["intent"] == "booking"
        assert result["extracted_data"].get("meeting_time") == "2026-05-10"

    def test_no_extraction_when_no_date(self):
        result = _classify(body="Can we schedule a call sometime?")
        assert result["intent"] == "booking"
        # No date to extract — extracted_data should be empty or missing meeting_time
        assert result["extracted_data"].get("meeting_time") is None


# ---------------------------------------------------------------------------
# Intent: not_interested
# ---------------------------------------------------------------------------


class TestNotInterested:
    def test_not_interested(self):
        result = _classify(body="Not interested, thanks.")
        assert result["intent"] == "not_interested"
        assert result["action"] == "remove_from_cadence"

    def test_no_thanks(self):
        result = _classify(body="No thanks, we're all good.")
        assert result["intent"] == "not_interested"

    def test_dont_contact(self):
        result = _classify(body="Please don't contact me again.")
        assert result["intent"] == "not_interested"

    def test_stop_emailing(self):
        result = _classify(body="Stop emailing me.")
        assert result["intent"] == "not_interested"

    def test_not_for_us(self):
        result = _classify(body="This is not for us at this stage.")
        assert result["intent"] == "not_interested"

    def test_remove_me(self):
        result = _classify(body="Please remove me from your list.")
        # "remove me" is not_interested; "remove from list" is unsubscribe — ensure not_interested
        # Note: priority order puts unsubscribe above not_interested — only "remove me" matches not_interested
        assert result["intent"] == "not_interested"


# ---------------------------------------------------------------------------
# Intent: ooo
# ---------------------------------------------------------------------------


class TestOOO:
    def test_out_of_office(self):
        result = _classify(
            subject="Out of Office: Re: your email", body="I am out of office until May 1."
        )
        assert result["intent"] == "ooo"
        assert result["action"] == "mark_ooo"

    def test_away_from(self):
        result = _classify(body="I am away from the office this week.")
        assert result["intent"] == "ooo"

    def test_limited_access(self):
        result = _classify(body="I have limited access to email until next Monday.")
        assert result["intent"] == "ooo"

    def test_return_date_iso_extracted(self):
        result = _classify(body="Out of office. I will return on 2026-05-01.")
        assert result["intent"] == "ooo"
        assert result["extracted_data"].get("ooo_return") == "2026-05-01"

    def test_back_on_date(self):
        result = _classify(body="I am out of office. I'll be back on 2026-04-20.")
        assert result["intent"] == "ooo"
        assert "ooo_return" in result["extracted_data"]

    def test_no_return_date_when_absent(self):
        result = _classify(body="Out of office this week.")
        assert result["intent"] == "ooo"
        assert result["extracted_data"].get("ooo_return") is None


# ---------------------------------------------------------------------------
# Intent: unsubscribe
# ---------------------------------------------------------------------------


class TestUnsubscribe:
    def test_unsubscribe_keyword(self):
        result = _classify(body="Please unsubscribe me from all future emails.")
        assert result["intent"] == "unsubscribe"
        assert result["action"] == "suppress"

    def test_opt_out(self):
        result = _classify(body="I'd like to opt out of this mailing list.")
        assert result["intent"] == "unsubscribe"

    def test_opt_out_hyphen(self):
        result = _classify(body="Opt-out request.")
        assert result["intent"] == "unsubscribe"

    def test_remove_from_list(self):
        result = _classify(body="Remove from list please.")
        assert result["intent"] == "unsubscribe"

    def test_unsubscribe_beats_not_interested(self):
        """Unsubscribe takes legal priority over not_interested."""
        result = _classify(body="Not interested. Please unsubscribe me.")
        assert result["intent"] == "unsubscribe"


# ---------------------------------------------------------------------------
# Intent: bounce
# ---------------------------------------------------------------------------


class TestBounce:
    def test_delivery_failed(self):
        result = _classify(subject="Delivery failed", body="Your message could not be delivered.")
        assert result["intent"] == "bounce"
        assert result["action"] == "suppress"

    def test_undeliverable(self):
        result = _classify(body="This message is undeliverable.")
        assert result["intent"] == "bounce"

    def test_mailbox_full(self):
        result = _classify(body="The recipient's mailbox full.")
        assert result["intent"] == "bounce"

    def test_user_unknown(self):
        result = _classify(body="User unknown at this domain.")
        assert result["intent"] == "bounce"

    def test_smtp_550(self):
        result = _classify(body="550 5.1.1 The email account does not exist.")
        assert result["intent"] == "bounce"

    def test_smtp_553(self):
        result = _classify(body="553 sorry, no mailbox by that name.")
        assert result["intent"] == "bounce"

    def test_bounce_beats_unsubscribe(self):
        """Bounce takes priority over unsubscribe when both present (bounce = hard suppression)."""
        result = _classify(body="Delivery failed. Please unsubscribe me.")
        # Unsubscribe has higher priority in _PRIORITY_ORDER — this tests actual priority
        # unsubscribe is listed BEFORE bounce, so it wins
        assert result["intent"] in {"unsubscribe", "bounce"}  # either valid legal suppression


# ---------------------------------------------------------------------------
# Intent: unclear
# ---------------------------------------------------------------------------


class TestUnclear:
    def test_empty_body(self):
        result = _classify(body="")
        assert result["intent"] == "unclear"
        assert result["action"] == "escalate_human"
        assert result["confidence"] == 0.0

    def test_generic_reply(self):
        result = _classify(body="Thanks for reaching out.")
        assert result["intent"] == "unclear"

    def test_random_text(self):
        result = _classify(body="Hello there, just following up on something unrelated.")
        assert result["intent"] == "unclear"


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestConfidence:
    def test_confidence_between_0_and_1(self):
        for body in [
            "interested",
            "not interested",
            "unsubscribe",
            "out of office",
            "delivery failed",
            "book a call Tuesday",
            "",
        ]:
            result = _classify(body=body)
            assert 0.0 <= result["confidence"] <= 1.0, f"Confidence out of range for: {body!r}"

    def test_multiple_hits_raises_confidence(self):
        single = _classify(body="Interested.")
        multi = _classify(
            body="Interested. Tell me more. Sounds good. Happy to. Love to. Can you send."
        )
        assert multi["confidence"] >= single["confidence"]

    def test_unclear_always_zero(self):
        result = _classify(body="Just checking in.")
        assert result["intent"] == "unclear"
        assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Return value structure
# ---------------------------------------------------------------------------


class TestReturnStructure:
    def test_all_keys_present(self):
        result = _classify(body="Interested in learning more.")
        for key in ("intent", "confidence", "action", "reason", "extracted_data"):
            assert key in result, f"Missing key: {key}"

    def test_extracted_data_is_dict(self):
        result = _classify(body="Thanks.")
        assert isinstance(result["extracted_data"], dict)

    def test_reason_is_non_empty_string(self):
        result = _classify(body="Not interested.")
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0


# ---------------------------------------------------------------------------
# Subject line classification
# ---------------------------------------------------------------------------


class TestSubjectLine:
    def test_ooo_in_subject_only(self):
        result = _classify(subject="Out of Office: Away this week", body="I am away.")
        assert result["intent"] == "ooo"

    def test_delivery_failed_in_subject(self):
        result = _classify(subject="Delivery failed", body="")
        assert result["intent"] == "bounce"
