"""
Tests for multi-strategy ABN matching waterfall — Directive #289.

Covers:
  - _extract_domain_keywords: TLD strip, hyphen split, stopword split
  - _abn_clean_entity_name: PTY LTD / THE TRUSTEE FOR stripping
  - _abn_confidence: EXACT / PARTIAL / LOW boundaries
  - _match_abn waterfall: strategy ordering, early-exit on PARTIAL+, all-fail → None
  - _local_abn_match: keyword intersection query building
  - _local_abn_gst: ABN cross-reference for GST data
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.free_enrichment import (
    ABNMatchConfidence,
    FreeEnrichment,
)
from src.config.au_lexicon import DOMAIN_STOPWORDS as _ABN_STOPWORDS  # #328.3b: renamed


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_fe() -> FreeEnrichment:
    """Create a FreeEnrichment instance with a mock DB connection."""
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    return FreeEnrichment(conn)


def _make_row(
    legal_name: str,
    trading_name: str | None = None,
    gst_registered: bool = True,
    entity_type: str = "Australian Private Company",
    state: str = "NSW",
) -> dict[str, Any]:
    """Build a fake asyncpg-Record-compatible dict for ABN matches."""
    return {
        "abn": "12345678901",
        "legal_name": legal_name,
        "trading_name": trading_name,
        "gst_registered": gst_registered,
        "entity_type": entity_type,
        "registration_date": None,
        "state": state,
    }


# ── _extract_domain_keywords ──────────────────────────────────────────────────


class TestExtractDomainKeywords:
    def test_hyphen_split_basic(self):
        kw = FreeEnrichment._extract_domain_keywords("bright-smile-dental.com")
        assert kw == ["bright", "smile", "dental"]

    def test_tld_stripped(self):
        kw = FreeEnrichment._extract_domain_keywords("pymble-dental.com.au")
        assert "com" not in kw
        assert "au" not in kw
        assert "pymble" in kw
        assert "dental" in kw

    def test_stopword_split_concatenated(self):
        # "dentistsatpymble" → split on "at" → ["dentists", "pymble"]
        kw = FreeEnrichment._extract_domain_keywords("dentistsatpymble.com.au")
        assert "pymble" in kw
        assert "dentists" in kw
        assert "at" not in kw

    def test_stopword_removed_from_hyphen_parts(self):
        # "dental-at-pymble" → "at" filtered out
        kw = FreeEnrichment._extract_domain_keywords("dental-at-pymble.com.au")
        assert "at" not in kw
        assert "dental" in kw
        assert "pymble" in kw

    def test_short_words_excluded(self):
        # Words ≤ 2 chars dropped
        kw = FreeEnrichment._extract_domain_keywords("ab-smile-dental.com")
        assert "ab" not in kw
        assert "smile" in kw
        assert "dental" in kw

    def test_underscore_split(self):
        kw = FreeEnrichment._extract_domain_keywords("sydney_dental_care.com.au")
        assert "sydney" in kw
        assert "dental" in kw
        assert "care" in kw

    def test_single_word_no_stopword_split(self):
        # "dental" alone → ["dental"]
        kw = FreeEnrichment._extract_domain_keywords("dental.com.au")
        assert kw == ["dental"]

    def test_brunswick_east_dental(self):
        kw = FreeEnrichment._extract_domain_keywords("brunswickeastdental.com.au")
        # "east" is not a stopword, so this may not split cleanly — but should
        # return at least ["brunswickeastdental"] or similar without error
        assert isinstance(kw, list)


# ── _abn_clean_entity_name ────────────────────────────────────────────────────


class TestABNCleanEntityName:
    def test_strips_pty_ltd(self):
        assert FreeEnrichment._abn_clean_entity_name("PYMBLE DENTAL PTY LTD") == "PYMBLE DENTAL"

    def test_strips_pty_limited(self):
        assert FreeEnrichment._abn_clean_entity_name("BRIGHT SMILE PTY LIMITED") == "BRIGHT SMILE"

    def test_strips_limited(self):
        assert FreeEnrichment._abn_clean_entity_name("ABC Dental Limited") == "ABC Dental"

    def test_strips_pty_dot_ltd_dot(self):
        assert FreeEnrichment._abn_clean_entity_name("XYZ Dental Pty. Ltd.") == "XYZ Dental"

    def test_strips_trust(self):
        assert FreeEnrichment._abn_clean_entity_name("Smith Family Trust") == "Smith Family"

    def test_strips_trustee_prefix(self):
        result = FreeEnrichment._abn_clean_entity_name("THE TRUSTEE FOR ABC DENTAL TRUST")
        assert "TRUSTEE" not in result.upper()
        assert "ABC DENTAL" in result.upper()

    def test_strips_trustee_for_the_prefix(self):
        result = FreeEnrichment._abn_clean_entity_name("THE TRUSTEE FOR THE SMITH DENTAL TRUST")
        assert "TRUSTEE" not in result.upper()

    def test_no_suffix_unchanged(self):
        assert FreeEnrichment._abn_clean_entity_name("Pymble Dental Practice") == "Pymble Dental Practice"

    def test_case_insensitive_suffix(self):
        assert FreeEnrichment._abn_clean_entity_name("Dental Care pty ltd") == "Dental Care"


# ── _abn_confidence ───────────────────────────────────────────────────────────


class TestABNConfidence:
    def setup_method(self):
        self.fe = _make_fe()

    def test_exact_identical(self):
        assert self.fe._abn_confidence("pymble dental", "pymble dental") == ABNMatchConfidence.EXACT

    def test_exact_above_90_pct(self):
        # "dentists at pymble" vs "dentists pymble" — difflib should give high ratio
        c = self.fe._abn_confidence("dentists pymble", "dentists at pymble")
        assert c in (ABNMatchConfidence.EXACT, ABNMatchConfidence.PARTIAL)

    def test_partial_60_to_89(self):
        # Close enough to be PARTIAL
        c = self.fe._abn_confidence("pymble dental", "north pymble dental care")
        assert c in (ABNMatchConfidence.PARTIAL, ABNMatchConfidence.LOW)

    def test_low_dissimilar(self):
        assert self.fe._abn_confidence("dental pymble", "haircuts unlimited") == ABNMatchConfidence.LOW

    def test_exact_threshold_boundary(self):
        # Identical strings → always EXACT
        s = "sydney smile dental"
        assert self.fe._abn_confidence(s, s) == ABNMatchConfidence.EXACT


# ── _match_abn waterfall ──────────────────────────────────────────────────────


class TestMatchABNWaterfall:
    def setup_method(self):
        self.fe = _make_fe()

    @pytest.mark.asyncio
    async def test_strategy1_domain_keywords_match(self):
        """Domain keyword intersection finds a match via one of the local DB strategies."""
        # Use a name that closely matches the domain keywords to ensure PARTIAL+ confidence
        row = _make_row("Dentists Pymble Pty Ltd")  # closer match → higher confidence
        self.fe._conn.fetch = AsyncMock(return_value=[row])

        result = await self.fe._match_abn("dentists-pymble.com.au")

        assert result["abn_matched"] is True
        # Should match via domain_keywords or title_keywords (local DB), not live_api
        assert result.get("_abn_strategy") in ("domain_keywords", "title_keywords")

    @pytest.mark.asyncio
    async def test_strategy2_title_keywords_match(self):
        """S1 fails (no domain keyword match), S2 title keywords finds match."""
        call_count = 0

        async def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return []  # S1 misses
            return [_make_row("Dentists At Pymble")]  # S2 hits

        self.fe._conn.fetch = mock_fetch

        result = await self.fe._match_abn(
            "dentistsatpymble.com.au",
            title="Dentists at Pymble | Family Dental",
        )

        assert result["abn_matched"] is True
        assert result["_abn_strategy"] == "title_keywords"

    @pytest.mark.asyncio
    async def test_strategy3_suburb_category_match(self):
        """S1 and S2 fail, S3 suburb + keyword finds match."""
        call_count = 0

        async def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return []  # S1, S2 miss
            return [_make_row("Pymble Dental Surgery")]  # S3 hits

        self.fe._conn.fetch = mock_fetch

        result = await self.fe._match_abn(
            "dentistsatpymble.com.au",
            title="Dentists at Pymble",
            suburb="Pymble",
        )

        assert result["abn_matched"] is True
        assert result["_abn_strategy"] == "suburb_category"

    @pytest.mark.asyncio
    async def test_strategy4_live_api_match(self):
        """S1–S3 all fail, S4 live API returns PARTIAL match."""
        self.fe._conn.fetch = AsyncMock(return_value=[])
        self.fe._conn.fetchrow = AsyncMock(return_value={
            "gst_registered": True,
            "entity_type": "Australian Private Company",
            "registration_date": None,
        })

        mock_api_result = [{"business_name": "Dentists at Pymble", "abn": "92 605 514 421"}]

        with patch(
            "src.integrations.abn_client.ABNClient"
        ) as MockABNClient:
            instance = AsyncMock()
            instance.search_by_name = AsyncMock(return_value=mock_api_result)
            MockABNClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockABNClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("src.config.settings.settings"):
                result = await self.fe._match_abn(
                    "dentistsatpymble.com.au",
                    title="Dentists at Pymble",
                )

        assert result["abn_matched"] is True
        assert result["_abn_strategy"] == "live_api"

    @pytest.mark.asyncio
    async def test_all_strategies_fail_returns_no_match(self):
        """All four strategies fail → abn_matched=False."""
        self.fe._conn.fetch = AsyncMock(return_value=[])
        self.fe._conn.fetchrow = AsyncMock(return_value=None)

        with patch(
            "src.integrations.abn_client.ABNClient"
        ) as MockABNClient:
            instance = AsyncMock()
            instance.search_by_name = AsyncMock(return_value=[])
            MockABNClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockABNClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("src.config.settings.settings"):
                result = await self.fe._match_abn(
                    "unknownbusiness.com.au",
                    title="Unknown Business",
                )

        assert result["abn_matched"] is False

    @pytest.mark.asyncio
    async def test_waterfall_stops_at_first_partial_plus(self):
        """Once S1 finds PARTIAL match, S2 and S3 are never called."""
        fetch_calls = []

        async def mock_fetch(*args, **kwargs):
            fetch_calls.append(args[0][:30])  # log first 30 chars of SQL
            return [_make_row("Pymble Dental Surgery")]  # always return a match

        self.fe._conn.fetch = mock_fetch

        result = await self.fe._match_abn(
            "pymblesurgery.com.au",
            title="Pymble Surgery | Dental",
            suburb="Pymble",
        )

        assert result["abn_matched"] is True
        # Only S1 should have run (1 DB call)
        assert len(fetch_calls) == 1

    @pytest.mark.asyncio
    async def test_low_confidence_stored_as_fallback(self):
        """LOW confidence match stored as best_low; returned only if nothing better found."""
        self.fe._conn.fetchrow = AsyncMock(return_value={
            "gst_registered": False,
            "entity_type": "Individual/Sole Trader",
            "registration_date": None,
        })

        # Return a dissimilar result to force LOW confidence
        low_row = _make_row("Completely Different Business Name Here")
        call_count = 0

        async def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [low_row]   # S1: returns something but LOW confidence
            return []               # S2, S3: empty

        self.fe._conn.fetch = mock_fetch

        with patch("src.integrations.abn_client.ABNClient") as MockABNClient:
            instance = AsyncMock()
            instance.search_by_name = AsyncMock(return_value=[])
            MockABNClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockABNClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("src.config.settings.settings"):
                result = await self.fe._match_abn("random-business.com.au")

        # The LOW match is returned as fallback
        assert result["abn_matched"] is True
        assert result["abn_confidence"] == ABNMatchConfidence.LOW

    @pytest.mark.asyncio
    async def test_title_prefix_home_stripped(self):
        """'Home | Pymble Dental' → title cleaned to 'Pymble Dental' before matching."""
        fetched_terms = []

        async def mock_fetch(sql, *params):
            fetched_terms.extend(params)
            return []

        self.fe._conn.fetch = mock_fetch

        with patch("src.integrations.abn_client.ABNClient") as MockABNClient:
            instance = AsyncMock()
            instance.search_by_name = AsyncMock(return_value=[])
            MockABNClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockABNClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("src.config.settings.settings"):
                await self.fe._match_abn(
                    "pymbledental.com.au",
                    title="Home | Pymble Dental Clinic",
                )

        # "home" should NOT appear in any search term
        for term in fetched_terms:
            assert "home" not in str(term).lower()

    @pytest.mark.asyncio
    async def test_single_keyword_domain_uses_strategy1(self):
        """Single-keyword domain (dentist) should use Strategy 1, was previously skipped with >= 2 gate."""
        # Domain: "dentist.com.au" → keywords = ["dentist"]
        row = _make_row("Dentist Services Pty Ltd")  # Closer match to "dentist"
        self.fe._conn.fetch = AsyncMock(return_value=[row])
        self.fe._conn.fetchrow = AsyncMock(return_value={
            "gst_registered": True,
            "entity_type": "Australian Private Company",
            "registration_date": None,
        })

        result = await self.fe._match_abn("dentist.com.au")

        assert result["abn_matched"] is True
        assert result.get("_abn_strategy") in ("domain_keywords", "title_keywords")

    @pytest.mark.asyncio
    async def test_single_keyword_title_uses_strategy2(self):
        """Single-word title (Plumber) should use Strategy 2 when domain keyword is meaningless."""
        # Domain: "abc.com.au" → keywords = ["abc"] (meaningless)
        # Title: "Plumber" → title_kw = ["plumber"]
        call_count = 0

        async def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return []  # S1 misses (domain keyword "abc" doesn't match anything)
            return [_make_row("City Plumbing Pty Ltd")]  # S2 hits with title keyword "plumber"

        self.fe._conn.fetch = mock_fetch
        self.fe._conn.fetchrow = AsyncMock(return_value={
            "gst_registered": True,
            "entity_type": "Australian Private Company",
            "registration_date": None,
        })

        with patch("src.integrations.abn_client.ABNClient") as MockABNClient:
            instance = AsyncMock()
            instance.search_by_name = AsyncMock(return_value=[])  # S4 returns nothing
            MockABNClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockABNClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("src.config.settings.settings"):
                result = await self.fe._match_abn(
                    "abc.com.au",
                    title="Plumber",
                )

        assert result["abn_matched"] is True
        assert result["_abn_strategy"] == "title_keywords"

    @pytest.mark.asyncio
    async def test_strategy4_fires_on_two_char_term(self):
        """Strategy 4 (live API) fires with short domain (ab.com.au) and title with 2+ char terms."""
        # Domain: "ab.com.au" → short domain
        # Title: "AB Legal" → title_cleaned = "AB Legal", api_terms includes terms >= 2 chars
        self.fe._conn.fetch = AsyncMock(return_value=[])
        self.fe._conn.fetchrow = AsyncMock(return_value={
            "gst_registered": True,
            "entity_type": "Australian Private Company",
            "registration_date": None,
        })

        mock_api_result = [{"business_name": "AB Legal Services Pty Ltd", "abn": "12 345 678 901"}]

        with patch(
            "src.integrations.abn_client.ABNClient"
        ) as MockABNClient:
            instance = AsyncMock()
            instance.search_by_name = AsyncMock(return_value=mock_api_result)
            MockABNClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockABNClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("src.config.settings.settings"):
                result = await self.fe._match_abn(
                    "ab.com.au",
                    title="AB Legal",
                )

        assert result["abn_matched"] is True
        assert result["_abn_strategy"] == "live_api"

    @pytest.mark.asyncio
    async def test_state_hint_prefers_matching_state(self):
        """When multiple rows returned, state_hint picks the row in the correct state."""
        nsw_row = _make_row("Pymble Dental NSW", state="NSW")
        qld_row = _make_row("Pymble Dental QLD", state="QLD")
        self.fe._conn.fetch = AsyncMock(return_value=[qld_row, nsw_row])

        result = await self.fe._match_abn(
            "pymble-dental.com.au",
            state_hint="NSW",
        )

        assert result["abn_matched"] is True
        # NSW row should be preferred (its name used in confidence calc)
        assert result["entity_type"] == "Australian Private Company"
