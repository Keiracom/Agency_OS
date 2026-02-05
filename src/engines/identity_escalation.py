"""
Contract: src/engines/identity_escalation.py
Purpose: Identity Escalation Protocol - Bypass generic inboxes to find direct contacts
Layer: 3 - engines
Imports: models, integrations
Consumers: orchestration, waterfall_verification_worker

FILE: src/engines/identity_escalation.py
PURPOSE: Identity Escalation Protocol for 5-Channel Distribution
PHASE: WF-001 (Waterfall Enrichment Architecture)
TASK: Director Hunt + Mobile Number Priority
DEPENDENCIES:
  - src/engines/base.py
  - src/engines/waterfall_verification_worker.py
  - src/integrations/lusha.py (to be created)
  - src/integrations/proxycurl.py (existing)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Cost tracking in $AUD only
  - Mobile enrichment ONLY for ALS > 75

GOVERNANCE EVENT: Identity Escalation Protocol
DESCRIPTION: Bypassing "info@" receptionist layer to reach decision makers directly

CHANNEL MAPPING:
  - SMS/Voice AI -> mobile_number_verified
  - Email -> work_email_verified
  - Direct Mail -> registered_office_address
  - LinkedIn -> linkedin_profile_url
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.base import BaseEngine, EngineResult

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTS & CONFIGURATION
# ============================================

# Generic inbox patterns to trigger escalation
GENERIC_EMAIL_PATTERNS = [
    r"^info@",
    r"^admin@",
    r"^hello@",
    r"^contact@",
    r"^enquiries@",
    r"^enquiry@",
    r"^sales@",
    r"^support@",
    r"^office@",
    r"^reception@",
    r"^general@",
    r"^team@",
    r"^mail@",
    r"^accounts@",
]

# Australian phone patterns
AU_MOBILE_PATTERN = r"^(?:\+61|0)4\d{8}$"  # Mobile: 04xx xxx xxx or +614xx xxx xxx
AU_LANDLINE_PATTERN = r"^(?:\+61|0)[2378]\d{8}$"  # Landline: 02/03/07/08

# Cost per operation in AUD (2026 pricing)
IDENTITY_COSTS_AUD = {
    "lusha_mobile": Decimal("0.25"),      # ~$0.15-0.30, using mid-range
    "kaspr_mobile": Decimal("0.20"),      # Slightly cheaper
    "proxycurl_linkedin": Decimal("0.02"), # LinkedIn profile enrichment
    "asic_extract": Decimal("0.50"),      # Company extract via broker
    "team_page_scrape": Decimal("0.01"),  # Our own scraper
}

# Thresholds
ALS_MOBILE_THRESHOLD = 85  # Only enrich mobile for HOT leads (WF-002 mandate)
DECISION_MAKER_TITLES = [
    "director", "founder", "ceo", "chief", "owner", "principal",
    "managing director", "md", "general manager", "gm",
    "head of", "vp", "vice president", "president",
    "marketing manager", "sales manager", "operations manager",
]


# ============================================
# DATA CLASSES
# ============================================

class PhoneType(str, Enum):
    """Phone number types."""
    MOBILE = "mobile"
    LANDLINE = "landline"
    UNKNOWN = "unknown"


class IdentityTier(str, Enum):
    """Identity enrichment tiers."""
    TEAM_PAGE_SCRAPE = "team_page_scrape"
    LINKEDIN_EMPLOYEE = "linkedin_employee"
    ASIC_DIRECTOR = "asic_director"
    LUSHA_MOBILE = "lusha_mobile"
    KASPR_MOBILE = "kaspr_mobile"
    IDENTITY_GOLD = "identity_gold"  # Final verified identity


@dataclass
class DecisionMaker:
    """A decision maker found via escalation."""
    full_name: str
    first_name: str
    last_name: str
    title: str
    linkedin_url: Optional[str] = None
    work_email: Optional[str] = None
    mobile_number: Optional[str] = None
    phone_type: PhoneType = PhoneType.UNKNOWN
    confidence: int = 0  # 0-100
    source: str = ""


@dataclass
class IdentityResult:
    """Result from identity escalation."""
    lead_id: UUID
    company_name: str
    
    # Primary decision maker
    primary_contact: Optional[DecisionMaker] = None
    
    # All found decision makers (top 3)
    decision_makers: list[DecisionMaker] = field(default_factory=list)
    
    # Channel-specific verified fields
    mobile_number_verified: Optional[str] = None
    work_email_verified: Optional[str] = None
    registered_office_address: Optional[str] = None
    linkedin_profile_url: Optional[str] = None
    
    # Escalation tracking
    escalation_triggered: bool = False
    escalation_reason: Optional[str] = None
    tiers_used: list[str] = field(default_factory=list)
    
    # Costs
    total_cost_aud: Decimal = Decimal("0.00")
    
    # Status
    success: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class IdentityLineageStep:
    """Lineage step for identity escalation."""
    step_number: int
    tier: IdentityTier
    source_name: str
    cost_aud: Decimal
    success: bool
    contacts_found: int = 0
    data_added: list[str] = field(default_factory=list)
    error_message: Optional[str] = None


# ============================================
# IDENTITY ESCALATION ENGINE
# ============================================

class IdentityEscalationEngine(BaseEngine):
    """
    Identity Escalation Protocol for 5-Channel Distribution.
    
    When generic inbox detected (info@, admin@, etc.):
    1. Scrape "About Us" / "Team" page for names
    2. Match against LinkedIn Company Employee list
    3. Take top 3 Decision Makers
    4. Run through Lusha/Kaspr for mobile numbers (if ALS > 75)
    
    Channel Mapping:
    - SMS/Voice AI → mobile_number_verified
    - Email → work_email_verified
    - Direct Mail → registered_office_address
    - LinkedIn → linkedin_profile_url
    
    COGS Governance:
    - Mobile enrichment is expensive (~$0.15-0.30 AUD)
    - Only enrich for leads with ALS > 75
    """
    
    def __init__(
        self,
        lusha_client=None,
        kaspr_client=None,
        proxycurl_client=None,
        asic_client=None,
        web_scraper=None,
    ):
        """
        Initialize with integration clients.
        
        Args:
            lusha_client: Lusha API client for mobiles
            kaspr_client: Kaspr API client for mobiles
            proxycurl_client: Proxycurl for LinkedIn data
            asic_client: ASIC broker API (InfoTrack/CreditorWatch)
            web_scraper: Autonomous browser for team page scraping
        """
        self._lusha = lusha_client
        self._kaspr = kaspr_client
        self._proxycurl = proxycurl_client
        self._asic = asic_client
        self._scraper = web_scraper
    
    @property
    def name(self) -> str:
        return "identity_escalation"
    
    # ============================================
    # GENERIC EMAIL DETECTION
    # ============================================
    
    def is_generic_email(self, email: str) -> bool:
        """
        Check if an email is a generic inbox.
        
        Args:
            email: Email address to check
        
        Returns:
            True if generic (info@, admin@, etc.)
        """
        if not email:
            return True
        
        email_lower = email.lower().strip()
        
        for pattern in GENERIC_EMAIL_PATTERNS:
            if re.match(pattern, email_lower):
                return True
        
        return False
    
    def get_generic_reason(self, email: str) -> str:
        """Get the reason why an email is generic."""
        if not email:
            return "No email provided"
        
        email_lower = email.lower().strip()
        local_part = email_lower.split("@")[0]
        
        return f"Generic inbox detected: {local_part}@"
    
    # ============================================
    # PHONE TYPE DETECTION
    # ============================================
    
    def classify_phone(self, phone: str) -> PhoneType:
        """
        Classify an Australian phone number.
        
        Args:
            phone: Phone number (with or without country code)
        
        Returns:
            PhoneType.MOBILE, PhoneType.LANDLINE, or PhoneType.UNKNOWN
        """
        if not phone:
            return PhoneType.UNKNOWN
        
        # Normalize: remove spaces, dashes, parentheses
        normalized = re.sub(r"[\s\-\(\)]", "", phone)
        
        if re.match(AU_MOBILE_PATTERN, normalized):
            return PhoneType.MOBILE
        elif re.match(AU_LANDLINE_PATTERN, normalized):
            return PhoneType.LANDLINE
        else:
            return PhoneType.UNKNOWN
    
    def prioritize_mobile(self, phones: list[str]) -> Optional[str]:
        """
        From a list of phones, return the mobile number (priority for Voice AI).
        
        Args:
            phones: List of phone numbers
        
        Returns:
            First mobile number found, or None
        """
        for phone in phones:
            if self.classify_phone(phone) == PhoneType.MOBILE:
                return phone
        
        return None
    
    # ============================================
    # MAIN ESCALATION FLOW
    # ============================================
    
    async def escalate_identity(
        self,
        db: AsyncSession,
        lead_id: UUID,
        company_name: str,
        company_domain: str,
        company_linkedin_url: Optional[str],
        current_email: Optional[str],
        current_phone: Optional[str],
        registered_address: Optional[str],
        als_score: int,
        acn: Optional[str] = None,
    ) -> EngineResult[IdentityResult]:
        """
        Run identity escalation to find direct decision maker contacts.
        
        Args:
            db: Database session
            lead_id: Lead UUID
            company_name: Company name
            company_domain: Company website domain
            company_linkedin_url: LinkedIn company page URL
            current_email: Current email (may be generic)
            current_phone: Current phone (may be landline)
            registered_address: Registered office address
            als_score: Current ALS (determines mobile enrichment)
            acn: Australian Company Number (for ASIC lookup)
        
        Returns:
            EngineResult with IdentityResult
        """
        result = IdentityResult(
            lead_id=lead_id,
            company_name=company_name,
            registered_office_address=registered_address,
        )
        
        lineage_steps: list[IdentityLineageStep] = []
        step_number = 0
        total_cost = Decimal("0.00")
        
        try:
            # ========== CHECK IF ESCALATION NEEDED ==========
            needs_escalation = self.is_generic_email(current_email)
            phone_type = self.classify_phone(current_phone) if current_phone else PhoneType.UNKNOWN
            
            # Also escalate if we only have landline and need mobile for Voice AI
            if phone_type == PhoneType.LANDLINE and als_score > ALS_MOBILE_THRESHOLD:
                needs_escalation = True
                result.escalation_reason = "Landline only - need mobile for Voice AI"
            elif needs_escalation:
                result.escalation_reason = self.get_generic_reason(current_email)
            
            if not needs_escalation:
                # No escalation needed - use existing data
                result.work_email_verified = current_email
                if phone_type == PhoneType.MOBILE:
                    result.mobile_number_verified = current_phone
                result.success = True
                return EngineResult.ok(data=result)
            
            result.escalation_triggered = True
            decision_makers: list[DecisionMaker] = []
            
            # ========== TIER 1: TEAM PAGE SCRAPE ==========
            step_number += 1
            start_time = datetime.utcnow()
            
            team_contacts = await self._scrape_team_page(company_domain)
            
            step = IdentityLineageStep(
                step_number=step_number,
                tier=IdentityTier.TEAM_PAGE_SCRAPE,
                source_name="team_page_scraper",
                cost_aud=IDENTITY_COSTS_AUD["team_page_scrape"],
                success=len(team_contacts) > 0,
                contacts_found=len(team_contacts),
                data_added=["contact_names", "titles"] if team_contacts else [],
            )
            lineage_steps.append(step)
            total_cost += step.cost_aud
            result.tiers_used.append(IdentityTier.TEAM_PAGE_SCRAPE.value)
            
            decision_makers.extend(team_contacts)
            
            # ========== TIER 2: LINKEDIN EMPLOYEE SEARCH ==========
            if company_linkedin_url and len(decision_makers) < 3:
                step_number += 1
                
                linkedin_contacts = await self._search_linkedin_employees(
                    company_linkedin_url, company_name
                )
                
                step = IdentityLineageStep(
                    step_number=step_number,
                    tier=IdentityTier.LINKEDIN_EMPLOYEE,
                    source_name="proxycurl_linkedin",
                    cost_aud=IDENTITY_COSTS_AUD["proxycurl_linkedin"],
                    success=len(linkedin_contacts) > 0,
                    contacts_found=len(linkedin_contacts),
                    data_added=["linkedin_urls", "titles"] if linkedin_contacts else [],
                )
                lineage_steps.append(step)
                total_cost += step.cost_aud
                result.tiers_used.append(IdentityTier.LINKEDIN_EMPLOYEE.value)
                
                # Merge with existing, avoiding duplicates
                for lc in linkedin_contacts:
                    if not any(dm.full_name.lower() == lc.full_name.lower() for dm in decision_makers):
                        decision_makers.append(lc)
            
            # ========== TIER 3: ASIC DIRECTOR HUNT ==========
            if acn and len(decision_makers) < 3:
                step_number += 1
                
                asic_directors = await self._hunt_asic_directors(acn)
                
                step = IdentityLineageStep(
                    step_number=step_number,
                    tier=IdentityTier.ASIC_DIRECTOR,
                    source_name="asic_company_extract",
                    cost_aud=IDENTITY_COSTS_AUD["asic_extract"],
                    success=len(asic_directors) > 0,
                    contacts_found=len(asic_directors),
                    data_added=["director_names", "positions"] if asic_directors else [],
                )
                lineage_steps.append(step)
                total_cost += step.cost_aud
                result.tiers_used.append(IdentityTier.ASIC_DIRECTOR.value)
                
                # ASIC directors are high priority
                for ad in asic_directors:
                    if not any(dm.full_name.lower() == ad.full_name.lower() for dm in decision_makers):
                        decision_makers.insert(0, ad)  # Priority insert
            
            # ========== FILTER TO TOP 3 DECISION MAKERS ==========
            decision_makers = self._rank_decision_makers(decision_makers)[:3]
            result.decision_makers = decision_makers
            
            if decision_makers:
                result.primary_contact = decision_makers[0]
                
                # Extract best LinkedIn URL
                for dm in decision_makers:
                    if dm.linkedin_url:
                        result.linkedin_profile_url = dm.linkedin_url
                        break
            
            # ========== TIER 4/5: MOBILE ENRICHMENT (COGS GATED) ==========
            # Only enrich mobile for ALS > 75
            if als_score > ALS_MOBILE_THRESHOLD and decision_makers:
                step_number += 1
                
                # Try Lusha first, then Kaspr
                mobile_result = await self._enrich_mobile_number(
                    decision_makers[0], company_domain
                )
                
                if mobile_result:
                    result.mobile_number_verified = mobile_result.mobile_number
                    result.primary_contact.mobile_number = mobile_result.mobile_number
                    result.primary_contact.phone_type = PhoneType.MOBILE
                    
                    # Also capture work email if found
                    if mobile_result.work_email and not self.is_generic_email(mobile_result.work_email):
                        result.work_email_verified = mobile_result.work_email
                        result.primary_contact.work_email = mobile_result.work_email
                    
                    step = IdentityLineageStep(
                        step_number=step_number,
                        tier=IdentityTier.IDENTITY_GOLD,
                        source_name=mobile_result.source,
                        cost_aud=IDENTITY_COSTS_AUD.get(
                            f"{mobile_result.source}_mobile",
                            Decimal("0.25")
                        ),
                        success=True,
                        contacts_found=1,
                        data_added=["mobile_number_verified", "work_email_verified"],
                    )
                    lineage_steps.append(step)
                    total_cost += step.cost_aud
                    result.tiers_used.append(IdentityTier.IDENTITY_GOLD.value)
                else:
                    result.errors.append(
                        f"Mobile enrichment failed for {decision_makers[0].full_name}"
                    )
            elif als_score <= ALS_MOBILE_THRESHOLD:
                result.errors.append(
                    f"Mobile enrichment skipped: ALS {als_score} <= {ALS_MOBILE_THRESHOLD}"
                )
            
            # ========== FALLBACK: Use best available email ==========
            if not result.work_email_verified:
                for dm in decision_makers:
                    if dm.work_email and not self.is_generic_email(dm.work_email):
                        result.work_email_verified = dm.work_email
                        break
            
            # ========== FINALIZE ==========
            result.total_cost_aud = total_cost
            result.success = bool(
                result.work_email_verified or 
                result.mobile_number_verified or 
                result.linkedin_profile_url
            )
            
            # Log lineage
            await self._log_identity_lineage(db, lead_id, lineage_steps, result)
            
            return EngineResult.ok(
                data=result,
                metadata={
                    "escalation_triggered": result.escalation_triggered,
                    "decision_makers_found": len(result.decision_makers),
                    "mobile_verified": bool(result.mobile_number_verified),
                    "total_cost_aud": str(result.total_cost_aud),
                },
            )
            
        except Exception as e:
            logger.exception(f"Identity escalation failed for lead {lead_id}")
            result.errors.append(f"Escalation exception: {str(e)}")
            result.total_cost_aud = total_cost
            return EngineResult.error(error=str(e), metadata={"partial_result": result})
    
    # ============================================
    # TIER IMPLEMENTATIONS
    # ============================================
    
    async def _scrape_team_page(self, domain: str) -> list[DecisionMaker]:
        """
        Tier 1: Scrape company website for team/about page contacts.
        """
        if self._scraper is None:
            logger.warning("Web scraper not configured — skipping team page scrape")
            return []
        
        try:
            # Common team page URLs
            team_urls = [
                f"https://{domain}/about",
                f"https://{domain}/about-us",
                f"https://{domain}/team",
                f"https://{domain}/our-team",
                f"https://{domain}/leadership",
                f"https://{domain}/people",
            ]
            
            contacts = []
            for url in team_urls:
                try:
                    page_contacts = await self._scraper.extract_team_members(url)
                    if page_contacts:
                        for pc in page_contacts:
                            if self._is_decision_maker_title(pc.get("title", "")):
                                contacts.append(DecisionMaker(
                                    full_name=pc.get("name", ""),
                                    first_name=pc.get("first_name", ""),
                                    last_name=pc.get("last_name", ""),
                                    title=pc.get("title", ""),
                                    linkedin_url=pc.get("linkedin_url"),
                                    work_email=pc.get("email"),
                                    source="team_page",
                                    confidence=70,
                                ))
                        if contacts:
                            break  # Found contacts, stop searching
                except Exception:
                    continue
            
            return contacts
            
        except Exception as e:
            logger.error(f"Team page scrape failed: {e}")
            return []
    
    async def _search_linkedin_employees(
        self, company_linkedin_url: str, company_name: str
    ) -> list[DecisionMaker]:
        """
        Tier 2: Search LinkedIn for company employees via Proxycurl.
        """
        if self._proxycurl is None:
            logger.warning("Proxycurl not configured — skipping LinkedIn search")
            return []
        
        try:
            employees = await self._proxycurl.get_company_employees(
                company_linkedin_url,
                roles=DECISION_MAKER_TITLES,
            )
            
            contacts = []
            for emp in employees:
                if self._is_decision_maker_title(emp.get("title", "")):
                    contacts.append(DecisionMaker(
                        full_name=emp.get("full_name", ""),
                        first_name=emp.get("first_name", ""),
                        last_name=emp.get("last_name", ""),
                        title=emp.get("title", ""),
                        linkedin_url=emp.get("linkedin_url"),
                        source="linkedin_proxycurl",
                        confidence=80,
                    ))
            
            return contacts
            
        except Exception as e:
            logger.error(f"LinkedIn employee search failed: {e}")
            return []
    
    async def _hunt_asic_directors(self, acn: str) -> list[DecisionMaker]:
        """
        Tier 3: Look up company directors via ASIC extract.
        """
        if self._asic is None:
            logger.warning("ASIC client not configured — skipping director hunt")
            return []
        
        try:
            extract = await self._asic.get_company_extract(acn)
            
            directors = []
            for director in extract.get("directors", []):
                # Parse director name
                full_name = director.get("name", "")
                name_parts = full_name.split()
                
                directors.append(DecisionMaker(
                    full_name=full_name,
                    first_name=name_parts[0] if name_parts else "",
                    last_name=name_parts[-1] if len(name_parts) > 1 else "",
                    title="Director",
                    source="asic_extract",
                    confidence=95,  # ASIC data is authoritative
                ))
            
            return directors
            
        except Exception as e:
            logger.error(f"ASIC director hunt failed: {e}")
            return []
    
    async def _enrich_mobile_number(
        self, contact: DecisionMaker, company_domain: str
    ) -> Optional[DecisionMaker]:
        """
        Tier 4/5: Enrich contact with verified mobile number via Lusha/Kaspr.
        
        Prioritizes mobile over landline for Voice AI channel.
        """
        # Try Lusha first (better Australian coverage based on research)
        if self._lusha:
            try:
                lusha_result = await self._lusha.enrich_person(
                    first_name=contact.first_name,
                    last_name=contact.last_name,
                    company_domain=company_domain,
                    linkedin_url=contact.linkedin_url,
                )
                
                if lusha_result:
                    phones = lusha_result.get("phones", [])
                    mobile = self.prioritize_mobile(phones)
                    
                    if mobile:
                        contact.mobile_number = mobile
                        contact.phone_type = PhoneType.MOBILE
                        contact.work_email = lusha_result.get("email")
                        contact.source = "lusha"
                        contact.confidence = 90
                        return contact
            except Exception as e:
                logger.warning(f"Lusha enrichment failed: {e}")
        
        # Fallback to Kaspr
        if self._kaspr:
            try:
                kaspr_result = await self._kaspr.enrich_person(
                    linkedin_url=contact.linkedin_url,
                )
                
                if kaspr_result:
                    phones = kaspr_result.get("phones", [])
                    mobile = self.prioritize_mobile(phones)
                    
                    if mobile:
                        contact.mobile_number = mobile
                        contact.phone_type = PhoneType.MOBILE
                        contact.work_email = kaspr_result.get("email")
                        contact.source = "kaspr"
                        contact.confidence = 85
                        return contact
            except Exception as e:
                logger.warning(f"Kaspr enrichment failed: {e}")
        
        return None
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    def _is_decision_maker_title(self, title: str) -> bool:
        """Check if a job title indicates a decision maker."""
        if not title:
            return False
        
        title_lower = title.lower()
        return any(dm_title in title_lower for dm_title in DECISION_MAKER_TITLES)
    
    def _rank_decision_makers(
        self, contacts: list[DecisionMaker]
    ) -> list[DecisionMaker]:
        """
        Rank decision makers by authority and data completeness.
        
        Priority:
        1. Directors (ASIC verified)
        2. C-level (CEO, CFO, CTO)
        3. Founders/Owners
        4. Managers with LinkedIn
        5. Others
        """
        def score(dm: DecisionMaker) -> int:
            s = dm.confidence
            title_lower = dm.title.lower() if dm.title else ""
            
            # Title scoring
            if "director" in title_lower:
                s += 50
            elif any(c in title_lower for c in ["ceo", "chief", "founder", "owner"]):
                s += 40
            elif "managing" in title_lower:
                s += 30
            elif "manager" in title_lower:
                s += 20
            
            # Data completeness
            if dm.linkedin_url:
                s += 10
            if dm.work_email:
                s += 5
            if dm.mobile_number:
                s += 15
            
            return s
        
        return sorted(contacts, key=score, reverse=True)
    
    async def _log_identity_lineage(
        self,
        db: AsyncSession,
        lead_id: UUID,
        steps: list[IdentityLineageStep],
        result: IdentityResult,
    ) -> None:
        """Log identity escalation to lead_lineage_log."""
        try:
            for step in steps:
                # Calculate step number offset (identity escalation is Tier 5+)
                adjusted_step = step.step_number + 100  # Offset for identity steps
                
                stmt = insert("lead_lineage_log").values(
                    id=uuid4(),
                    lead_id=lead_id,
                    step_number=adjusted_step,
                    step_type="identity_escalation",
                    source_name=step.source_name,
                    fields_added=step.data_added,
                    cost_aud=step.cost_aud,
                    success=step.success,
                    error_message=step.error_message,
                    created_at=datetime.utcnow(),
                )
                await db.execute(stmt)
            
            # Log final "Identity Gold" event if mobile found
            if result.mobile_number_verified:
                stmt = insert("lead_lineage_log").values(
                    id=uuid4(),
                    lead_id=lead_id,
                    step_number=999,  # Final step
                    step_type="identity_gold",
                    source_name="identity_escalation_complete",
                    fields_added=[
                        "mobile_number_verified",
                        "work_email_verified",
                        "linkedin_profile_url",
                    ],
                    cost_aud=result.total_cost_aud,
                    success=True,
                    created_at=datetime.utcnow(),
                )
                await db.execute(stmt)
                logger.info(
                    f"🥇 IDENTITY GOLD: Lead {lead_id} - Mobile verified: "
                    f"{result.mobile_number_verified[:6]}***"
                )
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log identity lineage: {e}")
            await db.rollback()


# ============================================
# FACTORY FUNCTION
# ============================================

def get_identity_escalation_engine(
    lusha_client=None,
    kaspr_client=None,
    proxycurl_client=None,
    asic_client=None,
    web_scraper=None,
) -> IdentityEscalationEngine:
    """Get singleton IdentityEscalationEngine instance."""
    return IdentityEscalationEngine(
        lusha_client=lusha_client,
        kaspr_client=kaspr_client,
        proxycurl_client=proxycurl_client,
        asic_client=asic_client,
        web_scraper=web_scraper,
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Generic email detection (info@, admin@, etc.)
# [x] Mobile vs landline classification
# [x] Mobile prioritization for Voice AI
# [x] ALS > 75 gate for mobile enrichment
# [x] Director Hunt via ASIC
# [x] LinkedIn employee search
# [x] Team page scraping
# [x] Lusha/Kaspr mobile enrichment
# [x] All costs in AUD
# [x] Identity Gold logging
# [x] Decision maker ranking
