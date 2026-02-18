"""
Contract: src/engines/waterfall_verification_worker.py
Purpose: Waterfall enrichment and verification for leads
Layer: 3 - engines
Imports: models, integrations
Consumers: orchestration only

FILE: src/engines/waterfall_verification_worker.py
PURPOSE: Waterfall Verification Worker - ABN + GMB + Hunter + ZeroBounce
PHASE: WF-001 (Waterfall Enrichment Architecture)
TASK: Nationwide Rollout
DEPENDENCIES:
  - src/engines/base.py
  - src/integrations/redis.py
  - src/models/lead_pool.py
  - src/models/lead_lineage_log.py (new)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - Rule 11: Session passed as argument
  - Cost tracking in $AUD only

GOVERNANCE EVENT: Waterfall Reliability Shift
DESCRIPTION: Moved from Apollo SPOF (deprecated) to ABN + GMB + Hunter.io + ZeroBounce waterfall
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from fuzzywuzzy import fuzz
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.base import BaseEngine, EngineResult
from src.models.lead_pool import LeadPool, EmailStatus

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTS & CONFIGURATION
# ============================================

class VerificationTier(str, Enum):
    """Waterfall verification tiers."""
    ABN_SEED = "abn_seed"
    ASIC_VERIFY = "asic_verify"  # T1.25: ABR SearchByASIC for registered_name
    GMB_SCRAPER = "gmb_scraper"
    HUNTER_IO = "hunter_io"
    ZEROBOUNCE = "zerobounce"
    DM0_LINKEDIN_DISCOVERY = "dm0_linkedin_discovery"  # T-DM0: DataForSEO SERP + Bright Data Profile


class MatchConfidence(str, Enum):
    """ABN ↔ GMB match confidence levels."""
    EXACT = "exact"           # Name + postcode + address exact match
    HIGH = "high"             # Name fuzzy ≥90% + postcode match
    MEDIUM = "medium"         # Name fuzzy ≥80% + postcode match
    LOW = "low"               # Name fuzzy ≥70% + postcode match
    NO_MATCH = "no_match"     # Below threshold or no GMB result


# Cost per operation in AUD (2026 pricing)
COSTS_AUD = {
    VerificationTier.ABN_SEED: Decimal("0.00"),      # Free (data.gov.au)
    VerificationTier.ASIC_VERIFY: Decimal("0.00"),   # Free (ABR SearchByASIC) - CEO Directive #039
    VerificationTier.GMB_SCRAPER: Decimal("0.0062"), # GMB scraper (Apify deprecated)
    VerificationTier.HUNTER_IO: Decimal("0.0064"),   # Hunter.io Growth tier
    VerificationTier.ZEROBOUNCE: Decimal("0.010"),   # ZeroBounce average
    VerificationTier.DM0_LINKEDIN_DISCOVERY: Decimal("0.0165"),  # DataForSEO SERP ($0.009) + Bright Data Profile ($0.0015 × 5 max)
}

# T-DM0 Title priority scores for decision maker identification
DM_TITLE_SCORES = {
    "founder": 100,
    "co-founder": 98,
    "ceo": 95,
    "chief executive": 95,
    "managing director": 90,
    "md": 90,
    "owner": 80,
    "director": 85,
    "principal": 82,
    "president": 88,
    "partner": 75,
}

# DataForSEO configuration
DATAFORSEO_SERP_COST_AUD = Decimal("0.009")  # Per SERP request
BRIGHTDATA_PROFILE_COST_AUD = Decimal("0.0015")  # Per profile scrape

# Thresholds
FUZZY_MATCH_THRESHOLD = 70  # Minimum Levenshtein similarity for match
HIGH_CONFIDENCE_THRESHOLD = 90
MEDIUM_CONFIDENCE_THRESHOLD = 80
HUNTER_CONFIDENCE_THRESHOLD = 70  # Below this → escalate to ZeroBounce
ALS_ESCALATION_THRESHOLD = 60  # Only verify Warm+ leads
MULTI_SOURCE_BONUS = 15  # +15 ALS for 3+ source verification


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class ABNRecord:
    """Record from ABN Bulk Extract."""
    abn: str
    abn_status: str
    entity_type: str
    legal_name: str
    business_names: list[str]
    state: str
    postcode: str
    gst_registered: bool
    acn: Optional[str] = None


@dataclass
class ASICVerifyRecord:
    """
    Record from ASIC verification (T1.25).
    
    CEO Directive #039: Uses ABR SearchByASIC to get ASIC-registered business name
    for improved T2 GMB fuzzy matching. Directors[] pending ASIC DSP approval.
    
    Source: ABR SearchByASICv201408
    Cost: $0.00 AUD (FREE)
    """
    acn: str
    registered_name: str  # ASIC-registered business name (clean, official)
    business_names: list[str]  # All ASIC-registered trading names
    entity_type: str
    state: str
    postcode: str
    directors: Optional[list[str]] = None  # Pending ASIC DSP approval


@dataclass
class GMBRecord:
    """Record from Google Maps scraping."""
    google_place_id: str
    business_name: str
    phone: Optional[str]
    website: Optional[str]
    address: str
    postcode: str
    state: str
    lat: float
    lng: float
    rating: Optional[float]
    review_count: int
    categories: list[str]


@dataclass
class HunterResult:
    """Result from Hunter.io email verification."""
    email: str
    confidence: int  # 0-100
    email_type: str  # personal, generic
    status: str  # valid, invalid, catch_all, unknown


@dataclass
class ZeroBounceResult:
    """Result from ZeroBounce verification."""
    email: str
    status: str  # valid, invalid, catch_all, unknown, spamtrap
    sub_status: str
    did_you_mean: Optional[str]
    activity_score: Optional[int]


@dataclass
class DMCandidate:
    """
    Decision Maker candidate from T-DM0 LinkedIn discovery.
    
    CEO Directive #040: DataForSEO SERP + Bright Data Profile scraping.
    """
    dm_name: str
    dm_title: str
    dm_linkedin_url: str
    company_match_score: int  # Fuzzy match score against registered_name
    title_score: int  # Title priority score (founder=100, CEO=95, MD=90, director=85, owner=80)


@dataclass
class LineageStep:
    """Single step in the enrichment lineage."""
    step_number: int
    step_type: str  # 'source', 'enrichment', 'verification', 'intent_signal'
    source_name: str
    cost_aud: Decimal
    success: bool
    data_added: list[str] = field(default_factory=list)
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    raw_response: Optional[dict] = None


@dataclass
class WaterfallResult:
    """Complete result from waterfall verification."""
    lead_id: UUID
    abn: Optional[str]
    acn: Optional[str] = None  # T1.25: ASIC company number
    asic_registered_name: Optional[str] = None  # T1.25: Clean registered name for fuzzy match
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # Match quality
    abn_gmb_match_confidence: MatchConfidence = MatchConfidence.NO_MATCH
    abn_gmb_match_score: int = 0
    
    # T-DM0: Decision Maker discovery (CEO Directive #040)
    dm_name: Optional[str] = None
    dm_title: Optional[str] = None
    dm_linkedin_url: Optional[str] = None
    dm_candidates_found: int = 0
    
    # Verification
    verification_method: str  # single_source, dual_match, triple_check
    verification_sources: list[str]
    verification_consensus: bool
    email_confidence: int
    
    # Costs
    total_cost_aud: Decimal
    lineage: list[LineageStep]
    
    # ALS contribution
    source_count: int
    multi_source_bonus: int
    
    # Status
    success: bool
    errors: list[str] = field(default_factory=list)


# ============================================
# WATERFALL VERIFICATION WORKER
# ============================================

class WaterfallVerificationWorker(BaseEngine):
    """
    Waterfall enrichment and verification worker.
    
    Implements the "ABN + GMB Double-Wedge" strategy:
    - Tier 1: ABN Seed (Free public data)
    - Tier 2: GMB Scraper (Phone/Website enrichment)
    - Tier 3: Hunter.io (Email finding/verification)
    - Tier 4: ZeroBounce (Premium escalation for catch-all/low-confidence)
    
    Cost Governance:
    - All costs tracked in AUD
    - Full lineage logged to lead_lineage_log table
    - +15 ALS bonus for 3+ source verification
    """
    
    def __init__(
        self,
        abn_client=None,
        gmb_scraper=None,
        hunter_client=None,
        zerobounce_client=None,
    ):
        """
        Initialize worker with integration clients.
        
        Args:
            abn_client: ABN Lookup API client
            gmb_scraper: GMB scraper client (Apify deprecated)
            hunter_client: Hunter.io API client
            zerobounce_client: ZeroBounce API client
        """
        self._abn_client = abn_client
        self._gmb_scraper = gmb_scraper
        self._hunter_client = hunter_client
        self._zerobounce_client = zerobounce_client
    
    @property
    def name(self) -> str:
        return "waterfall_verification"
    
    # ============================================
    # MAIN VERIFICATION FLOW
    # ============================================
    
    async def verify_lead(
        self,
        db: AsyncSession,
        lead_id: UUID,
        company_name: str,
        postcode: str,
        state: str,
        current_als_score: int = 0,
        force_full_waterfall: bool = False,
    ) -> EngineResult[WaterfallResult]:
        """
        Run waterfall verification on a lead.
        
        Args:
            db: Database session
            lead_id: Lead UUID
            company_name: Company name to match
            postcode: Australian postcode
            state: Australian state (NSW, VIC, etc.)
            current_als_score: Current ALS for escalation decisions
            force_full_waterfall: Force all tiers regardless of score
        
        Returns:
            EngineResult containing WaterfallResult
        """
        lineage: list[LineageStep] = []
        errors: list[str] = []
        total_cost = Decimal("0.00")
        step_number = 0
        
        # Initialize result
        result = WaterfallResult(
            lead_id=lead_id,
            abn=None,
            email=None,
            phone=None,
            website=None,
            abn_gmb_match_confidence=MatchConfidence.NO_MATCH,
            abn_gmb_match_score=0,
            verification_method="single_source",
            verification_sources=[],
            verification_consensus=False,
            email_confidence=0,
            total_cost_aud=Decimal("0.00"),
            lineage=[],
            source_count=0,
            multi_source_bonus=0,
            success=False,
        )
        
        try:
            # ========== TIER 1: ABN SEED ==========
            step_number += 1
            start_time = datetime.utcnow()
            
            abn_result = await self._tier1_abn_seed(company_name, postcode, state)
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            step = LineageStep(
                step_number=step_number,
                step_type="source",
                source_name=VerificationTier.ABN_SEED.value,
                cost_aud=COSTS_AUD[VerificationTier.ABN_SEED],
                success=abn_result is not None,
                data_added=["abn", "legal_name", "entity_type"] if abn_result else [],
                latency_ms=latency_ms,
            )
            lineage.append(step)
            total_cost += step.cost_aud
            
            if abn_result:
                result.abn = abn_result.abn
                result.verification_sources.append("abn")
            else:
                errors.append("ABN seed: No match found for company name/postcode")
            
            # ========== TIER 1.25: ASIC VERIFICATION (CEO Directive #039) ==========
            # Purpose: Get ASIC-registered business name for improved T2 fuzzy matching
            asic_result: Optional[ASICVerifyRecord] = None
            gmb_search_name = company_name  # Default: use original company name
            
            if abn_result and abn_result.acn:
                step_number += 1
                start_time = datetime.utcnow()
                
                asic_result = await self._tier1_25_asic_verify(
                    acn=abn_result.acn,
                    abn=abn_result.abn,
                )
                
                latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                asic_success = asic_result is not None
                
                step = LineageStep(
                    step_number=step_number,
                    step_type="verification",
                    source_name=VerificationTier.ASIC_VERIFY.value,
                    cost_aud=COSTS_AUD[VerificationTier.ASIC_VERIFY],
                    success=asic_success,
                    data_added=["registered_name", "acn"] if asic_success else [],
                    latency_ms=latency_ms,
                )
                lineage.append(step)
                total_cost += step.cost_aud
                
                if asic_result:
                    result.acn = asic_result.acn
                    result.asic_registered_name = asic_result.registered_name
                    # Use ASIC registered_name for GMB search (cleaner, improves match rate)
                    gmb_search_name = asic_result.registered_name
                    logger.info(
                        f"T1.25: Using ASIC registered_name '{gmb_search_name}' for T2 GMB search "
                        f"(was: '{company_name}')"
                    )
                else:
                    errors.append(f"T1.25: ASIC verify failed for ACN {abn_result.acn}")
            
            # ========== TIER DM-0: LINKEDIN DECISION MAKER DISCOVERY (CEO Directive #040) ==========
            # Runs if we have a registered_name from T1.25 (or fallback to company_name)
            dm_search_name = gmb_search_name  # Use ASIC registered_name if available
            
            step_number += 1
            start_time = datetime.utcnow()
            
            dm_candidate = await self._tier_dm0_linkedin_discovery(
                registered_name=dm_search_name,
                state=state,
            )
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            dm0_success = dm_candidate is not None
            
            # Calculate actual cost (SERP + profiles scraped)
            dm0_cost = DATAFORSEO_SERP_COST_AUD  # Always pay for SERP
            if dm0_success:
                # Add Bright Data profile costs (estimated at 1 per successful result)
                dm0_cost += BRIGHTDATA_PROFILE_COST_AUD
            
            step = LineageStep(
                step_number=step_number,
                step_type="enrichment",
                source_name=VerificationTier.DM0_LINKEDIN_DISCOVERY.value,
                cost_aud=dm0_cost,
                success=dm0_success,
                data_added=["dm_name", "dm_title", "dm_linkedin_url"] if dm0_success else [],
                latency_ms=latency_ms,
            )
            lineage.append(step)
            total_cost += dm0_cost
            
            if dm_candidate:
                result.dm_name = dm_candidate.dm_name
                result.dm_title = dm_candidate.dm_title
                result.dm_linkedin_url = dm_candidate.dm_linkedin_url
                result.dm_candidates_found = 1
                result.verification_sources.append("dm0_linkedin")
                logger.info(
                    f"T-DM0: Found DM '{dm_candidate.dm_name}' ({dm_candidate.dm_title}) "
                    f"for '{dm_search_name}'"
                )
            else:
                errors.append(f"T-DM0: No decision maker found for '{dm_search_name}'")
            
            # ========== TIER 2: GMB SCRAPER ==========
            step_number += 1
            start_time = datetime.utcnow()
            
            # Use ASIC registered_name if available, otherwise original company_name
            gmb_result = await self._tier2_gmb_scraper(gmb_search_name, postcode, state)
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Handle ABN ↔ GMB matching with error handling
            match_confidence = MatchConfidence.NO_MATCH
            match_score = 0
            gmb_success = False
            data_added = []
            
            if gmb_result:
                if abn_result:
                    # Both ABN and GMB found — attempt fuzzy match
                    # CEO Directive #039: Use ASIC registered_name if available
                    match_confidence, match_score = self._match_abn_gmb(
                        abn_result, gmb_result, asic_result
                    )
                    
                    if match_confidence != MatchConfidence.NO_MATCH:
                        # Match successful
                        gmb_success = True
                        result.phone = gmb_result.phone
                        result.website = gmb_result.website
                        result.abn_gmb_match_confidence = match_confidence
                        result.abn_gmb_match_score = match_score
                        result.verification_sources.append("gmb")
                        data_added = ["phone", "website", "address", "rating"]
                    else:
                        # ABN and GMB don't match — CRITICAL ERROR HANDLING
                        match_name = asic_result.registered_name if asic_result else abn_result.legal_name
                        errors.append(
                            f"ABN↔GMB mismatch: '{match_name}' "
                            f"vs GMB name '{gmb_result.business_name}' "
                            f"(score: {match_score}%, threshold: {FUZZY_MATCH_THRESHOLD}%)"
                        )
                        # Still capture GMB data but flag as unverified
                        result.phone = gmb_result.phone
                        result.website = gmb_result.website
                        result.abn_gmb_match_confidence = MatchConfidence.NO_MATCH
                        result.abn_gmb_match_score = match_score
                        data_added = ["phone", "website"]  # Marked as unverified
                        gmb_success = True  # Data captured, match failed
                else:
                    # No ABN but GMB found — use GMB as primary
                    result.phone = gmb_result.phone
                    result.website = gmb_result.website
                    result.verification_sources.append("gmb")
                    data_added = ["phone", "website"]
                    gmb_success = True
                    errors.append("ABN not found — using GMB as primary source (unverified)")
            else:
                errors.append("GMB scraper: No results for company/postcode")
            
            step = LineageStep(
                step_number=step_number,
                step_type="enrichment",
                source_name=VerificationTier.GMB_SCRAPER.value,
                cost_aud=COSTS_AUD[VerificationTier.GMB_SCRAPER],
                success=gmb_success,
                data_added=data_added,
                error_message=errors[-1] if not gmb_success else None,
                latency_ms=latency_ms,
            )
            lineage.append(step)
            total_cost += step.cost_aud
            
            # ========== TIER 3: HUNTER.IO (Conditional) ==========
            # Only proceed if ALS >= 60 (Warm+) or forced
            should_verify_email = (
                force_full_waterfall or 
                current_als_score >= ALS_ESCALATION_THRESHOLD
            )
            
            if should_verify_email and result.website:
                step_number += 1
                start_time = datetime.utcnow()
                
                domain = self._extract_domain(result.website)
                hunter_result = await self._tier3_hunter_io(domain, company_name)
                
                latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                hunter_success = False
                data_added = []
                
                if hunter_result:
                    result.email = hunter_result.email
                    result.email_confidence = hunter_result.confidence
                    result.verification_sources.append("hunter_io")
                    hunter_success = True
                    data_added = ["email"]
                    
                    # ========== TIER 4: ZEROBOUNCE (Escalation) ==========
                    # Escalate if catch_all or low confidence
                    needs_escalation = (
                        hunter_result.status == "catch_all" or
                        hunter_result.confidence < HUNTER_CONFIDENCE_THRESHOLD
                    )
                    
                    if needs_escalation:
                        step_number += 1
                        start_time = datetime.utcnow()
                        
                        zb_result = await self._tier4_zerobounce(hunter_result.email)
                        
                        latency_ms_zb = int(
                            (datetime.utcnow() - start_time).total_seconds() * 1000
                        )
                        zb_success = False
                        
                        if zb_result:
                            if zb_result.status == "valid":
                                result.email_confidence = 99
                                result.verification_sources.append("zerobounce")
                                zb_success = True
                            elif zb_result.status in ("invalid", "spamtrap"):
                                result.email = None
                                result.email_confidence = 0
                                errors.append(
                                    f"ZeroBounce rejected email: {zb_result.status}"
                                )
                            else:
                                # Ambiguous result — keep Hunter's email with note
                                errors.append(
                                    f"ZeroBounce ambiguous: {zb_result.status}"
                                )
                                result.verification_sources.append("zerobounce")
                                zb_success = True
                        
                        step = LineageStep(
                            step_number=step_number,
                            step_type="verification",
                            source_name=VerificationTier.ZEROBOUNCE.value,
                            cost_aud=COSTS_AUD[VerificationTier.ZEROBOUNCE],
                            success=zb_success,
                            data_added=["email_verified"] if zb_success else [],
                            error_message=errors[-1] if not zb_success else None,
                            latency_ms=latency_ms_zb,
                        )
                        lineage.append(step)
                        total_cost += step.cost_aud
                else:
                    errors.append(f"Hunter.io: No email found for domain {domain}")
                
                step = LineageStep(
                    step_number=step_number if not needs_escalation else step_number - 1,
                    step_type="verification",
                    source_name=VerificationTier.HUNTER_IO.value,
                    cost_aud=COSTS_AUD[VerificationTier.HUNTER_IO],
                    success=hunter_success,
                    data_added=data_added,
                    error_message=None if hunter_success else errors[-1],
                    latency_ms=latency_ms,
                )
                # Insert before ZeroBounce step if escalated
                if needs_escalation and len(lineage) > 0:
                    lineage.insert(-1, step)
                else:
                    lineage.append(step)
                total_cost += step.cost_aud
            
            # ========== FINALIZE RESULT ==========
            result.source_count = len(result.verification_sources)
            result.total_cost_aud = total_cost
            result.lineage = lineage
            result.errors = errors
            
            # Determine verification method
            if result.source_count >= 3:
                result.verification_method = "triple_check"
                result.verification_consensus = True
                result.multi_source_bonus = MULTI_SOURCE_BONUS
            elif result.source_count == 2:
                result.verification_method = "dual_match"
                result.verification_consensus = (
                    result.abn_gmb_match_confidence != MatchConfidence.NO_MATCH
                )
            else:
                result.verification_method = "single_source"
                result.verification_consensus = False
            
            # Overall success if we have at least email OR phone
            result.success = bool(result.email or result.phone)
            
            # Log to database
            await self._log_lineage(db, result)
            
            return EngineResult.ok(
                data=result,
                metadata={
                    "source_count": result.source_count,
                    "total_cost_aud": str(result.total_cost_aud),
                    "verification_method": result.verification_method,
                },
            )
            
        except Exception as e:
            logger.exception(f"Waterfall verification failed for lead {lead_id}")
            result.errors.append(f"Waterfall exception: {str(e)}")
            result.lineage = lineage
            result.total_cost_aud = total_cost
            return EngineResult.error(
                error=str(e),
                metadata={"partial_result": result},
            )
    
    # ============================================
    # ALS CALCULATION
    # ============================================
    
    def calculate_als_score(
        self,
        base_als_score: int,
        waterfall_result: WaterfallResult,
        intent_signals: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Calculate ALS with waterfall verification bonus.
        
        The ALS combines:
        - Base ALS score (0-100)
        - Multi-source verification bonus (+15 for 3+ sources)
        - Intent signal multipliers
        
        Args:
            base_als_score: Original ALS (0-100)
            waterfall_result: Result from verify_lead()
            intent_signals: Optional dict with ad_volume, is_hiring, etc.
        
        Returns:
            Dict with score breakdown:
            {
                "final_score": 92,
                "base_score": 75,
                "verification_bonus": 15,
                "intent_bonus": 2,
                "sources_used": ["abn", "gmb", "hunter_io"],
                "verification_method": "triple_check"
            }
        """
        components = {
            "base_score": base_als_score,
            "verification_bonus": 0,
            "intent_bonus": 0,
            "sources_used": waterfall_result.verification_sources,
            "verification_method": waterfall_result.verification_method,
        }
        
        # Multi-source verification bonus
        if waterfall_result.source_count >= 3:
            components["verification_bonus"] = MULTI_SOURCE_BONUS
        
        # Intent signal bonus
        if intent_signals:
            intent_bonus = 0
            
            # Ad volume signal: >50 ads running >60 days
            ad_volume = intent_signals.get("ad_volume", 0)
            ad_longevity = intent_signals.get("ad_longevity_days", 0)
            if ad_volume >= 50 and ad_longevity >= 60:
                intent_bonus += 10  # High-intent advertiser
            elif ad_volume >= 20:
                intent_bonus += 5   # Active advertiser
            
            # Hiring signal
            if intent_signals.get("is_hiring"):
                intent_bonus += 3
            
            # Funding signal
            if intent_signals.get("recent_funding"):
                intent_bonus += 5
            
            components["intent_bonus"] = min(intent_bonus, 15)  # Cap at 15
        
        # Calculate final score (capped at 100)
        final_score = min(
            100,
            components["base_score"] +
            components["verification_bonus"] +
            components["intent_bonus"]
        )
        
        components["final_score"] = final_score
        
        return components
    
    # ============================================
    # TIER IMPLEMENTATIONS
    # ============================================
    
    async def _tier1_abn_seed(
        self,
        company_name: str,
        postcode: str,
        state: str,
    ) -> Optional[ABNRecord]:
        """
        Tier 1: Look up company in ABN database.
        
        Uses ABN Lookup API or local bulk extract cache.
        """
        if self._abn_client is None:
            logger.warning("ABN client not configured — skipping Tier 1")
            return None
        
        try:
            # Search by name + postcode + state
            results = await self._abn_client.search_by_name(
                name=company_name,
                postcode=postcode,
                state=state,
                active_only=True,
            )
            
            if results and len(results) > 0:
                # Return best match (API should return sorted by relevance)
                return results[0]
            
            return None
            
        except Exception as e:
            logger.error(f"ABN lookup failed: {e}")
            return None
    
    async def _tier1_25_asic_verify(
        self,
        acn: Optional[str],
        abn: Optional[str],
    ) -> Optional[ASICVerifyRecord]:
        """
        Tier 1.25: ASIC Business Registry verification via ABR SearchByASIC.
        
        CEO Directive #039: Implemented to fix 55% fuzzy match failure.
        Uses ABR Web Services (SearchByASICv201408) to get ASIC-registered
        business name for improved T2 GMB matching.
        
        Directors[] left null pending ASIC DSP application approval.
        
        Args:
            acn: Australian Company Number from T1 (preferred)
            abn: Australian Business Number fallback
            
        Returns:
            ASICVerifyRecord with registered_name, or None if lookup fails
        """
        if self._abn_client is None:
            logger.warning("ABN client not configured — skipping T1.25 ASIC verify")
            return None
        
        # Need ACN for ASIC lookup
        if not acn:
            logger.info("T1.25: No ACN available — skipping ASIC verify")
            return None
        
        try:
            # Use ABR SearchByASIC to get ASIC-registered data
            result = await self._abn_client.search_by_acn(acn)
            
            if not result:
                logger.info(f"T1.25: No ASIC record found for ACN {acn}")
                return None
            
            # Extract registered business name (clean, official)
            # Priority: business_names (ASIC-registered) > legal_name
            business_names = result.get("business_names", [])
            legal_name = result.get("legal_name", "") or result.get("entity_name", "")
            
            # Use first ASIC-registered business name if available
            # These are cleaner for GMB matching (e.g., "Efficient Media" vs "EFFICIENT MEDIA PTY LTD")
            if business_names and len(business_names) > 0:
                registered_name = business_names[0]
            else:
                # Fallback to legal name, cleaned
                registered_name = self._clean_company_name(legal_name)
            
            logger.info(f"T1.25: ASIC registered_name = '{registered_name}' for ACN {acn}")
            
            return ASICVerifyRecord(
                acn=acn,
                registered_name=registered_name,
                business_names=business_names,
                entity_type=result.get("entity_type", ""),
                state=result.get("state", ""),
                postcode=result.get("postcode", ""),
                directors=None,  # Pending ASIC DSP approval - CEO Directive #039
            )
            
        except Exception as e:
            logger.error(f"T1.25 ASIC verify failed for ACN {acn}: {e}")
            return None
    
    async def _tier_dm0_linkedin_discovery(
        self,
        registered_name: str,
        state: str = "AU",
    ) -> Optional[DMCandidate]:
        """
        Tier DM-0: LinkedIn Decision Maker Discovery.
        
        CEO Directive #040 Part C: Uses DataForSEO SERP to find LinkedIn profiles,
        then Bright Data to scrape profile details, with local title filtering.
        
        Pipeline:
        1. DataForSEO SERP: site:linkedin.com/in "{registered_name}" founder OR director OR CEO OR owner OR MD
        2. Extract LinkedIn profile URLs (max 5)
        3. Bright Data LinkedIn Profile scrape per URL (gd_l1viktl72bvl7bjuj0)
        4. Local title filter → return top 1 as dm_candidate
        
        Args:
            registered_name: Company name from T1.25 (ASIC registered_name preferred)
            state: Australian state for location filtering (default: "AU")
        
        Returns:
            DMCandidate with dm_name, dm_title, dm_linkedin_url, or None if not found
        
        Cost: ~$0.0165 AUD (DataForSEO SERP $0.009 + up to 5 × Bright Data $0.0015)
        """
        import base64
        
        # DataForSEO credentials
        dataforseo_login = os.getenv("DATAFORSEO_LOGIN")
        dataforseo_password = os.getenv("DATAFORSEO_PASSWORD")
        brightdata_api_key = os.getenv("BRIGHTDATA_API_KEY")
        
        if not dataforseo_login or not dataforseo_password:
            logger.warning("DataForSEO credentials not set — skipping T-DM0")
            return None
        
        if not brightdata_api_key:
            logger.warning("BRIGHTDATA_API_KEY not set — skipping T-DM0 profile scraping")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # ========== STEP 1: DataForSEO SERP Query ==========
                # Query: site:linkedin.com/in "{registered_name}" founder OR director OR CEO OR owner OR MD
                search_query = f'site:linkedin.com/in "{registered_name}" founder OR director OR CEO OR owner OR MD'
                
                # DataForSEO location codes: 2036 = Australia
                serp_payload = [{
                    "keyword": search_query,
                    "location_code": 2036,
                    "language_code": "en",
                    "depth": 10,
                }]
                
                # Basic auth for DataForSEO
                auth_str = f"{dataforseo_login}:{dataforseo_password}"
                auth_bytes = base64.b64encode(auth_str.encode()).decode()
                
                serp_resp = await client.post(
                    "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
                    headers={
                        "Authorization": f"Basic {auth_bytes}",
                        "Content-Type": "application/json",
                    },
                    json=serp_payload,
                )
                serp_resp.raise_for_status()
                serp_data = serp_resp.json()
                
                # Extract items from SERP response
                items = []
                if (serp_data.get("tasks") and 
                    serp_data["tasks"][0].get("result") and
                    serp_data["tasks"][0]["result"][0].get("items")):
                    items = serp_data["tasks"][0]["result"][0]["items"]
                
                if not items:
                    logger.info(f"T-DM0: No LinkedIn profiles found for '{registered_name}'")
                    return None
                
                # ========== STEP 2: Extract LinkedIn Profile URLs (max 5) ==========
                linkedin_urls = []
                for item in items[:10]:  # Check top 10 SERP results
                    url = item.get("url", "")
                    if "linkedin.com/in/" in url and url not in linkedin_urls:
                        linkedin_urls.append(url)
                    if len(linkedin_urls) >= 5:
                        break
                
                if not linkedin_urls:
                    logger.info(f"T-DM0: No linkedin.com/in/ URLs in SERP results for '{registered_name}'")
                    return None
                
                logger.info(f"T-DM0: Found {len(linkedin_urls)} LinkedIn profile URLs for '{registered_name}'")
                
                # ========== STEP 3: Bright Data LinkedIn Profile Scrape ==========
                # Dataset: gd_l1viktl72bvl7bjuj0 (LinkedIn People)
                profiles = []
                
                for profile_url in linkedin_urls:
                    try:
                        # Trigger scrape
                        trigger_resp = await client.post(
                            "https://api.brightdata.com/datasets/v3/trigger",
                            params={
                                "dataset_id": "gd_l1viktl72bvl7bjuj0",
                                "include_errors": "true",
                            },
                            headers={
                                "Authorization": f"Bearer {brightdata_api_key}",
                                "Content-Type": "application/json",
                            },
                            json=[{"url": profile_url}],
                        )
                        trigger_resp.raise_for_status()
                        snapshot_id = trigger_resp.json().get("snapshot_id")
                        
                        if not snapshot_id:
                            logger.warning(f"T-DM0: No snapshot_id for {profile_url}")
                            continue
                        
                        # Poll for completion (max 2 minutes per profile)
                        profile_data = None
                        for _ in range(24):  # 24 × 5s = 120s
                            await asyncio.sleep(5)
                            status_resp = await client.get(
                                f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
                                headers={"Authorization": f"Bearer {brightdata_api_key}"},
                            )
                            status_data = status_resp.json()
                            if status_data.get("status") == "ready":
                                # Download result
                                data_resp = await client.get(
                                    f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                                    params={"format": "json"},
                                    headers={"Authorization": f"Bearer {brightdata_api_key}"},
                                )
                                result_list = data_resp.json()
                                if result_list and len(result_list) > 0:
                                    profile_data = result_list[0]
                                break
                            elif status_data.get("status") == "failed":
                                logger.warning(f"T-DM0: Bright Data scrape failed for {profile_url}")
                                break
                        
                        if profile_data and "error" not in profile_data:
                            profiles.append({
                                "url": profile_url,
                                "data": profile_data,
                            })
                    
                    except Exception as e:
                        logger.warning(f"T-DM0: Error scraping {profile_url}: {e}")
                        continue
                
                if not profiles:
                    logger.info(f"T-DM0: No valid profiles scraped for '{registered_name}'")
                    return None
                
                # ========== STEP 4: Local Title Filter ==========
                candidates = []
                
                for profile in profiles:
                    data = profile["data"]
                    name = data.get("name", "") or data.get("full_name", "")
                    title = data.get("headline", "") or data.get("occupation", "") or ""
                    current_company = data.get("current_company_name", "") or ""
                    
                    # Check for experience entries with current company
                    experiences = data.get("experience", []) or []
                    for exp in experiences:
                        if exp.get("is_current"):
                            current_company = exp.get("company_name", "") or current_company
                            title = exp.get("title", "") or title
                            break
                    
                    # Calculate company match score
                    company_match_score = fuzz.token_set_ratio(
                        registered_name.lower(), 
                        current_company.lower()
                    )
                    
                    # Calculate title score based on DM_TITLE_SCORES
                    title_score = 0
                    title_lower = title.lower()
                    for dm_title, score in DM_TITLE_SCORES.items():
                        if dm_title in title_lower:
                            title_score = max(title_score, score)
                    
                    # Only consider if company match is reasonable (>60%) and has DM title
                    if company_match_score >= 60 and title_score > 0:
                        candidates.append(DMCandidate(
                            dm_name=name,
                            dm_title=title,
                            dm_linkedin_url=profile["url"],
                            company_match_score=company_match_score,
                            title_score=title_score,
                        ))
                
                if not candidates:
                    logger.info(f"T-DM0: No DM candidates passed title filter for '{registered_name}'")
                    return None
                
                # Sort by title_score (desc), then company_match_score (desc)
                candidates.sort(key=lambda c: (c.title_score, c.company_match_score), reverse=True)
                
                best_candidate = candidates[0]
                logger.info(
                    f"T-DM0: Found DM candidate '{best_candidate.dm_name}' ({best_candidate.dm_title}) "
                    f"for '{registered_name}' — company_match={best_candidate.company_match_score}%, "
                    f"title_score={best_candidate.title_score}"
                )
                
                return best_candidate
        
        except httpx.HTTPStatusError as e:
            logger.error(f"T-DM0 HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"T-DM0 failed for '{registered_name}': {e}")
            return None
    
    def _clean_company_name(self, name: str) -> str:
        """
        Clean company name for better fuzzy matching.
        
        Removes common suffixes like PTY LTD, LIMITED, etc.
        Normalizes case to title case.
        """
        if not name:
            return ""
        
        import re
        
        # Remove common Australian company suffixes
        suffixes_pattern = r'\s+(PTY\.?\s*LTD\.?|LIMITED|LTD\.?|PROPRIETARY|INC\.?|INCORPORATED|HOLDINGS?|GROUP|AUSTRALIA|AUST\.?|AU)\s*$'
        cleaned = re.sub(suffixes_pattern, '', name.upper(), flags=re.IGNORECASE)
        
        # Normalize to title case
        cleaned = cleaned.strip().title()
        
        return cleaned
    
    async def _tier2_gmb_scraper(
        self,
        company_name: str,
        postcode: str,
        state: str,
    ) -> Optional[GMBRecord]:
        """
        Tier 2: Scrape Google Maps for business info via Bright Data.
        
        CEO Directive #036: Replaced deprecated Apify with Bright Data Web Scraper API.
        Dataset: gd_m8ebnr0q2qlklc02fz (Google Maps Business Information)
        Method: discover_by=location
        """
        api_key = os.getenv("BRIGHTDATA_API_KEY")
        if not api_key:
            logger.warning("BRIGHTDATA_API_KEY not set — skipping Tier 2")
            return None
        
        # Map state code to city for better search results
        state_city_map = {
            "NSW": "Sydney", "VIC": "Melbourne", "QLD": "Brisbane",
            "WA": "Perth", "SA": "Adelaide", "TAS": "Hobart",
            "ACT": "Canberra", "NT": "Darwin",
        }
        city = state_city_map.get(state, state)
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Step 1: Trigger collection
                trigger_resp = await client.post(
                    "https://api.brightdata.com/datasets/v3/trigger",
                    params={
                        "dataset_id": "gd_m8ebnr0q2qlklc02fz",
                        "type": "discover_new",
                        "discover_by": "location",
                        "notify": "false",
                        "include_errors": "true",
                    },
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"input": [{"country": "AU", "keyword": f"{company_name} {city}", "lat": ""}]},
                )
                trigger_resp.raise_for_status()
                snapshot_id = trigger_resp.json().get("snapshot_id")
                if not snapshot_id:
                    logger.error("Bright Data trigger returned no snapshot_id")
                    return None
                
                logger.info(f"Bright Data T2 triggered: {snapshot_id}")
                
                # Step 2: Poll for completion (max 3 minutes)
                for _ in range(18):  # 18 x 10s = 180s
                    await asyncio.sleep(10)
                    status_resp = await client.get(
                        f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    status_data = status_resp.json()
                    if status_data.get("status") == "ready":
                        break
                else:
                    logger.warning(f"Bright Data T2 timeout for {company_name}")
                    return None
                
                # Step 3: Fetch results
                data_resp = await client.get(
                    f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                    params={"format": "json"},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                results = data_resp.json()
                
                if not results or len(results) == 0:
                    logger.info(f"Bright Data T2 returned no results for {company_name}")
                    return None
                
                # Step 4: Find best match by fuzzy name similarity
                best_match = None
                best_score = 0
                
                for r in results:
                    if "error" in r:
                        continue
                    name = r.get("name", "")
                    score = fuzz.ratio(company_name.lower(), name.lower())
                    if score > best_score:
                        best_score = score
                        best_match = r
                
                if best_score < FUZZY_MATCH_THRESHOLD:
                    logger.info(f"Bright Data T2: best match score {best_score} below threshold for {company_name}")
                    return None
                
                # Step 5: Parse into GMBRecord
                return GMBRecord(
                    google_place_id=best_match.get("place_id", ""),
                    business_name=best_match.get("name", ""),
                    phone=best_match.get("phone_number"),
                    website=best_match.get("open_website"),
                    address=best_match.get("address", ""),
                    postcode=self._extract_postcode(best_match.get("address", "")),
                    state=state,
                    lat=best_match.get("lat", 0.0),
                    lng=best_match.get("lon", 0.0),
                    rating=best_match.get("rating"),
                    review_count=best_match.get("reviews_count", 0) or 0,
                    categories=best_match.get("all_categories", []),
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Bright Data T2 HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Bright Data T2 failed: {e}")
            return None
    
    def _extract_postcode(self, address: str) -> str:
        """Extract Australian postcode (4 digits) from address string."""
        import re
        match = re.search(r'\b(\d{4})\b', address)
        return match.group(1) if match else ""
    
    async def _tier3_hunter_io(
        self,
        domain: str,
        company_name: str,
    ) -> Optional[HunterResult]:
        """
        Tier 3: Find and verify email via Hunter.io.
        """
        if self._hunter_client is None:
            logger.warning("Hunter.io client not configured — skipping Tier 3")
            return None
        
        try:
            # Domain search for contacts
            result = await self._hunter_client.domain_search(
                domain=domain,
                company=company_name,
            )
            
            if result and result.email:
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Hunter.io failed: {e}")
            return None
    
    async def _tier4_zerobounce(
        self,
        email: str,
    ) -> Optional[ZeroBounceResult]:
        """
        Tier 4: Premium verification via ZeroBounce.
        """
        if self._zerobounce_client is None:
            logger.warning("ZeroBounce client not configured — skipping Tier 4")
            return None
        
        try:
            result = await self._zerobounce_client.validate(email)
            return result
            
        except Exception as e:
            logger.error(f"ZeroBounce failed: {e}")
            return None
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    def _match_abn_gmb(
        self,
        abn: ABNRecord,
        gmb: GMBRecord,
        asic: Optional[ASICVerifyRecord] = None,
    ) -> tuple[MatchConfidence, int]:
        """
        Match ABN record to GMB record using fuzzy matching.
        
        CEO Directive #039: Prioritizes ASIC registered_name when available
        for improved match rates (fixes 55% failure).
        
        Args:
            abn: ABN record from T1
            gmb: GMB record from T2
            asic: Optional ASIC verify record from T1.25
        
        Returns:
            Tuple of (MatchConfidence, match_score_percentage)
        """
        # Check postcode first (must match or be adjacent)
        if abn.postcode != gmb.postcode:
            # Allow adjacent postcodes (within 10)
            try:
                if abs(int(abn.postcode) - int(gmb.postcode)) > 10:
                    return MatchConfidence.NO_MATCH, 0
            except ValueError:
                return MatchConfidence.NO_MATCH, 0
        
        # Build list of names to check
        # CEO Directive #039: ASIC registered_name takes priority (cleaner, normalized)
        names_to_check = []
        
        if asic and asic.registered_name:
            # Priority 1: ASIC registered name (clean, normalized)
            names_to_check.append(asic.registered_name)
            # Priority 2: All ASIC business names
            names_to_check.extend(asic.business_names or [])
        
        # Priority 3: ABN legal name and business names (fallback)
        names_to_check.append(abn.legal_name)
        names_to_check.extend(abn.business_names)
        
        # Also try cleaned version of legal name
        cleaned_legal = self._clean_company_name(abn.legal_name)
        if cleaned_legal and cleaned_legal not in names_to_check:
            names_to_check.append(cleaned_legal)
        
        best_score = 0
        best_match_name = ""
        
        for name in names_to_check:
            if not name:
                continue
            score = fuzz.ratio(name.lower(), gmb.business_name.lower())
            # Also try token_set_ratio for word order independence
            token_score = fuzz.token_set_ratio(name.lower(), gmb.business_name.lower())
            current_best = max(score, token_score)
            if current_best > best_score:
                best_score = current_best
                best_match_name = name
        
        # Log the match attempt for debugging
        logger.debug(
            f"ABN↔GMB match: best='{best_match_name}' vs GMB='{gmb.business_name}' "
            f"score={best_score}% (threshold={FUZZY_MATCH_THRESHOLD}%)"
        )
        
        # Determine confidence level
        if best_score >= 95:
            return MatchConfidence.EXACT, best_score
        elif best_score >= HIGH_CONFIDENCE_THRESHOLD:
            return MatchConfidence.HIGH, best_score
        elif best_score >= MEDIUM_CONFIDENCE_THRESHOLD:
            return MatchConfidence.MEDIUM, best_score
        elif best_score >= FUZZY_MATCH_THRESHOLD:
            return MatchConfidence.LOW, best_score
        else:
            return MatchConfidence.NO_MATCH, best_score
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        
        return domain
    
    async def _log_lineage(
        self,
        db: AsyncSession,
        result: WaterfallResult,
    ) -> None:
        """
        Log all lineage steps to lead_lineage_log table.
        """
        try:
            for step in result.lineage:
                stmt = insert("lead_lineage_log").values(
                    id=uuid4(),
                    lead_id=result.lead_id,
                    step_number=step.step_number,
                    step_type=step.step_type,
                    source_name=step.source_name,
                    fields_added=step.data_added,
                    cost_aud=step.cost_aud,
                    latency_ms=step.latency_ms,
                    success=step.success,
                    error_message=step.error_message,
                    created_at=datetime.utcnow(),
                )
                await db.execute(stmt)
            
            await db.commit()
            logger.info(
                f"Logged {len(result.lineage)} lineage steps for lead {result.lead_id}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log lineage: {e}")
            await db.rollback()


# ============================================
# FACTORY FUNCTION
# ============================================

def get_waterfall_worker(
    abn_client=None,
    gmb_scraper=None,
    hunter_client=None,
    zerobounce_client=None,
) -> WaterfallVerificationWorker:
    """Get singleton WaterfallVerificationWorker instance."""
    return WaterfallVerificationWorker(
        abn_client=abn_client,
        gmb_scraper=gmb_scraper,
        hunter_client=hunter_client,
        zerobounce_client=zerobounce_client,
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument
# [x] No imports from orchestration
# [x] All costs in AUD
# [x] Fuzzy matching for ABN ↔ GMB
# [x] Error handling for mismatches
# [x] +15 bonus for 3+ source verification
# [x] Lineage logging to database
# [x] Type hints throughout
# [x] Docstrings on all public methods
