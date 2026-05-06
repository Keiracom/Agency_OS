"""Tests for FreeEnrichment — Directive #285 additions (ABN confidence, JSON-LD, email maturity)."""

from __future__ import annotations

from src.pipeline.free_enrichment import ABNMatchConfidence, EmailMaturity, FreeEnrichment


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_fe() -> FreeEnrichment:
    """Instantiate FreeEnrichment without a real DB connection."""
    fe = FreeEnrichment.__new__(FreeEnrichment)
    fe._pool = None
    fe._conn = None
    return fe


# ─── Task B: ABN confidence ────────────────────────────────────────────────────


def test_abn_confidence_exact():
    """Names that are highly similar score EXACT or PARTIAL — not LOW."""
    fe = make_fe()
    conf = fe._abn_confidence("bespoke dental", "BESPOKE DENTAL PTY LTD")
    assert conf != ABNMatchConfidence.LOW


def test_abn_confidence_exact_identical():
    """Identical names produce EXACT confidence."""
    fe = make_fe()
    conf = fe._abn_confidence("acme services", "acme services")
    assert conf == ABNMatchConfidence.EXACT


def test_abn_confidence_partial():
    """Moderately similar names produce PARTIAL confidence."""
    fe = make_fe()
    # "smith plumbing" vs "smith plumbing pty ltd" — ratio ~0.72
    conf = fe._abn_confidence("smith plumbing", "SMITH PLUMBING PTY LTD")
    assert conf in (ABNMatchConfidence.PARTIAL, ABNMatchConfidence.EXACT)


def test_abn_confidence_low():
    """Dissimilar names produce LOW confidence."""
    fe = make_fe()
    conf = fe._abn_confidence("beyondental", "TOTALLY DIFFERENT PTY LTD")
    assert conf == ABNMatchConfidence.LOW


# ─── Task C: JSON-LD address extraction ───────────────────────────────────────


def test_extract_jsonld_address_local_business():
    """Extracts address fields from a LocalBusiness JSON-LD block."""
    html = """
    <html><body>
    <script type="application/ld+json">
    {"@type": "LocalBusiness", "name": "Test Dental",
     "address": {"@type": "PostalAddress", "streetAddress": "123 Main St",
                 "addressLocality": "Sydney", "addressRegion": "NSW", "postalCode": "2000"}}
    </script>
    </body></html>
    """
    fe = make_fe()
    result = fe._extract_jsonld_address(html)
    assert result is not None
    assert result["suburb"] == "Sydney"
    assert result["state"] == "NSW"
    assert result["postcode"] == "2000"
    assert result["street"] == "123 Main St"


def test_extract_jsonld_address_no_jsonld():
    """Returns None when no JSON-LD blocks are present."""
    html = "<p>Visit us at Central Park Sydney NSW 2000</p>"
    fe = make_fe()
    result = fe._extract_jsonld_address(html)
    assert result is None


def test_extract_jsonld_address_malformed_json():
    """Gracefully handles malformed JSON-LD blocks — returns None."""
    html = """
    <script type="application/ld+json">
    { not valid json
    </script>
    """
    fe = make_fe()
    result = fe._extract_jsonld_address(html)
    assert result is None


def test_extract_jsonld_address_no_address_key():
    """Returns None when JSON-LD has no address field."""
    html = """
    <script type="application/ld+json">
    {"@type": "Organization", "name": "Example Corp"}
    </script>
    """
    fe = make_fe()
    result = fe._extract_jsonld_address(html)
    assert result is None


def test_extract_jsonld_address_graph_wrapper():
    """Handles @graph wrapper in JSON-LD."""
    html = """
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@graph": [
      {"@type": "Dentist", "name": "Smile Clinic",
       "address": {"@type": "PostalAddress", "addressLocality": "Melbourne",
                   "addressRegion": "VIC", "postalCode": "3000"}}
    ]}
    </script>
    """
    fe = make_fe()
    result = fe._extract_jsonld_address(html)
    assert result is not None
    assert result["suburb"] == "Melbourne"
    assert result["state"] == "VIC"


# ─── Task D: Email maturity ────────────────────────────────────────────────────


def test_email_maturity_professional():
    """MX provider with SPF → PROFESSIONAL."""
    fe = make_fe()
    mat = fe._compute_email_maturity("microsoft365", has_spf=True)
    assert mat == EmailMaturity.PROFESSIONAL


def test_email_maturity_professional_google_with_spf():
    """Google MX with SPF → PROFESSIONAL."""
    fe = make_fe()
    mat = fe._compute_email_maturity("google", has_spf=True)
    assert mat == EmailMaturity.PROFESSIONAL


def test_email_maturity_webmail():
    """Google MX without SPF → WEBMAIL."""
    fe = make_fe()
    mat = fe._compute_email_maturity("google", has_spf=False)
    assert mat == EmailMaturity.WEBMAIL


def test_email_maturity_webmail_other_provider():
    """Other MX provider without SPF → WEBMAIL."""
    fe = make_fe()
    mat = fe._compute_email_maturity("other", has_spf=False)
    assert mat == EmailMaturity.WEBMAIL


def test_email_maturity_none():
    """No MX provider → NONE."""
    fe = make_fe()
    mat = fe._compute_email_maturity(None, has_spf=False)
    assert mat == EmailMaturity.NONE


def test_email_maturity_none_with_spf_false():
    """No MX provider even if SPF somehow present → NONE."""
    fe = make_fe()
    mat = fe._compute_email_maturity(None, has_spf=True)
    assert mat == EmailMaturity.NONE
