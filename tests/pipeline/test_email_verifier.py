"""Tests for src/pipeline/email_verifier.py — Directive #301."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.email_verifier import generate_patterns, discover_email, verify_emails


# ── test_generate_patterns ────────────────────────────────────────────────────


def test_generate_patterns_count():
    """Should return up to 13 unique variants for a full name."""
    patterns = generate_patterns("Raj", "Patel", "example.com")
    assert len(patterns) <= 13
    assert len(patterns) >= 8  # at minimum raj@, patel@, raj.patel@, etc.


def test_generate_patterns_lowercase():
    patterns = generate_patterns("RAJ", "PATEL", "Example.COM")
    for p in patterns:
        local = p.split("@")[0]
        assert local == local.lower()


def test_generate_patterns_strips_www():
    patterns = generate_patterns("Raj", "Patel", "www.example.com")
    for p in patterns:
        assert "@www." not in p


def test_generate_patterns_no_duplicates():
    patterns = generate_patterns("Jane", "Doe", "example.com")
    assert len(patterns) == len(set(patterns))


def test_generate_patterns_single_name():
    """Single-word name: should still generate first@ and last@ variants."""
    patterns = generate_patterns("Jane", "", "example.com")
    assert len(patterns) >= 1
    assert "jane@example.com" in patterns


# ── test_accept_all_detection ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_accept_all_detection():
    """If canary address returns 250, domain is accept_all and we bail early."""
    with patch("src.pipeline.email_verifier.resolve_mx", return_value="mail.example.com"):
        with patch("src.pipeline.email_verifier.probe_domain") as mock_probe:
            from src.pipeline.email_verifier import SmtpProbeResult

            mock_probe.return_value = SmtpProbeResult(
                domain="example.com",
                mx_host="mail.example.com",
                accept_all=True,
                verified_emails=[],
                invalid_emails=[],
                patterns_tested=13,
            )
            result = await discover_email("Raj", "Patel", "example.com")
    assert result["accept_all"] is True
    assert result["verified_emails"] == []


# ── test_valid_email_found ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_email_found():
    """Returns the first verified email."""
    with patch("src.pipeline.email_verifier.resolve_mx", return_value="mail.brightsmile.com.au"):
        with patch("src.pipeline.email_verifier.probe_domain") as mock_probe:
            from src.pipeline.email_verifier import SmtpProbeResult

            mock_probe.return_value = SmtpProbeResult(
                domain="brightsmile.com.au",
                mx_host="mail.brightsmile.com.au",
                accept_all=False,
                verified_emails=["r.patel@brightsmile.com.au"],
                invalid_emails=["raj@brightsmile.com.au", "raj.patel@brightsmile.com.au"],
                patterns_tested=13,
            )
            result = await discover_email("Raj", "Patel", "brightsmile.com.au")
    assert result["verified_emails"] == ["r.patel@brightsmile.com.au"]
    assert result["accept_all"] is False
    assert result["patterns_tested"] == 13


# ── test_no_mx_record_handled ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_mx_record_handled():
    """Returns error dict gracefully when no MX record found."""
    with patch("src.pipeline.email_verifier.resolve_mx", return_value=None):
        result = await discover_email("Jane", "Smith", "noemail.com.au")
    assert result["error"] == "no_mx"
    assert result["verified_emails"] == []


# ── test_timeout_handled ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_timeout_handled():
    """Timeout during SMTP probe is caught gracefully."""
    import socket

    with patch("src.pipeline.email_verifier.resolve_mx", return_value="mail.example.com"):
        with patch("src.pipeline.email_verifier.probe_domain") as mock_probe:
            from src.pipeline.email_verifier import SmtpProbeResult

            mock_probe.return_value = SmtpProbeResult(
                domain="example.com",
                mx_host="mail.example.com",
                accept_all=False,
                verified_emails=[],
                invalid_emails=[],
                patterns_tested=0,
                error="timed out",
            )
            result = await discover_email("Jane", "Smith", "timeout.com")
    assert result["error"] == "timed out"
    assert result["verified_emails"] == []
