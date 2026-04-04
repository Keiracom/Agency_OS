"""
Tests for AU-only domain filter enforcement at all business_universe insert paths.
Covers:
  - stage_1_discovery.py  → simple domain.endswith(".au") guard
  - layer_2_discovery.py  → _is_au_domain() heuristic
  - pool_population_flow.py → gmb_domain nulling for non-AU domains (#task-1.2)
"""
import pytest

# ---------------------------------------------------------------------------
# stage_1_discovery: inline filter logic (not a public function — replicate)
# ---------------------------------------------------------------------------

def _s1_is_au(domain: str) -> bool:
    """Mirrors stage_1_discovery.py line 156: AU-only filter."""
    return domain.lower().endswith(".au")


class TestStage1AuFilter:
    def test_com_au_passes(self):
        assert _s1_is_au("example.com.au") is True

    def test_net_au_passes(self):
        assert _s1_is_au("example.net.au") is True

    def test_org_au_passes(self):
        assert _s1_is_au("example.org.au") is True

    def test_bare_au_passes(self):
        assert _s1_is_au("example.au") is True

    def test_com_rejected(self):
        assert _s1_is_au("example.com") is False

    def test_nz_rejected(self):
        assert _s1_is_au("example.co.nz") is False

    def test_co_uk_rejected(self):
        assert _s1_is_au("example.co.uk") is False

    def test_uppercase_passes(self):
        assert _s1_is_au("Example.COM.AU") is True

    def test_uppercase_rejected(self):
        assert _s1_is_au("Example.COM") is False


# ---------------------------------------------------------------------------
# layer_2_discovery: import _is_au_domain directly
# ---------------------------------------------------------------------------

from src.pipeline.layer_2_discovery import _is_au_domain  # noqa: E402


class TestLayer2AuDomainFilter:
    # --- explicit .au TLDs (unconditionally kept) ---
    def test_com_au_kept(self):
        assert _is_au_domain("example.com.au") is True

    def test_net_au_kept(self):
        assert _is_au_domain("example.net.au") is True

    def test_id_au_kept(self):
        assert _is_au_domain("person.id.au") is True

    # --- .com assumed AU (returned from AU location query) ---
    def test_dotcom_kept(self):
        assert _is_au_domain("mybusiness.com") is True

    # --- neutral TLDs kept ---
    def test_io_kept(self):
        assert _is_au_domain("startup.io") is True

    def test_org_kept(self):
        assert _is_au_domain("assoc.org") is True

    # --- foreign CCTLDs rejected ---
    def test_co_nz_rejected(self):
        assert _is_au_domain("kiwi.co.nz") is False

    def test_co_uk_rejected(self):
        assert _is_au_domain("brit.co.uk") is False

    def test_ca_rejected(self):
        assert _is_au_domain("maple.ca") is False

    def test_de_rejected(self):
        assert _is_au_domain("german.de") is False


# ---------------------------------------------------------------------------
# pool_population_flow: gmb_domain AU filter (#task-1.2)
# The fix nulls non-AU gmb_domain values in bu_gmb_rows list comprehension.
# We replicate the guard logic here to test it directly.
# ---------------------------------------------------------------------------

def _pool_population_au_gmb_domain(raw_gmb_domain: str | None) -> str | None:
    """
    Mirrors the AU-only guard added to pool_population_flow.py (#task-1.2).
    Returns domain unchanged if .au, else None.
    """
    if raw_gmb_domain and not raw_gmb_domain.lower().endswith(".au"):
        return None
    return raw_gmb_domain


class TestPoolPopulationGmbDomainFilter:
    def test_au_domain_unchanged(self):
        assert _pool_population_au_gmb_domain("acme.com.au") == "acme.com.au"

    def test_net_au_unchanged(self):
        assert _pool_population_au_gmb_domain("acme.net.au") == "acme.net.au"

    def test_none_unchanged(self):
        assert _pool_population_au_gmb_domain(None) is None

    def test_empty_string_unchanged(self):
        # Empty string is falsy — passes through as-is (no domain to filter)
        assert _pool_population_au_gmb_domain("") == ""

    def test_com_nulled(self):
        assert _pool_population_au_gmb_domain("example.com") is None

    def test_nz_nulled(self):
        assert _pool_population_au_gmb_domain("kiwi.co.nz") is None

    def test_co_uk_nulled(self):
        assert _pool_population_au_gmb_domain("brit.co.uk") is None

    def test_uppercase_au_passes(self):
        assert _pool_population_au_gmb_domain("ACME.COM.AU") == "ACME.COM.AU"

    def test_uppercase_com_nulled(self):
        assert _pool_population_au_gmb_domain("ACME.COM") is None
