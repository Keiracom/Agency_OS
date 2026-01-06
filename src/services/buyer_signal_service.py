"""
FILE: src/services/buyer_signal_service.py
TASK: CUST-011
PHASE: 24F - Customer Import
PURPOSE: Query platform buyer signals for lead scoring
LAYER: 3 - services
IMPORTS: models, config
CONSUMERS: Scorer Engine, Content Engine
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


class BuyerSignal(BaseModel):
    """Platform buyer signal data."""

    id: UUID
    domain: str
    company_name: Optional[str] = None
    industry: Optional[str] = None
    employee_count_range: Optional[str] = None
    times_bought: int = 1
    total_value: Optional[float] = None
    avg_deal_value: Optional[float] = None
    services_bought: list[str] = []
    buyer_score: int = 50


class BuyerScoreBoost(BaseModel):
    """Score boost calculation result."""

    boost_points: int = 0
    reason: Optional[str] = None
    signal: Optional[BuyerSignal] = None


# ============================================================================
# BUYER SIGNAL SERVICE
# ============================================================================


class BuyerSignalService:
    """
    Query platform buyer signals for lead scoring.

    Buyer signals are aggregated, anonymized data about companies
    that have bought from ANY client on the platform. This helps
    score leads - if a company has bought agency services before,
    they're more likely to buy again.
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    # =========================================================================
    # SIGNAL LOOKUP
    # =========================================================================

    async def get_buyer_signal(self, domain: str) -> Optional[BuyerSignal]:
        """
        Check if this company is a known buyer.
        Returns signal data for scoring boost.

        Args:
            domain: Company domain to check

        Returns:
            BuyerSignal if found, None otherwise
        """
        result = await self.db.execute(
            text("""
                SELECT id, domain, company_name, industry, employee_count_range,
                       times_bought, total_value, avg_deal_value, services_bought,
                       buyer_score
                FROM platform_buyer_signals
                WHERE domain = :domain
            """),
            {"domain": domain.lower()},
        )
        row = result.fetchone()

        if not row:
            return None

        return BuyerSignal(
            id=row.id,
            domain=row.domain,
            company_name=row.company_name,
            industry=row.industry,
            employee_count_range=row.employee_count_range,
            times_bought=row.times_bought,
            total_value=float(row.total_value) if row.total_value else None,
            avg_deal_value=float(row.avg_deal_value) if row.avg_deal_value else None,
            services_bought=row.services_bought or [],
            buyer_score=row.buyer_score,
        )

    async def get_buyer_signal_from_email(self, email: str) -> Optional[BuyerSignal]:
        """
        Get buyer signal from email address.

        Args:
            email: Email address to extract domain from

        Returns:
            BuyerSignal if found, None otherwise
        """
        domain = self._extract_domain(email)
        if not domain:
            return None
        return await self.get_buyer_signal(domain)

    async def get_buyer_score_boost(self, domain: str) -> BuyerScoreBoost:
        """
        Get score boost for known buyers.
        Used by Scorer Engine.

        The boost is calculated as buyer_score * 0.15, max 15 points.

        Args:
            domain: Company domain to check

        Returns:
            BuyerScoreBoost with points and reason
        """
        signal = await self.get_buyer_signal(domain)

        if not signal:
            return BuyerScoreBoost(
                boost_points=0,
                reason=None,
                signal=None,
            )

        # Use database function for calculation
        result = await self.db.execute(
            text("SELECT get_buyer_score_boost(:domain) as boost"),
            {"domain": domain.lower()},
        )
        row = result.fetchone()
        boost = row.boost if row else 0

        # Determine reason based on signal strength
        reason = None
        if signal.times_bought >= 3:
            reason = f"Repeat agency buyer ({signal.times_bought}x)"
        elif signal.times_bought >= 2:
            reason = "Has bought agency services before (2x)"
        else:
            reason = "Known agency services buyer"

        return BuyerScoreBoost(
            boost_points=boost,
            reason=reason,
            signal=signal,
        )

    async def get_buyer_signals_batch(
        self,
        domains: list[str],
    ) -> dict[str, Optional[BuyerSignal]]:
        """
        Get buyer signals for multiple domains at once.
        More efficient for bulk scoring.

        Args:
            domains: List of domains to check

        Returns:
            Dict mapping domain to BuyerSignal (None if not found)
        """
        if not domains:
            return {}

        result = await self.db.execute(
            text("""
                SELECT id, domain, company_name, industry, employee_count_range,
                       times_bought, total_value, avg_deal_value, services_bought,
                       buyer_score
                FROM platform_buyer_signals
                WHERE domain = ANY(:domains)
            """),
            {"domains": [d.lower() for d in domains]},
        )

        signals: dict[str, Optional[BuyerSignal]] = {d.lower(): None for d in domains}

        for row in result.fetchall():
            signals[row.domain] = BuyerSignal(
                id=row.id,
                domain=row.domain,
                company_name=row.company_name,
                industry=row.industry,
                employee_count_range=row.employee_count_range,
                times_bought=row.times_bought,
                total_value=float(row.total_value) if row.total_value else None,
                avg_deal_value=float(row.avg_deal_value) if row.avg_deal_value else None,
                services_bought=row.services_bought or [],
                buyer_score=row.buyer_score,
            )

        return signals

    # =========================================================================
    # STATISTICS
    # =========================================================================

    async def get_platform_stats(self) -> dict:
        """Get aggregate statistics about buyer signals."""
        result = await self.db.execute(
            text("""
                SELECT
                    COUNT(*) as total_signals,
                    COUNT(*) FILTER (WHERE times_bought >= 2) as repeat_buyers,
                    COUNT(*) FILTER (WHERE buyer_score >= 70) as high_score_buyers,
                    AVG(buyer_score)::INTEGER as avg_buyer_score,
                    AVG(avg_deal_value)::NUMERIC(12,2) as avg_deal_value,
                    COUNT(DISTINCT industry) as unique_industries
                FROM platform_buyer_signals
            """)
        )
        row = result.fetchone()

        return {
            "total_signals": row.total_signals,
            "repeat_buyers": row.repeat_buyers,
            "high_score_buyers": row.high_score_buyers,
            "avg_buyer_score": row.avg_buyer_score,
            "avg_deal_value": float(row.avg_deal_value) if row.avg_deal_value else None,
            "unique_industries": row.unique_industries,
        }

    async def get_top_industries(self, limit: int = 10) -> list[dict]:
        """Get industries with highest buyer signal concentration."""
        result = await self.db.execute(
            text("""
                SELECT
                    industry,
                    COUNT(*) as buyer_count,
                    AVG(buyer_score)::INTEGER as avg_score,
                    SUM(times_bought) as total_purchases
                FROM platform_buyer_signals
                WHERE industry IS NOT NULL
                GROUP BY industry
                ORDER BY buyer_count DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )

        return [
            {
                "industry": row.industry,
                "buyer_count": row.buyer_count,
                "avg_score": row.avg_score,
                "total_purchases": row.total_purchases,
            }
            for row in result.fetchall()
        ]

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _extract_domain(self, email: str) -> Optional[str]:
        """Extract domain from email address."""
        if not email or "@" not in email:
            return None
        return email.split("@")[1].lower()
