"""
FILE: src/enrichment/waterfall_v2.py  
PURPOSE: Full Phase 1→2→3 pipeline for Waterfall v2
PHASE: SIEGE (CEO Directive #023)
TASK: Waterfall v2 Pipeline Implementation
DEPENDENCIES:
  - src/enrichment/discovery_modes.py
  - src/integrations/bright_data_client.py (TBD)
  - src/integrations/abn_client.py
  - src/integrations/hunter.py
  - src/integrations/kaspr.py
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
    Tier 2.5: LinkedIn People Profile - $0.0015 (ALS >= 30)
    Tier 3: Hunter.io Email - $0.012 (ALS >= 30)
    Tier 5: Kaspr Direct Contact - $0.45 (ALS >= 85)

Created: 2026-02-16 by subagent (CEO Directive #023)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import structlog

from src.enrichment.discovery_modes import (
    DiscoveryMode, 
    CampaignConfig, 
    DiscoveryRecord,
    ABNFirstDiscovery,
    MapsFirstDiscovery, 
    ParallelDiscovery
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
    employees: List[dict] = field(default_factory=list)
    decision_makers: List[dict] = field(default_factory=list)
    company_size: str = None
    industry: str = None
    founded: int = None
    headquarters: str = None
    specialties: str = None
    
    # Contact enrichment fields (Tier 2.5 + 3)
    email: str = None
    email_confidence: float = None
    direct_mobile: str = None
    contact_source: str = None
    
    # Kaspr Premium fields (Tier 5)
    kaspr_data: dict = field(default_factory=dict)
    verified_contacts: List[dict] = field(default_factory=list)
    
    # Scoring and quality
    als_score: int = 0
    als_breakdown: dict = field(default_factory=dict)
    confidence_score: float = 0.0
    
    # Tracking and metadata
    enrichment_tiers_completed: List[str] = field(default_factory=list)
    cost_aud: float = 0.0
    discovery_source: str = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Error tracking
    enrichment_errors: List[dict] = field(default_factory=list)


class WaterfallV2:
    """
    Siege Waterfall v2 — Full enrichment pipeline
    
    PHASE 1: Discovery (Mode A/B/C)
    PHASE 2: Enrichment (Tiers 1 → 5, with gates)
    PHASE 3: Scoring (ALS)
    
    Quality Gates:
    - PRE_ALS_GATE: Minimum score to continue past Tier 2 (cost control)
    - HOT_THRESHOLD: Minimum score for Tier 5 Kaspr enrichment (premium leads only)
    """
    
    PRE_ALS_GATE = 30      # Minimum score to continue past Tier 2
    HOT_THRESHOLD = 85     # Minimum for Tier 5 (Kaspr)
    
    # Cost constants (AUD)
    COSTS = {
        "serp_maps": 0.0015,
        "serp_linkedin": 0.0015, 
        "linkedin_company": 0.0015,
        "linkedin_people": 0.0015,
        "hunter_email": 0.012,
        "kaspr_contact": 0.45
    }
    
    def __init__(
        self, 
        bright_data_client=None,
        abn_client=None, 
        hunter_client=None, 
        kaspr_client=None
    ):
        """Initialize waterfall with all integration clients"""
        self.bd = bright_data_client
        self.abn_client = abn_client
        self.hunter = hunter_client
        self.kaspr = kaspr_client
        
        # Initialize discovery engines
        self.abn_discovery = ABNFirstDiscovery(abn_client=abn_client)
        self.maps_discovery = MapsFirstDiscovery(
            bright_data_client=bright_data_client,
            abn_client=abn_client
        )
        self.parallel_discovery = ParallelDiscovery(
            abn_client=abn_client,
            bright_data_client=bright_data_client
        )
    
    # PHASE 1: DISCOVERY
    
    async def run_discovery(self, config: CampaignConfig) -> List[LeadRecord]:
        """PHASE 1: Run discovery mode based on campaign config"""
        logger.info(f"Phase 1: Starting discovery with mode={config.mode.value}")
        
        try:
            # Select discovery engine based on mode
            if config.mode == DiscoveryMode.ABN_FIRST:
                discovery_records = await self.abn_discovery.discover(config)
            elif config.mode == DiscoveryMode.MAPS_FIRST:
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
            discovery_source=record.discovery_source
        )
        
        # Set initial tiers as completed based on discovery source
        if record.discovery_source == "abn_api":
            lead.enrichment_tiers_completed = ["tier_1"]
        elif record.discovery_source == "google_maps":
            lead.enrichment_tiers_completed = ["tier_1", "tier_1_5a"]
            lead.cost_aud += self.COSTS["serp_maps"]
        elif record.discovery_source == "both":
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
                    name=lead.business_name,
                    state=lead.state,
                    isCurrentIndicator="Y"
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
            error = {"tier": "tier_1", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 1 failed for {lead.id}: {str(e)}")
        
        return lead
    
    async def enrich_tier_1_5a(self, lead: LeadRecord) -> LeadRecord:
        """Tier 1.5a: SERP Google Maps - $0.0015 - If missing phone/website"""
        if "tier_1_5a" in lead.enrichment_tiers_completed:
            return lead
        
        # Skip if we already have phone and website
        if lead.phone and lead.website:
            lead.enrichment_tiers_completed.append("tier_1_5a")
            return lead
        
        logger.debug(f"Tier 1.5a: Google Maps enrichment for {lead.business_name}")
        
        try:
            if not self.bd:
                raise ValueError("Bright Data client not configured")
            
            # Search Google Maps for business
            search_query = f"{lead.business_name} {lead.address or lead.state or ''}"
            gmb_results = await self.bd.search_google_maps(
                query=search_query.strip(),
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
            error = {"tier": "tier_1_5a", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 1.5a failed for {lead.id}: {str(e)}")
        
        return lead
    
    async def enrich_tier_1_5b(self, lead: LeadRecord) -> LeadRecord:
        """Tier 1.5b: SERP Google LinkedIn Discovery - $0.0015 - Find LinkedIn URL"""
        if "tier_1_5b" in lead.enrichment_tiers_completed:
            return lead
        
        logger.debug(f"Tier 1.5b: LinkedIn URL discovery for {lead.business_name}")
        
        try:
            if not self.bd:
                raise ValueError("Bright Data client not configured")
            
            # Search LinkedIn company URL via SERP
            search_query = f'site:linkedin.com/company "{lead.business_name}" {lead.address or lead.state or ""}'
            
            serp_results = await self.bd.search_serp(
                query=search_query.strip(),
                max_results=10
            )
            
            if serp_results:
                # Find LinkedIn company URL in results
                for result in serp_results:
                    url = result.get("url", "")
                    if "linkedin.com/company/" in url and not url.endswith("/jobs"):
                        lead.linkedin_company_url = url
                        break
            
            lead.enrichment_tiers_completed.append("tier_1_5b")
            lead.cost_aud += self.COSTS["serp_linkedin"]
            logger.debug(f"Tier 1.5b completed for {lead.id}")
            
        except Exception as e:
            error = {"tier": "tier_1_5b", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
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
            
            if linkedin_data:
                lead.linkedin_data = linkedin_data
                
                # Extract key fields
                lead.company_size = linkedin_data.get("company_size")
                lead.industry = linkedin_data.get("industries")
                lead.founded = linkedin_data.get("founded")
                lead.headquarters = linkedin_data.get("headquarters")
                lead.specialties = linkedin_data.get("specialties")
                
                # Extract employee data for decision makers
                employees = linkedin_data.get("employees", [])
                if employees:
                    lead.employees = employees
                    # Filter for decision makers (C-level, VP, Director, Manager)
                    lead.decision_makers = self._extract_decision_makers(employees)
            
            lead.enrichment_tiers_completed.append("tier_2")
            lead.cost_aud += self.COSTS["linkedin_company"]
            logger.debug(f"Tier 2 completed for {lead.id}")
            
        except Exception as e:
            error = {"tier": "tier_2", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 2 failed for {lead.id}: {str(e)}")
        
        return lead
    
    def _extract_decision_makers(self, employees: List[dict]) -> List[dict]:
        """Extract decision makers from employee list"""
        decision_makers = []
        decision_keywords = [
            "ceo", "cto", "cfo", "cmo", "coo", "chief", "president", "founder",
            "vp", "vice president", "director", "head of", "manager"
        ]
        
        for employee in employees:
            title = employee.get("title", "").lower()
            if any(keyword in title for keyword in decision_keywords):
                decision_makers.append(employee)
        
        return decision_makers[:5]  # Limit to top 5
    
    # PHASE 3: SCORING AND QUALITY GATES
    
    def calculate_als(self, lead: LeadRecord) -> int:
        """Calculate Agency Lead Score (0-100)"""
        score_breakdown = {
            "company_fit": 0,      # 25 pts max
            "authority": 0,        # 25 pts max  
            "timing": 0,          # 15 pts max
            "data_quality": 0,    # 20 pts max
            "engagement": 0       # 15 pts max
        }
        
        # Company Fit (25 points)
        if lead.industry:
            score_breakdown["company_fit"] += 10
        if lead.company_size and "11-50" in lead.company_size or "51-200" in lead.company_size:
            score_breakdown["company_fit"] += 10  # Sweet spot for agencies
        if lead.specialties:
            score_breakdown["company_fit"] += 5
        
        # Authority (25 points)
        if lead.decision_makers:
            score_breakdown["authority"] += min(len(lead.decision_makers) * 5, 15)
            # Bonus for C-level contacts
            c_level = sum(1 for dm in lead.decision_makers if any(
                keyword in dm.get("title", "").lower() 
                for keyword in ["ceo", "cto", "cfo", "cmo", "chief", "founder"]
            ))
            score_breakdown["authority"] += min(c_level * 5, 10)
        
        # Timing (15 points) - Based on recent activity signals
        if lead.linkedin_data.get("updates"):
            recent_updates = len(lead.linkedin_data["updates"])
            score_breakdown["timing"] += min(recent_updates * 2, 10)
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
        lead.als_breakdown = score_breakdown
        
        logger.debug(f"ALS calculated for {lead.id}: {total_score} (breakdown: {score_breakdown})")
        return total_score
    
    # PREMIUM ENRICHMENT TIERS (WITH GATES)
    
    async def enrich_tier_2_5(self, lead: LeadRecord) -> LeadRecord:
        """Tier 2.5: LinkedIn People Profile - $0.0015 - Only if ALS >= 30"""
        if "tier_2_5" in lead.enrichment_tiers_completed:
            return lead
        
        if lead.als_score < self.PRE_ALS_GATE:
            logger.debug(f"Tier 2.5 skipped for {lead.id} - ALS score {lead.als_score} below gate {self.PRE_ALS_GATE}")
            return lead
        
        if not lead.decision_makers:
            # Skip if no decision makers found
            lead.enrichment_tiers_completed.append("tier_2_5")
            return lead
        
        logger.debug(f"Tier 2.5: LinkedIn people profiles for {lead.business_name}")
        
        try:
            if not self.bd:
                raise ValueError("Bright Data client not configured")
            
            # Enrich decision maker profiles
            enriched_decision_makers = []
            
            for dm in lead.decision_makers[:3]:  # Limit to top 3 to control costs
                profile_url = dm.get("link")
                if profile_url:
                    profile_data = await self.bd.scrape_linkedin_profile(profile_url)
                    if profile_data:
                        dm.update(profile_data)
                        enriched_decision_makers.append(dm)
            
            if enriched_decision_makers:
                lead.decision_makers = enriched_decision_makers
            
            lead.enrichment_tiers_completed.append("tier_2_5")
            lead.cost_aud += self.COSTS["linkedin_people"]
            logger.debug(f"Tier 2.5 completed for {lead.id}")
            
        except Exception as e:
            error = {"tier": "tier_2_5", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 2.5 failed for {lead.id}: {str(e)}")
        
        return lead
    
    async def enrich_tier_3(self, lead: LeadRecord) -> LeadRecord:
        """Tier 3: Hunter.io Email - $0.012 - Only if ALS >= 30"""
        if "tier_3" in lead.enrichment_tiers_completed:
            return lead
        
        if lead.als_score < self.PRE_ALS_GATE:
            logger.debug(f"Tier 3 skipped for {lead.id} - ALS score {lead.als_score} below gate {self.PRE_ALS_GATE}")
            return lead
        
        if not lead.website:
            # Skip if no website for domain extraction
            lead.enrichment_tiers_completed.append("tier_3")
            return lead
        
        logger.debug(f"Tier 3: Hunter.io email enrichment for {lead.business_name}")
        
        try:
            if not self.hunter:
                raise ValueError("Hunter.io client not configured")
            
            # Extract domain from website
            domain = self._extract_domain(lead.website)
            if domain:
                # Find email addresses for domain
                email_results = await self.hunter.domain_search(domain)
                
                if email_results and email_results.get("emails"):
                    # Find best email (decision maker or generic contact)
                    best_email = self._select_best_email(email_results["emails"], lead.decision_makers)
                    if best_email:
                        lead.email = best_email.get("value")
                        lead.email_confidence = best_email.get("confidence", 0) / 100.0
                        lead.contact_source = "hunter"
            
            lead.enrichment_tiers_completed.append("tier_3")
            lead.cost_aud += self.COSTS["hunter_email"]
            logger.debug(f"Tier 3 completed for {lead.id}")
            
        except Exception as e:
            error = {"tier": "tier_3", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 3 failed for {lead.id}: {str(e)}")
        
        return lead
    
    def _extract_domain(self, website: str) -> Optional[str]:
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
    
    def _select_best_email(self, emails: List[dict], decision_makers: List[dict]) -> Optional[dict]:
        """Select best email from Hunter results"""
        if not emails:
            return None
        
        # Sort by confidence score first
        emails_sorted = sorted(emails, key=lambda e: e.get("confidence", 0), reverse=True)
        
        # If we have decision makers, try to match emails
        if decision_makers:
            dm_names = [dm.get("name", "").lower() for dm in decision_makers if dm.get("name")]
            
            for email in emails_sorted:
                email_address = email.get("value", "").lower()
                first_name = email.get("first_name", "").lower()
                last_name = email.get("last_name", "").lower()
                
                # Check if email matches any decision maker
                full_name = f"{first_name} {last_name}".strip()
                if any(name in full_name or full_name in name for name in dm_names if name):
                    return email
        
        # Fall back to highest confidence email
        return emails_sorted[0]
    
    async def enrich_tier_5(self, lead: LeadRecord) -> LeadRecord:
        """Tier 5: Kaspr Direct Contact - $0.45 - Only if ALS >= 85"""
        if "tier_5" in lead.enrichment_tiers_completed:
            return lead
        
        if lead.als_score < self.HOT_THRESHOLD:
            logger.debug(f"Tier 5 skipped for {lead.id} - ALS score {lead.als_score} below hot threshold {self.HOT_THRESHOLD}")
            return lead
        
        if not lead.decision_makers:
            # Skip if no decision makers to enrich
            lead.enrichment_tiers_completed.append("tier_5")
            return lead
        
        logger.debug(f"Tier 5: Kaspr premium contact enrichment for {lead.business_name}")
        
        try:
            if not self.kaspr:
                raise ValueError("Kaspr client not configured")
            
            # Enrich top decision makers with Kaspr
            verified_contacts = []
            
            for dm in lead.decision_makers[:2]:  # Limit to top 2 to control costs  
                linkedin_url = dm.get("link")
                if linkedin_url:
                    kaspr_data = await self.kaspr.enrich_contact(linkedin_url)
                    if kaspr_data:
                        verified_contacts.append(kaspr_data)
                        
                        # Update lead with best contact info
                        if not lead.direct_mobile and kaspr_data.get("mobile"):
                            lead.direct_mobile = kaspr_data["mobile"]
                        if not lead.email and kaspr_data.get("email"):
                            lead.email = kaspr_data["email"]
                            lead.email_confidence = 0.95  # Kaspr is high confidence
                            lead.contact_source = "kaspr"
            
            if verified_contacts:
                lead.verified_contacts = verified_contacts
                lead.kaspr_data = {
                    "contacts_enriched": len(verified_contacts),
                    "enrichment_timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            lead.enrichment_tiers_completed.append("tier_5")
            lead.cost_aud += self.COSTS["kaspr_contact"]
            logger.debug(f"Tier 5 completed for {lead.id}")
            
        except Exception as e:
            error = {"tier": "tier_5", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            lead.enrichment_errors.append(error)
            logger.warning(f"Tier 5 failed for {lead.id}: {str(e)}")
        
        return lead
    
    # FULL PIPELINE ORCHESTRATION
    
    async def run_full_pipeline(self, config: CampaignConfig) -> List[LeadRecord]:
        """Execute complete Phase 1 → 2 → 3 pipeline"""
        logger.info(f"Starting full Waterfall v2 pipeline for {config.industry} in {config.location}")
        
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
                lead = await self.enrich_tier_1(lead)
                lead = await self.enrich_tier_1_5a(lead)
                lead = await self.enrich_tier_1_5b(lead)
                lead = await self.enrich_tier_2(lead)
                
                # Phase 3: Initial ALS Scoring
                lead.als_score = self.calculate_als(lead)
                logger.debug(f"Initial ALS score for {lead.id}: {lead.als_score}")
                
                # Quality Gate Check - Continue enrichment only if score >= PRE_ALS_GATE
                if lead.als_score >= self.PRE_ALS_GATE:
                    logger.debug(f"Lead {lead.id} passed ALS gate ({lead.als_score} >= {self.PRE_ALS_GATE})")
                    
                    # Phase 2 continued: Premium Enrichment
                    lead = await self.enrich_tier_2_5(lead)
                    lead = await self.enrich_tier_3(lead)
                    lead = await self.enrich_tier_5(lead)
                    
                    # Phase 3: Final ALS Scoring
                    lead.als_score = self.calculate_als(lead)
                    logger.debug(f"Final ALS score for {lead.id}: {lead.als_score}")
                else:
                    logger.debug(f"Lead {lead.id} did not pass ALS gate ({lead.als_score} < {self.PRE_ALS_GATE})")
                
                # Update final metadata
                lead.updated_at = datetime.now(timezone.utc).isoformat()
                enriched.append(lead)
            
            # Pipeline summary
            total_cost = sum(lead.cost_aud for lead in enriched)
            high_quality_leads = len([lead for lead in enriched if lead.als_score >= self.HOT_THRESHOLD])
            
            logger.info(
                f"Waterfall v2 pipeline completed: {len(enriched)} leads processed, "
                f"{high_quality_leads} high-quality leads (ALS >= {self.HOT_THRESHOLD}), "
                f"Total cost: ${total_cost:.4f} AUD"
            )
            
            return enriched
            
        except Exception as e:
            logger.error(f"Full pipeline failed: {str(e)}")
            return []
    
    # UTILITY METHODS
    
    def get_pipeline_stats(self, leads: List[LeadRecord]) -> dict:
        """Get pipeline statistics and performance metrics"""
        if not leads:
            return {}
        
        stats = {
            "total_leads": len(leads),
            "total_cost_aud": sum(lead.cost_aud for lead in leads),
            "average_cost_per_lead": sum(lead.cost_aud for lead in leads) / len(leads),
            "als_distribution": {
                "hot_leads": len([l for l in leads if l.als_score >= self.HOT_THRESHOLD]),
                "qualified_leads": len([l for l in leads if l.als_score >= self.PRE_ALS_GATE]),
                "low_quality_leads": len([l for l in leads if l.als_score < self.PRE_ALS_GATE])
            },
            "enrichment_completion": {},
            "discovery_sources": {},
            "error_summary": {}
        }
        
        # Enrichment tier completion rates
        all_tiers = ["tier_1", "tier_1_5a", "tier_1_5b", "tier_2", "tier_2_5", "tier_3", "tier_5"]
        for tier in all_tiers:
            completed = len([l for l in leads if tier in l.enrichment_tiers_completed])
            stats["enrichment_completion"][tier] = {
                "completed": completed,
                "rate": completed / len(leads) if leads else 0
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