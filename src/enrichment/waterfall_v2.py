"""
FILE: src/enrichment/waterfall_v2.py
PURPOSE: Full Phase 1→2→3 pipeline for Waterfall v2
PHASE: SIEGE (CEO Directive #023)
TASK: Waterfall v2 Pipeline Implementation
DEPENDENCIES:
  - src/enrichment/discovery_modes.py
  - src/integrations/bright_data_client.py (TBD)
  - src/integrations/abn_client.py
  - src/integrations/leadmagic.py
  - src/config/settings.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - LAW II: All costs in $AUD

WATERFALL V2 PIPELINE:
  PHASE 1: Discovery (Mode A/B/C) - Variable cost depending on mode
  PHASE 2: Enrichment (Tiers 1 → 5) - Tiered cost structure with gates
  PHASE 3: Scoring (ALS) - Agency Lead Score calculation with quality gates

  Cost Structure (AUD):
    Tier 1: ABN API - FREE
    Tier 1.5a: SERP Google Maps - $0.0015
    Tier 1.5b: SERP LinkedIn Discovery - $0.0015
    Tier 2: LinkedIn Company Scraper - $0.0015
    Tier 2.5: LinkedIn People Profile - $0.0015 (ALS >= 35)
    Tier 3: Leadmagic Email Finder - $0.015 (ALS >= 35)
    Tier 5: Leadmagic Mobile Finder - $0.077 (ALS >= 85)

  NOTE: Leadmagic replaces Hunter (T3) and Kaspr (T5) per CEO decision.
        If credits exhausted, raises LeadmagicCreditExhaustedError (hard fail).
        Use LEADMAGIC_MOCK=true for testing without credits.

Created: 2026-02-16 by subagent (CEO Directive #023)
Updated: 2026-02-25 - Leadmagic migration (CEO Directive)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from src.enrichment.discovery_modes import (
    CampaignConfig,
    DiscoveryMode,
    DiscoveryRecord,
    MapsFirstDiscovery,
    ParallelDiscovery,
)
from src.integrations.leadmagic import (
    LeadmagicCreditExhaustedError,
    LeadmagicNoPlanError,
)

logger = structlog.get_logger()


@dataclass
class LeadRecord:
    """Unified lead record through the waterfall pipeline"""

    # Core identifiers
    id: str = None
    abn: str = None
    business_name: str = None
    legal_name: str = None
    trading_name: str = None
    discovery_source: str = None

    # ABN Registry fields (Tier 1)
    gst_registered: bool = False
    entity_type: str = None
    state: str = None
    acn: str = None

    # GMB fields (Tier 1.5a)
    phone: str = None
    website: str = None
    address: str = None
    rating: float = None
    reviews_count: int = None
    category: str = None
    gmb_place_id: str = None

    # LinkedIn Company fields (Tier 1.5b + 2)
    linkedin_company_url: str = None
    linkedin_data: dict = field(default_factory=dict)
    employees: list[dict] = field(default_factory=list)
    decision_makers: list[dict] = field(default_factory=list)
    company_size: str = None
    industry: str = None
    founded: int = None
    headquarters: str = None
    specialties: str = None

    # Contact enrichment fields (Tier 2.5 + 3 + 5)
    email: str = None
    email_confidence: float = None
    direct_mobile: str = None
    contact_source: str = None

    # Leadmagic Premium fields (Tier 5)
    leadmagic_data: dict = field(default_factory=dict)
    verified_contacts: list[dict] = field(default_factory=dict)

    # Scoring and quality
    propensity_score: int = 0
    als_breakdown: dict = field(default_factory=dict)
    confidence_score: float = 0.0

    # Tracking and metadata
    enrichment_tiers_completed: list[str] = field(default_factory=list)
    cost_aud: float = 0.0
    discovery_source: str = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    # Error tracking
    enrichment_errors: list[dict] = field(default_factory=list)


class WaterfallV2:
    """
    Siege Waterfall v2 — Full enrichment pipeline

    PHASE 1: Discovery (Mode A/B/C)
    PHASE 2: Enrichment (Tiers 1 → 5, with gates)
    PHASE 3: Scoring (ALS)

    Quality Gates:
    - PRE_ALS_GATE: Minimum score to continue past Tier 2 (cost control)
    - HOT_THRESHOLD: Minimum score for Tier 5 Leadmagic mobile enrichment (premium leads only)

    Enrichment Providers:
    - Tier 3 (Email): Leadmagic email finder ($0.015 AUD, ALS >= 35)
    - Tier 5 (Mobile): Leadmagic mobile finder ($0.077 AUD, ALS >= 85)

    Error Handling:
    - LeadmagicCreditExhaustedError: Hard fail, do not silently skip
    - LeadmagicNoPlanError: Hard fail, do not silently skip
    """

    PRE_ALS_GATE = 20  # Minimum score for premium enrichment (T2.5, T3) - lowered to allow leads with GMB data
    HOT_THRESHOLD = 85  # Minimum for Tier 5 (Leadmagic mobile)

    # Cost constants (AUD) - Updated for Leadmagic
    COSTS = {
        "serp_maps": 0.0015,
        "serp_linkedin": 0.0015,
        "linkedin_company": 0.0015,
        "linkedin_people": 0.0015,
        "leadmagic_email": 0.015,  # T3: Leadmagic email finder (replaces Hunter $0.012)
        "leadmagic_mobile": 0.077,  # T5: Leadmagic mobile finder (replaces Kaspr $0.45)
    }

    def __init__(self, bright_data_client=None, abn_client=None, leadmagic_client=None):
        """
        Initialize waterfall with all integration clients.

        Args:
            bright_data_client: Bright Data client for SERP and LinkedIn scraping
            abn_client: ABN Lookup client for Tier 1
            leadmagic_client: Leadmagic client for T3 email + T5 mobile enrichment
        """
        self.bd = bright_data_client
        self.abn_client = abn_client
        self.leadmagic = leadmagic_client

        # Initialize discovery engines
        # ABNFirstDiscovery deprecated per Waterfall v3 Decision #1 (2026-03-01)
        self.maps_discovery = MapsFirstDiscovery(
            bright_data_client=bright_data_client, abn_client=abn_client
        )
        self.parallel_discovery = ParallelDiscovery(
            abn_client=abn_client, bright_data_client=bright_data_client
        )

    # PHASE 1: DISCOVERY

    async def run_discovery(self, config: CampaignConfig) -> list[LeadRecord]:
        """PHASE 1: Run discovery mode based on campaign config"""
        logger.info(f"Phase 1: Starting discovery with mode={config.mode.value}")

        try:
            # Select discovery engine based on mode
            # ABN_FIRST deprecated per Waterfall v3 Decision #1 (2026-03-01)
            if config.mode == DiscoveryMode.MAPS_FIRST:
                discovery_records = await self.maps_discovery.discover(config)
            elif config.mode == DiscoveryMode.PARALLEL:
                discovery_records = await self.parallel_discovery.discover(config)
            else:
                raise ValueError(f"Unknown discovery mode: {config.mode}")

            # Convert DiscoveryRecord to LeadRecord
            leads = []
            for record in discovery_records:
                lead = self._convert_discovery_to_lead(record)
                leads.append(lead)

            logger.info(f"Phase 1 completed: {len(leads)} leads discovered")
            return leads

        except Exception as e:
            logger.error(f"Phase 1 discovery failed: {str(e)}")
            return []

    def _convert_discovery_to_lead(self, record: DiscoveryRecord) -> LeadRecord:
        """Convert DiscoveryRecord to LeadRecord for enrichment pipeline"""
        lead = LeadRecord(
            id=f"lead_{record.abn or hash(record.business_name)}",
            abn=record.abn,
            business_name=record.business_name,
            legal_name=record.legal_name,
            gst_registered=record.gst_registered,
            entity_type=record.entity_type,
            state=record.state,
            phone=record.phone,
            website=record.website,
            address=record.address,
            rating=record.rating,
            reviews_count=record.reviews_count,
            category=record.category,
            gmb_place_id=record.gmb_place_id,
            confidence_score=record.confidence_score,
            discovery_source=record.discovery_source,
        )

        # Set initial tiers as completed based on discovery source
        if record.discovery_source == "abn_api":
            lead.enrichment_tiers_completed = ["tier_1"]
        elif record.discovery_source == "google_maps" or record.discovery_source == "both":
            lead.enrichment_tiers_completed = ["tier_1", "tier_1_5a"]
            lead.cost_aud += self.COSTS["serp_maps"]

        return lead

    # PHASE 2: ENRICHMENT TIERS

    async def enrich_tier_1(self, lead: LeadRecord) -> LeadRecord:
        """Tier 1: ABN API - FREE - Always runs (if not from discovery)"""
        if "tier_1" in lead.enrichment_tiers_completed:
            logger.debug(f"Tier 1 already completed for {lead.id}")
            return lead

        logger.debug(f"Tier 1: ABN enrichment for {lead.business_name}")

        try:
            if not self.abn_client:
                raise ValueError("ABN client not configured")

            # Search ABN by business name if no ABN
            if not lead.abn and lead.business_name:
                abn_results = await self.abn_client.search_by_name_advanced(
                    name=lead.business_name, state=lead.state, isCurrentIndicator="Y"
                )

                if abn_results:
                    best_match = abn_results[0]  # Take first result for now
                    lead.abn = best_match.get("abn")
                    lead.legal_name = best_match.get("legalName")
                    lead.gst_registered = best_match.get("gstRegistered", False)
                    lead.entity_type = best_match.get("entityType")
                    lead.state = best_match.get("state")

            lead.enrichment_tiers_completed.append("tier_1")
            logger.debug(f"Tier 1 completed for {lead.id}")

        except Exception as e:
            error = {"tier": "tier_1", "error": str(e), "timestamp": datetime.now(UTC).isoformat()}
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 1 failed for {lead.id}: {str(e)}")

        return lead

    async def enrich_tier_1_25(self, lead: LeadRecord) -> LeadRecord:
        """
        Tier 1.25: ABR Entity Lookup - FREE - Get trading name for ABN-sourced leads.
        
        Only runs for ABN-sourced leads. Maps SERP leads already have real names.
        SDK disambiguation used when ABR returns no trading name and legal name
        ends with "Pty Ltd" (indicates company, not trading name).
        """
        if "tier_1_25" in lead.enrichment_tiers_completed:
            return lead

        # Only run for ABN-sourced leads that have an ABN
        if lead.discovery_source not in ("abn_api", "abn_lookup") or not lead.abn:
            lead.enrichment_tiers_completed.append("tier_1_25")
            return lead

        logger.debug(f"Tier 1.25: ABR entity lookup for {lead.business_name} ({lead.abn})")

        try:
            if not self.abn_client:
                raise ValueError("ABN client not configured")

            # Lookup full entity details by ABN
            entity_data = await self.abn_client.search_by_abn(lead.abn)

            if entity_data and entity_data.get("found"):
                # Set legal name (entity/company name)
                lead.legal_name = entity_data.get("business_name")

                # Set trading name: prefer trading_name, then first business_name, fallback to legal
                trading = entity_data.get("trading_name")
                business_names = entity_data.get("business_names") or []

                if trading:
                    lead.trading_name = trading
                elif business_names:
                    lead.trading_name = business_names[0]
                else:
                    lead.trading_name = lead.legal_name

                # Update other ABN fields if available
                if entity_data.get("gst_registered") is not None:
                    lead.gst_registered = entity_data.get("gst_registered")
                if entity_data.get("entity_type"):
                    lead.entity_type = entity_data.get("entity_type")

                logger.info(
                    f"Tier 1.25: Found trading_name='{lead.trading_name}' "
                    f"legal_name='{lead.legal_name}' for ABN {lead.abn}"
                )

                # SDK disambiguation: if trading_name == legal_name AND looks like company name
                if (
                    lead.trading_name == lead.legal_name
                    and lead.legal_name
                    and any(
                        lead.legal_name.upper().endswith(suffix)
                        for suffix in ("PTY LTD", "PTY LIMITED", "PTY. LTD.", "PTY. LIMITED")
                    )
                ):
                    # Try SDK disambiguation
                    try:
                        sdk_trading = await self._sdk_disambiguate_trading_name(lead)
                        if sdk_trading and sdk_trading != lead.legal_name:
                            lead.trading_name = sdk_trading
                            logger.info(f"Tier 1.25: SDK disambiguated to '{sdk_trading}'")
                    except Exception as sdk_err:
                        logger.warning(f"SDK disambiguation failed: {sdk_err}")

            lead.enrichment_tiers_completed.append("tier_1_25")

            # Write audit log
            if self.supabase:
                await self._log_enrichment(
                    lead,
                    "tier_1_25_complete",
                    {
                        "abn": lead.abn,
                        "trading_name": lead.trading_name,
                        "legal_name": lead.legal_name,
                        "business_name": lead.business_name,
                        "source": lead.discovery_source,
                    },
                )

            logger.debug(f"Tier 1.25 completed for {lead.id}")

        except Exception as e:
            error = {
                "tier": "tier_1_25",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 1.25 failed for {lead.id}: {str(e)}")

        return lead

    async def _sdk_disambiguate_trading_name(self, lead: LeadRecord) -> str | None:
        """
        Use SDK to disambiguate trading name when ABR returns only legal name.
        
        Cost: ~$0.01 per call (Haiku)
        Returns: Trading name string or None
        """
        from src.integrations.sdk_brain import get_simple_client

        client = get_simple_client("classification")

        prompt = f"""What is the likely trading name for this Australian business?

