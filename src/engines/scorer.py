"""
FILE: src/engines/scorer.py
PURPOSE: Calculate ALS (Agency Lead Score) using 5-component formula
PHASE: 4 (Engines)
TASK: ENG-003
DEPENDENCIES:
  - src/engines/base.py
  - src/models/lead.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines
  - Rule 14: Soft deletes only
"""

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.base import BaseEngine, EngineResult
from src.models.base import ChannelType, LeadStatus
from src.models.lead import Lead


# ============================================
# ALS Scoring Constants
# ============================================

# Data Quality (20 points max)
SCORE_EMAIL_VERIFIED = 8
SCORE_PHONE = 6
SCORE_LINKEDIN = 4
SCORE_PERSONAL_EMAIL = 2

# Authority (25 points max)
AUTHORITY_SCORES = {
    "owner": 25,
    "ceo": 25,
    "founder": 25,
    "co-founder": 25,
    "chief": 22,  # CTO, CFO, CMO, etc.
    "c-suite": 22,
    "president": 22,
    "vice president": 18,
    "vp": 18,
    "director": 15,
    "head": 15,
    "senior manager": 10,
    "manager": 7,
    "lead": 7,
}

# Company Fit (25 points max)
SCORE_INDUSTRY_MATCH = 10
SCORE_EMPLOYEE_COUNT_IDEAL = 8  # 5-50 employees
SCORE_COUNTRY_AUSTRALIA = 7

# Timing (15 points max)
SCORE_NEW_ROLE = 6  # < 6 months
SCORE_HIRING = 5
SCORE_RECENT_FUNDING = 4  # < 12 months

# Risk (15 points max - deductions)
DEDUCTION_BOUNCED = -10
DEDUCTION_UNSUBSCRIBED = -15
DEDUCTION_COMPETITOR = -15
DEDUCTION_BAD_TITLE = -5  # assistant, intern, student

# Tier thresholds
TIER_HOT = 85
TIER_WARM = 60
TIER_COOL = 35
TIER_COLD = 20

# Bad titles to penalize
BAD_TITLES = ["assistant", "intern", "student", "coordinator", "receptionist"]

# Target industries (for Company Fit)
TARGET_INDUSTRIES = [
    "technology",
    "software",
    "saas",
    "fintech",
    "marketing",
    "professional services",
    "consulting",
    "healthcare",
    "real estate",
    "construction",
    "manufacturing",
]


