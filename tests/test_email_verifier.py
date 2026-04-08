"""
Tests for src/enrichment/email_verifier.py — #301
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import asyncio
import smtplib
import socket
from unittest.mock import MagicMock, patch, call

import pytest

from enrichment.email_verifier import (
    generate_patterns,
    discover_email,
    verify_emails,
    discover_and_verify_batch,
    _smtp_probe,
)


# ---------------------------------------------------------------------------
# test_generate_patterns — 13 variants, correct format
# ---------------------------------------------------------------------------

def test_generate_patterns():
    patterns = generate_patterns("Raj", "Patel", "brightsmile.com.au")
    assert len(patterns) == 13, f"Expected 13, got {len(patterns)}: {patterns}"

    expected_locals = [
        "raj",
        "patel",
        "raj.patel",
        "patel.raj",
        "rajpatel",
        "patelraj",
        "r.patel",
        "rpatel",
        "raj.p",
        "raj_patel",
        "r_patel",
        "raj-patel",
        "r-patel",
    ]
    for local in expected_locals:
        addr = f"{local}@brightsmile.com.au"
        assert addr in patterns, f"Missing pattern: {addr}"


def test_generate_patterns_cleans_special_chars():
    patterns = generate_patterns("O'Brien", "McDonald", "example.com.au")
    assert len(patterns) == 13
    # Should strip apostrophes and hyphens
    assert "obrien@example.com.au" in patterns
    assert "mcdonald@example.com.au" in patterns


def test_generate_patterns_empty_name():
    patterns = generate_patterns("", "Patel", "example.com.au")
    assert patterns == []

    patterns = generate_patterns("Raj", "", "example.com.au")
    assert patterns == []


# ---------------------------------------------------------------------------
# test_accept_all_detection
# ---------------------------------------------------------------------------

def test_accept_all_detection():
    """If fake address returns 250, accept_all=True and no real probing."""
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp.rcpt.return_value = (250, b"OK")  # fake addr returns 250 = accept-all

    with patch("smtplib.SMTP", return_value=mock_smtp):
        result = _smtp_probe(
            mx_host="mail.example.com",
            domain="example.com",
            candidates=["raj@example.com", "raj.patel@example.com"],
            fake_addr="xq7z9fake@example.com",
        )

    assert result["accept_all"] is True
    assert result["verified"] == []
    assert result["invalid"] == []
    # Should quit immediately after accept-all detection
    mock_smtp.quit.assert_called_once()
    # rcpt should only be called once (for the fake addr)
    assert mock_smtp.rcpt.call_count == 1


# ---------------------------------------------------------------------------
# test_valid_email_found
# ---------------------------------------------------------------------------

def test_valid_email_found():
    """250 on real addr, 550 on others → only real addr verified."""
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    def rcpt_side_effect(addr):
        if addr == "xq7z9fake@brightsmile.com.au":
            return (550, b"No such user")  # not accept-all
        if addr == "r.patel@brightsmile.com.au":
            return (250, b"OK")
        return (550, b"No such user")

    mock_smtp.rcpt.side_effect = rcpt_side_effect

    with patch("smtplib.SMTP", return_value=mock_smtp):
        result = _smtp_probe(
            mx_host="mail.brightsmile.com.au",
            domain="brightsmile.com.au",
            candidates=[
                "raj@brightsmile.com.au",
                "r.patel@brightsmile.com.au",
                "rajpatel@brightsmile.com.au",
            ],
            fake_addr="xq7z9fake@brightsmile.com.au",
        )

    assert result["accept_all"] is False
    assert "r.patel@brightsmile.com.au" in result["verified"]
    assert "raj@brightsmile.com.au" in result["invalid"]
    assert result["error"] is None


# ---------------------------------------------------------------------------
# test_no_mx_record_handled
# ---------------------------------------------------------------------------

def test_no_mx_record_handled():
    """If MX lookup fails, return graceful error without crashing."""
    with patch("enrichment.email_verifier.resolve_mx", return_value=None):
        result = discover_email("Raj", "Patel", "no-mx-domain.com.au")

    assert result["mx_host"] is None
    assert result["error"] == "no_mx_record"
    assert result["verified_emails"] == []
    assert result["accept_all"] is False
    assert result["patterns_tested"] == 13


# ---------------------------------------------------------------------------
# test_timeout_handled
# ---------------------------------------------------------------------------

def test_timeout_handled():
    """Socket timeout should be caught and returned as error, not raise."""
    with patch("enrichment.email_verifier.resolve_mx", return_value="mail.example.com"):
        with patch("smtplib.SMTP") as mock_smtp_class:
            instance = MagicMock()
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            instance.connect.side_effect = socket.timeout("timed out")
            mock_smtp_class.return_value = instance

            result = discover_email("Raj", "Patel", "example.com.au")

    assert result["error"] == "timeout"
    assert result["verified_emails"] == []
    assert "time_seconds" in result


# ---------------------------------------------------------------------------
# test_verify_emails_groups_by_domain
# ---------------------------------------------------------------------------

def test_verify_emails_groups_by_domain():
    """verify_emails groups by domain and returns correct verified flags."""
    emails = [
        "r.patel@brightsmile.com.au",
        "info@brightsmile.com.au",
        "contact@other-domain.com.au",
    ]

    def mock_probe(mx_host, domain, candidates, fake_addr):
        if domain == "brightsmile.com.au":
            return {
                "verified": ["r.patel@brightsmile.com.au"],
                "invalid": ["info@brightsmile.com.au"],
                "accept_all": False,
                "error": None,
            }
        return {
            "verified": ["contact@other-domain.com.au"],
            "invalid": [],
            "accept_all": False,
            "error": None,
        }

    with patch("enrichment.email_verifier.resolve_mx", return_value="mail.example.com"):
        with patch("enrichment.email_verifier._smtp_probe", side_effect=mock_probe):
            results = verify_emails(emails)

    result_map = {r["email"]: r for r in results}
    assert result_map["r.patel@brightsmile.com.au"]["verified"] is True
    assert result_map["info@brightsmile.com.au"]["verified"] is False
    assert result_map["contact@other-domain.com.au"]["verified"] is True


# ---------------------------------------------------------------------------
# test_batch_async
# ---------------------------------------------------------------------------

def test_discover_and_verify_batch():
    """Batch runs all prospects and attaches smtp_result."""
    prospects = [
        {"first_name": "Raj", "last_name": "Patel", "domain": "brightsmile.com.au"},
        {"first_name": "Jane", "last_name": "Smith", "domain": "example.com.au"},
    ]

    fake_smtp_result = {
        "domain": "x",
        "mx_host": "mail.x",
        "accept_all": False,
        "verified_emails": [],
        "invalid_emails": [],
        "patterns_tested": 13,
        "time_seconds": 0.5,
        "error": None,
    }

    with patch("enrichment.email_verifier.discover_email", return_value=fake_smtp_result):
        results = asyncio.run(discover_and_verify_batch(prospects))

    assert len(results) == 2
    for r in results:
        assert "smtp_result" in r
        assert r["smtp_result"] == fake_smtp_result
