"""Tests for domain_blocklist utility. Directive #267"""

from src.utils.domain_blocklist import is_blocked


def test_blocks_facebook():
    assert is_blocked("facebook.com") is True


def test_blocks_subdomain_gov():
    assert is_blocked("rfs.nsw.gov.au") is True


def test_blocks_empty():
    assert is_blocked("") is True
    assert is_blocked(None) is True


def test_allows_business_domain():
    assert is_blocked("acme-dental.com.au") is False
    assert is_blocked("sydneydentist.com.au") is False


def test_blocks_google():
    assert is_blocked("google.com") is True
    assert is_blocked("google.com.au") is True


def test_blocks_instagram():
    assert is_blocked("instagram.com") is True


def test_blocks_gov_au_subdomain():
    assert is_blocked("health.nsw.gov.au") is True


def test_allows_whitespace_stripped():
    # domain with surrounding spaces should still be caught if blocked
    assert is_blocked("  facebook.com  ") is True


def test_blocks_case_insensitive():
    assert is_blocked("Facebook.COM") is True
    assert is_blocked("INSTAGRAM.COM") is True
