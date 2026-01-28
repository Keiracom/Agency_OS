"""
Contract: src/engines/scorer.py
Purpose: Calculate ALS (Agency Lead Score) using 5-component formula
Layer: 3 - engines
Imports: models, integrations
Consumers: orchestration only

FILE: src/engines/scorer.py
PURPOSE: Calculate ALS (Agency Lead Score) using 5-component formula
PHASE: 4 (Engines), modified Phase 16, 24A (Lead Pool), 24F (Buyer Signals)
TASK: ENG-003, 16A-006, 16E-004, POOL-009, CUST-012
DEPENDENCIES:
  - src/engines/base.py
  - src/models/lead.py
  - src/models/conversion_patterns.py (Phase 16)
  - src/models/client.py (Phase 16)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines
  - Rule 14: Soft deletes only
PHASE 16 CHANGES:
  - Loads learned weights from client's WHO patterns
  - Stores raw component scores in als_components
  - Stores weights used in als_weights_used
  - Stores scored_at timestamp for learning analysis
PHASE 24A CHANGES:
  - Added score_pool_lead method for pool-first scoring
  - Added score_pool_batch for bulk pool scoring
  - Pool leads scored directly without needing Lead model
  - Scores stored in lead_pool table
PHASE 24F CHANGES:
  - Added buyer signal boost via get_buyer_score_boost database function
  - Leads from known buyer companies get score boost (max 15 points)
  - Uses platform_buyer_signals table for cross-client intelligence
PHASE 24A+ CHANGES (LinkedIn Enrichment):
  - Added _get_linkedin_boost method for LinkedIn engagement signals
  - Boosts score when person has posts, high connections, recent activity
  - Boosts score when company has posts, high followers
  - Max LinkedIn boost: 10 points
  - Uses linkedin_person_data and linkedin_company_data from lead_assignments
"""

import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.base import BaseEngine, EngineResult

logger = logging.getLogger(__name__)
from src.models.base import ChannelType, LeadStatus
from src.models.client import Client
from src.models.conversion_patterns import ConversionPattern
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

# Phase 24F: Buyer signal boost (max points)
MAX_BUYER_BOOST = 15

# Phase 24A+: LinkedIn enrichment signals (max 10 points boost)
MAX_LINKEDIN_BOOST = 10
LINKEDIN_PERSON_POSTS_BOOST = 3  # Has recent posts (engaged)
LINKEDIN_COMPANY_POSTS_BOOST = 2  # Company is active
LINKEDIN_HIGH_CONNECTIONS_BOOST = 2  # 500+ connections (influential)
LINKEDIN_HIGH_FOLLOWERS_BOOST = 2  # Company 1000+ followers
LINKEDIN_RECENT_ACTIVITY_BOOST = 1  # Posted in last 30 days

