"""tests/test_compliance_handler.py — Unit tests for compliance_handler.py.

Tests AU Spam Act 2003 compliance logic without any external dependencies.
All Supabase writes are patched out so tests are fully offline.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Patch _write_supabase before importing the module under test
with patch("subprocess.run"):
    from src.pipeline import compliance_handler as ch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_suppression() -> None:
    """Reset the in-memory suppression store between tests."""
    ch._SUPPRESSION.clear()


# ---------------------------------------------------------------------------
# process_unsubscribe
# ---------------------------------------------------------------------------

class TestProcessUnsubscribe:
    def setup_method(self) -> None:
        _clear_suppression()

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_returns_suppressed_status(self, mock_write) -> None:
        result = ch.process_unsubscribe("test@example.com")
        assert result["status"] == "suppressed"

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_email_in_result(self, mock_write) -> None:
        result = ch.process_unsubscribe("test@example.com")
        assert result["email"] == "test@example.com"

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_suppressed_at_present(self, mock_write) -> None:
        result = ch.process_unsubscribe("test@example.com")
        assert "suppressed_at" in result
        assert result["suppressed_at"]  # non-empty string

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_channel_is_all(self, mock_write) -> None:
        result = ch.process_unsubscribe("test@example.com")
        assert result["channel"] == "all"

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_act_reference_present(self, mock_write) -> None:
        result = ch.process_unsubscribe("test@example.com")
        assert "AU Spam Act 2003" in result["act_reference"]

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_optional_reason_accepted(self, mock_write) -> None:
        result = ch.process_unsubscribe("test@example.com", reason="User replied STOP")
        assert result["status"] == "suppressed"


# ---------------------------------------------------------------------------
# is_suppressed
# ---------------------------------------------------------------------------

class TestIsSuppressed:
    def setup_method(self) -> None:
        _clear_suppression()

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_true_after_unsubscribe(self, mock_write) -> None:
        ch.process_unsubscribe("suppressed@example.com")
        assert ch.is_suppressed("suppressed@example.com") is True

    def test_false_for_unknown_email(self) -> None:
        assert ch.is_suppressed("unknown@example.com") is False

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_global_suppression_blocks_all_channels(self, mock_write) -> None:
        ch.process_unsubscribe("global@example.com")
        assert ch.is_suppressed("global@example.com", channel="email") is True
        assert ch.is_suppressed("global@example.com", channel="sms") is True
        assert ch.is_suppressed("global@example.com", channel="voice") is True

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_per_channel_suppression(self, mock_write) -> None:
        ch.process_opt_out("partial@example.com", channel="sms")
        assert ch.is_suppressed("partial@example.com", channel="sms") is True
        assert ch.is_suppressed("partial@example.com", channel="email") is False


# ---------------------------------------------------------------------------
# process_bounce
# ---------------------------------------------------------------------------

class TestProcessBounce:
    def setup_method(self) -> None:
        _clear_suppression()

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_hard_bounce_permanently_suppressed(self, mock_write) -> None:
        result = ch.process_bounce("hard@example.com", "hard_bounce")
        assert result["status"] == "permanently_suppressed"
        assert result["permanent"] is True

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_hard_bounce_is_suppressed(self, mock_write) -> None:
        ch.process_bounce("hard2@example.com", "hard_bounce")
        assert ch.is_suppressed("hard2@example.com") is True

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_soft_bounce_not_suppressed(self, mock_write) -> None:
        result = ch.process_bounce("soft@example.com", "soft_bounce")
        assert result["status"] == "soft_bounce_logged"
        assert result["permanent"] is False

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_soft_bounce_email_not_in_suppression_list(self, mock_write) -> None:
        ch.process_bounce("soft2@example.com", "mailbox_full")
        assert ch.is_suppressed("soft2@example.com") is False

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_unknown_bounce_type_treated_as_hard(self, mock_write) -> None:
        result = ch.process_bounce("unknown@example.com", "550_user_unknown")
        assert result["permanent"] is True


# ---------------------------------------------------------------------------
# generate_compliance_report
# ---------------------------------------------------------------------------

class TestGenerateComplianceReport:
    def setup_method(self) -> None:
        _clear_suppression()

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_report_has_required_keys(self, mock_write) -> None:
        report = ch.generate_compliance_report("2026-01-01", "2026-12-31")
        assert "report_period" in report
        assert "total_suppressions" in report
        assert "by_reason" in report
        assert "by_channel" in report
        assert "processing_time_compliance" in report
        assert "re_contact_violations" in report

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_report_counts_suppressions_in_range(self, mock_write) -> None:
        ch.process_unsubscribe("a@example.com")
        ch.process_unsubscribe("b@example.com")
        report = ch.generate_compliance_report("2026-01-01", "2026-12-31")
        assert report["total_suppressions"] == 2

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_report_zero_outside_range(self, mock_write) -> None:
        ch.process_unsubscribe("c@example.com")
        report = ch.generate_compliance_report("2020-01-01", "2020-12-31")
        assert report["total_suppressions"] == 0

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_by_reason_breakdown(self, mock_write) -> None:
        ch.process_unsubscribe("d@example.com")
        ch.process_bounce("e@example.com", "hard_bounce")
        report = ch.generate_compliance_report("2026-01-01", "2026-12-31")
        assert report["by_reason"].get("unsubscribe", 0) >= 1
        assert report["by_reason"].get("hard_bounce", 0) >= 1

    @patch("src.pipeline.compliance_handler._write_supabase")
    def test_act_reference_in_report(self, mock_write) -> None:
        report = ch.generate_compliance_report("2026-01-01", "2026-12-31")
        assert "AU Spam Act 2003" in report["act_reference"]
