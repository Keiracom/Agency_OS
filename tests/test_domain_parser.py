"""Tests for domain_parser utility — Directive #260"""
import pytest
from src.utils.domain_parser import extract_business_name


@pytest.mark.parametrize("domain,expected", [
    ("acme-marketing.com.au", "Acme Marketing"),
    ("www.best-plumbers.net.au", "Best Plumbers"),
    ("digitalgrowth.co", "Digitalgrowth"),
    ("the-local-seo-agency.com", "The Local Seo Agency"),
    ("www.smithandco.com.au", "Smithandco"),
    ("app.acme-digital.com.au", "Acme Digital"),
    ("", ""),
    ("simpledomain.com", "Simpledomain"),
    ("multi.sub.domain.com.au", "Domain"),
])
def test_extract_business_name(domain, expected):
    assert extract_business_name(domain) == expected