class ScorerEngine(BaseEngine):
    """
    Scorer engine for ALS (Agency Lead Score) calculation.

    ALS Formula (5 Components, 100 points max):
    - Data Quality: 20 points
    - Authority: 25 points
    - Company Fit: 25 points
    - Timing: 15 points
    - Risk: 15 points (deductions)

    Tier Assignment:
    - Hot (85-100): Email, SMS, LinkedIn, Voice, Direct Mail
    - Warm (60-84): Email, LinkedIn, Voice
    - Cool (35-59): Email, LinkedIn
    - Cold (20-34): Email only
    - Dead (0-19): None (suppress)
    """

    @property
    def name(self) -> str:
        return "scorer"

    async def score_lead(
        self,
        db: AsyncSession,
        lead_id: UUID,
        target_industries: list[str] | None = None,
        competitor_domains: list[str] | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Calculate ALS score for a lead.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID to score
            target_industries: Optional list of target industries
            competitor_domains: Optional list of competitor domains to penalize

        Returns:
            EngineResult with scoring breakdown
        """
        lead = await self.get_lead_by_id(db, lead_id)

        # Calculate each component
        data_quality = self._score_data_quality(lead)
        authority = self._score_authority(lead)
        company_fit = self._score_company_fit(lead, target_industries)
        timing = self._score_timing(lead)
        risk = self._score_risk(lead, competitor_domains)

        # Calculate total score (capped at 0-100)
        total_score = max(0, min(100,
            data_quality + authority + company_fit + timing + risk
        ))

        # Determine tier
        tier = self._get_tier(total_score)

        # Get available channels for this tier
        channels = self._get_channels_for_tier(tier)

        # Build result
        score_breakdown = {
            "als_score": total_score,
            "als_tier": tier,
            "als_data_quality": data_quality,
            "als_authority": authority,
            "als_company_fit": company_fit,
            "als_timing": timing,
            "als_risk": risk,
            "available_channels": [c.value for c in channels],
            "lead_id": str(lead_id),
        }

        # Update lead in database
        await self._update_lead_score(db, lead, score_breakdown)

        return EngineResult.ok(
            data=score_breakdown,
            metadata={
                "engine": self.name,
                "tier": tier,
                "channels_available": len(channels),
            },
        )

    async def score_batch(
        self,
        db: AsyncSession,
        lead_ids: list[UUID],
        target_industries: list[str] | None = None,
        competitor_domains: list[str] | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Score a batch of leads.

        Args:
            db: Database session (passed by caller)
            lead_ids: List of lead UUIDs to score
            target_industries: Optional target industries
            competitor_domains: Optional competitor domains

        Returns:
            EngineResult with batch scoring summary
        """
        results = {
            "total": len(lead_ids),
            "scored": 0,
            "failures": 0,
            "tier_distribution": {"hot": 0, "warm": 0, "cool": 0, "cold": 0, "dead": 0},
            "average_score": 0.0,
            "scored_leads": [],
            "failed_leads": [],
        }

        total_score = 0

        for lead_id in lead_ids:
            try:
                result = await self.score_lead(
                    db=db,
                    lead_id=lead_id,
                    target_industries=target_industries,
                    competitor_domains=competitor_domains,
                )

                if result.success:
                    results["scored"] += 1
                    tier = result.data["als_tier"]
                    score = result.data["als_score"]
                    total_score += score
                    results["tier_distribution"][tier] += 1
                    results["scored_leads"].append({
                        "lead_id": str(lead_id),
                        "score": score,
                        "tier": tier,
                    })
                else:
                    results["failures"] += 1
                    results["failed_leads"].append({
                        "lead_id": str(lead_id),
                        "error": result.error,
                    })

            except Exception as e:
                results["failures"] += 1
                results["failed_leads"].append({
                    "lead_id": str(lead_id),
                    "error": str(e),
                })

        # Calculate average
        if results["scored"] > 0:
            results["average_score"] = total_score / results["scored"]

        return EngineResult.ok(
            data=results,
            metadata={
                "batch_size": len(lead_ids),
                "success_rate": results["scored"] / results["total"]
                if results["total"] > 0 else 0,
            },
        )

    def _score_data_quality(self, lead: Lead) -> int:
        """
        Calculate Data Quality score (max 20 points).

        - Email verified: 8 points
        - Phone: 6 points
        - LinkedIn: 4 points
        - Personal email: 2 points
        """
        score = 0

        # Email verified
        if lead.email_verified:
            score += SCORE_EMAIL_VERIFIED
        elif lead.email:  # Has email but not verified
            score += 4  # Partial credit

        # Phone
        if lead.phone:
            if lead.phone_verified:
                score += SCORE_PHONE
            else:
                score += 3  # Partial credit

        # LinkedIn
        if lead.linkedin_url:
            score += SCORE_LINKEDIN

        # Personal email
        if lead.personal_email:
            score += SCORE_PERSONAL_EMAIL

        return min(20, score)

    def _score_authority(self, lead: Lead) -> int:
        """
        Calculate Authority score (max 25 points).

        Based on job title seniority.
        """
        if not lead.title:
            return 0

        title_lower = lead.title.lower()

        # Check for exact matches and partial matches
        for title_keyword, points in AUTHORITY_SCORES.items():
            if title_keyword in title_lower:
                return points

        # Default score for unknown titles
        return 5

    def _score_company_fit(
        self,
        lead: Lead,
        target_industries: list[str] | None = None,
    ) -> int:
        """
        Calculate Company Fit score (max 25 points).

        - Industry match: 10 points
        - Employee count 5-50: 8 points
        - Australia: 7 points
        """
        score = 0
        industries = target_industries or TARGET_INDUSTRIES

        # Industry match
        if lead.organization_industry:
            industry_lower = lead.organization_industry.lower()
            for target in industries:
                if target.lower() in industry_lower:
                    score += SCORE_INDUSTRY_MATCH
                    break

        # Employee count (ideal range: 5-50)
        if lead.organization_employee_count:
            count = lead.organization_employee_count
            if 5 <= count <= 50:
                score += SCORE_EMPLOYEE_COUNT_IDEAL
            elif 51 <= count <= 200:
                score += 5  # Partial credit
            elif 1 <= count <= 4:
                score += 3  # Small startup

        # Country (Australia preferred)
        if lead.organization_country:
            country = lead.organization_country.lower()
            if country in ["australia", "au", "aus"]:
                score += SCORE_COUNTRY_AUSTRALIA
            elif country in ["new zealand", "nz", "united states", "us", "usa", "united kingdom", "uk", "gb"]:
                score += 4  # Partial credit for English-speaking countries

        return min(25, score)

    def _score_timing(self, lead: Lead) -> int:
        """
        Calculate Timing score (max 15 points).

        - New role < 6 months: 6 points
        - Company is hiring: 5 points
        - Recent funding < 12 months: 4 points
        """
        score = 0
        today = date.today()

        # New role (< 6 months)
        if lead.employment_start_date:
            months_in_role = (today - lead.employment_start_date).days / 30
            if months_in_role < 6:
                score += SCORE_NEW_ROLE
            elif months_in_role < 12:
                score += 3  # Partial credit

        # Company is hiring
        if lead.organization_is_hiring:
            score += SCORE_HIRING

        # Recent funding (< 12 months)
        if lead.organization_latest_funding_date:
            months_since_funding = (today - lead.organization_latest_funding_date).days / 30
            if months_since_funding < 12:
                score += SCORE_RECENT_FUNDING
            elif months_since_funding < 24:
                score += 2  # Partial credit

        return min(15, score)

    def _score_risk(
        self,
        lead: Lead,
        competitor_domains: list[str] | None = None,
    ) -> int:
        """
        Calculate Risk score (deductions from base 15 points).

        - Bounced: -10 points
        - Unsubscribed: -15 points
        - Competitor domain: -15 points
        - Bad title: -5 points
        """
        score = 15  # Start with full points

        # Bounced email
        if lead.bounce_count > 0:
            score += DEDUCTION_BOUNCED

        # Unsubscribed
        if lead.status == LeadStatus.UNSUBSCRIBED:
            score += DEDUCTION_UNSUBSCRIBED

        # Competitor domain check
        if competitor_domains and lead.domain:
            domain = lead.domain.lower()
            if domain in [d.lower() for d in competitor_domains]:
                score += DEDUCTION_COMPETITOR

        # Bad title check
        if lead.title:
            title_lower = lead.title.lower()
            for bad_title in BAD_TITLES:
                if bad_title in title_lower:
                    score += DEDUCTION_BAD_TITLE
                    break

        return max(0, score)

    def _get_tier(self, score: int) -> str:
        """
        Get tier based on ALS score.

        - Hot: 85-100
        - Warm: 60-84
        - Cool: 35-59
        - Cold: 20-34
        - Dead: 0-19
        """
        if score >= TIER_HOT:
            return "hot"
        elif score >= TIER_WARM:
            return "warm"
        elif score >= TIER_COOL:
            return "cool"
        elif score >= TIER_COLD:
            return "cold"
        else:
            return "dead"

    def _get_channels_for_tier(self, tier: str) -> list[ChannelType]:
        """
        Get available channels for a tier.

        - Hot: Email, SMS, LinkedIn, Voice, Direct Mail
        - Warm: Email, LinkedIn, Voice
        - Cool: Email, LinkedIn
        - Cold: Email only
        - Dead: None
        """
        tier_channels = {
            "hot": [
                ChannelType.EMAIL,
                ChannelType.SMS,
                ChannelType.LINKEDIN,
                ChannelType.VOICE,
                ChannelType.MAIL,
            ],
            "warm": [
                ChannelType.EMAIL,
                ChannelType.LINKEDIN,
                ChannelType.VOICE,
            ],
            "cool": [
                ChannelType.EMAIL,
                ChannelType.LINKEDIN,
            ],
            "cold": [
                ChannelType.EMAIL,
            ],
            "dead": [],
        }
        return tier_channels.get(tier, [])

    async def _update_lead_score(
        self,
        db: AsyncSession,
        lead: Lead,
        score_data: dict[str, Any],
    ) -> None:
        """Update lead with scoring data."""
        stmt = (
            update(Lead)
            .where(Lead.id == lead.id)
            .values(
                als_score=score_data["als_score"],
                als_tier=score_data["als_tier"],
                als_data_quality=score_data["als_data_quality"],
                als_authority=score_data["als_authority"],
                als_company_fit=score_data["als_company_fit"],
                als_timing=score_data["als_timing"],
                als_risk=score_data["als_risk"],
                status=LeadStatus.SCORED,
                updated_at=datetime.utcnow(),
            )
        )
        await db.execute(stmt)
        await db.commit()

    async def get_leads_by_tier(
        self,
        db: AsyncSession,
        client_id: UUID,
        tier: str,
        limit: int = 100,
    ) -> list[Lead]:
        """
        Get leads by tier for a client.

        Args:
            db: Database session
            client_id: Client UUID
            tier: Tier to filter by
            limit: Maximum leads to return

        Returns:
            List of leads in the specified tier
        """
        stmt = (
            select(Lead)
            .where(
                and_(
                    Lead.client_id == client_id,
                    Lead.als_tier == tier,
                    Lead.deleted_at.is_(None),  # Soft delete check
                )
            )
            .order_by(Lead.als_score.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


# Singleton instance
_scorer_engine: ScorerEngine | None = None


def get_scorer_engine() -> ScorerEngine:
    """Get or create Scorer engine instance."""
    global _scorer_engine
    if _scorer_engine is None:
        _scorer_engine = ScorerEngine()
    return _scorer_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Soft delete check in queries (Rule 14)
# [x] ALS Formula: 5 components, 100 points max
# [x] Data Quality scoring (20 max)
# [x] Authority scoring (25 max)
# [x] Company Fit scoring (25 max)
# [x] Timing scoring (15 max)
# [x] Risk scoring (15 base with deductions)
# [x] Tier assignment (hot/warm/cool/cold/dead)
# [x] Channel mapping per tier
# [x] Batch scoring support
# [x] Lead update with scores
# [x] EngineResult wrapper for responses
# [x] Test file created: tests/test_engines/test_scorer.py
# [x] All functions have type hints
# [x] All functions have docstrings