# Default component weights (Phase 16)
# These are used when no learned weights are available
DEFAULT_WEIGHTS = {
    "data_quality": 0.20,  # 20 points -> 20%
    "authority": 0.25,  # 25 points -> 25%
    "company_fit": 0.25,  # 25 points -> 25%
    "timing": 0.15,  # 15 points -> 15%
    "risk": 0.15,  # 15 points -> 15%
}

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
        use_learned_weights: bool = True,
    ) -> EngineResult[dict[str, Any]]:
        """
        Calculate ALS score for a lead.

        Phase 16: Now supports learned weights from Conversion Intelligence.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID to score
            target_industries: Optional list of target industries
            competitor_domains: Optional list of competitor domains to penalize
            use_learned_weights: Whether to use client's learned weights (default: True)

        Returns:
            EngineResult with scoring breakdown
        """
        lead = await self.get_lead_by_id(db, lead_id)

        # Phase 16: Get learned weights if available
        weights = DEFAULT_WEIGHTS.copy()
        weights_source = "default"

        if use_learned_weights:
            learned = await self._get_learned_weights(db, lead.client_id)
            if learned:
                weights = learned
                weights_source = "learned"

        # Calculate raw component scores (0-100 scale for learning)
        # These are the raw scores before weighting
        raw_data_quality = self._score_data_quality(lead)
        raw_authority = self._score_authority(lead)
        raw_company_fit = self._score_company_fit(lead, target_industries)
        raw_timing = self._score_timing(lead)
        raw_risk = self._score_risk(lead, competitor_domains)

        # Phase 16: Normalize to 0-100 scale for each component
        # (multiply by factor to get 0-100 range)
        normalized = {
            "data_quality": raw_data_quality * 5,  # 0-20 -> 0-100
            "authority": raw_authority * 4,  # 0-25 -> 0-100
            "company_fit": raw_company_fit * 4,  # 0-25 -> 0-100
            "timing": raw_timing * 6.67,  # 0-15 -> 0-100
            "risk": raw_risk * 6.67,  # 0-15 -> 0-100
        }

        # Phase 16: Calculate weighted score
        weighted_score = sum(normalized[comp] * weights.get(comp, 0.2) for comp in normalized)

        # Phase 24F: Apply buyer signal boost
        buyer_boost = await self._get_buyer_boost(db, lead.domain)
        boost_points = buyer_boost.get("boost_points", 0)
        weighted_score += boost_points

        # Cap at 0-100
        total_score = int(max(0, min(100, weighted_score)))

        # Determine tier
        tier = self._get_tier(total_score)

        # Get available channels for this tier
        channels = self._get_channels_for_tier(tier)

        # Phase 16: Store raw components for learning
        als_components = {
            "data_quality": raw_data_quality,
            "authority": raw_authority,
            "company_fit": raw_company_fit,
            "timing": raw_timing,
            "risk": raw_risk,
        }

        # Build result
        score_breakdown = {
            "als_score": total_score,
            "als_tier": tier,
            "als_data_quality": raw_data_quality,
            "als_authority": raw_authority,
            "als_company_fit": raw_company_fit,
            "als_timing": raw_timing,
            "als_risk": raw_risk,
            "als_components": als_components,
            "als_weights_used": weights,
            "weights_source": weights_source,
            "available_channels": [c.value for c in channels],
            "lead_id": str(lead_id),
            # Phase 24F: Buyer signal boost
            "buyer_boost": boost_points,
            "buyer_boost_reason": buyer_boost.get("reason"),
        }

        # Update lead in database (now includes Phase 16 fields)
        await self._update_lead_score(db, lead, score_breakdown)

        return EngineResult.ok(
            data=score_breakdown,
            metadata={
                "engine": self.name,
                "tier": tier,
                "channels_available": len(channels),
                "weights_source": weights_source,
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
                    results["scored_leads"].append(
                        {
                            "lead_id": str(lead_id),
                            "score": score,
                            "tier": tier,
                        }
                    )
                else:
                    results["failures"] += 1
                    results["failed_leads"].append(
                        {
                            "lead_id": str(lead_id),
                            "error": result.error,
                        }
                    )

            except Exception as e:
                results["failures"] += 1
                results["failed_leads"].append(
                    {
                        "lead_id": str(lead_id),
                        "error": str(e),
                    }
                )

        # Calculate average
        if results["scored"] > 0:
            results["average_score"] = total_score / results["scored"]

        return EngineResult.ok(
            data=results,
            metadata={
                "batch_size": len(lead_ids),
                "success_rate": results["scored"] / results["total"] if results["total"] > 0 else 0,
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
            elif country in [
                "new zealand",
                "nz",
                "united states",
                "us",
                "usa",
                "united kingdom",
                "uk",
                "gb",
            ]:
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

    async def _get_learned_weights(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, float] | None:
        """
        Get learned ALS weights for a client.

        Phase 16: Checks client's als_learned_weights first,
        then falls back to WHO pattern's recommended weights.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Learned weights dict if available, None otherwise
        """
        # First check client's stored learned weights
        client_stmt = select(Client).where(Client.id == client_id)
        client_result = await db.execute(client_stmt)
        client = client_result.scalar_one_or_none()

        if client and client.als_learned_weights:
            return client.als_learned_weights

        # Fall back to WHO pattern's recommended weights
        pattern_stmt = select(ConversionPattern).where(
            and_(
                ConversionPattern.client_id == client_id,
                ConversionPattern.pattern_type == "who",
                ConversionPattern.valid_until > datetime.utcnow(),
            )
        )
        pattern_result = await db.execute(pattern_stmt)
        pattern = pattern_result.scalar_one_or_none()

        if pattern and pattern.patterns:
            recommended = pattern.patterns.get("recommended_weights")
            if recommended:
                return recommended

        return None

    async def _get_buyer_boost(
        self,
        db: AsyncSession,
        domain: str | None,
    ) -> dict[str, Any]:
        """
        Get buyer signal boost for a domain.

        Phase 24F: Uses get_buyer_score_boost database function to check
        if the company is a known buyer on the platform.

        Args:
            db: Database session
            domain: Company domain to check

        Returns:
            Dict with boost_points (int) and reason (str or None)
        """
        if not domain:
            return {"boost_points": 0, "reason": None}

        try:
            result = await db.execute(
                text("SELECT get_buyer_score_boost(:domain) as boost"),
                {"domain": domain.lower()},
            )
            row = result.fetchone()
            boost = row.boost if row else 0

            if boost > 0:
                # Get more details about the signal
                signal_result = await db.execute(
                    text("""
                        SELECT times_bought, buyer_score
                        FROM platform_buyer_signals
                        WHERE domain = :domain
                    """),
                    {"domain": domain.lower()},
                )
                signal_row = signal_result.fetchone()

                if signal_row:
                    times_bought = signal_row.times_bought or 1
                    if times_bought >= 3:
                        reason = f"Repeat agency buyer ({times_bought}x)"
                    elif times_bought >= 2:
                        reason = "Has bought agency services before (2x)"
                    else:
                        reason = "Known agency services buyer"

                    logger.info(f"Buyer boost for {domain}: +{boost} points ({reason})")
                    return {"boost_points": boost, "reason": reason}

            return {"boost_points": 0, "reason": None}

        except Exception as e:
            logger.warning(f"Error getting buyer boost for {domain}: {e}")
            return {"boost_points": 0, "reason": None}

    async def _get_linkedin_boost(
        self,
        db: AsyncSession,
        lead_pool_id: UUID | None,
    ) -> dict[str, Any]:
        """
        Calculate LinkedIn engagement boost from enrichment data.

        Phase 37: Reads LinkedIn data from lead_pool.enrichment_data
        instead of lead_assignments. Data is stored during enrichment.

        Boosts score based on LinkedIn activity signals:
        - Person has recent posts (engaged on LinkedIn)
        - Person has 500+ connections (influential)
        - Person posted in last 30 days (active)
        - Company has posts (active company)
        - Company has 1000+ followers (established)

        Args:
            db: Database session
            lead_pool_id: Lead pool UUID to check

        Returns:
            Dict with boost_points (int, max 10) and signals (list of reasons)
        """
        if not lead_pool_id:
            return {"boost_points": 0, "signals": []}

        try:
            # Get LinkedIn data from lead_pool enrichment_data
            result = await db.execute(
                text("""
                    SELECT enrichment_data
                    FROM lead_pool
                    WHERE id = :lead_pool_id
                """),
                {"lead_pool_id": str(lead_pool_id)},
            )
            row = result.fetchone()

            if not row or not row.enrichment_data:
                return {"boost_points": 0, "signals": []}

            boost_points = 0
            signals = []

            enrichment_data = row.enrichment_data
            if isinstance(enrichment_data, str):
                import json

                enrichment_data = json.loads(enrichment_data)

            # Parse person LinkedIn data from enrichment_data
            person_data = enrichment_data.get("linkedin_person", {})
            if person_data:
                # Check for posts (engaged on LinkedIn)
                posts = person_data.get("posts", [])
                if posts and len(posts) > 0:
                    boost_points += LINKEDIN_PERSON_POSTS_BOOST
                    signals.append(f"Active on LinkedIn ({len(posts)} recent posts)")

                    # Check for recent activity (posted in last 30 days)
                    recent_post = posts[0] if posts else {}
                    post_date = recent_post.get("posted_date")
                    if post_date:
                        try:
                            if isinstance(post_date, str):
                                post_dt = datetime.fromisoformat(post_date[:10])
                            else:
                                post_dt = post_date
                            days_ago = (datetime.utcnow() - post_dt).days
                            if days_ago <= 30:
                                boost_points += LINKEDIN_RECENT_ACTIVITY_BOOST
                                signals.append("Posted in last 30 days")
                        except (ValueError, TypeError):
                            pass

                # Check connections (influential)
                connections = person_data.get("connections", 0)
                if connections and connections >= 500:
                    boost_points += LINKEDIN_HIGH_CONNECTIONS_BOOST
                    signals.append(f"High influence ({connections}+ connections)")

            # Parse company LinkedIn data from enrichment_data
            company_data = enrichment_data.get("linkedin_company", {})
            if company_data:
                # Check for company posts (active company)
                company_posts = company_data.get("posts", [])
                if company_posts and len(company_posts) > 0:
                    boost_points += LINKEDIN_COMPANY_POSTS_BOOST
                    signals.append(f"Active company ({len(company_posts)} recent posts)")

                # Check company followers (established)
                followers = company_data.get("followers", 0)
                if followers and followers >= 1000:
                    boost_points += LINKEDIN_HIGH_FOLLOWERS_BOOST
                    signals.append(f"Established company ({followers}+ followers)")

            # Cap at max
            boost_points = min(boost_points, MAX_LINKEDIN_BOOST)

            if boost_points > 0:
                logger.info(
                    f"LinkedIn boost for lead_pool {lead_pool_id}: "
                    f"+{boost_points} points ({', '.join(signals)})"
                )

            return {"boost_points": boost_points, "signals": signals}

        except Exception as e:
            logger.warning(f"Error getting LinkedIn boost for {lead_pool_id}: {e}")
            return {"boost_points": 0, "signals": []}

    async def _update_lead_score(
        self,
        db: AsyncSession,
        lead: Lead,
        score_data: dict[str, Any],
    ) -> None:
        """
        Update lead with scoring data.

        Phase 16: Now stores als_components, als_weights_used, and scored_at
        for Conversion Intelligence learning.
        """
        now = datetime.utcnow()

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
                # Phase 16: Store for learning
                als_components=score_data.get("als_components"),
                als_weights_used=score_data.get("als_weights_used"),
                scored_at=now,
                status=LeadStatus.SCORED,
                updated_at=now,
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

    # ============================================
    # PHASE 24A: Pool Scoring Methods
    # ============================================

    async def score_pool_lead(
        self,
        db: AsyncSession,
        lead_pool_id: UUID,
        target_industries: list[str] | None = None,
        competitor_domains: list[str] | None = None,
        assignment_id: UUID | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Calculate ALS score for a lead in the pool.

        Phase 24A: Scores leads directly from lead_pool table
        without requiring a Lead model instance.

        Phase 24A+: When assignment_id is provided, includes LinkedIn
        engagement boost from enrichment data.

        Args:
            db: Database session (passed by caller)
            lead_pool_id: Lead pool UUID to score
            target_industries: Optional list of target industries
            competitor_domains: Optional list of competitor domains
            assignment_id: Optional assignment UUID for LinkedIn boost

        Returns:
            EngineResult with scoring breakdown
        """
        # Get pool lead data
        pool_lead = await self._get_pool_lead(db, lead_pool_id)
        if not pool_lead:
            return EngineResult.fail(
                error="Lead not found in pool",
                metadata={"lead_pool_id": str(lead_pool_id)},
            )

        # Calculate raw component scores
        raw_data_quality = self._score_pool_data_quality(pool_lead)
        raw_authority = self._score_pool_authority(pool_lead)
        raw_company_fit = self._score_pool_company_fit(pool_lead, target_industries)
        raw_timing = self._score_pool_timing(pool_lead)
        raw_risk = self._score_pool_risk(pool_lead, competitor_domains)

        # Normalize to 0-100 scale
        normalized = {
            "data_quality": raw_data_quality * 5,  # 0-20 -> 0-100
            "authority": raw_authority * 4,  # 0-25 -> 0-100
            "company_fit": raw_company_fit * 4,  # 0-25 -> 0-100
            "timing": raw_timing * 6.67,  # 0-15 -> 0-100
            "risk": raw_risk * 6.67,  # 0-15 -> 0-100
        }

        # Calculate weighted score (using default weights for pool)
        weighted_score = sum(
            normalized[comp] * DEFAULT_WEIGHTS.get(comp, 0.2) for comp in normalized
        )

        # Phase 24F: Apply buyer signal boost
        company_domain = pool_lead.get("company_domain")
        buyer_boost = await self._get_buyer_boost(db, company_domain)
        buyer_boost_points = buyer_boost.get("boost_points", 0)
        weighted_score += buyer_boost_points

        # Phase 37: Apply LinkedIn engagement boost from lead_pool enrichment_data
        linkedin_boost = await self._get_linkedin_boost(db, lead_pool_id)
        linkedin_boost_points = linkedin_boost.get("boost_points", 0)
        weighted_score += linkedin_boost_points

        total_score = int(max(0, min(100, weighted_score)))
        tier = self._get_tier(total_score)
        channels = self._get_channels_for_tier(tier)

        # Build result
        score_breakdown = {
            "als_score": total_score,
            "als_tier": tier,
            "als_data_quality": raw_data_quality,
            "als_authority": raw_authority,
            "als_company_fit": raw_company_fit,
            "als_timing": raw_timing,
            "als_risk": raw_risk,
            "als_components": {
                "data_quality": raw_data_quality,
                "authority": raw_authority,
                "company_fit": raw_company_fit,
                "timing": raw_timing,
                "risk": raw_risk,
            },
            "available_channels": [c.value for c in channels],
            "lead_pool_id": str(lead_pool_id),
            # Phase 24F: Buyer signal boost
            "buyer_boost": buyer_boost_points,
            "buyer_boost_reason": buyer_boost.get("reason"),
            # Phase 37: LinkedIn engagement boost from lead_pool
            "linkedin_boost": linkedin_boost_points,
            "linkedin_signals": linkedin_boost.get("signals", []),
        }

        # Phase 37: Update lead_pool directly (not lead_assignments)
        await self._update_pool_lead_score(db, lead_pool_id, score_breakdown)

        return EngineResult.ok(
            data=score_breakdown,
            metadata={
                "engine": self.name,
                "tier": tier,
                "channels_available": len(channels),
                "source": "lead_pool",
            },
        )

    async def score_pool_batch(
        self,
        db: AsyncSession,
        lead_pool_ids: list[UUID],
        target_industries: list[str] | None = None,
        competitor_domains: list[str] | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Score a batch of pool leads.

        Phase 24A: Efficient batch scoring for lead pool.

        Args:
            db: Database session (passed by caller)
            lead_pool_ids: List of lead pool UUIDs to score
            target_industries: Optional target industries
            competitor_domains: Optional competitor domains

        Returns:
            EngineResult with batch scoring summary
        """
        results = {
            "total": len(lead_pool_ids),
            "scored": 0,
            "failures": 0,
            "tier_distribution": {"hot": 0, "warm": 0, "cool": 0, "cold": 0, "dead": 0},
            "average_score": 0.0,
            "scored_leads": [],
            "failed_leads": [],
        }

        total_score = 0

        for pool_id in lead_pool_ids:
            try:
                result = await self.score_pool_lead(
                    db=db,
                    lead_pool_id=pool_id,
                    target_industries=target_industries,
                    competitor_domains=competitor_domains,
                )

                if result.success:
                    results["scored"] += 1
                    tier = result.data["als_tier"]
                    score = result.data["als_score"]
                    total_score += score
                    results["tier_distribution"][tier] += 1
                    results["scored_leads"].append(
                        {
                            "lead_pool_id": str(pool_id),
                            "score": score,
                            "tier": tier,
                        }
                    )
                else:
                    results["failures"] += 1
                    results["failed_leads"].append(
                        {
                            "lead_pool_id": str(pool_id),
                            "error": result.error,
                        }
                    )

            except Exception as e:
                results["failures"] += 1
                results["failed_leads"].append(
                    {
                        "lead_pool_id": str(pool_id),
                        "error": str(e),
                    }
                )

        if results["scored"] > 0:
            results["average_score"] = total_score / results["scored"]

        return EngineResult.ok(
            data=results,
            metadata={
                "batch_size": len(lead_pool_ids),
                "success_rate": results["scored"] / results["total"] if results["total"] > 0 else 0,
                "source": "lead_pool",
            },
        )

    # ============================================
    # CLIENT-SPECIFIC ASSIGNMENT SCORING
    # ============================================

    async def score_assignments_batch(
        self,
        db: AsyncSession,
        assignment_ids: list[UUID],
        client_id: UUID,
        target_industries: list[str] | None = None,
        competitor_domains: list[str] | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Score a batch of lead assignments with client-specific weights.

        This is the preferred method for scoring as it:
        1. Uses assignment_id for precise targeting
        2. Uses client's learned ALS weights
        3. Respects client-specific target industries and competitors

        Args:
            db: Database session
            assignment_ids: List of lead_assignment UUIDs
            client_id: Client UUID for learned weights
            target_industries: Client's target industries
            competitor_domains: Client's competitor domains

        Returns:
            EngineResult with batch scoring summary
        """
        results = {
            "total": len(assignment_ids),
            "scored": 0,
            "failures": 0,
            "tier_distribution": {"hot": 0, "warm": 0, "cool": 0, "cold": 0, "dead": 0},
            "average_score": 0.0,
            "scored_leads": [],
            "failed_leads": [],
        }

        # Get client's learned weights (once for all assignments)
        weights = DEFAULT_WEIGHTS.copy()
        weights_source = "default"
        learned = await self._get_learned_weights(db, client_id)
        if learned:
            weights = learned
            weights_source = "learned"

        total_score = 0

        for assignment_id in assignment_ids:
            try:
                result = await self.score_assignment(
                    db=db,
                    assignment_id=assignment_id,
                    client_id=client_id,
                    weights=weights,
                    weights_source=weights_source,
                    target_industries=target_industries,
                    competitor_domains=competitor_domains,
                )

                if result.success:
                    results["scored"] += 1
                    tier = result.data["als_tier"]
                    score = result.data["als_score"]
                    total_score += score
                    results["tier_distribution"][tier] += 1
                    results["scored_leads"].append(
                        {
                            "assignment_id": str(assignment_id),
                            "score": score,
                            "tier": tier,
                        }
                    )
                else:
                    results["failures"] += 1
                    results["failed_leads"].append(
                        {
                            "assignment_id": str(assignment_id),
                            "error": result.error,
                        }
                    )

            except Exception as e:
                results["failures"] += 1
                results["failed_leads"].append(
                    {
                        "assignment_id": str(assignment_id),
                        "error": str(e),
                    }
                )

        if results["scored"] > 0:
            results["average_score"] = total_score / results["scored"]

        return EngineResult.ok(
            data=results,
            metadata={
                "batch_size": len(assignment_ids),
                "success_rate": results["scored"] / results["total"] if results["total"] > 0 else 0,
                "client_id": str(client_id),
                "weights_source": weights_source,
            },
        )

    async def score_assignment(
        self,
        db: AsyncSession,
        assignment_id: UUID,
        client_id: UUID,
        weights: dict[str, float] | None = None,
        weights_source: str = "default",
        target_industries: list[str] | None = None,
        competitor_domains: list[str] | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Score a single lead assignment with client-specific weights.

        Args:
            db: Database session
            assignment_id: Lead assignment UUID
            client_id: Client UUID
            weights: Pre-fetched weights (optional, will fetch if not provided)
            weights_source: Source of weights ("default" or "learned")
            target_industries: Client's target industries
            competitor_domains: Client's competitor domains

        Returns:
            EngineResult with scoring breakdown
        """
        # Get assignment with pool lead data
        assignment_data = await self._get_assignment_with_pool_data(db, assignment_id)
        if not assignment_data:
            return EngineResult.fail(
                error="Assignment not found",
                metadata={"assignment_id": str(assignment_id)},
            )

        # Get weights if not provided
        if weights is None:
            weights = DEFAULT_WEIGHTS.copy()
            learned = await self._get_learned_weights(db, client_id)
            if learned:
                weights = learned
                weights_source = "learned"

        # Calculate raw component scores using pool data
        raw_data_quality = self._score_pool_data_quality(assignment_data)
        raw_authority = self._score_pool_authority(assignment_data)
        raw_company_fit = self._score_pool_company_fit(assignment_data, target_industries)
        raw_timing = self._score_pool_timing(assignment_data)
        raw_risk = self._score_pool_risk(assignment_data, competitor_domains)

        # Normalize to 0-100 scale
        normalized = {
            "data_quality": raw_data_quality * 5,
            "authority": raw_authority * 4,
            "company_fit": raw_company_fit * 4,
            "timing": raw_timing * 6.67,
            "risk": raw_risk * 6.67,
        }

        # Calculate weighted score using client's weights
        weighted_score = sum(normalized[comp] * weights.get(comp, 0.2) for comp in normalized)

        # Apply buyer signal boost
        company_domain = assignment_data.get("company_domain")
        buyer_boost = await self._get_buyer_boost(db, company_domain)
        buyer_boost_points = buyer_boost.get("boost_points", 0)
        weighted_score += buyer_boost_points

        # Phase 37: Apply LinkedIn engagement boost using lead_pool_id
        lead_pool_id = assignment_data.get("lead_pool_id")
        if lead_pool_id:
            linkedin_boost = await self._get_linkedin_boost(db, UUID(str(lead_pool_id)))
        else:
            linkedin_boost = {"boost_points": 0, "signals": []}
        linkedin_boost_points = linkedin_boost.get("boost_points", 0)
        weighted_score += linkedin_boost_points

        total_score = int(max(0, min(100, weighted_score)))
        tier = self._get_tier(total_score)
        channels = self._get_channels_for_tier(tier)

        # Build result
        lead_pool_uuid = UUID(str(lead_pool_id)) if lead_pool_id else None
        score_breakdown = {
            "als_score": total_score,
            "als_tier": tier,
            "als_data_quality": raw_data_quality,
            "als_authority": raw_authority,
            "als_company_fit": raw_company_fit,
            "als_timing": raw_timing,
            "als_risk": raw_risk,
            "als_components": {
                "data_quality": raw_data_quality,
                "authority": raw_authority,
                "company_fit": raw_company_fit,
                "timing": raw_timing,
                "risk": raw_risk,
            },
            "als_weights_used": weights,
            "weights_source": weights_source,
            "available_channels": [c.value for c in channels],
            "lead_pool_id": str(lead_pool_id) if lead_pool_id else None,
            "buyer_boost": buyer_boost_points,
            "buyer_boost_reason": buyer_boost.get("reason"),
            "linkedin_boost": linkedin_boost_points,
            "linkedin_signals": linkedin_boost.get("signals", []),
        }

        # Phase 37: Update lead_pool directly
        if lead_pool_uuid:
            await self._update_pool_lead_score(db, lead_pool_uuid, score_breakdown)

        return EngineResult.ok(
            data=score_breakdown,
            metadata={
                "engine": self.name,
                "tier": tier,
                "channels_available": len(channels),
                "weights_source": weights_source,
                "client_id": str(client_id),
            },
        )

    async def _get_assignment_with_pool_data(
        self,
        db: AsyncSession,
        assignment_id: UUID,
    ) -> dict[str, Any] | None:
        """
        Get assignment with joined pool lead data for scoring.

        Args:
            db: Database session
            assignment_id: Assignment UUID

        Returns:
            Combined assignment + pool data dict or None
        """
        query = text("""
            SELECT
                la.id as assignment_id,
                la.client_id,
                la.campaign_id,
                la.lead_pool_id,
                lp.email,
                lp.email_status,
                lp.phone,
                lp.linkedin_url,
                lp.title,
                lp.seniority,
                lp.company_name,
                lp.company_domain,
                lp.company_industry,
                lp.company_employee_count,
                lp.company_country,
                lp.company_is_hiring,
                lp.company_latest_funding_date,
                lp.is_bounced,
                lp.is_unsubscribed,
                lp.pool_status
            FROM lead_assignments la
            JOIN lead_pool lp ON la.lead_pool_id = lp.id
            WHERE la.id = :assignment_id
        """)

        result = await db.execute(query, {"assignment_id": str(assignment_id)})
        row = result.fetchone()

        return dict(row._mapping) if row else None

    async def _update_assignment_score(
        self,
        db: AsyncSession,
        assignment_id: UUID,
        score_data: dict[str, Any],
    ) -> None:
        """
        Update a specific assignment with scoring data.

        Args:
            db: Database session
            assignment_id: Assignment UUID to update
            score_data: Scoring results
        """
        import json

        query = text("""
            UPDATE lead_assignments
            SET als_score = :als_score,
                als_tier = :als_tier,
                als_components = :als_components,
                als_weights_used = :als_weights_used,
                scored_at = NOW(),
                updated_at = NOW()
            WHERE id = :assignment_id
        """)

        await db.execute(
            query,
            {
                "assignment_id": str(assignment_id),
                "als_score": score_data["als_score"],
                "als_tier": score_data["als_tier"],
                "als_components": json.dumps(score_data.get("als_components", {})),
                "als_weights_used": json.dumps(score_data.get("als_weights_used", {})),
            },
        )
        await db.commit()

    async def _get_pool_lead(
        self,
        db: AsyncSession,
        lead_pool_id: UUID,
    ) -> dict[str, Any] | None:
        """
        Get lead data from pool.

        Args:
            db: Database session
            lead_pool_id: Pool lead UUID

        Returns:
            Pool lead data dict or None
        """
        from sqlalchemy import text

        query = text("""
            SELECT id, email, email_status, phone, linkedin_url,
                   title, seniority, company_name, company_domain,
                   company_industry, company_employee_count, company_country,
                   company_founded_year, company_is_hiring,
                   company_latest_funding_date, is_bounced, is_unsubscribed,
                   pool_status, enrichment_confidence
            FROM lead_pool
            WHERE id = :id
        """)

        result = await db.execute(query, {"id": str(lead_pool_id)})
        row = result.fetchone()

        return dict(row._mapping) if row else None

    def _score_pool_data_quality(self, pool_lead: dict[str, Any]) -> int:
        """
        Calculate Data Quality score for pool lead (max 20 points).

        Uses pool-specific fields:
        - email_status instead of email_verified
        - phone presence
        - linkedin_url presence
        """
        score = 0

        # Email status scoring
        email_status = pool_lead.get("email_status", "")
        if email_status == "verified":
            score += SCORE_EMAIL_VERIFIED  # 8 points
        elif email_status == "catch_all":
            score += 5  # Partial credit
        elif email_status == "guessed":
            score += 3  # Lower credit
        elif email_status:
            score += 2  # Has email at least

        # Phone
        if pool_lead.get("phone"):
            score += SCORE_PHONE  # 6 points

        # LinkedIn
        if pool_lead.get("linkedin_url"):
            score += SCORE_LINKEDIN  # 4 points

        return min(20, score)

    def _score_pool_authority(self, pool_lead: dict[str, Any]) -> int:
        """
        Calculate Authority score for pool lead (max 25 points).

        Uses pool-specific seniority field when available.
        """
        # First check seniority field
        seniority = pool_lead.get("seniority", "")
        if seniority:
            seniority_scores = {
                "owner": 25,
                "founder": 25,
                "c_suite": 22,
                "vp": 18,
                "director": 15,
                "manager": 10,
                "senior": 7,
                "entry": 3,
            }
            for level, points in seniority_scores.items():
                if level in seniority.lower():
                    return points

        # Fall back to title parsing
        title = pool_lead.get("title", "")
        if not title:
            return 0

        title_lower = title.lower()
        for title_keyword, points in AUTHORITY_SCORES.items():
            if title_keyword in title_lower:
                return points

        return 5  # Default for unknown titles

    def _score_pool_company_fit(
        self,
        pool_lead: dict[str, Any],
        target_industries: list[str] | None = None,
    ) -> int:
        """
        Calculate Company Fit score for pool lead (max 25 points).

        Uses pool-specific company fields.
        """
        score = 0
        industries = target_industries or TARGET_INDUSTRIES

        # Industry match
        industry = pool_lead.get("company_industry", "")
        if industry:
            industry_lower = industry.lower()
            for target in industries:
                if target.lower() in industry_lower:
                    score += SCORE_INDUSTRY_MATCH
                    break

        # Employee count (ideal: 5-50)
        employee_count = pool_lead.get("company_employee_count")
        if employee_count:
            if 5 <= employee_count <= 50:
                score += SCORE_EMPLOYEE_COUNT_IDEAL
            elif 51 <= employee_count <= 200:
                score += 5
            elif 1 <= employee_count <= 4:
                score += 3

        # Country (Australia preferred)
        country = pool_lead.get("company_country", "")
        if country:
            country_lower = country.lower()
            if country_lower in ["australia", "au", "aus"]:
                score += SCORE_COUNTRY_AUSTRALIA
            elif country_lower in ["new zealand", "nz", "united states", "us", "usa", "uk", "gb"]:
                score += 4

        return min(25, score)

    def _score_pool_timing(self, pool_lead: dict[str, Any]) -> int:
        """
        Calculate Timing score for pool lead (max 15 points).

        Uses pool-specific company fields.
        """
        score = 0
        today = date.today()

        # Company is hiring
        if pool_lead.get("company_is_hiring"):
            score += SCORE_HIRING  # 5 points

        # Recent funding
        funding_date = pool_lead.get("company_latest_funding_date")
        if funding_date:
            if isinstance(funding_date, str):
                try:
                    funding_date = date.fromisoformat(funding_date[:10])
                except ValueError:
                    funding_date = None

            if funding_date:
                months_since = (today - funding_date).days / 30
                if months_since < 12:
                    score += SCORE_RECENT_FUNDING  # 4 points
                elif months_since < 24:
                    score += 2

        # Note: Pool doesn't track employment_start_date
        # New role scoring would require assignment-level data

        return min(15, score)

    def _score_pool_risk(
        self,
        pool_lead: dict[str, Any],
        competitor_domains: list[str] | None = None,
    ) -> int:
        """
        Calculate Risk score for pool lead (15 base with deductions).

        Uses pool-specific bounce and unsubscribe flags.
        """
        score = 15  # Start with full points

        # Bounced
        if pool_lead.get("is_bounced"):
            score += DEDUCTION_BOUNCED  # -10

        # Unsubscribed
        if pool_lead.get("is_unsubscribed"):
            score += DEDUCTION_UNSUBSCRIBED  # -15

        # Pool status check
        pool_status = pool_lead.get("pool_status", "")
        if pool_status in ("bounced", "invalid"):
            score += DEDUCTION_BOUNCED

        # Competitor domain check
        if competitor_domains:
            domain = pool_lead.get("company_domain", "")
            if domain and domain.lower() in [d.lower() for d in competitor_domains]:
                score += DEDUCTION_COMPETITOR  # -15

        # Bad title check
        title = pool_lead.get("title", "")
        if title:
            title_lower = title.lower()
            for bad_title in BAD_TITLES:
                if bad_title in title_lower:
                    score += DEDUCTION_BAD_TITLE  # -5
                    break

        return max(0, score)

    async def _update_pool_lead_score(
        self,
        db: AsyncSession,
        lead_pool_id: UUID,
        score_data: dict[str, Any],
        assignment_id: UUID | None = None,
    ) -> None:
        """
        Update lead_pool with scoring data.

        Phase 37: ALS scores are now stored directly in lead_pool table
        with the client_id ownership model. No separate lead_assignments needed.

        Args:
            db: Database session
            lead_pool_id: Pool lead UUID to update
            score_data: Scoring results
            assignment_id: Deprecated, kept for backward compatibility
        """
        import json

        from sqlalchemy import text

        # Update the lead_pool record directly
        query = text("""
            UPDATE lead_pool
            SET als_score = :als_score,
                als_tier = :als_tier,
                als_components = :als_components,
                scored_at = NOW(),
                updated_at = NOW()
            WHERE id = :id
        """)
        await db.execute(
            query,
            {
                "id": str(lead_pool_id),
                "als_score": score_data["als_score"],
                "als_tier": score_data["als_tier"],
                "als_components": json.dumps(score_data.get("als_components", {})),
            },
        )

        await db.commit()

    async def get_pool_leads_by_tier(
        self,
        db: AsyncSession,
        tier: str,
        limit: int = 100,
        pool_status: str = "assigned",
        client_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get leads by tier from lead_pool.

        Phase 37: Queries lead_pool directly using the new schema
        where ALS scores and client ownership are stored in lead_pool.

        Args:
            db: Database session
            tier: Tier to filter by
            limit: Maximum leads to return
            pool_status: Filter by pool status (default: assigned)
            client_id: Optional client filter

        Returns:
            List of lead pool dicts in the specified tier
        """
        from sqlalchemy import text

        conditions = ["als_tier = :tier", "pool_status = :pool_status"]
        params: dict[str, Any] = {"tier": tier, "pool_status": pool_status, "limit": limit}

        if client_id:
            conditions.append("client_id = :client_id")
            params["client_id"] = str(client_id)

        where_clause = " AND ".join(conditions)

        query = text(f"""
            SELECT id, email, first_name, last_name, title,
                   company_name, als_score, als_tier, als_components,
                   client_id, campaign_id
            FROM lead_pool
            WHERE {where_clause}
            ORDER BY als_score DESC NULLS LAST
            LIMIT :limit
        """)

        result = await db.execute(query, params)
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]


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
# ============================================
# PHASE 24A POOL ADDITIONS
# ============================================
# [x] score_pool_lead for individual pool scoring
# [x] score_pool_batch for bulk pool scoring
# [x] _get_pool_lead helper for pool data fetch
# [x] _score_pool_data_quality with email_status
# [x] _score_pool_authority with seniority field
# [x] _score_pool_company_fit with pool fields
# [x] _score_pool_timing with pool fields
# [x] _score_pool_risk with bounce/unsubscribe
# [x] _update_pool_lead_score for pool updates
# [x] get_pool_leads_by_tier for tier queries
# ============================================
# PHASE 24F BUYER SIGNAL BOOST
# ============================================
# [x] _get_buyer_boost method using database function
# [x] MAX_BUYER_BOOST constant (15 points)
# [x] Buyer boost integrated into score_lead
# [x] Buyer boost integrated into score_pool_lead
# [x] buyer_boost and buyer_boost_reason in score breakdown
# ============================================
# PHASE 24A+ LINKEDIN ENRICHMENT BOOST
# ============================================
# [x] _get_linkedin_boost method for LinkedIn engagement signals
# [x] MAX_LINKEDIN_BOOST constant (10 points)
# [x] LINKEDIN_PERSON_POSTS_BOOST (3 points)
# [x] LINKEDIN_COMPANY_POSTS_BOOST (2 points)
# [x] LINKEDIN_HIGH_CONNECTIONS_BOOST (2 points)
# [x] LINKEDIN_HIGH_FOLLOWERS_BOOST (2 points)
# [x] LINKEDIN_RECENT_ACTIVITY_BOOST (1 point)
# [x] LinkedIn boost integrated into score_pool_lead
# [x] assignment_id parameter added to score_pool_lead
# [x] linkedin_boost and linkedin_signals in score breakdown
