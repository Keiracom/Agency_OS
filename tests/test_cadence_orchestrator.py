"""tests/test_cadence_orchestrator.py — Unit tests for CadenceOrchestrator functions."""

from __future__ import annotations

import pytest

from src.pipeline.cadence_orchestrator import (
    get_channel_for_step,
    get_default_sequence,
    get_next_step,
    is_converted,
    is_suppressed,
    should_pause,
)

# ---------------------------------------------------------------------------
# get_default_sequence
# ---------------------------------------------------------------------------


class TestDefaultSequence:
    def test_returns_five_steps(self):
        seq = get_default_sequence()
        assert len(seq) == 5

    def test_steps_are_numbered_1_to_5(self):
        seq = get_default_sequence()
        assert [s["step"] for s in seq] == [1, 2, 3, 4, 5]

    def test_channels_follow_spec(self):
        seq = get_default_sequence()
        channels = [s["channel"] for s in seq]
        assert channels == ["email", "email", "linkedin", "email", "voice"]

    def test_first_step_zero_delay(self):
        seq = get_default_sequence()
        assert seq[0]["delay_after_previous"] == 0

    def test_delays_are_positive_after_step_1(self):
        seq = get_default_sequence()
        for s in seq[1:]:
            assert s["delay_after_previous"] > 0

    def test_returns_independent_copies(self):
        seq1 = get_default_sequence()
        seq2 = get_default_sequence()
        seq1[0]["channel"] = "MUTATED"
        assert seq2[0]["channel"] == "email"


# ---------------------------------------------------------------------------
# should_pause
# ---------------------------------------------------------------------------


class TestShouldPause:
    def test_pauses_on_positive(self):
        assert should_pause("p1", "positive") is True

    def test_pauses_on_booked(self):
        assert should_pause("p1", "booked") is True

    def test_pauses_on_meeting_request(self):
        assert should_pause("p1", "meeting_request") is True

    def test_pauses_on_unsubscribe(self):
        assert should_pause("p1", "unsubscribe") is True

    def test_does_not_pause_on_not_interested(self):
        assert should_pause("p1", "not_interested") is False

    def test_does_not_pause_on_none_like_string(self):
        assert should_pause("p1", "bounce") is False

    def test_does_not_pause_on_no_reply(self):
        # Callers pass None for no reply; should_pause receives a string when called
        # This test ensures unknown intents don't trigger a pause
        assert should_pause("p1", "unknown_intent") is False


# ---------------------------------------------------------------------------
# is_suppressed / is_converted
# ---------------------------------------------------------------------------


class TestSuppressionAndConversion:
    def test_unsubscribe_is_suppressed(self):
        assert is_suppressed("unsubscribe") is True

    def test_opt_out_is_suppressed(self):
        assert is_suppressed("opt_out") is True

    def test_positive_not_suppressed(self):
        assert is_suppressed("positive") is False

    def test_booked_is_converted(self):
        assert is_converted("booked") is True

    def test_positive_not_converted(self):
        assert is_converted("positive") is False

    def test_unsubscribe_not_converted(self):
        assert is_converted("unsubscribe") is False


# ---------------------------------------------------------------------------
# get_channel_for_step
# ---------------------------------------------------------------------------


class TestGetChannelForStep:
    def test_preferred_email_returned_when_available(self):
        assert (
            get_channel_for_step(1, has_email=True, has_phone=False, has_linkedin=False) == "email"
        )

    def test_falls_back_to_linkedin_when_no_email(self):
        # Step 1 prefers email; linkedin is next in fallback order
        ch = get_channel_for_step(1, has_email=False, has_phone=False, has_linkedin=True)
        assert ch == "linkedin"

    def test_falls_back_to_voice_when_only_phone(self):
        ch = get_channel_for_step(1, has_email=False, has_phone=True, has_linkedin=False)
        assert ch == "voice"

    def test_returns_none_when_no_channels_available(self):
        assert get_channel_for_step(1, has_email=False, has_phone=False, has_linkedin=False) is None

    def test_linkedin_step_returns_linkedin_when_available(self):
        ch = get_channel_for_step(3, has_email=True, has_phone=False, has_linkedin=True)
        assert ch == "linkedin"

    def test_linkedin_step_falls_back_to_email_when_no_linkedin(self):
        ch = get_channel_for_step(3, has_email=True, has_phone=False, has_linkedin=False)
        assert ch == "email"

    def test_voice_step_returns_voice_when_phone_available(self):
        ch = get_channel_for_step(5, has_email=False, has_phone=True, has_linkedin=False)
        assert ch == "voice"

    def test_voice_step_falls_back_to_email_when_no_phone(self):
        ch = get_channel_for_step(5, has_email=True, has_phone=False, has_linkedin=False)
        assert ch == "email"


# ---------------------------------------------------------------------------
# get_next_step
# ---------------------------------------------------------------------------


class TestGetNextStep:
    def test_advances_from_step_0_to_step_1(self):
        result = get_next_step("p1", current_step=0, last_response=None)
        assert result["action"] == "send"
        assert result["next_step"] == 1

    def test_advances_through_sequence(self):
        for step in range(1, 5):
            result = get_next_step("p1", current_step=step, last_response=None)
            assert result["action"] == "send"
            assert result["next_step"] == step + 1

    def test_completes_after_last_step(self):
        result = get_next_step("p1", current_step=5, last_response=None)
        assert result["action"] == "complete"
        assert result.get("converted") is False

    def test_pauses_on_positive_reply(self):
        result = get_next_step("p1", current_step=2, last_response="positive")
        assert result["action"] == "pause"
        assert result["converted"] is False

    def test_pauses_and_converts_on_booked(self):
        result = get_next_step("p1", current_step=2, last_response="booked")
        assert result["action"] == "pause"
        assert result["converted"] is True

    def test_suppresses_on_unsubscribe(self):
        result = get_next_step("p1", current_step=1, last_response="unsubscribe")
        assert result["action"] == "suppress"
        assert result["converted"] is False

    def test_suppresses_on_opt_out(self):
        result = get_next_step("p1", current_step=3, last_response="opt_out")
        assert result["action"] == "suppress"

    def test_send_result_includes_delay_and_channel(self):
        result = get_next_step("p1", current_step=0, last_response=None)
        assert "channel" in result
        assert "delay_days" in result

    def test_not_interested_does_not_pause(self):
        # not_interested → continue sequence
        result = get_next_step("p1", current_step=1, last_response="not_interested")
        assert result["action"] == "send"
        assert result["next_step"] == 2
