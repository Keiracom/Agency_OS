"""
Tests for email_scoring_gate — CB Insights anti-pattern detection.
Directive #339
"""

import pytest

from src.pipeline.email_scoring_gate import score_email, PASS_THRESHOLD


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GOOD_SUBJECT = "Noticed you're running Google Ads without conversion tracking"
GOOD_BODY = (
    "Hi Sarah, your Google Ads account at Acme Plumbing caught my eye — "
    "you're spending on broad match keywords but the site has no conversion pixel. "
    "That usually means paying for clicks that never become jobs. "
    "Would it be useful to do a 15-minute audit together this week?"
)


def _flag_patterns(result: dict) -> list[str]:
    return [f["pattern"] for f in result["flags"]]


# ---------------------------------------------------------------------------
# Perfect email
# ---------------------------------------------------------------------------

class TestPerfectEmail:
    def test_perfect_email_scores_100(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_name="Sarah",
            recipient_company="Acme Plumbing",
            sequence_position=1,
            total_sequence_length=5,
        )
        assert result["score"] == 100
        assert result["pass"] is True
        assert result["flags"] == []
        assert result["recommendations"] == []


# ---------------------------------------------------------------------------
# Subject line checks
# ---------------------------------------------------------------------------

class TestSubjectChecks:
    def test_empty_subject_deducts_30(self):
        # Pass recipient_company so zero_buyer_knowledge doesn't fire — isolating subject check
        result = score_email(subject="", body=GOOD_BODY, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "weak_subject" in _flag_patterns(result)
        assert result["score"] == 70  # 100 - 30

    def test_short_subject_deducts_30(self):
        result = score_email(subject="Hi", body=GOOD_BODY, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "weak_subject" in _flag_patterns(result)
        assert result["score"] == 70

    def test_all_caps_subject_deducts_15(self):
        result = score_email(subject="BIG OPPORTUNITY FOR YOU", body=GOOD_BODY, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "spammy_subject" in _flag_patterns(result)
        assert result["score"] == 85

    def test_excessive_punctuation_deducts_15(self):
        # Three exclamation marks — over the limit
        result = score_email(subject="Hot deal available now!!!", body=GOOD_BODY, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "spammy_subject" in _flag_patterns(result)
        assert result["score"] == 85

    def test_two_punctuation_is_ok(self):
        result = score_email(subject="Quick win for you!?", body=GOOD_BODY, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "spammy_subject" not in _flag_patterns(result)

    def test_fake_re_threading_deducts_20(self):
        result = score_email(subject="Re: our conversation", body=GOOD_BODY, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "fake_threading" in _flag_patterns(result)
        assert result["score"] == 80

    def test_fake_fw_threading_deducts_20(self):
        result = score_email(subject="Fw: something important", body=GOOD_BODY, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "fake_threading" in _flag_patterns(result)

    def test_generic_subject_deducts_10(self):
        result = score_email(subject="Following up", body=GOOD_BODY, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "generic_subject" in _flag_patterns(result)
        assert result["score"] == 90

    def test_generic_subject_case_insensitive(self):
        result = score_email(subject="QUICK QUESTION", body=GOOD_BODY, recipient_company="Acme Plumbing", total_sequence_length=5)
        # all-caps triggers spammy_subject (-15); generic match on "quick question" also (-10)
        assert "generic_subject" in _flag_patterns(result)
        assert "spammy_subject" in _flag_patterns(result)


# ---------------------------------------------------------------------------
# Body checks
# ---------------------------------------------------------------------------

class TestBodyChecks:
    def test_curly_template_token_deducts_25(self):
        body = "Hi {first_name}, I wanted to reach out about " + GOOD_BODY[20:]
        result = score_email(subject=GOOD_SUBJECT, body=body, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "mail_merge_failure" in _flag_patterns(result)
        assert result["score"] <= 75  # 100 - 25

    def test_double_curly_token(self):
        body = "Hey {{name}}, " + GOOD_BODY[10:]
        result = score_email(subject=GOOD_SUBJECT, body=body, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "mail_merge_failure" in _flag_patterns(result)

    def test_angle_bracket_token(self):
        body = "Dear <FIRST_NAME>, " + GOOD_BODY[10:]
        result = score_email(subject=GOOD_SUBJECT, body=body, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "mail_merge_failure" in _flag_patterns(result)

    def test_square_bracket_token(self):
        body = "Hi [COMPANY_NAME] team, " + GOOD_BODY[10:]
        result = score_email(subject=GOOD_SUBJECT, body=body, recipient_company="Acme Plumbing", total_sequence_length=5)
        assert "mail_merge_failure" in _flag_patterns(result)

    def test_no_company_mention_deducts_15(self):
        generic_body = "Your business caught my eye and I think we can help. Would you be open to a chat?"
        result = score_email(
            subject=GOOD_SUBJECT,
            body=generic_body,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "zero_buyer_knowledge" in _flag_patterns(result)

    def test_company_mention_clears_buyer_knowledge_flag(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "zero_buyer_knowledge" not in _flag_patterns(result)

    def test_long_body_deducts_10(self):
        long_body = (GOOD_BODY + " Also, ") * 20  # well over 300 words
        result = score_email(
            subject=GOOD_SUBJECT,
            body=long_body,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "too_long" in _flag_patterns(result)

    def test_body_under_300_words_ok(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "too_long" not in _flag_patterns(result)

    def test_no_cta_deducts_10(self):
        no_cta = "Hi Sarah, your Acme Plumbing ads need work. I can help. Let me know."
        result = score_email(
            subject=GOOD_SUBJECT,
            body=no_cta,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "no_call_to_action" in _flag_patterns(result)

    def test_question_in_last_sentence_clears_cta_flag(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "no_call_to_action" not in _flag_patterns(result)

    def test_unsubscribe_without_link_deducts_5(self):
        body = GOOD_BODY + " Reply 'unsubscribe' to opt out."
        result = score_email(
            subject=GOOD_SUBJECT,
            body=body,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "missing_unsubscribe_link" in _flag_patterns(result)

    def test_unsubscribe_with_link_is_ok(self):
        body = GOOD_BODY + " Unsubscribe: https://example.com/unsub"
        result = score_email(
            subject=GOOD_SUBJECT,
            body=body,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "missing_unsubscribe_link" not in _flag_patterns(result)


# ---------------------------------------------------------------------------
# Pronoun balance checks
# ---------------------------------------------------------------------------

class TestPronounBalance:
    def test_self_focused_email_deducts_15(self):
        self_focused = (
            "I am reaching out because I think we can help. My company has worked "
            "with lots of businesses like yours. I want to share our approach. "
            "Would you be open to a call about Acme Plumbing?"
        )
        result = score_email(
            subject=GOOD_SUBJECT,
            body=self_focused,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "self_focused" in _flag_patterns(result)

    def test_buyer_centric_email_ok(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "self_focused" not in _flag_patterns(result)

    def test_three_first_person_before_you_is_ok(self):
        # Exactly 3 first-person before ANY second-person — should NOT trigger.
        # Note: "your" also counts as second-person, so avoid it before the threshold.
        body = (
            "I run a digital agency. I work with plumbing businesses. I specialise in ads. "
            "Would you be open to a quick audit of Acme Plumbing?"
        )
        result = score_email(
            subject=GOOD_SUBJECT,
            body=body,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "self_focused" not in _flag_patterns(result)

    def test_four_first_person_before_you_triggers(self):
        # Four first-person pronouns before first second-person usage — triggers self_focused
        body = (
            "I run a digital agency. I work with plumbers. I built a tool for this. I find gaps. "
            "Would you be open to a quick audit of Acme Plumbing?"
        )
        result = score_email(
            subject=GOOD_SUBJECT,
            body=body,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "self_focused" in _flag_patterns(result)


# ---------------------------------------------------------------------------
# Sequence checks
# ---------------------------------------------------------------------------

class TestSequenceChecks:
    def test_single_touch_deducts_10(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_company="Acme Plumbing",
            sequence_position=1,
            total_sequence_length=1,
        )
        assert "insufficient_follow_up" in _flag_patterns(result)
        assert result["score"] == 90

    def test_multi_touch_sequence_ok(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_company="Acme Plumbing",
            sequence_position=2,
            total_sequence_length=5,
        )
        assert "insufficient_follow_up" not in _flag_patterns(result)

    def test_position_beyond_5_deducts_5(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_company="Acme Plumbing",
            sequence_position=6,
            total_sequence_length=8,
        )
        assert "spam_fatigue_risk" in _flag_patterns(result)
        assert result["score"] == 95

    def test_position_5_is_ok(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_company="Acme Plumbing",
            sequence_position=5,
            total_sequence_length=8,
        )
        assert "spam_fatigue_risk" not in _flag_patterns(result)


# ---------------------------------------------------------------------------
# Personalisation checks
# ---------------------------------------------------------------------------

class TestPersonalisationChecks:
    def test_name_available_but_unused_deducts_10(self):
        body = "Your business caught my eye at Acme Plumbing. Would you like a quick audit?"
        result = score_email(
            subject=GOOD_SUBJECT,
            body=body,
            recipient_name="Sarah",
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "name_unused" in _flag_patterns(result)

    def test_name_used_in_body_ok(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_name="Sarah",
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "name_unused" not in _flag_patterns(result)

    def test_no_recipient_name_no_flag(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_name=None,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert "name_unused" not in _flag_patterns(result)

    def test_company_unused_deducts_10_when_not_already_flagged(self):
        # No company in body, company provided — should flag zero_buyer_knowledge (not company_unused)
        body = "Your business caught my eye. Would you like a quick audit call?"
        result = score_email(
            subject=GOOD_SUBJECT,
            body=body,
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        # zero_buyer_knowledge triggers first, company_unused should NOT double-penalise
        assert "zero_buyer_knowledge" in _flag_patterns(result)
        assert "company_unused" not in _flag_patterns(result)


# ---------------------------------------------------------------------------
# Multi-flag accumulation
# ---------------------------------------------------------------------------

class TestMultipleFlags:
    def test_multiple_flags_accumulate(self):
        """Mail merge failure + weak subject + single touch = -30 -25 -10 = 35."""
        result = score_email(
            subject="Hi",
            body="Dear {name}, we want to help. Let me know.",
            total_sequence_length=1,
        )
        patterns = _flag_patterns(result)
        assert "weak_subject" in patterns
        assert "mail_merge_failure" in patterns
        assert "insufficient_follow_up" in patterns
        # Score: 100 - 30 - 25 - 10 = 35, also no CTA (-10), no buyer knowledge (-15) = 10
        assert result["score"] < PASS_THRESHOLD
        assert result["pass"] is False

    def test_score_floor_is_zero(self):
        """Score never goes negative."""
        result = score_email(
            subject="",
            body="I I I I {name} {{company}} <FIRST_NAME> [COMPANY_NAME].",
            total_sequence_length=1,
            sequence_position=7,
        )
        assert result["score"] >= 0


# ---------------------------------------------------------------------------
# Pass / fail threshold
# ---------------------------------------------------------------------------

class TestPassFailThreshold:
    def test_score_70_passes(self):
        # Single touch only (-10) + generic subject (-10) + no CTA (-10) = 70
        body = "Your business at Acme Plumbing caught my eye. I can help with your ads. Let me know."
        result = score_email(
            subject="Following up",
            body=body,
            recipient_company="Acme Plumbing",
            total_sequence_length=1,
        )
        # Flags: generic_subject(-10), insufficient_follow_up(-10), no_cta(-10)
        # Score should be 70 → pass
        assert result["score"] == 70
        assert result["pass"] is True

    def test_score_69_fails(self):
        # Ensure that a score below 70 is correctly marked as fail
        result = score_email(
            subject="Following up",
            body="Your Acme Plumbing business caught my eye. I can help with your ads. Let me know.",
            recipient_name="Sarah",
            recipient_company="Acme Plumbing",
            total_sequence_length=1,
        )
        # generic_subject(-10), insufficient_follow_up(-10), no_cta(-10), name_unused(-10) = 60
        assert result["score"] == 60
        assert result["pass"] is False

    def test_pass_threshold_constant_is_70(self):
        assert PASS_THRESHOLD == 70

    def test_recommendations_present_on_fail(self):
        result = score_email(subject="", body="Test.", total_sequence_length=1)
        assert len(result["recommendations"]) > 0

    def test_recommendations_empty_on_perfect(self):
        result = score_email(
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            recipient_name="Sarah",
            recipient_company="Acme Plumbing",
            total_sequence_length=5,
        )
        assert result["recommendations"] == []