Legal Name: {lead.legal_name}
State: {lead.state or 'Unknown'}
Industry: {lead.category or lead.industry or 'Unknown'}

Return ONLY the trading name, no explanation. 
If the trading name is likely the same as the legal name (minus Pty Ltd suffix), return just the company name without the suffix.
If truly unknown, return the legal name without the Pty Ltd suffix."""

        result = await client.complete(
            prompt=prompt,
            system="You are a business name expert. Return only the trading name, nothing else.",
            max_tokens=50,
            temperature=0.3,
        )

        trading_name = result.get("content", "").strip()
        cost = result.get("cost_aud", 0)

        # Log SDK usage
        if self.supabase and cost > 0:
            await self._log_enrichment(
                lead,
                "tier_1_25_sdk_used",
                {"cost_aud": cost, "result": trading_name},
            )

        return trading_name if trading_name else None

    def _validate_au_nz_headquarters(self, headquarters: str | None) -> tuple[bool, str]:
        """
        Validate that headquarters location is in Australia or New Zealand.
        
        Returns:
            tuple[bool, str]: (is_valid, reason)
            - is_valid: True if AU/NZ location or empty (allow through)
            - reason: Description of validation result
        """
        if not headquarters:
            return True, "empty_headquarters"
        
        hq_lower = headquarters.lower()
        
        # AU indicators (case-insensitive)
        au_indicators = [
            # Country
            "australia",
            # States (check as word boundaries to avoid false matches)
            " nsw", ",nsw", " vic", ",vic", " qld", ",qld",
            " wa,", " wa ", ",wa,", " sa,", " sa ", ",sa,",
            " tas", ",tas", " act", ",act", " nt,", " nt ", ",nt,",
            "new south wales", "victoria", "queensland",
            "western australia", "south australia", "tasmania",
            "australian capital territory", "northern territory",
            # Major cities
            "sydney", "melbourne", "brisbane", "perth", "adelaide",
            "canberra", "darwin", "hobart", "gold coast", "newcastle",
            "wollongong", "geelong", "townsville", "cairns",
        ]
        
        # NZ indicators
        nz_indicators = [
            "new zealand", "auckland", "wellington", "christchurch",
            "hamilton", "tauranga", "dunedin",
        ]
        
        # Check AU indicators
        for indicator in au_indicators:
            if indicator in hq_lower:
                return True, f"au_match:{indicator}"
        
        # Check for standalone "AU" (word boundary)
        import re
        if re.search(r'\bau\b', hq_lower):
            return True, "au_match:AU"
        
        # Check NZ indicators  
        for indicator in nz_indicators:
            if indicator in hq_lower:
                return True, f"nz_match:{indicator}"
        
        # Check for standalone "NZ" (word boundary)
        if re.search(r'\bnz\b', hq_lower):
            return True, "nz_match:NZ"
        
        return False, f"no_au_nz_match:{headquarters}"

    async def enrich_tier_1_5a(self, lead: LeadRecord) -> LeadRecord:
        """Tier 1.5a: SERP Google Maps - $0.0015 - If missing phone/website"""
        if "tier_1_5a" in lead.enrichment_tiers_completed:
            return lead

        # Skip if we already have phone and website
        if lead.phone and lead.website:
            lead.enrichment_tiers_completed.append("tier_1_5a")
            return lead

        # Prefer trading name over legal/entity name for GMB search
        search_name = lead.trading_name or lead.business_name or ""
        logger.debug(f"Tier 1.5a: Google Maps enrichment for {search_name}")

        try:
            if not self.bd:
                raise ValueError("Bright Data client not configured")

            # Search Google Maps for business - use trading name if available
            search_query = search_name
            location = lead.address or lead.state or "Australia"
            gmb_results = await self.bd.search_google_maps(
                query=search_query.strip(),
                location=location.strip(),
                max_results=5
            )

            if gmb_results:
                # Take best match (first result for now)
                gmb_data = gmb_results[0]

                # Fill missing fields
                if not lead.phone:
                    lead.phone = gmb_data.get("phone")
                if not lead.website:
                    lead.website = gmb_data.get("website")
                if not lead.address:
                    lead.address = gmb_data.get("address")
                if not lead.rating:
                    lead.rating = gmb_data.get("rating")
                if not lead.reviews_count:
                    lead.reviews_count = gmb_data.get("reviews_count")
                if not lead.category:
                    lead.category = gmb_data.get("category")
                if not lead.gmb_place_id:
                    lead.gmb_place_id = gmb_data.get("place_id")

            lead.enrichment_tiers_completed.append("tier_1_5a")
            lead.cost_aud += self.COSTS["serp_maps"]
            logger.debug(f"Tier 1.5a completed for {lead.id}")

        except Exception as e:
            error = {
                "tier": "tier_1_5a",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 1.5a failed for {lead.id}: {str(e)}")

        return lead

    async def enrich_tier_1_5b(self, lead: LeadRecord) -> LeadRecord:
        """Tier 1.5b: SERP Google LinkedIn Discovery - $0.0015 - Find LinkedIn URL"""
        if "tier_1_5b" in lead.enrichment_tiers_completed:
            return lead

        # Prefer trading name over legal/entity name for LinkedIn search
        search_name = lead.trading_name or lead.business_name or ""
        logger.debug(f"Tier 1.5b: LinkedIn URL discovery for {search_name}")

        try:
            if not self.bd:
                raise ValueError("Bright Data client not configured")

            # Search LinkedIn company URL via SERP - use trading name if available
            search_query = f'site:linkedin.com/company "{search_name}" {lead.address or lead.state or ""}'

            serp_results = await self.bd.search_google(query=search_query.strip(), max_results=10)

            if serp_results:
                # Find LinkedIn company URL in results
                for result in serp_results:
                    url = result.get("link") or result.get("url", "")
                    if "linkedin.com/company/" in url and not url.endswith("/jobs"):
                        lead.linkedin_company_url = url
                        break

            lead.enrichment_tiers_completed.append("tier_1_5b")
            lead.cost_aud += self.COSTS["serp_linkedin"]
            logger.debug(f"Tier 1.5b completed for {lead.id}")

        except Exception as e:
            error = {
                "tier": "tier_1_5b",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 1.5b failed for {lead.id}: {str(e)}")

        return lead

    async def enrich_tier_2(self, lead: LeadRecord) -> LeadRecord:
        """Tier 2: LinkedIn Company Scraper - $0.0015 - If LinkedIn URL found"""
        if "tier_2" in lead.enrichment_tiers_completed:
            return lead

        if not lead.linkedin_company_url:
            # Skip tier 2 if no LinkedIn URL found
            lead.enrichment_tiers_completed.append("tier_2")
            return lead

        logger.debug(f"Tier 2: LinkedIn company scraping for {lead.business_name}")

        try:
            if not self.bd:
                raise ValueError("Bright Data client not configured")

            # Scrape LinkedIn company page
            linkedin_data = await self.bd.scrape_linkedin_company(lead.linkedin_company_url)

            # Geo-validation: Ensure company is in AU/NZ (CEO Directive #168)
            geo_validated = False
            returned_location = None
            if linkedin_data:
                returned_location = linkedin_data.get("headquarters")
                geo_valid, geo_reason = self._validate_au_nz_headquarters(returned_location)
                
                if not returned_location:
                    logger.warning(f"Tier 2 geo-validation: empty headquarters for {lead.id}, allowing through")
                    geo_validated = True  # Allow empty through
                elif geo_valid:
                    geo_validated = True
                else:
                    logger.warning(f"Tier 2 geo-validation failed for {lead.id}: expected AU/NZ, got headquarters={returned_location}")
                    geo_validated = False

            if linkedin_data and geo_validated:
                lead.linkedin_data = linkedin_data

                # Update business_name from LinkedIn company name if available
                # This fixes truncated names from Maps SERP (e.g., "MARKETING" -> "Bright Valley Marketing")
                linkedin_name = linkedin_data.get("name")
                if linkedin_name and len(linkedin_name) > len(lead.business_name or ""):
                    lead.business_name = linkedin_name

                # Extract key fields
                lead.company_size = linkedin_data.get("company_size")
                lead.industry = linkedin_data.get("industries")
                lead.founded = linkedin_data.get("founded")
                lead.headquarters = linkedin_data.get("headquarters")
                lead.specialties = linkedin_data.get("specialties")

                # Extract website from LinkedIn if not already set
                if not lead.website:
                    lead.website = linkedin_data.get("website")

                # Store employees for T2.5 to process (T2.5 scrapes profiles to get real job titles)
                employees = linkedin_data.get("employees", [])
                if employees:
                    lead.employees = employees[:5]  # Store top 5 for T2.5 to filter

            # Always mark tier complete and add cost (we paid for the API call)
            lead.enrichment_tiers_completed.append("tier_2")
            lead.cost_aud += self.COSTS["linkedin_company"]
            logger.debug(f"Tier 2 completed for {lead.id}, geo_validated={geo_validated}, returned_location={returned_location}")

        except Exception as e:
            error = {"tier": "tier_2", "error": str(e), "timestamp": datetime.now(UTC).isoformat()}
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 2 failed for {lead.id}: {str(e)}")

        return lead

    def _extract_decision_makers(self, employees: list[dict]) -> list[dict]:
        """Extract decision makers from employee list"""
        decision_makers = []
        decision_keywords = [
            "ceo",
            "cto",
            "cfo",
            "cmo",
            "coo",
            "chief",
            "president",
            "founder",
            "vp",
            "vice president",
            "director",
            "head of",
            "manager",
        ]

        for employee in employees:
            title = (employee.get("title") or "").lower()
            if any(keyword in title for keyword in decision_keywords):
                decision_makers.append(employee)

        return decision_makers[:5]  # Limit to top 5

    # PHASE 3: SCORING AND QUALITY GATES

    def calculate_als(self, lead: LeadRecord) -> int:
        """Calculate Agency Lead Score (0-100)"""
        score_breakdown = {
            "company_fit": 0,  # 25 pts max
            "authority": 0,  # 25 pts max
            "timing": 0,  # 15 pts max
            "data_quality": 0,  # 20 pts max
            "engagement": 0,  # 15 pts max
        }

        # Company Fit (25 points)
        if lead.industry:
            score_breakdown["company_fit"] += 10
        if lead.company_size and ("11-50" in lead.company_size or "51-200" in lead.company_size):
            score_breakdown["company_fit"] += 10  # Sweet spot for agencies
        if lead.specialties:
            score_breakdown["company_fit"] += 5

        # Authority (25 points) - Score based on best decision maker title
        if lead.decision_makers:
            for dm in lead.decision_makers[:1]:  # Score on best DM only
                title = (dm.get("title") or "").lower()
                if any(k in title for k in ["ceo", "founder", "owner", "chief", "president", "managing director"]):
                    score_breakdown["authority"] = 25
                elif any(k in title for k in ["vp", "vice president"]):
                    score_breakdown["authority"] = 18
                elif any(k in title for k in ["director", "head of"]):
                    score_breakdown["authority"] = 15
                elif any(k in title for k in ["manager", "partner"]):
                    score_breakdown["authority"] = 7
                break  # Score on best DM only

        # Timing (15 points) - Based on recent activity signals
        if lead.linkedin_data.get("updates"):
            recent_updates = len(lead.linkedin_data["updates"])
            score_breakdown["timing"] += min(recent_updates * 2, 10)

            # Hiring signal detection - bonus 5 points for active growth
            for update in lead.linkedin_data["updates"]:
                update_text = (update.get("text") or "").lower()
                if (
                    "#hiring" in update_text
                    or "we're hiring" in update_text
                    or "we are hiring" in update_text
                ):
                    score_breakdown["timing"] += 5  # Active hiring = growth signal
                    logger.debug("hiring_signal_detected", lead_id=lead.id)
                    break  # Only count once

        if lead.founded and lead.founded >= datetime.now().year - 2:
            score_breakdown["timing"] += 5  # New companies often need services

        # Data Quality (20 points) - Based on verified sources
        verified_sources = len(lead.enrichment_tiers_completed)
        score_breakdown["data_quality"] += min(verified_sources * 3, 15)
        if lead.email:
            score_breakdown["data_quality"] += 5

        # Engagement Potential (15 points)
        if lead.website:
            score_breakdown["engagement"] += 5
        if lead.phone:
            score_breakdown["engagement"] += 5
        if lead.rating and lead.rating >= 4.0:
            score_breakdown["engagement"] += 3
        if lead.reviews_count and lead.reviews_count >= 10:
            score_breakdown["engagement"] += 2

        total_score = sum(score_breakdown.values())
        lead.propensity_components = score_breakdown

        logger.debug(f"ALS calculated for {lead.id}: {total_score} (breakdown: {score_breakdown})")
        return total_score

    # PREMIUM ENRICHMENT TIERS (WITH GATES)

    async def enrich_tier_2_5(self, lead: LeadRecord) -> LeadRecord:
        """
        Tier 2.5: LinkedIn People Profile - $0.0015 per profile - Only if ALS >= gate
        
        Scrapes employee profiles from T2 to get real job titles, then filters for decision makers.
        BD company scraper returns employee NAME in 'title' field, not job title.
        This tier scrapes each profile to extract actual title for DM filtering.
        """
        if "tier_2_5" in lead.enrichment_tiers_completed:
            return lead

        if lead.propensity_score < self.PRE_ALS_GATE:
            logger.debug(
                f"Tier 2.5 skipped for {lead.id} - propensity score {lead.propensity_score} below gate {self.PRE_ALS_GATE}"
            )
            return lead

        # Use employees from T2 (not decision_makers which is empty at this point)
        if not lead.employees:
            lead.enrichment_tiers_completed.append("tier_2_5")
            return lead

        logger.debug(f"Tier 2.5: LinkedIn people profiles for {lead.business_name}")

        try:
            if not self.bd:
                raise ValueError("Bright Data client not configured")

            # Decision maker keywords for filtering
            dm_keywords = [
                "ceo", "cto", "cfo", "cmo", "coo", "chief", "founder", "president",
                "vp", "vice president", "director", "head of", "owner", "partner", "managing"
            ]

            # Scrape profiles and filter for decision makers
            scraped_profiles = []
            decision_makers = []

            for emp in lead.employees[:3]:  # Limit to top 3 to control costs
                profile_url = emp.get("link")
                if profile_url:
                    profile_data = await self.bd.scrape_linkedin_profile(profile_url)
                    
                    # FIX B: Defensive check - BD sometimes returns string errors
                    if not isinstance(profile_data, dict):
                        logger.warning(
                            "tier_2_5_invalid_response",
                            type=type(profile_data).__name__,
                            value=str(profile_data)[:100]
                        )
                        continue
                    
                    if profile_data:
                        # FIX A: Extract job title - BD returns "position" as STRING
                        # Defensive chain tries all likely field names
                        job_title = (
                            profile_data.get("position")  # Primary: BD position field (STRING)
                            or profile_data.get("headline")  # Fallback: headline
                            or profile_data.get("title")  # Fallback: title
                            or profile_data.get("occupation")  # Fallback: occupation
                        )
                        
                        # If position is a list (legacy/edge case), extract from first item
                        if isinstance(job_title, list) and job_title:
                            first_pos = job_title[0]
                            job_title = first_pos.get("title") if isinstance(first_pos, dict) else None
                        
                        # Last resort: parse from about/summary
                        if not job_title:
                            about = profile_data.get("about") or profile_data.get("summary") or ""
                            if about:
                                job_title = about.split("\n")[0][:100]  # First line, truncated
                        
                        # FIX C: Debug log showing extracted title
                        logger.debug(
                            "tier_2_5_title_extracted",
                            name=profile_data.get("name"),
                            job_title=job_title,
                            source_field="position" if profile_data.get("position") else "fallback"
                        )
                        
                        profile_info = {
                            "first_name": profile_data.get("first_name"),
                            "last_name": profile_data.get("last_name"),
                            "name": profile_data.get("name"),
                            "title": job_title,  # Normalized job title
                            "link": profile_url,
                            "about": profile_data.get("about"),
                            "position": profile_data.get("position"),  # Keep original for reference
                        }
                        
                        scraped_profiles.append(profile_info)
                        
                        # Check if decision maker
                        title = (profile_info.get("title") or "").lower()
                        if any(kw in title for kw in dm_keywords):
                            decision_makers.append(profile_info)
                        
                        lead.cost_aud += self.COSTS["linkedin_people"]

            # Store decision makers, or best profile if none found
            if decision_makers:
                lead.decision_makers = decision_makers
                logger.info(f"Tier 2.5: Found {len(decision_makers)} decision makers for {lead.business_name}")
            elif scraped_profiles:
                # Any contact is better than none
                lead.decision_makers = [scraped_profiles[0]]
                logger.info(f"Tier 2.5: No DM found, using top profile for {lead.business_name}")

            lead.enrichment_tiers_completed.append("tier_2_5")
            logger.debug(f"Tier 2.5 completed for {lead.id}")

        except Exception as e:
            error = {
                "tier": "tier_2_5",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 2.5 failed for {lead.id}: {str(e)}")

        return lead

    async def enrich_tier_3(self, lead: LeadRecord) -> LeadRecord:
        """
        Tier 3: Leadmagic Email Finder - $0.015 - Only if ALS >= 35

        Replaces Hunter.io per CEO directive.
        Raises LeadmagicCreditExhaustedError if credits exhausted (hard fail).
        """
        if "tier_3" in lead.enrichment_tiers_completed:
            return lead

        if lead.propensity_score < self.PRE_ALS_GATE:
            logger.debug(
                f"Tier 3 skipped for {lead.id} - propensity score {lead.propensity_score} below gate {self.PRE_ALS_GATE}"
            )
            return lead

        # Need either website (for domain) or decision maker with LinkedIn
        if not lead.website and not lead.decision_makers:
            lead.enrichment_tiers_completed.append("tier_3")
            return lead

        logger.debug(f"Tier 3: Leadmagic email enrichment for {lead.business_name}")

        try:
            if not self.leadmagic:
                raise ValueError(
                    "Leadmagic client not configured - required for T3 email enrichment"
                )

            # Try to find email for best decision maker
            email_found = False

            if lead.decision_makers:
                for dm in lead.decision_makers[:2]:  # Try top 2 decision makers
                    first_name = dm.get("first_name") or dm.get("name", "").split()[0]
                    last_name = dm.get("last_name") or (
                        dm.get("name", "").split()[-1]
                        if len(dm.get("name", "").split()) > 1
                        else ""
                    )
                    domain = self._extract_domain(lead.website) if lead.website else None

                    if first_name and last_name and domain:
                        result = await self.leadmagic.find_email(
                            first_name=first_name,
                            last_name=last_name,
                            domain=domain,
                            company=lead.business_name,
                        )

                        if result.found and result.email:
                            lead.email = result.email
                            lead.email_confidence = result.confidence / 100.0
                            lead.contact_source = "leadmagic"
                            lead.cost_aud += result.cost_aud
                            email_found = True
                            break

            # If no decision maker email found, try generic domain search
            if not email_found and lead.website:
                domain = self._extract_domain(lead.website)
                if domain:
                    # Use company name as fallback for generic contact
                    result = await self.leadmagic.find_email(
                        first_name="info",
                        last_name="Contact",
                        domain=domain,
                        company=lead.business_name,
                    )
                    if result.found and result.email:
                        lead.email = result.email
                        lead.email_confidence = result.confidence / 100.0
                        lead.contact_source = "leadmagic"
                        lead.cost_aud += result.cost_aud

            lead.enrichment_tiers_completed.append("tier_3")
            lead.cost_aud += self.COSTS["leadmagic_email"]
            logger.debug(f"Tier 3 completed for {lead.id}")

        except (LeadmagicCreditExhaustedError, LeadmagicNoPlanError) as e:
            # HARD FAIL - Do not silently skip, propagate error
            logger.error(f"Tier 3 BLOCKED for {lead.id}: {str(e)}")
            error = {
                "tier": "tier_3",
                "error": str(e),
                "fatal": True,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            lead.enrichment_errors.append(error)
            raise  # Re-raise to stop pipeline

        except Exception as e:
            error = {"tier": "tier_3", "error": str(e), "timestamp": datetime.now(UTC).isoformat()}
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 3 failed for {lead.id}: {str(e)}")

        return lead

    def _extract_domain(self, website: str) -> str | None:
        """Extract domain from website URL"""
        if not website:
            return None

        # Clean up URL
        domain = website.lower().strip()
        if domain.startswith("http://"):
            domain = domain[7:]
        elif domain.startswith("https://"):
            domain = domain[8:]

        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]

        # Remove path and parameters
        domain = domain.split("/")[0].split("?")[0]

        return domain if "." in domain else None

    async def enrich_tier_5(self, lead: LeadRecord) -> LeadRecord:
        """
        Tier 5: Leadmagic Mobile Finder - $0.077 - Only if ALS >= 85

        Replaces Kaspr per CEO directive.
        Raises LeadmagicCreditExhaustedError if credits exhausted (hard fail).
        """
        if "tier_5" in lead.enrichment_tiers_completed:
            return lead

        if lead.propensity_score < self.HOT_THRESHOLD:
            logger.debug(
                f"Tier 5 skipped for {lead.id} - propensity score {lead.propensity_score} below hot threshold {self.HOT_THRESHOLD}"
            )
            return lead

        if not lead.decision_makers:
            # Skip if no decision makers to enrich
            lead.enrichment_tiers_completed.append("tier_5")
            return lead

        logger.debug(f"Tier 5: Leadmagic mobile enrichment for {lead.business_name}")

        try:
            if not self.leadmagic:
                raise ValueError(
                    "Leadmagic client not configured - required for T5 mobile enrichment"
                )

            # Enrich top decision makers with Leadmagic mobile finder
            verified_contacts = []

            for dm in lead.decision_makers[:2]:  # Limit to top 2 to control costs
                linkedin_url = dm.get("link")
                if linkedin_url:
                    result = await self.leadmagic.find_mobile(linkedin_url)

                    if result.found:
                        contact_data = {
                            "mobile": result.mobile_number,
                            "mobile_confidence": result.mobile_confidence,
                            "email": result.email,
                            "full_name": result.full_name,
                            "title": result.title,
                            "company": result.company,
                            "linkedin_url": result.linkedin_url,
                            "source": "leadmagic",
                        }
                        verified_contacts.append(contact_data)

                        # Update lead with best contact info
                        if not lead.direct_mobile and result.mobile_number:
                            lead.direct_mobile = result.mobile_number
                        if not lead.email and result.email:
                            lead.email = result.email
                            lead.email_confidence = 0.95  # Leadmagic is high confidence
                            lead.contact_source = "leadmagic"

                        lead.cost_aud += result.cost_aud

            if verified_contacts:
                lead.verified_contacts = verified_contacts
                lead.leadmagic_data = {
                    "contacts_enriched": len(verified_contacts),
                    "enrichment_timestamp": datetime.now(UTC).isoformat(),
                }

            lead.enrichment_tiers_completed.append("tier_5")
            lead.cost_aud += self.COSTS["leadmagic_mobile"]
            logger.debug(f"Tier 5 completed for {lead.id}")

        except (LeadmagicCreditExhaustedError, LeadmagicNoPlanError) as e:
            # HARD FAIL - Do not silently skip, propagate error
            logger.error(f"Tier 5 BLOCKED for {lead.id}: {str(e)}")
            error = {
                "tier": "tier_5",
                "error": str(e),
                "fatal": True,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            lead.enrichment_errors.append(error)
            raise  # Re-raise to stop pipeline

        except Exception as e:
            error = {"tier": "tier_5", "error": str(e), "timestamp": datetime.now(UTC).isoformat()}
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 5 failed for {lead.id}: {str(e)}")

        return lead

    # FULL PIPELINE ORCHESTRATION

    async def run_full_pipeline(self, config: CampaignConfig) -> list[LeadRecord]:
        """Execute complete Phase 1 → 2 → 3 pipeline"""
        logger.info(
            f"Starting full Waterfall v2 pipeline for {config.industry} in {config.location}"
        )

        try:
            # Phase 1: Discovery
            leads = await self.run_discovery(config)
            logger.info(f"Phase 1 completed: {len(leads)} leads discovered")

            if not leads:
                return []

            enriched = []

            for lead in leads:
                logger.debug(f"Processing lead: {lead.business_name} ({lead.id})")

                # Phase 2: Core Enrichment (Always run)
                # v2.2 Order: T1 → T1.25(ABR) → T1.5b(LinkedIn) → T1.5a(GMB) → T2
                lead = await self.enrich_tier_1(lead)
                lead = await self.enrich_tier_1_25(lead)   # ABR trading name lookup
                lead = await self.enrich_tier_1_5b(lead)   # LinkedIn first (confirms business exists)
                lead = await self.enrich_tier_1_5a(lead)   # GMB second (cross-reference with trading name)
                lead = await self.enrich_tier_2(lead)

                # Phase 3: Initial Propensity Scoring
                lead.propensity_score = self.calculate_als(lead)
                logger.debug(f"Initial propensity score for {lead.id}: {lead.propensity_score}")

                # Quality Gate Check - Continue enrichment only if score >= PRE_ALS_GATE
                if lead.propensity_score >= self.PRE_ALS_GATE:
                    logger.debug(
                        f"Lead {lead.id} passed propensity gate ({lead.propensity_score} >= {self.PRE_ALS_GATE})"
                    )

                    # Phase 2 continued: Premium Enrichment
                    lead = await self.enrich_tier_2_5(lead)
                    lead = await self.enrich_tier_3(lead)
                    lead = await self.enrich_tier_5(lead)

                    # Phase 3: Final Propensity Scoring
                    lead.propensity_score = self.calculate_als(lead)
                    logger.debug(f"Final propensity score for {lead.id}: {lead.propensity_score}")
                else:
                    logger.debug(
                        f"Lead {lead.id} did not pass propensity gate ({lead.propensity_score} < {self.PRE_ALS_GATE})"
                    )

                # Update final metadata
                lead.updated_at = datetime.now(UTC).isoformat()
                enriched.append(lead)

            # Pipeline summary
            total_cost = sum(lead.cost_aud for lead in enriched)
            high_quality_leads = len(
                [lead for lead in enriched if lead.propensity_score >= self.HOT_THRESHOLD]
            )

            logger.info(
                f"Waterfall v2 pipeline completed: {len(enriched)} leads processed, "
                f"{high_quality_leads} high-quality leads (ALS >= {self.HOT_THRESHOLD}), "
                f"Total cost: ${total_cost:.4f} AUD"
            )

            return enriched

        except Exception as e:
            logger.error(f"Full pipeline failed: {str(e)}")
            raise  # Re-raise to surface Leadmagic credit errors

    # UTILITY METHODS

    def get_pipeline_stats(self, leads: list[LeadRecord]) -> dict:
        """Get pipeline statistics and performance metrics"""
        if not leads:
            return {}

        stats = {
            "total_leads": len(leads),
            "total_cost_aud": sum(lead.cost_aud for lead in leads),
            "average_cost_per_lead": sum(lead.cost_aud for lead in leads) / len(leads),
            "propensity_distribution": {
                "hot_leads": len([l for l in leads if l.propensity_score >= self.HOT_THRESHOLD]),
                "qualified_leads": len([l for l in leads if l.propensity_score >= self.PRE_ALS_GATE]),
                "low_quality_leads": len([l for l in leads if l.propensity_score < self.PRE_ALS_GATE]),
            },
            "enrichment_completion": {},
            "discovery_sources": {},
            "error_summary": {},
        }

        # Enrichment tier completion rates
        all_tiers = ["tier_1", "tier_1_5a", "tier_1_5b", "tier_2", "tier_2_5", "tier_3", "tier_5"]
        for tier in all_tiers:
            completed = len([l for l in leads if tier in l.enrichment_tiers_completed])
            stats["enrichment_completion"][tier] = {
                "completed": completed,
                "rate": completed / len(leads) if leads else 0,
            }

        # Discovery source breakdown
        for lead in leads:
            source = lead.discovery_source or "unknown"
            stats["discovery_sources"][source] = stats["discovery_sources"].get(source, 0) + 1

        # Error summary
        for lead in leads:
            for error in lead.enrichment_errors:
                tier = error.get("tier", "unknown")
                stats["error_summary"][tier] = stats["error_summary"].get(tier, 0) + 1

        return stats
