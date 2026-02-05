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
DESCRIPTION: Moving from Apollo SPOF to ABN + GMB + Hunter.io + ZeroBounce waterfall
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

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
    GMB_SCRAPER = "gmb_scraper"
    HUNTER_IO = "hunter_io"
    ZEROBOUNCE = "zerobounce"


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
    VerificationTier.GMB_SCRAPER: Decimal("0.0062"), # Apify ~$6.20/1000
    VerificationTier.HUNTER_IO: Decimal("0.0064"),   # Hunter.io Growth tier
    VerificationTier.ZEROBOUNCE: Decimal("0.010"),   # ZeroBounce average
}

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
    email: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    
    # Match quality
    abn_gmb_match_confidence: MatchConfidence
    abn_gmb_match_score: int
    
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
            gmb_scraper: GMB/Apify scraper client
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
            
            # ========== TIER 2: GMB SCRAPER ==========
            step_number += 1
            start_time = datetime.utcnow()
            
            gmb_result = await self._tier2_gmb_scraper(company_name, postcode, state)
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Handle ABN ↔ GMB matching with error handling
            match_confidence = MatchConfidence.NO_MATCH
            match_score = 0
            gmb_success = False
            data_added = []
            
            if gmb_result:
                if abn_result:
                    # Both ABN and GMB found — attempt fuzzy match
                    match_confidence, match_score = self._match_abn_gmb(
                        abn_result, gmb_result
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
                        errors.append(
                            f"ABN↔GMB mismatch: ABN name '{abn_result.legal_name}' "
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
    
    async def _tier2_gmb_scraper(
        self,
        company_name: str,
        postcode: str,
        state: str,
    ) -> Optional[GMBRecord]:
        """
        Tier 2: Scrape Google Maps for business info.
        
        Uses Apify Google Maps Scraper or similar.
        """
        if self._gmb_scraper is None:
            logger.warning("GMB scraper not configured — skipping Tier 2")
            return None
        
        try:
            # Search by company name + location
            results = await self._gmb_scraper.search(
                query=f"{company_name} {postcode} {state} Australia",
                limit=5,
            )
            
            if results and len(results) > 0:
                # Find best match by name similarity
                best_match = None
                best_score = 0
                
                for r in results:
                    score = fuzz.ratio(
                        company_name.lower(),
                        r.business_name.lower()
                    )
                    if score > best_score:
                        best_score = score
                        best_match = r
                
                if best_score >= FUZZY_MATCH_THRESHOLD:
                    return best_match
            
            return None
            
        except Exception as e:
            logger.error(f"GMB scraper failed: {e}")
            return None
    
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
    ) -> tuple[MatchConfidence, int]:
        """
        Match ABN record to GMB record using fuzzy matching.
        
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
        
        # Fuzzy match on business name
        # Try legal name and all trading names
        names_to_check = [abn.legal_name] + abn.business_names
        
        best_score = 0
        for name in names_to_check:
            score = fuzz.ratio(name.lower(), gmb.business_name.lower())
            # Also try token_set_ratio for word order independence
            token_score = fuzz.token_set_ratio(name.lower(), gmb.business_name.lower())
            best_score = max(best_score, score, token_score)
        
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
