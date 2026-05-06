"""
Tests for card quality fixes — Directive #305:
- Business name waterfall (resolve_business_name)
- Location waterfall (resolve_location)
- Placeholder filter (is_placeholder_email, is_placeholder_phone)
"""

from __future__ import annotations

import pytest

from src.pipeline.pipeline_orchestrator import resolve_business_name, resolve_location
from src.pipeline.email_waterfall import is_placeholder_email, is_placeholder_phone


# ── resolve_business_name ─────────────────────────────────────────────────────


def test_abn_trading_name_priority():
    """ABN trading name wins over domain stem."""
    enrichment = {
        "abn_trading_name": "Dental1 Clinic Pty Ltd",
        "abn_legal_name": "",
        "company_name": "dental1",
    }
    result = resolve_business_name("dental1.com.au", enrichment)
    assert result == "Dental1 Clinic Pty Ltd"


def test_pty_ltd_alone_falls_through():
    """ABN trading name = only entity suffix → falls through to GMB name."""
    enrichment = {
        "abn_trading_name": "Pty Ltd",
        "abn_legal_name": "",
        "company_name": "dental1",
    }
    gmb_data = {"gmb_name": "Bright Smile Dental"}
    result = resolve_business_name("dental1.com.au", enrichment, gmb_data)
    assert result == "Bright Smile Dental"


def test_domain_stem_fallback():
    """All candidates blank → domain stem."""
    enrichment = {
        "abn_trading_name": "",
        "abn_legal_name": "",
        "company_name": "",
    }
    result = resolve_business_name("bright-smile-dental.com.au", enrichment)
    assert result == "Bright Smile Dental"


def test_abn_legal_name_used_when_trading_empty():
    """Falls through trading → GMB (None) → legal name."""
    enrichment = {
        "abn_trading_name": "",
        "abn_legal_name": "Bright Smile Dental Pty Ltd",
        "company_name": "fallback",
    }
    result = resolve_business_name("example.com.au", enrichment)
    assert result == "Bright Smile Dental Pty Ltd"


# ── resolve_location ──────────────────────────────────────────────────────────


def test_gmb_address_suburb_state():
    """GMB address parsed to suburb + state."""
    gmb_data = {"gmb_address": "42 Main St, Parramatta NSW 2150"}
    suburb, state, display = resolve_location("example.com.au", {}, gmb_data)
    assert suburb == "Parramatta"
    assert state == "NSW"
    assert display == "Parramatta, NSW"


def test_abn_postcode_resolves_to_state():
    """Postcode 2000 → NSW when no suburb / GMB available."""
    enrichment = {"website_address": {"postcode": "2000"}}
    suburb, state, display = resolve_location("example.com.au", enrichment)
    assert suburb == ""
    assert state == "NSW"
    assert display == "NSW"


def test_australia_only_when_all_fail():
    """No enrichment, no GMB → default 'Australia'."""
    suburb, state, display = resolve_location("example.com.au", {})
    assert suburb == ""
    assert state == ""
    assert display == "Australia"


# ── is_placeholder_email ──────────────────────────────────────────────────────


def test_placeholder_email_exact_match():
    assert is_placeholder_email("example@mail.com") is True


def test_placeholder_email_pattern():
    assert is_placeholder_email("yourname@company.com") is True


def test_real_email_passes():
    assert is_placeholder_email("john.smith@dentist.com.au") is False


# ── is_placeholder_phone ─────────────────────────────────────────────────────


def test_placeholder_phone_all_same_digit():
    assert is_placeholder_phone("0000000000") is True


def test_placeholder_phone_sequential():
    assert is_placeholder_phone("0412345678") is True


def test_real_phone_passes():
    assert is_placeholder_phone("0412 987 654") is False
    assert is_placeholder_phone("+61 2 9123 4567") is False
