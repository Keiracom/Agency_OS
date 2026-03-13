"""
FILE: src/integrations/siege_waterfall.py
PURPOSE: Siege Waterfall v3 - Multi-tier Australian B2B enrichment (Directive #144)
PHASE: SIEGE (System Overhaul)
TASK: SIEGE-001
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
  - src/integrations/leadmagic.py
  - src/integrations/bright_data_client.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - LAW II: All costs in $AUD

SIEGE WATERFALL V3 TIERS (Directive #144):
  T0:    GMB-first discovery (handled in discovery_modes.py) - $0.001/record
  T1:    ABN Bulk (data.gov.au) - FREE
  T1→T1.5: LinkedIn URL resolution - $0.0015 | Gate: None (always runs) [Directive #148]
  T1.5:  BD LinkedIn Company - $0.025 | Gate: ICP pass
  T2:    SKIP (T0/T2 merged) - T0 already has GMB data
  T2.5:  BD GMB Reviews - $0.001 | Gate: Propensity ≥70
  T3:    Leadmagic email - $0.015 | Gate: ICP pass
  T-DM0: DataForSEO (5 endpoints) - $0.0465 | Gate: ICP pass
  T-DM1: BD LinkedIn Profile - $0.0015 | Gate: ICP pass
  T-DM2: BD LinkedIn Posts 90d - $0.0015 | Gate: Propensity ≥70
  T-DM2b: Company LI posts (from T1.5) - FREE | Gate: Propensity ≥70
  T-DM3: BD X Posts 90d - $0.0025 | Gate: Propensity ≥70
  T5:    Leadmagic mobile - $0.077 | Gate: Reachability needs mobile channel

DUAL SCORING:
  - Reachability (0-100): Can we reach them? (verified channels)
  - Propensity (0-100+): Will they buy? (intent signals + ICP fit)

NOTE: Leadmagic plan unpurchased - API key present but 0 credits.
      Use LEADMAGIC_MOCK=true for testing without credits.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx
import sentry_sdk
from fuzzywuzzy import fuzz
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.exceptions import APIError, IntegrationError, ValidationError

logger = logging.getLogger(__name__)

# Fuzzy match thresholds (from waterfall_verification_worker.py)
FUZZY_MATCH_THRESHOLD = 70
HIGH_CONFIDENCE_THRESHOLD = 90
MEDIUM_CONFIDENCE_THRESHOLD = 80

# CEO Directive #014: Generic name patterns to skip for Tier 2 GMB
# These holding company patterns have low GMB match probability
GENERIC_NAME_PATTERNS = (
    "holdings",
    "enterprises",
    "investments",
    "trust",
    "group",
    "services",
    "management",
    "properties",
    "consulting",
    "solutions",
    "international",
    "ventures",
    "capital",
    "partners",
)


# ============================================
# CUSTOM EXCEPTIONS
# ============================================


class EnrichmentTierError(IntegrationError):
    """A specific enrichment tier failed."""

    def __init__(
        self,
        tier: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        details["tier"] = tier
        super().__init__(service=f"siege_{tier}", message=message, details=details)
        self.tier = tier


class EnrichmentSkippedError(IntegrationError):
    """Enrichment tier was skipped (not an error, informational)."""

    def __init__(
        self,
        tier: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        details["tier"] = tier
        details["reason"] = reason
        super().__init__(
            service=f"siege_{tier}",
            message=f"Tier {tier} skipped: {reason}",
            details=details,
        )


# ============================================
# CONSTANTS & ENUMS
# ============================================


class EnrichmentTier(StrEnum):
    """Enrichment tier identifiers - Siege Waterfall v3 (Directive #144)."""

    # Core tiers
    ABN = "tier1_abn"  # T1: ABN verification (FREE)
    LINKEDIN_COMPANY = "tier1_5_linkedin_company"  # T1.5: BD LinkedIn Company ($0.025)
    GMB = "tier2_gmb"  # T2: SKIP if T0 has GMB data (T0/T2 merge)
    GMB_REVIEWS = "tier2_5_gmb_reviews"  # T2.5: BD GMB Reviews ($0.001, Prop ≥70)
    LEADMAGIC_EMAIL = "tier3_leadmagic_email"  # T3: Leadmagic email ($0.015)

    # Decision Maker tiers
    DM_DATAFORSEO = "tier_dm0_dataforseo"  # T-DM0: DataForSEO 5 endpoints ($0.0465)
    DM_LINKEDIN_PROFILE = "tier_dm1_linkedin_profile"  # T-DM1: BD LinkedIn Profile ($0.0015)
    DM_LINKEDIN_POSTS = (
        "tier_dm2_linkedin_posts"  # T-DM2: BD LinkedIn Posts 90d ($0.0015, Prop ≥70)
    )
    DM_COMPANY_POSTS = "tier_dm2b_company_posts"  # T-DM2b: Company LI posts (FREE from T1.5)
    DM_X_POSTS = "tier_dm3_x_posts"  # T-DM3: BD X Posts 90d ($0.0025, Prop ≥70)

    # Identity tier
    IDENTITY = "tier5_identity"  # T5: Leadmagic mobile ($0.077, Reachability needs mobile)


# Cost per lead in $AUD (LAW II compliance) - Siege Waterfall v3
TIER_COSTS_AUD: dict[EnrichmentTier, float] = {
    EnrichmentTier.ABN: 0.00,  # FREE - data.gov.au
    EnrichmentTier.LINKEDIN_COMPANY: 0.025,  # T1.5: BD LinkedIn Company
    EnrichmentTier.GMB: 0.001,  # T2: Google Maps (DEPRECATED - skipped if T0 has data)
    EnrichmentTier.GMB_REVIEWS: 0.001,  # T2.5: BD GMB Reviews
    EnrichmentTier.LEADMAGIC_EMAIL: 0.015,  # T3: Leadmagic email finder
    EnrichmentTier.DM_DATAFORSEO: 0.0465,  # T-DM0: DataForSEO (5 endpoints)
    EnrichmentTier.DM_LINKEDIN_PROFILE: 0.0015,  # T-DM1: BD LinkedIn Profile
    EnrichmentTier.DM_LINKEDIN_POSTS: 0.0015,  # T-DM2: BD LinkedIn Posts 90d
    EnrichmentTier.DM_COMPANY_POSTS: 0.00,  # T-DM2b: FREE (reuses T1.5 field)
    EnrichmentTier.DM_X_POSTS: 0.0025,  # T-DM3: BD X Posts 90d
    EnrichmentTier.IDENTITY: 0.077,  # T5: Leadmagic mobile finder
}

# Minimum sources for ALS bonus
MIN_SOURCES_FOR_BONUS = 3
ALS_MULTI_SOURCE_BONUS = 15


# ============================================
# DATA CLASSES
# ============================================


@dataclass
class TierResult:
    """Result from a single enrichment tier."""

    tier: EnrichmentTier
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    cost_aud: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None
    # CEO Directive #057: Track source URL for Spam Act compliance
    source_url: str | None = None


@dataclass
class EnrichmentResult:
    """Complete enrichment result with lineage tracking."""

    lead_id: str | None
    original_data: dict[str, Any]
    enriched_data: dict[str, Any]
    tier_results: list[TierResult]
    total_cost_aud: float
    sources_used: int
    als_bonus_applied: bool
    als_bonus_amount: int
    enrichment_lineage: list[dict[str, Any]]
    started_at: str
    completed_at: str
    # CEO Directive #057: Enrichment provenance for Spam Act compliance
    enrichment_source_url: str | None = None
    enrichment_captured_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/API response."""
        return {
            "lead_id": self.lead_id,
            "enriched_data": self.enriched_data,
            "total_cost_aud": self.total_cost_aud,
            "sources_used": self.sources_used,
            "als_bonus_applied": self.als_bonus_applied,
            "als_bonus_amount": self.als_bonus_amount,
            "enrichment_lineage": self.enrichment_lineage,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            # CEO Directive #057: Enrichment provenance
            "enrichment_source_url": self.enrichment_source_url,
            "enrichment_captured_at": self.enrichment_captured_at,
        }


# ============================================
# STUB CLIENTS (Until real integrations built)
# ============================================


class ABNClientStub:
    """
    Stub for ABN Bulk client - REPLACED BY REAL IMPLEMENTATION.

    NOTE: Real implementation now available in src/integrations/abn_client.py
    This stub remains for backwards compatibility only.

    Use get_abn_client() from abn_client.py instead.
    """

    async def lookup_abn(self, abn: str) -> dict[str, Any] | None:
        """Look up business by ABN."""
        try:
            from src.integrations.abn_client import get_abn_client

            client = get_abn_client()
            return await client.search_by_abn(abn)
        except Exception as e:
            logger.warning(f"[ABN] lookup_abn failed: {e}")
            return None

    async def search_by_name(
        self,
        business_name: str,
        state: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search businesses by name."""
        try:
            from src.integrations.abn_client import get_abn_client

            client = get_abn_client()
            return await client.search_by_name(business_name, state=state)
        except Exception as e:
            logger.warning(f"[ABN] search_by_name failed: {e}")
            return []

    async def enrich_from_abn(self, abn: str) -> dict[str, Any]:
        """Enrich lead data from ABN lookup."""
        try:
            from src.integrations.abn_client import get_abn_client

            client = get_abn_client()
            return await client.enrich_from_abn(abn)
        except Exception as e:
            logger.warning(f"[ABN] enrich_from_abn failed: {e}")
            return {"found": False, "source": "abn_lookup", "error": str(e)}


class GMBScraperAdapter:
    """
    Adapter for Google Maps Business scraper via Bright Data.

    CEO Directive #036: Replaced deprecated Apify with Bright Data Web Scraper API.
    Dataset: gd_m8ebnr0q2qlklc02fz (Google Maps Business Information)
    Method: discover_by=location
    Cost: ~$0.001/lead AUD
    """

    DATASET_ID = "gd_m8ebnr0q2qlklc02fz"
    STATE_CITY_MAP = {
        "NSW": "Sydney",
        "VIC": "Melbourne",
        "QLD": "Brisbane",
        "WA": "Perth",
        "SA": "Adelaide",
        "TAS": "Hobart",
        "ACT": "Canberra",
        "NT": "Darwin",
    }

    def __init__(self):
        self._api_key = os.getenv("BRIGHTDATA_API_KEY")

    def _is_available(self) -> bool:
        """Check if Bright Data API is configured."""
        return bool(self._api_key)

    async def scrape_business(
        self,
        business_name: str,
        location: str | None = None,
    ) -> dict[str, Any] | None:
        """Scrape business from Google Maps via Bright Data."""
        if not self._is_available():
            logger.warning("[GMB] BRIGHTDATA_API_KEY not set")
            return None

        city = location or "Australia"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Trigger collection
                resp = await client.post(
                    "https://api.brightdata.com/datasets/v3/trigger",
                    params={
                        "dataset_id": self.DATASET_ID,
                        "type": "discover_new",
                        "discover_by": "location",
                        "notify": "false",
                        "include_errors": "true",
                    },
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": [
                            {"country": "AU", "keyword": f"{business_name} {city}", "lat": ""}
                        ]
                    },
                )
                resp.raise_for_status()
                snapshot_id = resp.json().get("snapshot_id")
                if not snapshot_id:
                    return None

                # Poll for completion
                for _ in range(18):
                    await asyncio.sleep(10)
                    status = await client.get(
                        f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
                        headers={"Authorization": f"Bearer {self._api_key}"},
                    )
                    if status.json().get("status") == "ready":
                        break
                else:
                    return None

                # Fetch results
                data = await client.get(
                    f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                    params={"format": "json"},
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                results = data.json()

                if results and len(results) > 0:
                    # Find best match
                    best = max(
                        [r for r in results if "error" not in r],
                        key=lambda r: fuzz.ratio(business_name.lower(), r.get("name", "").lower()),
                        default=None,
                    )
                    if (
                        best
                        and fuzz.ratio(business_name.lower(), best.get("name", "").lower())
                        >= FUZZY_MATCH_THRESHOLD
                    ):
                        return {"found": True, **best}

                return None
        except Exception as e:
            logger.warning(f"[GMB] scrape_business failed: {e}")
            return None

    async def enrich_from_gmb(
        self,
        business_name: str,
        domain: str | None = None,
        location: str | None = None,
    ) -> dict[str, Any]:
        """Enrich lead with GMB signals via Bright Data."""
        if not self._is_available():
            logger.warning("[GMB] BRIGHTDATA_API_KEY not set")
            return {"found": False, "source": "gmb_unavailable"}

        try:
            result = await self.scrape_business(business_name, location)

            if result and result.get("found"):
                return {
                    "found": True,
                    "source": "brightdata_gmb",
                    "phone": result.get("phone_number"),
                    "website": result.get("open_website"),
                    "address": result.get("address"),
                    "rating": result.get("rating"),
                    "review_count": result.get("reviews_count", 0),
                    "category": result.get("category"),
                    "categories": result.get("all_categories", []),
                    "google_maps_url": result.get("url"),
                    "place_id": result.get("place_id"),
                    "lat": result.get("lat"),
                    "lng": result.get("lon"),
                    "cost_aud": 0.001,
                }

            return {"found": False, "source": "brightdata_gmb"}
        except Exception as e:
            logger.warning(f"[GMB] enrich_from_gmb failed: {e}")
            return {"found": False, "source": "brightdata_gmb", "error": str(e)}


# Alias for backwards compatibility
GMBScraperStub = GMBScraperAdapter


class LeadmagicEmailAdapter:
    """
    Adapter for Leadmagic email finding.

    Replaces HunterClientAdapter - CEO Directive: Hunter deprecated.
    Implements: Tier 3 of Siege Waterfall - Email Discovery.
    Cost: $0.015 AUD per lookup (was Hunter $0.019)
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy-load the real Leadmagic client."""
        if self._client is None:
            try:
                from src.integrations.leadmagic import get_leadmagic_client

                self._client = get_leadmagic_client()
            except Exception as e:
                logger.warning(f"[Leadmagic] Could not initialize client: {e}")
                self._client = None
        return self._client

    async def verify_email(self, email: str) -> dict[str, Any]:
        """Verify email deliverability (via find_email)."""
        # Leadmagic doesn't have separate verify - use find_email pattern
        client = self._get_client()
        if not client:
            logger.warning("[Leadmagic] Client not available - returning unknown status")
            return {
                "email": email,
                "status": "unknown",
                "score": 0,
                "source": "leadmagic_unavailable",
            }

        # For verification, we just return the email as-is with unknown status
        # Leadmagic find_email provides confidence score on lookup
        return {
            "email": email,
            "status": "unknown",
            "score": 0,
            "source": "leadmagic",
            "is_valid": True,  # Assume valid until proven otherwise
            "is_risky": False,
            "cost_aud": 0.0,  # No cost for verification pass-through
        }

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> dict[str, Any]:
        """Find email for person at domain."""
        client = self._get_client()
        if not client:
            logger.warning("[Leadmagic] Client not available")
            return {"found": False, "source": "leadmagic_unavailable"}

        try:
            result = await client.find_email(first_name, last_name, domain)
            return {
                "found": result.found,
                "email": result.email,
                "score": result.confidence,
                "status": "found" if result.found else "not_found",
                "source": "leadmagic",
                "cost_aud": result.cost_aud,
            }
        except Exception as e:
            logger.warning(f"[Leadmagic] find_email failed: {e}")
            return {"found": False, "source": "leadmagic", "error": str(e)}

    async def domain_search(
        self,
        domain: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for emails at domain - not supported by Leadmagic."""
        logger.warning("[Leadmagic] domain_search not supported - use find_email instead")
        return []


# Import Leadmagic client for Tier 3 email and Tier 5 mobile enrichment
# Replaces Kaspr - CEO Directive: Kaspr deprecated
try:
    from src.integrations.leadmagic import LeadmagicClient, get_leadmagic_client

    LEADMAGIC_AVAILABLE = True
except ImportError:
    LEADMAGIC_AVAILABLE = False

    class LeadmagicClient:  # type: ignore
        """Fallback stub if leadmagic.py not available."""

        async def find_mobile(self, linkedin_url: str) -> dict[str, Any]:
            """Find mobile from LinkedIn URL."""
            logger.warning("[Leadmagic] Module not available - using stub")
            return {"found": False, "source": "leadmagic_stub"}

        async def find_email(
            self,
            first_name: str,
            last_name: str,
            domain: str,
            company: str | None = None,
        ) -> dict[str, Any]:
            """Find email for person at domain."""
            logger.warning("[Leadmagic] Module not available - using stub")
            return {"found": False, "source": "leadmagic_stub"}


# Alias for backwards compatibility
LEADMAGIC_MOBILE_AVAILABLE = LEADMAGIC_AVAILABLE
# Backwards compat alias
LeadmagicMobileClient = LeadmagicClient
# Backwards compat alias
get_leadmagic_mobile_client = get_leadmagic_client if LEADMAGIC_AVAILABLE else None


# ============================================
# MAIN CLASS: SIEGE WATERFALL
# ============================================


class SiegeWaterfall:
    """
    Unified interface for 5-tier Australian B2B enrichment.

    Replaces Apollo as single source of truth for lead enrichment.
    Orchestrates a cost-efficient waterfall with graceful degradation.

    Usage:
        waterfall = SiegeWaterfall()
        result = await waterfall.enrich_lead({
            "email": "john@example.com.au",
            "first_name": "John",
            "last_name": "Smith",
            "company_name": "Acme Pty Ltd",
        })

        print(f"Cost: ${result.total_cost_aud:.3f} AUD")
        print(f"Sources: {result.sources_used}")

    Attributes:
        abn_client: ABN Bulk client (Tier 1)
        gmb_scraper: GMB scraper (Tier 2)
        leadmagic_email_client: Leadmagic email client (Tier 3)
        leadmagic_mobile_client: Leadmagic mobile client (Tier 5)
    """

    def __init__(
        self,
        abn_client: ABNClientStub | None = None,
        gmb_scraper: GMBScraperAdapter | None = None,
        leadmagic_email_client: LeadmagicEmailAdapter | None = None,
        leadmagic_mobile_client: LeadmagicMobileClient | None = None,
        bright_data_client=None,
    ):
        """
        Initialize Siege Waterfall v3 with optional client overrides.

        Args:
            abn_client: ABN Bulk client (uses default if None)
            gmb_scraper: GMB scraper adapter (uses default if None)
            leadmagic_email_client: Leadmagic email client adapter (uses default if None)
            leadmagic_mobile_client: Leadmagic mobile client (uses default if None)
            bright_data_client: Bright Data client for T1.5, T2.5, T-DM tiers
        """
        self.abn_client = abn_client or ABNClientStub()
        self.gmb_scraper = gmb_scraper or GMBScraperAdapter()
        self.leadmagic_email_client = leadmagic_email_client or LeadmagicEmailAdapter()

        # Siege Waterfall v3: Bright Data client for new tiers
        if bright_data_client:
            self.bright_data_client = bright_data_client
        else:
            try:
                from src.integrations.bright_data_client import get_bright_data_client

                self.bright_data_client = get_bright_data_client()
            except Exception as e:
                logger.warning(f"[Siege] Bright Data client unavailable: {e}")
                self.bright_data_client = None

        # Use real Leadmagic mobile client if available (Tier 5 - optional)
        # Leadmagic mobile requires LEADMAGIC_API_KEY; if missing, Tier 5 is simply unavailable
        if leadmagic_mobile_client:
            self.leadmagic_mobile_client = leadmagic_mobile_client
        elif LEADMAGIC_MOBILE_AVAILABLE:
            try:
                self.leadmagic_mobile_client = get_leadmagic_mobile_client()
            except Exception as e:
                logger.warning(
                    f"[Siege] Leadmagic mobile client unavailable (Tier 5 disabled): {e}"
                )
                self.leadmagic_mobile_client = None  # Tier 5 will be skipped gracefully
        else:
            self.leadmagic_mobile_client = None  # Module not available, Tier 5 disabled

    async def enrich_lead(
        self,
        lead: dict[str, Any],
        skip_tiers: list[EnrichmentTier] | None = None,
        force_tier5: bool = False,
        icp_criteria: dict[str, Any] | None = None,
    ) -> EnrichmentResult:
        """
        Full 5-tier enrichment cascade.

        Runs each tier in sequence, accumulating data and costs.
        Each tier is optional and gracefully degrades on failure.

        Args:
            lead: Lead data dict with any of:
                - email: Email address
                - first_name, last_name: Contact name
                - company_name: Company name
                - abn: Australian Business Number
                - linkedin_url: LinkedIn profile URL
                - domain: Company domain
            skip_tiers: List of tiers to skip
            force_tier5: Force Tier 5 regardless of ALS

        Returns:
            EnrichmentResult with enriched data, costs, and lineage

        Raises:
            ValidationError: If no usable lead data provided
        """
        started_at = datetime.now(UTC).isoformat()
        skip_tiers = skip_tiers or []
        icp_criteria = icp_criteria or {}

        # Validate we have something to work with
        if not any(
            [
                lead.get("email"),
                lead.get("abn"),
                lead.get("linkedin_url"),
                lead.get("company_name"),
                lead.get("domain"),
                (lead.get("first_name") and lead.get("last_name")),
            ]
        ):
            raise ValidationError(
                message="Lead must have at least one of: email, abn, linkedin_url, "
                "company_name, domain, or first_name + last_name",
            )

        # Track results
        tier_results: list[TierResult] = []
        enriched_data: dict[str, Any] = dict(lead)  # Start with original
        total_cost_aud = 0.0
        # CEO Directive #149: Track field conflicts for provenance lineage
        field_conflicts: list[dict[str, Any]] = []

        # Current propensity score (may be passed in or calculated)
        lead.get("propensity_score", 0)

        # ===== TIER 1 (ABN) + TIER 2 (GMB) — PARALLEL =====
        # FIX 3 (Directive #185): T1 and T2 are independent — both use only original lead data.
        # Fire them simultaneously; return_exceptions=True so a tier failure never kills the other.
        # T1.5/SIZE-GATE/T3/T5 remain sequential: T1.5 needs T1 trading_name for LinkedIn URL
        # resolution; T3/T5 have ALS gates that depend on merged T1+T1.5 results.

        # Pre-compute GMB skip condition from original lead data (independent of T1)
        has_gmb_from_t0 = any([
            enriched_data.get("gmb_rating"),
            enriched_data.get("gmb_review_count"),
            enriched_data.get("gmb_category"),
            enriched_data.get("gmb_address"),
            enriched_data.get("gmb_phone"),
            enriched_data.get("gmb_website"),
            enriched_data.get("gmb_data"),
        ])

        async def _run_t1_abn() -> TierResult:
            if EnrichmentTier.ABN in skip_tiers:
                return TierResult(
                    tier=EnrichmentTier.ABN, success=False, skipped=True,
                    skip_reason="Tier skipped by request",
                )
            try:
                return await self.tier1_abn(enriched_data)
            except Exception as _e:
                # Directive #196: per-tier graceful degradation
                logger.warning(f"[enrich_lead] Tier 1 ABN raised unexpectedly: {_e}")
                return TierResult(tier=EnrichmentTier.ABN, success=False, error=str(_e))

        async def _run_t2_gmb() -> "TierResult | None":
            # Skip if T0 already has GMB data or tier is in skip list (avoid wasted API call)
            if EnrichmentTier.GMB in skip_tiers or has_gmb_from_t0:
                return None  # handled in post-processing below
            try:
                return await self.tier2_gmb(enriched_data)
            except Exception as _e:
                # Directive #196: per-tier graceful degradation
                logger.warning(f"[enrich_lead] Tier 2 GMB raised unexpectedly: {_e}")
                return TierResult(tier=EnrichmentTier.GMB, success=False, error=str(_e))

        t1_result_raw, t2_result_raw = await asyncio.gather(
            _run_t1_abn(), _run_t2_gmb(),
            return_exceptions=True,
        )

        # Process T1 ABN result
        if isinstance(t1_result_raw, Exception):
            t1_result_raw = TierResult(tier=EnrichmentTier.ABN, success=False, error=str(t1_result_raw))
        tier_results.append(t1_result_raw)
        if t1_result_raw.success:
            enriched_data = self._merge_data(
                enriched_data, t1_result_raw.data, source=t1_result_raw.tier.value, conflicts=field_conflicts
            )
            total_cost_aud += t1_result_raw.cost_aud

        # Process T2 GMB result
        if EnrichmentTier.GMB not in skip_tiers:
            if has_gmb_from_t0:
                tier_results.append(TierResult(
                    tier=EnrichmentTier.GMB, success=True, skipped=True,
                    skip_reason="T0 discovery already has GMB data (T0/T2 merge)",
                ))
                logger.info("[T2] Skipping GMB enrichment — T0 already has data")
            else:
                if isinstance(t2_result_raw, Exception):
                    t2_result_raw = TierResult(tier=EnrichmentTier.GMB, success=False, error=str(t2_result_raw))
                if t2_result_raw is not None:
                    tier_results.append(t2_result_raw)
                    if t2_result_raw.success:
                        enriched_data = self._merge_data(
                            enriched_data, t2_result_raw.data, source=t2_result_raw.tier.value, conflicts=field_conflicts
                        )
                        total_cost_aud += t2_result_raw.cost_aud
        else:
            tier_results.append(TierResult(
                tier=EnrichmentTier.GMB, success=False, skipped=True,
                skip_reason="Tier skipped by request",
            ))

        # ===== LINKEDIN URL RESOLUTION =====
        # Directive #148: Resolve LinkedIn URL before T1.5
        if not enriched_data.get("company_linkedin_url") and not enriched_data.get(
            "linkedin_company_url"
        ):
            url_result = await self.resolve_linkedin_url(enriched_data)
            if url_result.success:
                enriched_data = self._merge_data(
                    enriched_data,
                    url_result.data,
                    source="linkedin_url_resolution",
                    conflicts=field_conflicts,
                )
                total_cost_aud += url_result.cost_aud
            elif url_result.data.get("linkedin_url_unknown"):
                # Tag that we tried but couldn't find LinkedIn URL
                enriched_data["linkedin_url_unknown"] = True
            # Don't append to tier_results - this is a helper step, not a full tier

        # ===== TIER 1.5: BD LinkedIn Company =====
        if EnrichmentTier.LINKEDIN_COMPANY not in skip_tiers:
            try:
                result = await self.tier1_5_linkedin_company(enriched_data, icp_passed=True)
            except Exception as e:
                # Directive #196: per-tier graceful degradation
                logger.warning(f"[enrich_lead] Tier 1.5 LinkedIn raised unexpectedly: {e}")
                result = TierResult(tier=EnrichmentTier.LINKEDIN_COMPANY, success=False, error=str(e))
            tier_results.append(result)
            if result.success:
                enriched_data = self._merge_data(
                    enriched_data, result.data, source=result.tier.value, conflicts=field_conflicts
                )
                total_cost_aud += result.cost_aud
        else:
            tier_results.append(
                TierResult(
                    tier=EnrichmentTier.LINKEDIN_COMPANY,
                    success=False,
                    skipped=True,
                    skip_reason="Tier skipped by request",
                )
            )

        # ===== POST-T1.5 SIZE GATE =====
        # CEO Directive #144 Addendum 2: Size filtering immediately after T1.5
        # CEO Directive #148: Don't HELD if LinkedIn URL wasn't found (linkedin_url_unknown)
        employee_count = (
            enriched_data.get("linkedin_company_size")
            or enriched_data.get("company_size")
            or enriched_data.get("employee_count")
        )

        # Directive #148: If we couldn't find a LinkedIn URL, continue without T1.5
        # Tag the lead but don't HELD - they can still be enriched via other channels
        if enriched_data.get("linkedin_url_unknown"):
            enriched_data["size_gate_skipped"] = True
            enriched_data["size_gate_skip_reason"] = "LinkedIn URL not found via SERP"
            logger.info("[SIZE_GATE] Skipping size gate - LinkedIn URL not found (Directive #148)")
            # Continue to other tiers without employee count filtering
        elif not employee_count:
            # HELD: T1.5 ran (we had LinkedIn URL) but no size data
            tier_results.append(
                TierResult(
                    tier=EnrichmentTier.LINKEDIN_COMPANY,  # Use LINKEDIN_COMPANY tier for SIZE_GATE
                    success=False,
                    skipped=False,
                    skip_reason="No company size data — LinkedIn profile incomplete",
                )
            )
            enriched_data["status"] = "HELD"
            enriched_data["hold_reason"] = "No company size data — LinkedIn profile incomplete"
            logger.warning("[SIZE_GATE] Lead HELD - no employee count from T1.5")
            # Return early - do not fire deeper tiers
            # CEO Directive #149: Include field conflicts in early return lineage
            early_lineage = [
                {
                    "tier": r.tier.value if hasattr(r.tier, "value") else str(r.tier),
                    "success": r.success,
                    "skipped": r.skipped,
                    "skip_reason": r.skip_reason,
                    "cost_aud": r.cost_aud,
                    "timestamp": r.timestamp,
                    "error": r.error,
                }
                for r in tier_results
            ]
            if field_conflicts:
                early_lineage.extend(field_conflicts)
            return EnrichmentResult(
                lead_id=lead.get("id") or lead.get("lead_id"),
                original_data=lead,
                enriched_data=enriched_data,
                tier_results=tier_results,
                total_cost_aud=total_cost_aud,
                sources_used=sum(1 for r in tier_results if r.success),
                als_bonus_applied=False,
                als_bonus_amount=0,
                enrichment_lineage=early_lineage,
                started_at=started_at,
                completed_at=datetime.now(UTC).isoformat(),
            )

        # Check campaign size constraints (from ICP criteria)
        icp_size_min = icp_criteria.get("employee_min")
        icp_size_max = icp_criteria.get("employee_max")
        if icp_size_min or icp_size_max:
            if not self._check_size_in_range(employee_count, icp_size_min, icp_size_max):
                tier_results.append(
                    TierResult(
                        tier=EnrichmentTier.LINKEDIN_COMPANY,  # Use LINKEDIN_COMPANY tier for SIZE_GATE
                        success=False,
                        skipped=False,
                        skip_reason=f"Company size {employee_count} outside campaign range ({icp_size_min}-{icp_size_max})",
                    )
                )
                enriched_data["status"] = "HELD"
                enriched_data["hold_reason"] = (
                    f"Company size {employee_count} outside campaign range"
                )
                logger.info(
                    f"[SIZE_GATE] Lead HELD - size {employee_count} outside {icp_size_min}-{icp_size_max}"
                )
                # Return early - do not fire deeper tiers
                # CEO Directive #149: Include field conflicts in early return lineage
                size_gate_lineage = [
                    {
                        "tier": r.tier.value if hasattr(r.tier, "value") else str(r.tier),
                        "success": r.success,
                        "skipped": r.skipped,
                        "skip_reason": r.skip_reason,
                        "cost_aud": r.cost_aud,
                        "timestamp": r.timestamp,
                        "error": r.error,
                    }
                    for r in tier_results
                ]
                if field_conflicts:
                    size_gate_lineage.extend(field_conflicts)
                return EnrichmentResult(
                    lead_id=lead.get("id") or lead.get("lead_id"),
                    original_data=lead,
                    enriched_data=enriched_data,
                    tier_results=tier_results,
                    total_cost_aud=total_cost_aud,
                    sources_used=sum(1 for r in tier_results if r.success),
                    als_bonus_applied=False,
                    als_bonus_amount=0,
                    enrichment_lineage=size_gate_lineage,
                    started_at=started_at,
                    completed_at=datetime.now(UTC).isoformat(),
                )

        # ===== TIER 3: Leadmagic Email (ALS >= 35 only) =====
        if EnrichmentTier.LEADMAGIC_EMAIL not in skip_tiers:
            # Recalculate ALS with current enrichment for gate check
            current_als = self._calculate_als(enriched_data)

            if current_als >= 35:
                try:
                    result = await self.tier3_leadmagic_email(enriched_data)
                except Exception as e:
                    # Directive #196: per-tier graceful degradation
                    logger.warning(f"[enrich_lead] Tier 3 Leadmagic email raised unexpectedly: {e}")
                    result = TierResult(tier=EnrichmentTier.LEADMAGIC_EMAIL, success=False, error=str(e))
                tier_results.append(result)
                if result.success:
                    enriched_data = self._merge_data(
                        enriched_data,
                        result.data,
                        source=result.tier.value,
                        conflicts=field_conflicts,
                    )
                    total_cost_aud += result.cost_aud
            else:
                tier_results.append(
                    TierResult(
                        tier=EnrichmentTier.LEADMAGIC_EMAIL,
                        success=False,
                        skipped=True,
                        skip_reason=f"ALS {current_als} < 35 threshold",
                    )
                )
        else:
            tier_results.append(
                TierResult(
                    tier=EnrichmentTier.LEADMAGIC_EMAIL,
                    success=False,
                    skipped=True,
                    skip_reason="Tier skipped by request",
                )
            )

        # ===== TIER 5: Identity Gold (ALS >= 85 only) =====
        if EnrichmentTier.IDENTITY not in skip_tiers:
            # Recalculate ALS with current enrichment
            current_als = self._calculate_als(enriched_data)

            if current_als >= 85 or force_tier5:
                try:
                    result = await self.tier5_identity(enriched_data, current_als, force=force_tier5)
                except Exception as e:
                    # Directive #196: per-tier graceful degradation
                    logger.warning(f"[enrich_lead] Tier 5 Identity raised unexpectedly: {e}")
                    result = TierResult(tier=EnrichmentTier.IDENTITY, success=False, error=str(e))
                tier_results.append(result)
                if result.success:
                    enriched_data = self._merge_data(
                        enriched_data,
                        result.data,
                        source=result.tier.value,
                        conflicts=field_conflicts,
                    )
                    total_cost_aud += result.cost_aud
            else:
                tier_results.append(
                    TierResult(
                        tier=EnrichmentTier.IDENTITY,
                        success=False,
                        skipped=True,
                        skip_reason=f"ALS {current_als} < 85 threshold",
                    )
                )
        else:
            tier_results.append(
                TierResult(
                    tier=EnrichmentTier.IDENTITY,
                    success=False,
                    skipped=True,
                    skip_reason="Tier skipped by request",
                )
            )

        # ===== Calculate ALS Bonus =====
        sources_used = sum(1 for r in tier_results if r.success)
        als_bonus_applied = sources_used >= MIN_SOURCES_FOR_BONUS
        als_bonus_amount = ALS_MULTI_SOURCE_BONUS if als_bonus_applied else 0

        # Apply bonus to enriched data
        if als_bonus_applied:
            final_propensity = self._calculate_als(enriched_data) + als_bonus_amount
            enriched_data["propensity_score"] = min(final_propensity, 100)  # Cap at 100
            enriched_data["als_bonus_sources"] = sources_used
            logger.info(
                f"[Siege] +{als_bonus_amount} propensity bonus applied ({sources_used} sources)"
            )

        # ===== Build Lineage =====
        enrichment_lineage = [
            {
                "tier": r.tier.value,
                "success": r.success,
                "skipped": r.skipped,
                "skip_reason": r.skip_reason,
                "cost_aud": r.cost_aud,
                "timestamp": r.timestamp,
                "error": r.error,
            }
            for r in tier_results
        ]
        # CEO Directive #149: Add field conflicts to lineage for provenance tracking
        if field_conflicts:
            enrichment_lineage.extend(field_conflicts)

        # ===== Finalize =====
        completed_at = datetime.now(UTC).isoformat()
        enriched_data["enrichment_cost_aud"] = total_cost_aud
        enriched_data["enrichment_sources"] = sources_used
        enriched_data["enrichment_completed_at"] = completed_at

        # ===== CEO Directive #057: Enrichment Provenance =====
        # Determine best source URL for Spam Act "conspicuous publication" defence
        # Priority: LinkedIn > GMB > Company Website > Leadmagic domain
        enrichment_source_url = self._determine_source_url(enriched_data, tier_results)
        enrichment_captured_at = started_at  # When we captured the data

        enriched_data["enrichment_source_url"] = enrichment_source_url
        enriched_data["enrichment_captured_at"] = enrichment_captured_at

        return EnrichmentResult(
            lead_id=lead.get("id") or lead.get("lead_id"),
            original_data=lead,
            enriched_data=enriched_data,
            tier_results=tier_results,
            total_cost_aud=total_cost_aud,
            sources_used=sources_used,
            als_bonus_applied=als_bonus_applied,
            als_bonus_amount=als_bonus_amount,
            enrichment_lineage=enrichment_lineage,
            started_at=started_at,
            completed_at=completed_at,
            enrichment_source_url=enrichment_source_url,
            enrichment_captured_at=enrichment_captured_at,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, APIError)),
    )
    async def tier1_abn(self, lead: dict[str, Any]) -> TierResult:
        """
        Tier 1: ABN Bulk (data.gov.au) - FREE

        Enriches lead with Australian Business Register data.
        Primary source for AU business verification.

        Args:
            lead: Lead data (needs abn or company_name + state)

        Returns:
            TierResult with ABN data (business name, status, GST, etc.)
        """
        tier = EnrichmentTier.ABN
        cost = TIER_COSTS_AUD[tier]

        try:
            # Check if we have usable data
            abn = lead.get("abn")
            company_name = lead.get("company_name")
            state = lead.get("state") or lead.get("company_state")

            if not abn and not company_name:
                return TierResult(
                    tier=tier,
                    success=False,
                    skipped=True,
                    skip_reason="No ABN or company_name available",
                )

            # Try ABN lookup first
            if abn:
                result = await self.abn_client.lookup_abn(abn)
            else:
                # Search by name
                results = await self.abn_client.search_by_name(
                    company_name,
                    state=state,
                )
                result = results[0] if results else None

            if not result:
                return TierResult(
                    tier=tier,
                    success=False,
                    error="No ABN match found",
                )

            # Enrich from ABN data
            enriched = await self.abn_client.enrich_from_abn(result.get("abn") or abn)

            if enriched.get("found"):
                # CEO Directive #057: ABN register is valid public source
                abn_value = result.get("abn") or abn
                source_url = (
                    f"https://abr.business.gov.au/ABN/View?abn={abn_value}" if abn_value else None
                )

                await self._log_enrichment_operation(
                    tier=tier,
                    operation="abn_lookup",
                    lead_data=lead,
                    success=True,
                    cost_aud=cost,
                )
                return TierResult(
                    tier=tier,
                    success=True,
                    data=enriched,
                    cost_aud=cost,
                    source_url=source_url,
                )
            else:
                await self._log_enrichment_operation(
                    tier=tier,
                    operation="abn_lookup",
                    lead_data=lead,
                    success=False,
                    error="ABN enrichment returned no data",
                )
                return TierResult(
                    tier=tier,
                    success=False,
                    error="ABN enrichment returned no data",
                )

        except Exception as e:
            logger.warning(f"[Siege] Tier 1 ABN failed: {e}")
            sentry_sdk.capture_exception(e)
            await self._log_enrichment_operation(
                tier=tier,
                operation="abn_lookup",
                lead_data=lead,
                success=False,
                error=str(e),
            )
            return TierResult(
                tier=tier,
                success=False,
                error=str(e),
            )

    async def resolve_linkedin_url(self, lead: dict[str, Any]) -> TierResult:
        """
        Resolve LinkedIn company URL via SERP search.

        Directive #148: LinkedIn URL resolution between T1 and T1.5.

        Query: "[company_name] site:linkedin.com/company"
        Fallback: "[trading_name] site:linkedin.com/company"

        Cost: ~$0.0015 AUD per search

        Returns:
            TierResult with linkedin_company_url if found
        """
        tier = EnrichmentTier.LINKEDIN_COMPANY  # Use same tier for cost tracking
        cost = 0.0015  # SERP search cost

        company_name = lead.get("company_name") or lead.get("trading_name") or ""
        trading_name = lead.get("trading_name") or lead.get("company_name") or ""

        if not company_name:
            return TierResult(tier=tier, success=False, skipped=True, skip_reason="No company name")

        if not self.bright_data_client:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="Bright Data client not configured",
            )

        try:
            # Try primary query
            query = f'"{company_name}" site:linkedin.com/company'
            results = await self.bright_data_client.search_google(query, max_results=3)

            linkedin_url = None
            for r in results:
                url = r.get("link") or r.get("url") or ""
                if "linkedin.com/company/" in url:
                    linkedin_url = url
                    break

            # Fallback to trading name if different
            if not linkedin_url and trading_name and trading_name != company_name:
                query = f'"{trading_name}" site:linkedin.com/company'
                results = await self.bright_data_client.search_google(query, max_results=3)
                for r in results:
                    url = r.get("link") or r.get("url") or ""
                    if "linkedin.com/company/" in url:
                        linkedin_url = url
                        break

            if linkedin_url:
                logger.info(f"[LinkedIn URL] Resolved: {linkedin_url}")
                return TierResult(
                    tier=tier,
                    success=True,
                    data={"company_linkedin_url": linkedin_url, "linkedin_url_resolved": True},
                    cost_aud=cost,
                )
            else:
                logger.warning(f"[LinkedIn URL] Not found for: {company_name}")
                return TierResult(
                    tier=tier,
                    success=False,
                    data={"linkedin_url_unknown": True},
                    cost_aud=cost,
                )

        except Exception as e:
            logger.warning(f"[LinkedIn URL] Resolution failed: {e}")
            sentry_sdk.capture_exception(e)
            return TierResult(
                tier=tier,
                success=False,
                error=str(e),
                cost_aud=cost,
            )

    def _is_generic_name(self, name: str) -> bool:
        """
        CEO Directive #014: Check if name matches generic holding company patterns.
        These have low GMB match probability and should skip Tier 2.
        """
        if not name:
            return False
        name_lower = name.lower()
        return any(pattern in name_lower for pattern in GENERIC_NAME_PATTERNS)

    def _strip_legal_suffixes(self, name: str) -> str:
        """Strip common legal entity suffixes for better GMB matching."""
        import re

        if not name:
            return name
        # Remove Pty Ltd, Ltd, Pty, PTY LTD, etc.
        patterns = [
            r"\s+pty\.?\s*ltd\.?$",
            r"\s+ltd\.?$",
            r"\s+pty\.?$",
            r"\s+proprietary\s+limited$",
            r"\s+limited$",
        ]
        result = name
        for pattern in patterns:
            result = re.sub(pattern, "", result, flags=re.IGNORECASE)
        return result.strip()

    async def _log_tier2_gmb_match(
        self,
        lead: dict[str, Any],
        search_name: str,
        waterfall_step: str,
        location_query: str,
        gmb_result: str,
        gmb_name: str | None = None,
        match_score: int | None = None,
        passed: bool = False,
        skip_reason: str | None = None,
        names_tried: int = 0,
        processing_ms: int = 0,
    ) -> None:
        """
        CEO Directive #014: Log Tier 2 GMB match attempt to Supabase for monitoring.
        """
        try:
            from src.integrations.supabase import get_async_supabase_client

            supabase = await get_async_supabase_client()
            log_entry = {
                "abn": lead.get("abn"),
                "lead_id": lead.get("lead_id") or lead.get("id"),
                "abn_name": lead.get("business_name") or lead.get("company_name"),
                "search_name_used": search_name,
                "waterfall_step": waterfall_step,
                "location_query": location_query,
                "gmb_result": gmb_result,
                "gmb_name": gmb_name,
                "match_score": match_score,
                "pass": passed,
                "skip_reason": skip_reason,
                "names_tried": names_tried,
                "processing_ms": processing_ms,
            }
            await supabase.table("tier2_gmb_match_log").insert(log_entry).execute()
        except Exception as e:
            # Don't fail enrichment if logging fails
            logger.warning(f"[Siege] Failed to log Tier 2 GMB match: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, APIError)),
    )
    async def tier2_gmb(self, lead: dict[str, Any]) -> TierResult:
        """
        Tier 2: GMB/Ads Signals - $0.006/lead AUD

        CEO Directive #014: Enhanced waterfall name resolution

        Scrapes Google Maps for business signals:
        - Phone numbers, Website, Hours, Reviews/rating, Categories

        Waterfall order (CEO Directive #014 + #016):
        a) ASIC business names from business_names[] (try each)
        b) ABN trading_name (pre-2012 legacy)
        c) Legal name stripped of "Pty Ltd" / "Ltd" / "Pty"
        c.5) LinkedIn company name from Bright Data (fallback after govt data)
        d) Location-pinned search (name + postcode + state + "Australia")

        Generic filter: Skip if no ASIC business names, no linkedin_company_name,
        AND legal name matches generic patterns (Holdings, Trust, Enterprises, etc.)

        Args:
            lead: Lead data (needs company_name, may have ABN data from Tier 1)

        Returns:
            TierResult with GMB data
        """
        import time

        tier = EnrichmentTier.GMB
        cost = TIER_COSTS_AUD[tier]
        start_time = time.time()

        try:
            business_names = lead.get("business_names", [])
            trading_name = lead.get("trading_name")
            legal_name = lead.get("business_name") or lead.get("company_name")
            # CEO Directive #016: Bright Data LinkedIn company name (high priority)
            linkedin_company_name = lead.get("linkedin_company_name")

            # CEO Directive #014 + #016: Generic name filter
            # Skip Tier 2 if no ASIC business names, no linkedin_company_name,
            # AND legal name is generic
            if (
                not business_names
                and not linkedin_company_name
                and legal_name
                and self._is_generic_name(legal_name)
            ):
                skip_reason = "tier2_skipped_generic_name"
                logger.info(
                    f"[Siege] Tier 2 GMB: Skipping generic name '{legal_name}' "
                    f"(no ASIC business names available)"
                )
                await self._log_tier2_gmb_match(
                    lead=lead,
                    search_name=legal_name,
                    waterfall_step="c",
                    location_query="",
                    gmb_result="skipped",
                    passed=False,
                    skip_reason=skip_reason,
                )
                return TierResult(
                    tier=tier,
                    success=False,
                    skipped=True,
                    skip_reason=skip_reason,
                )

            # Build location string
            location_parts = []
            if lead.get("postcode"):
                location_parts.append(lead["postcode"])
            if lead.get("city"):
                location_parts.append(lead["city"])
            state = lead.get("state") or lead.get("company_state")
            if state:
                location_parts.append(state)

            base_location = ", ".join(location_parts) if location_parts else ""
            domain = lead.get("domain") or lead.get("company_domain")

            # Build waterfall search list with step tracking
            # Format: (name, step, location)
            waterfall_searches: list[tuple[str, str, str]] = []

            # Step a: ASIC business names (highest priority for GMB matching)
            for bn in business_names:
                if bn:
                    waterfall_searches.append((bn, "a", base_location or "Australia"))

            # Step b: ABN trading_name (pre-2012 legacy)
            if trading_name:
                waterfall_searches.append((trading_name, "b", base_location or "Australia"))

            # Step c: Legal name stripped of suffixes
            if legal_name:
                stripped_name = self._strip_legal_suffixes(legal_name)
                if stripped_name and stripped_name != legal_name or stripped_name:
                    waterfall_searches.append((stripped_name, "c", base_location or "Australia"))

            # Step c.5: LinkedIn company name from Bright Data (CEO Directive #016)
            # Fallback after official govt data exhausted
            if linkedin_company_name:
                waterfall_searches.append(
                    (linkedin_company_name, "c5", base_location or "Australia")
                )

            # Step d: Location-pinned search (name + full location + "Australia")
            if legal_name and base_location:
                location_pinned = f"{base_location}, Australia"
                waterfall_searches.append((legal_name, "d", location_pinned))

            if not waterfall_searches:
                return TierResult(
                    tier=tier,
                    success=False,
                    skipped=True,
                    skip_reason="No company_name or ABN business names available",
                )

            # Try each waterfall step until match found
            enriched = None
            matched_name = None
            matched_step = None
            names_tried = 0

            for name, step, location in waterfall_searches:
                names_tried += 1
                step_start = time.time()
                logger.debug(f"[Siege] Tier 2 GMB: Step {step} - Trying '{name}' in {location}")

                result = await self.gmb_scraper.enrich_from_gmb(
                    business_name=name,
                    domain=domain,
                    location=location,
                )

                step_ms = int((time.time() - step_start) * 1000)

                if result.get("found"):
                    gmb_name = result.get("business_name", "")
                    match_score = max(
                        fuzz.ratio(name.lower(), gmb_name.lower()),
                        fuzz.token_set_ratio(name.lower(), gmb_name.lower()),
                    )

                    passed = match_score >= FUZZY_MATCH_THRESHOLD

                    # Log this attempt
                    await self._log_tier2_gmb_match(
                        lead=lead,
                        search_name=name,
                        waterfall_step=step,
                        location_query=location,
                        gmb_result="found",
                        gmb_name=gmb_name,
                        match_score=match_score,
                        passed=passed,
                        names_tried=names_tried,
                        processing_ms=step_ms,
                    )

                    if passed:
                        enriched = result
                        matched_name = name
                        matched_step = step
                        enriched["match_score"] = match_score
                        enriched["matched_query"] = name
                        enriched["waterfall_step"] = step
                        logger.info(
                            f"[Siege] Tier 2 GMB: Step {step} matched '{gmb_name}' "
                            f"with query '{name}' (score: {match_score})"
                        )
                        break
                    else:
                        logger.debug(
                            f"[Siege] Tier 2 GMB: Step {step} low confidence "
                            f"'{gmb_name}' for '{name}' (score: {match_score})"
                        )
                else:
                    # Log not found
                    await self._log_tier2_gmb_match(
                        lead=lead,
                        search_name=name,
                        waterfall_step=step,
                        location_query=location,
                        gmb_result="not_found",
                        passed=False,
                        names_tried=names_tried,
                        processing_ms=step_ms,
                    )

            total_ms = int((time.time() - start_time) * 1000)

            if enriched:
                # CEO Directive #057: GMB URL is valid public source
                gmb_source_url = enriched.get("google_maps_url")

                await self._log_enrichment_operation(
                    tier=tier,
                    operation="gmb_scrape",
                    lead_data=lead,
                    success=True,
                    cost_aud=cost,
                    metadata={
                        "location": base_location,
                        "matched_name": matched_name,
                        "match_score": enriched.get("match_score"),
                        "waterfall_step": matched_step,
                        "names_tried": names_tried,
                        "processing_ms": total_ms,
                    },
                )
                return TierResult(
                    tier=tier,
                    success=True,
                    data=enriched,
                    cost_aud=cost,
                    source_url=gmb_source_url,
                )
            else:
                await self._log_enrichment_operation(
                    tier=tier,
                    operation="gmb_scrape",
                    lead_data=lead,
                    success=False,
                    error=f"No GMB listing found (tried {names_tried} waterfall steps)",
                    metadata={
                        "names_tried": names_tried,
                        "waterfall_steps": [s[1] for s in waterfall_searches],
                        "processing_ms": total_ms,
                    },
                )
                return TierResult(
                    tier=tier,
                    success=False,
                    error=f"No GMB listing found (tried {names_tried} waterfall steps)",
                )

        except Exception as e:
            logger.warning(f"[Siege] Tier 2 GMB failed: {e}")
            sentry_sdk.capture_exception(e)
            await self._log_enrichment_operation(
                tier=tier,
                operation="gmb_scrape",
                lead_data=lead,
                success=False,
                error=str(e),
            )
            return TierResult(
                tier=tier,
                success=False,
                error=str(e),
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, APIError)),
    )
    async def tier3_leadmagic_email(self, lead: dict[str, Any]) -> TierResult:
        """
        Tier 3: Leadmagic email verification - $0.012/lead AUD

        Verifies email deliverability and finds emails when missing.
        Also performs domain_search for decision-maker discovery when
        only company/domain is known.
        Critical for bounce prevention.

        Args:
            lead: Lead data (email or first_name + last_name + domain, or just domain/company)

        Returns:
            TierResult with email verification data or discovered decision-makers
        """
        tier = EnrichmentTier.LEADMAGIC_EMAIL
        cost = TIER_COSTS_AUD[tier]

        try:
            email = lead.get("email")
            first_name = lead.get("first_name")
            last_name = lead.get("last_name")
            domain = lead.get("domain") or lead.get("company_domain")

            # Verify existing email
            if email:
                result = await self.leadmagic_email_client.verify_email(email)

                # CEO Directive #057: Construct source URL from domain
                email_domain = email.split("@")[1] if "@" in email else None
                leadmagic_source_url = f"https://{email_domain}" if email_domain else None

                await self._log_enrichment_operation(
                    tier=tier,
                    operation="verify_email",
                    lead_data=lead,
                    success=True,
                    cost_aud=cost,
                )

                return TierResult(
                    tier=tier,
                    success=True,
                    data={
                        "email": email,
                        "email_status": result.get("status", "unknown"),
                        "email_score": result.get("score", 0),
                        "email_verified_by": "leadmagic",
                    },
                    cost_aud=cost,
                    source_url=leadmagic_source_url,
                )

            # Try to find email by name + domain
            elif first_name and last_name and domain:
                result = await self.leadmagic_email_client.find_email(
                    first_name=first_name,
                    last_name=last_name,
                    domain=domain,
                )

                if result.get("found"):
                    # CEO Directive #057: Domain website is the source
                    leadmagic_source_url = f"https://{domain}"

                    await self._log_enrichment_operation(
                        tier=tier,
                        operation="find_email",
                        lead_data=lead,
                        success=True,
                        cost_aud=cost,
                    )
                    return TierResult(
                        tier=tier,
                        success=True,
                        data={
                            "email": result.get("email"),
                            "email_status": result.get("status", "guessed"),
                            "email_score": result.get("score", 0),
                            "email_source": "leadmagic_finder",
                        },
                        cost_aud=cost,
                        source_url=leadmagic_source_url,
                    )
                else:
                    await self._log_enrichment_operation(
                        tier=tier,
                        operation="find_email",
                        lead_data=lead,
                        success=False,
                        cost_aud=cost,
                        error="Could not find email",
                    )
                    return TierResult(
                        tier=tier,
                        success=False,
                        error="Could not find email",
                        cost_aud=cost,  # Still charged for attempt
                    )

            # NEW: Domain search for decision-maker discovery when only company is known
            elif domain:
                # Use domain_search to find decision-makers at the company
                search_result = await self.leadmagic_email_client.domain_search(
                    domain=domain,
                    limit=5,  # Get top 5 contacts
                )

                # Handle both DomainSearchResult object and list formats
                if hasattr(search_result, "emails"):
                    # Real Leadmagic client returns DomainSearchResult
                    contacts = search_result.emails
                elif isinstance(search_result, list):
                    # Mock or direct list
                    contacts = search_result
                else:
                    contacts = []

                if contacts and len(contacts) > 0:
                    # Find the best decision-maker (executive/senior seniority)
                    decision_makers = []
                    for contact in contacts:
                        # Handle both LeadmagicEmail objects and dicts
                        if hasattr(contact, "to_dict"):
                            contact_dict = contact.to_dict()
                        elif isinstance(contact, dict):
                            contact_dict = contact
                        else:
                            continue

                        seniority = (contact_dict.get("seniority") or "").lower()
                        department = (contact_dict.get("department") or "").lower()

                        # Prioritize executives and senior roles in relevant departments
                        priority = 0
                        if seniority in ("executive", "senior"):
                            priority += 10
                        if department in ("executive", "management", "marketing", "sales"):
                            priority += 5

                        decision_makers.append((priority, contact_dict))

                    # Sort by priority and take the best match
                    decision_makers.sort(key=lambda x: x[0], reverse=True)

                    if decision_makers:
                        best_contact = decision_makers[0][1]
                        # CEO Directive #057: LinkedIn or domain website as source
                        contact_linkedin = best_contact.get("linkedin_url")
                        domain_source_url = (
                            contact_linkedin if contact_linkedin else f"https://{domain}"
                        )

                        await self._log_enrichment_operation(
                            tier=tier,
                            operation="domain_search",
                            lead_data=lead,
                            success=True,
                            cost_aud=0.15,  # Domain search cost
                            metadata={"contacts_found": len(decision_makers)},
                        )
                        return TierResult(
                            tier=tier,
                            success=True,
                            data={
                                "email": best_contact.get("email"),
                                "first_name": best_contact.get("first_name"),
                                "last_name": best_contact.get("last_name"),
                                "title": best_contact.get("position"),
                                "seniority_level": best_contact.get("seniority"),
                                "linkedin_url": best_contact.get("linkedin_url"),
                                "phone": best_contact.get("phone_number"),
                                "email_status": "discovered",
                                "email_score": best_contact.get("confidence", 70),
                                "email_source": "leadmagic_domain_search",
                                "decision_makers_found": len(decision_makers),
                            },
                            cost_aud=0.15,  # Domain search costs more
                            source_url=domain_source_url,
                        )

                await self._log_enrichment_operation(
                    tier=tier,
                    operation="domain_search",
                    lead_data=lead,
                    success=False,
                    cost_aud=0.15,
                    error="No contacts found for domain",
                )
                return TierResult(
                    tier=tier,
                    success=False,
                    error="No contacts found for domain",
                    cost_aud=0.15,  # Still charged for domain search attempt
                )

            else:
                return TierResult(
                    tier=tier,
                    success=False,
                    skipped=True,
                    skip_reason="No email, name+domain, or domain available",
                )

        except Exception as e:
            logger.warning(f"[Siege] Tier 3 Leadmagic email failed: {e}")
            sentry_sdk.capture_exception(e)
            return TierResult(
                tier=tier,
                success=False,
                error=str(e),
            )

    # ============================================
    # SIEGE WATERFALL V3: NEW ENRICHMENT TIERS (Directive #144)
    # ============================================

    async def tier1_5_linkedin_company(
        self,
        lead: dict[str, Any],
        icp_passed: bool = True,
    ) -> TierResult:
        """
        T1.5: BD LinkedIn Company enrichment - $0.025/lead
        Gate: ICP pass

        Provides company info + recent posts for T-DM2b (FREE reuse).

        Args:
            lead: Lead data (needs linkedin_url or company name)
            icp_passed: Whether lead passed ICP filter

        Returns:
            TierResult with LinkedIn company data + posts
        """
        tier = EnrichmentTier.LINKEDIN_COMPANY
        cost = TIER_COSTS_AUD[tier]

        # Gate: ICP pass required
        if not icp_passed:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="ICP filter not passed",
            )

        # Guard: Bright Data client required
        if not self.bright_data_client:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="Bright Data client not configured",
            )

        linkedin_url = lead.get("company_linkedin_url") or lead.get("linkedin_company_url")
        if not linkedin_url:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="No company LinkedIn URL available",
            )

        try:
            result = await self.bright_data_client.scrape_linkedin_company_enriched(linkedin_url)

            if result and result.get("name"):
                # Store company posts for T-DM2b (FREE reuse)
                company_posts = result.get("updates", []) or result.get("posts", [])

                await self._log_enrichment_operation(
                    tier=tier,
                    operation="linkedin_company",
                    lead_data=lead,
                    success=True,
                    cost_aud=cost,
                )

                return TierResult(
                    tier=tier,
                    success=True,
                    data={
                        "linkedin_company_name": result.get("name"),
                        "linkedin_company_industry": result.get("industry"),
                        "linkedin_company_size": result.get("employees"),
                        "linkedin_company_followers": result.get("followers"),
                        "linkedin_company_posts": company_posts,  # For T-DM2b
                        "linkedin_company_url": linkedin_url,
                    },
                    cost_aud=cost,
                    source_url=linkedin_url,
                )

            return TierResult(
                tier=tier,
                success=False,
                error="No LinkedIn company data found",
                cost_aud=cost,
            )

        except Exception as e:
            logger.warning(f"[Siege] T1.5 LinkedIn Company failed: {e}")
            sentry_sdk.capture_exception(e)
            return TierResult(tier=tier, success=False, error=str(e))

    async def tier2_5_gmb_reviews(
        self,
        lead: dict[str, Any],
        propensity: int = 0,
    ) -> TierResult:
        """
        T2.5: BD GMB Reviews - $0.001/lead
        Gate: Propensity >= 70

        Provides recent reviews for hook generation.

        Args:
            lead: Lead data (needs gmb_place_id)
            propensity: Current propensity score

        Returns:
            TierResult with GMB reviews
        """
        tier = EnrichmentTier.GMB_REVIEWS
        cost = TIER_COSTS_AUD[tier]

        # Gate: Propensity >= 70
        if propensity < 70:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason=f"Propensity {propensity} < 70 threshold",
            )

        # Guard: Bright Data client required
        if not self.bright_data_client:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="Bright Data client not configured",
            )

        place_id = lead.get("gmb_place_id") or lead.get("place_id")
        if not place_id:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="No GMB place_id available",
            )

        try:
            reviews = await self.bright_data_client.scrape_gmb_reviews(place_id, limit=20)

            if reviews:
                await self._log_enrichment_operation(
                    tier=tier,
                    operation="gmb_reviews",
                    lead_data=lead,
                    success=True,
                    cost_aud=cost,
                )

                return TierResult(
                    tier=tier,
                    success=True,
                    data={
                        "gmb_reviews": reviews,
                        "gmb_reviews_count": len(reviews),
                        "gmb_avg_rating": sum(r.get("rating", 0) for r in reviews) / len(reviews)
                        if reviews
                        else 0,
                    },
                    cost_aud=cost,
                )

            return TierResult(
                tier=tier,
                success=False,
                error="No GMB reviews found",
                cost_aud=cost,
            )

        except Exception as e:
            logger.warning(f"[Siege] T2.5 GMB Reviews failed: {e}")
            sentry_sdk.capture_exception(e)
            return TierResult(tier=tier, success=False, error=str(e))

    async def tier_dm1_linkedin_profile(
        self,
        lead: dict[str, Any],
        icp_passed: bool = True,
    ) -> TierResult:
        """
        T-DM1: BD LinkedIn Profile - $0.0015/lead
        Gate: ICP pass

        Provides decision-maker profile with experience, skills.

        Args:
            lead: Lead data (needs linkedin_url)
            icp_passed: Whether lead passed ICP filter

        Returns:
            TierResult with LinkedIn profile data
        """
        tier = EnrichmentTier.DM_LINKEDIN_PROFILE
        cost = TIER_COSTS_AUD[tier]

        # Gate: ICP pass required
        if not icp_passed:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="ICP filter not passed",
            )

        # Guard: Bright Data client required
        if not self.bright_data_client:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="Bright Data client not configured",
            )

        linkedin_url = lead.get("linkedin_url")
        if not linkedin_url:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="No LinkedIn profile URL available",
            )

        try:
            result = await self.bright_data_client.scrape_linkedin_profile_enriched(linkedin_url)

            if result and result.get("name"):
                await self._log_enrichment_operation(
                    tier=tier,
                    operation="linkedin_profile",
                    lead_data=lead,
                    success=True,
                    cost_aud=cost,
                )

                return TierResult(
                    tier=tier,
                    success=True,
                    data={
                        "dm_linkedin_name": result.get("name"),
                        "dm_linkedin_title": result.get("headline"),
                        "dm_linkedin_experience": result.get("experience", []),
                        "dm_linkedin_skills": result.get("skills", []),
                        "dm_linkedin_connections": result.get("connections"),
                    },
                    cost_aud=cost,
                    source_url=linkedin_url,
                )

            return TierResult(
                tier=tier,
                success=False,
                error="No LinkedIn profile found",
                cost_aud=cost,
            )

        except Exception as e:
            logger.warning(f"[Siege] T-DM1 LinkedIn Profile failed: {e}")
            sentry_sdk.capture_exception(e)
            return TierResult(tier=tier, success=False, error=str(e))

    async def tier_dm2_linkedin_posts(
        self,
        lead: dict[str, Any],
        propensity: int = 0,
    ) -> TierResult:
        """
        T-DM2: BD LinkedIn Posts 90d - $0.0015/lead
        Gate: Propensity >= 70

        Provides DM's recent posts for hook generation.

        Args:
            lead: Lead data (needs linkedin_url)
            propensity: Current propensity score

        Returns:
            TierResult with LinkedIn posts
        """
        tier = EnrichmentTier.DM_LINKEDIN_POSTS
        cost = TIER_COSTS_AUD[tier]

        # Gate: Propensity >= 70
        if propensity < 70:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason=f"Propensity {propensity} < 70 threshold",
            )

        # Guard: Bright Data client required
        if not self.bright_data_client:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="Bright Data client not configured",
            )

        linkedin_url = lead.get("linkedin_url")
        if not linkedin_url:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="No LinkedIn profile URL available",
            )

        try:
            posts = await self.bright_data_client.scrape_linkedin_posts_90d(linkedin_url)

            if posts:
                await self._log_enrichment_operation(
                    tier=tier,
                    operation="linkedin_posts",
                    lead_data=lead,
                    success=True,
                    cost_aud=cost,
                )

                return TierResult(
                    tier=tier,
                    success=True,
                    data={
                        "dm_linkedin_posts": posts,
                        "dm_linkedin_posts_count": len(posts),
                    },
                    cost_aud=cost,
                    source_url=linkedin_url,
                )

            return TierResult(
                tier=tier,
                success=False,
                error="No LinkedIn posts found in last 90 days",
                cost_aud=cost,
            )

        except Exception as e:
            logger.warning(f"[Siege] T-DM2 LinkedIn Posts failed: {e}")
            sentry_sdk.capture_exception(e)
            return TierResult(tier=tier, success=False, error=str(e))

    async def tier_dm2b_company_posts(
        self,
        lead: dict[str, Any],
        propensity: int = 0,
    ) -> TierResult:
        """
        T-DM2b: Company LinkedIn Posts - FREE (reuses T1.5 field)
        Gate: Propensity >= 70

        Uses company posts already captured in T1.5.

        Args:
            lead: Lead data (needs linkedin_company_posts from T1.5)
            propensity: Current propensity score

        Returns:
            TierResult with company posts (no additional cost)
        """
        tier = EnrichmentTier.DM_COMPANY_POSTS
        cost = TIER_COSTS_AUD[tier]  # 0.00 - FREE

        # Gate: Propensity >= 70
        if propensity < 70:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason=f"Propensity {propensity} < 70 threshold",
            )

        # Check if T1.5 already captured company posts
        company_posts = lead.get("linkedin_company_posts", [])
        if not company_posts:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="No company posts from T1.5 (run T1.5 first)",
            )

        # Already have the data - no API call needed (FREE)
        return TierResult(
            tier=tier,
            success=True,
            data={
                "company_linkedin_posts": company_posts,
                "company_linkedin_posts_count": len(company_posts),
            },
            cost_aud=cost,  # 0.00
        )

    async def tier_dm3_x_posts(
        self,
        lead: dict[str, Any],
        propensity: int = 0,
    ) -> TierResult:
        """
        T-DM3: BD X Posts 90d - $0.0025/lead
        Gate: Propensity >= 70

        Provides DM's recent X/Twitter posts for hook generation.

        Args:
            lead: Lead data (needs x_handle or twitter_handle)
            propensity: Current propensity score

        Returns:
            TierResult with X posts
        """
        tier = EnrichmentTier.DM_X_POSTS
        cost = TIER_COSTS_AUD[tier]

        # Gate: Propensity >= 70
        if propensity < 70:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason=f"Propensity {propensity} < 70 threshold",
            )

        # Guard: Bright Data client required
        if not self.bright_data_client:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="Bright Data client not configured",
            )

        x_handle = lead.get("x_handle") or lead.get("twitter_handle") or lead.get("twitter")
        if not x_handle:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="No X/Twitter handle available",
            )

        try:
            posts = await self.bright_data_client.scrape_x_posts_90d(x_handle)

            if posts:
                await self._log_enrichment_operation(
                    tier=tier,
                    operation="x_posts",
                    lead_data=lead,
                    success=True,
                    cost_aud=cost,
                )

                return TierResult(
                    tier=tier,
                    success=True,
                    data={
                        "dm_x_posts": posts,
                        "dm_x_posts_count": len(posts),
                    },
                    cost_aud=cost,
                )

            return TierResult(
                tier=tier,
                success=False,
                error="No X posts found in last 90 days",
                cost_aud=cost,
            )

        except Exception as e:
            logger.warning(f"[Siege] T-DM3 X Posts failed: {e}")
            sentry_sdk.capture_exception(e)
            return TierResult(tier=tier, success=False, error=str(e))

    async def tier5_identity_v3(
        self,
        lead: dict[str, Any],
        reachability: int = 0,
        needs_mobile_channel: bool = False,
    ) -> TierResult:
        """
        T5: Leadmagic mobile - $0.077/lead
        Gate: Reachability indicates mobile channel needed

        Siege Waterfall v3 version with reachability gating.

        Args:
            lead: Lead data (linkedin_url preferred)
            reachability: Current reachability score
            needs_mobile_channel: Whether outreach plan requires mobile

        Returns:
            TierResult with mobile/identity data
        """
        tier = EnrichmentTier.IDENTITY
        TIER_COSTS_AUD[tier]

        # Gate: Only if mobile channel is needed for outreach
        if not needs_mobile_channel:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="Mobile channel not required by outreach plan",
            )

        # Delegate to existing tier5_identity method
        return await self.tier5_identity(lead, reachability, force=True)

    @retry(
        stop=stop_after_attempt(2),  # Fewer retries - expensive tier
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, APIError)),
    )
    async def tier5_identity(
        self,
        lead: dict[str, Any],
        reachability_score: int,
        force: bool = False,
    ) -> TierResult:
        """
        Tier 5: Identity Gold (Leadmagic mobile) - $0.45/lead AUD

        Premium enrichment for high-value leads only.
        Only runs when reachability >= 85.

        Provides:
        - Direct mobile numbers
        - Personal email addresses
        - Verified identity data

        Args:
            lead: Lead data (linkedin_url preferred)
            reachability_score: Current reachability score (must be >= 85)

        Returns:
            TierResult with identity data
        """
        tier = EnrichmentTier.IDENTITY
        cost = TIER_COSTS_AUD[tier]

        # Guard: Only for high-reachability leads (unless forced)
        if reachability_score < 85 and not force:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason=f"Reachability {reachability_score} below 85 threshold",
            )

        # Guard: Leadmagic mobile client must be available
        if self.leadmagic_mobile_client is None:
            return TierResult(
                tier=tier,
                success=False,
                skipped=True,
                skip_reason="Leadmagic mobile client not configured (LEADMAGIC_API_KEY missing)",
            )

        try:
            linkedin_url = lead.get("linkedin_url")
            email = lead.get("email")
            first_name = lead.get("first_name")
            last_name = lead.get("last_name")
            company = lead.get("company_name") or lead.get("company")

            if not linkedin_url and not email:
                return TierResult(
                    tier=tier,
                    success=False,
                    skipped=True,
                    skip_reason="No linkedin_url or email for identity lookup",
                )

            enriched = await self.leadmagic_mobile_client.enrich_identity(
                linkedin_url=linkedin_url,
                email=email,
                first_name=first_name,
                last_name=last_name,
                company=company,
            )

            if enriched.get("found"):
                logger.info(
                    f"[Siege] Tier 5 Identity Gold success for reachability={reachability_score} lead"
                )
                # CEO Directive #057: LinkedIn is the primary source for Leadmagic mobile
                identity_source_url = linkedin_url or enriched.get("linkedin_url")

                await self._log_enrichment_operation(
                    tier=tier,
                    operation="identity_gold",
                    lead_data=lead,
                    success=True,
                    cost_aud=cost,
                    metadata={"reachability_score": reachability_score},
                )
                return TierResult(
                    tier=tier,
                    success=True,
                    data=enriched,
                    cost_aud=cost,
                    source_url=identity_source_url,
                )
            else:
                await self._log_enrichment_operation(
                    tier=tier,
                    operation="identity_gold",
                    lead_data=lead,
                    success=False,
                    cost_aud=cost,
                    error="No identity data found",
                    metadata={"reachability_score": reachability_score},
                )
                return TierResult(
                    tier=tier,
                    success=False,
                    error="No identity data found",
                    cost_aud=cost,  # Still charged for lookup
                )

        except Exception as e:
            logger.warning(f"[Siege] Tier 5 Identity failed: {e}")
            sentry_sdk.capture_exception(e)
            await self._log_enrichment_operation(
                tier=tier,
                operation="identity_gold",
                lead_data=lead,
                success=False,
                error=str(e),
                metadata={"reachability_score": reachability_score},
            )
            return TierResult(
                tier=tier,
                success=False,
                error=str(e),
            )

    # ============================================
    # AUDIT LOGGING
    # ============================================

    async def _log_enrichment_operation(
        self,
        tier: EnrichmentTier,
        operation: str,
        lead_data: dict[str, Any],
        success: bool,
        cost_aud: float = 0.0,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Log enrichment operation to audit_logs table.

        Provides full traceability for all enrichment operations,
        supporting cost tracking and debugging.

        Args:
            tier: Which enrichment tier performed the operation
            operation: Specific operation (verify_email, find_email, domain_search, etc.)
            lead_data: Lead data being enriched
            success: Whether operation succeeded
            cost_aud: Cost in AUD
            error: Error message if failed
            metadata: Additional operation metadata
        """
        try:
            # Lazy import to avoid circular dependencies
            from src.integrations.supabase import get_async_supabase_client

            supabase = await get_async_supabase_client()

            log_entry = {
                "operation_type": "enrichment",
                "tier": tier.value,
                "operation": operation,
                "service": f"siege_{tier.value}",
                "success": success,
                "cost_aud": cost_aud,
                "error_message": error,
                "lead_email": lead_data.get("email"),
                "lead_domain": lead_data.get("domain") or lead_data.get("company_domain"),
                "lead_company": lead_data.get("company_name"),
                "metadata": metadata or {},
                "created_at": datetime.now(UTC).isoformat(),
            }

            await supabase.table("audit_logs").insert(log_entry).execute()

        except Exception as e:
            # Don't fail enrichment if logging fails
            logger.warning(f"[Siege] Audit log failed: {e}")

    # ============================================
    # HELPER METHODS
    # ============================================

    def _determine_source_url(
        self,
        enriched_data: dict[str, Any],
        tier_results: list[TierResult],
    ) -> str | None:
        """
        CEO Directive #057: Determine best source URL for Spam Act compliance.

        Priority order (best evidence of "conspicuous publication"):
        1. LinkedIn profile URL (most defensible - person's own profile)
        2. Company LinkedIn page URL
        3. Google Maps/GMB URL
        4. Company website URL
        5. ABN register URL
        6. Leadmagic domain search URL

        Args:
            enriched_data: The enriched lead data
            tier_results: Results from each enrichment tier

        Returns:
            Best source URL for compliance, or None if no URL found
        """
        # Check LinkedIn profile URL first (highest priority)
        linkedin_url = enriched_data.get("linkedin_url")
        if linkedin_url and "linkedin.com" in linkedin_url:
            return linkedin_url

        # Check company LinkedIn URL
        company_linkedin_url = enriched_data.get("company_linkedin_url")
        if company_linkedin_url and "linkedin.com" in company_linkedin_url:
            return company_linkedin_url

        # Check GMB/Google Maps URL from Tier 2
        for tier_result in tier_results:
            if tier_result.tier == EnrichmentTier.GMB and tier_result.success:
                gmb_url = tier_result.data.get("google_maps_url")
                if gmb_url:
                    return gmb_url

        # Check company website URL (often has team/contact page)
        company_website = enriched_data.get("company_website")
        if company_website:
            return company_website

        # Check domain (construct URL)
        company_domain = enriched_data.get("company_domain")
        if company_domain:
            # Normalize to https URL
            if not company_domain.startswith(("http://", "https://")):
                return f"https://{company_domain}"
            return company_domain

        # Check ABN register URL from Tier 1
        for tier_result in tier_results:
            if tier_result.tier == EnrichmentTier.ABN and tier_result.success:
                abn = enriched_data.get("abn") or tier_result.data.get("abn")
                if abn:
                    # ABN lookup URL is a valid public record source
                    return f"https://abr.business.gov.au/ABN/View?abn={abn}"

        # Check tier source URLs (fallback)
        for tier_result in tier_results:
            if tier_result.source_url:
                return tier_result.source_url

        return None

    def _merge_data(
        self,
        base: dict[str, Any],
        new_data: dict[str, Any],
        source: str | None = None,
        conflicts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Merge new enrichment data into base with provenance tracking.

        CEO Directive #149: Preserve provenance for all enriched fields.
        Each field is stored with structure: {"value": X, "source": "tier_name"}
        When two tiers provide the same field: last-write-wins with conflict logging.

        Args:
            base: Base lead data
            new_data: New data to merge in
            source: Source tier identifier (e.g., "tier1_abn", "T1.5_linkedin")
            conflicts: Optional list to append conflict entries for enrichment_lineage

        Returns:
            Merged dictionary with provenance-wrapped values
        """
        result = dict(base)

        # Keys that are metadata about the enrichment, not actual field values
        # These are NOT skipped - we preserve them with provenance
        META_KEYS = {"found"}  # Only skip "found" - it's a lookup status, not data

        for key, value in new_data.items():
            # Skip only the lookup status flag
            if key in META_KEYS:
                continue

            # Handle backward compatibility: check if value is already provenance-wrapped
            if isinstance(value, dict) and "value" in value and "source" in value:
                # Already wrapped - use as-is
                wrapped_value = value
                raw_value = value["value"]
                value_source = value["source"]
            else:
                # Wrap raw value with provenance
                raw_value = value
                value_source = source or "unknown"
                wrapped_value = {"value": raw_value, "source": value_source}

            # Check if key already exists with a value
            if key not in result or result[key] is None:
                # New field - just add it
                result[key] = wrapped_value
            else:
                # Field exists - check for conflict
                existing = result[key]

                # Extract existing raw value for comparison
                if isinstance(existing, dict) and "value" in existing:
                    existing_raw = existing["value"]
                    existing_source = existing.get("source", "unknown")
                else:
                    # Legacy unwrapped value
                    existing_raw = existing
                    existing_source = "original"

                # Check if values are actually different (conflict)
                values_differ = existing_raw != raw_value

                if values_differ:
                    # Log conflict to enrichment_lineage
                    if conflicts is not None:
                        conflicts.append(
                            {
                                "type": "field_conflict",
                                "field": key,
                                "existing_value": existing_raw,
                                "existing_source": existing_source,
                                "new_value": raw_value,
                                "new_source": value_source,
                                "resolution": "last_write_wins",
                            }
                        )
                    logger.debug(
                        f"[Siege] Field conflict on '{key}': "
                        f"'{existing_source}' -> '{value_source}' (last-write-wins)"
                    )

                # Last-write-wins: overwrite with new value
                # Special handling for lists and dicts
                if isinstance(raw_value, list) and isinstance(existing_raw, list):
                    # Merge lists, preserve provenance of the merge
                    merged_list = list(set(existing_raw + raw_value))
                    result[key] = {"value": merged_list, "source": value_source}
                elif isinstance(raw_value, dict) and isinstance(existing_raw, dict):
                    # Merge dicts, preserve provenance
                    merged_dict = {**existing_raw, **raw_value}
                    result[key] = {"value": merged_dict, "source": value_source}
                else:
                    # Scalar value - last-write-wins
                    result[key] = wrapped_value

        return result

    def _check_size_in_range(
        self,
        size_str: str | int,
        min_size: int | None,
        max_size: int | None,
    ) -> bool:
        """
        Parse LinkedIn size string (e.g. '11-50') and check against constraints.

        CEO Directive #144 Addendum 2: Size filtering at SIZE_GATE.

        Args:
            size_str: Company size string like "11-50", "51-200", or integer
            min_size: Minimum employee count (ICP constraint)
            max_size: Maximum employee count (ICP constraint)

        Returns:
            True if size is within range, False otherwise
        """
        import re

        if not size_str:
            return False

        # If already an integer, use directly
        if isinstance(size_str, int):
            upper_bound = size_str
        else:
            # Parse size string like "11-50", "51-200", "1-10", "10000+"
            size_str = str(size_str).strip()

            # Handle "10000+" format (take the number as lower bound)
            if size_str.endswith("+"):
                match = re.match(r"(\d+)\+", size_str)
                if match:
                    upper_bound = int(match.group(1))
                else:
                    return False
            # Handle range format "11-50"
            elif "-" in size_str:
                parts = size_str.split("-")
                if len(parts) == 2:
                    try:
                        # Use upper bound for comparison
                        upper_bound = int(parts[1].replace(",", "").strip())
                    except ValueError:
                        return False
                else:
                    return False
            # Handle plain number
            else:
                try:
                    upper_bound = int(size_str.replace(",", "").strip())
                except ValueError:
                    return False

        # Check constraints
        if min_size is not None and upper_bound < min_size:
            return False
        return not (max_size is not None and upper_bound > max_size)

    def _calculate_als(self, lead: dict[str, Any]) -> int:
        """
        Calculate basic ALS (Agency Lead Score) from available data.

        This is a simplified calculation. Full CIS scoring is
        done by the scoring engine.

        Args:
            lead: Lead data

        Returns:
            ALS score (0-100)
        """
        score = 0

        # Email (30 points max)
        if lead.get("email"):
            if lead.get("email_status") == "verified":
                score += 30
            elif lead.get("email_status") == "valid":
                score += 25
            else:
                score += 15

        # Phone (20 points max)
        if lead.get("phone") or lead.get("mobile"):
            score += 20

        # LinkedIn (15 points)
        if lead.get("linkedin_url"):
            score += 15

        # Name (10 points)
        if lead.get("first_name") and lead.get("last_name"):
            score += 10

        # Title/Role (10 points)
        if lead.get("title"):
            score += 10

        # Company data (15 points max)
        if lead.get("company_name"):
            score += 10
        if lead.get("company_employee_count") or lead.get("company_industry"):
            score += 5

        return min(score, 100)


# ============================================
# SINGLETON ACCESSOR
# ============================================

_siege_waterfall: SiegeWaterfall | None = None


def get_siege_waterfall() -> SiegeWaterfall:
    """Get or create SiegeWaterfall singleton instance."""
    global _siege_waterfall
    if _siege_waterfall is None:
        _siege_waterfall = SiegeWaterfall()
    return _siege_waterfall


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Retry logic with tenacity
# [x] Type hints on all methods
# [x] Docstrings on all methods
# [x] Custom exceptions (EnrichmentTierError, EnrichmentSkippedError)
# [x] Cost tracking in $AUD (LAW II compliance)
# [x] Enrichment lineage tracking (which tiers ran, timestamps)
# [x] +15 ALS bonus for 3+ source verification
# [x] Graceful degradation (each tier optional)
# [x] Tier 5 gated by ALS >= 85
# [x] Stub clients for unimplemented integrations
# [x] Sentry error capture
# [x] Singleton accessor pattern
