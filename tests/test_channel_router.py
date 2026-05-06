"""Tests for src/pipeline/channel_router.py"""

import pytest
from src.pipeline.channel_router import route_prospect


# ------------------------------------------------------------------ #
# Channel combination tests
# ------------------------------------------------------------------ #


def test_full_coverage_email_phone_linkedin():
    result = route_prospect(has_email=True, has_phone=True, has_linkedin=True)
    assert result["primary_channel"] == "email"
    assert "voice" in result["fallback_channels"]
    assert "linkedin" in result["fallback_channels"]
    assert result["channels_available"] == ["email", "voice", "linkedin"]
    assert len(result["recommended_sequence"]) == 5


def test_email_linkedin_no_phone():
    result = route_prospect(has_email=True, has_phone=False, has_linkedin=True)
    assert result["primary_channel"] == "email"
    assert result["fallback_channels"] == ["linkedin"]
    assert "voice" not in result["channels_available"]
    assert len(result["recommended_sequence"]) == 4


def test_voice_linkedin_no_email():
    result = route_prospect(has_email=False, has_phone=True, has_linkedin=True)
    assert result["primary_channel"] == "voice"
    assert result["fallback_channels"] == ["linkedin"]
    assert "email" not in result["channels_available"]
    assert len(result["recommended_sequence"]) == 3


def test_phone_only():
    result = route_prospect(has_email=False, has_phone=True, has_linkedin=False)
    assert result["primary_channel"] == "voice"
    assert result["fallback_channels"] == []
    assert result["channels_available"] == ["voice"]
    assert len(result["recommended_sequence"]) == 2


def test_linkedin_only():
    result = route_prospect(has_email=False, has_phone=False, has_linkedin=True)
    assert result["primary_channel"] == "linkedin"
    assert result["fallback_channels"] == []
    assert result["channels_available"] == ["linkedin"]
    assert len(result["recommended_sequence"]) == 3


def test_email_only():
    result = route_prospect(has_email=True, has_phone=False, has_linkedin=False)
    assert result["primary_channel"] == "email"
    assert result["fallback_channels"] == []
    assert result["channels_available"] == ["email"]
    assert len(result["recommended_sequence"]) == 3


def test_email_phone_no_linkedin():
    result = route_prospect(has_email=True, has_phone=True, has_linkedin=False)
    assert result["primary_channel"] == "email"
    assert result["fallback_channels"] == ["voice"]
    assert "linkedin" not in result["channels_available"]
    assert len(result["recommended_sequence"]) == 4


# ------------------------------------------------------------------ #
# No reachability
# ------------------------------------------------------------------ #


def test_no_reachability():
    result = route_prospect(has_email=False, has_phone=False, has_linkedin=False)
    assert result["primary_channel"] == "none"
    assert result["fallback_channels"] == []
    assert result["channels_available"] == []
    assert result["routing_reason"] == "no_reachability"
    assert result["recommended_sequence"] == []


# ------------------------------------------------------------------ #
# CIS-based priority adjustment
# ------------------------------------------------------------------ #


def test_high_cis_promotes_voice_when_full_coverage():
    """High CIS (>=85) with phone available should promote voice to primary."""
    result = route_prospect(has_email=True, has_phone=True, has_linkedin=True, cis_score=90)
    assert result["primary_channel"] == "voice"
    assert "high_cis_voice_priority" in result["routing_reason"]


def test_high_cis_adds_extra_touch():
    """High CIS should append an extra touch to the sequence."""
    result_high = route_prospect(has_email=True, has_phone=True, has_linkedin=True, cis_score=90)
    result_normal = route_prospect(has_email=True, has_phone=True, has_linkedin=True, cis_score=60)
    assert len(result_high["recommended_sequence"]) > len(result_normal["recommended_sequence"])


def test_high_cis_extra_touch_is_voice_when_phone_available():
    """Extra touch for high CIS should be voice if phone is available."""
    result = route_prospect(has_email=False, has_phone=True, has_linkedin=True, cis_score=90)
    extra = result["recommended_sequence"][-1]
    assert extra["channel"] == "voice"
    assert extra["note"] == "high-value extra touch"


def test_low_cis_restricts_to_email_when_available():
    """Low CIS (<40) with email should reduce to email-only touches."""
    result = route_prospect(has_email=True, has_phone=True, has_linkedin=True, cis_score=30)
    assert result["primary_channel"] == "email"
    assert result["fallback_channels"] == []
    assert "low_cis_email_only" in result["routing_reason"]
    channels_used = {t["channel"] for t in result["recommended_sequence"]}
    assert channels_used == {"email"}


def test_low_cis_no_email_keeps_best_available():
    """Low CIS without email should not force email-only (email unavailable)."""
    result = route_prospect(has_email=False, has_phone=True, has_linkedin=True, cis_score=25)
    # No email means low-CIS email-only clause does not fire
    assert result["primary_channel"] == "voice"
    assert "low_cis_email_only" not in result["routing_reason"]


def test_mid_cis_no_adjustment():
    """Mid-range CIS (40-84) should produce unmodified base routing."""
    result = route_prospect(has_email=True, has_phone=True, has_linkedin=True, cis_score=60)
    assert result["primary_channel"] == "email"
    assert "high_cis" not in result["routing_reason"]
    assert "low_cis" not in result["routing_reason"]


# ------------------------------------------------------------------ #
# Sequence shape
# ------------------------------------------------------------------ #


def test_sequence_touch_numbers_are_sequential():
    result = route_prospect(has_email=True, has_phone=True, has_linkedin=True)
    touches = [t["touch"] for t in result["recommended_sequence"]]
    assert touches == list(range(1, len(touches) + 1))


def test_sequence_days_are_non_decreasing():
    result = route_prospect(has_email=True, has_phone=True, has_linkedin=True)
    days = [t["day"] for t in result["recommended_sequence"]]
    assert days == sorted(days)


def test_sequence_items_have_required_keys():
    result = route_prospect(has_email=True, has_phone=True, has_linkedin=True)
    for touch in result["recommended_sequence"]:
        assert "day" in touch
        assert "channel" in touch
        assert "touch" in touch
        assert "note" in touch


def test_sequence_channels_are_valid():
    valid = {"email", "voice", "linkedin"}
    result = route_prospect(has_email=True, has_phone=True, has_linkedin=True)
    for touch in result["recommended_sequence"]:
        assert touch["channel"] in valid
