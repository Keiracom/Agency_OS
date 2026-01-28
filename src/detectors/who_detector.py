"""
FILE: src/detectors/who_detector.py
PURPOSE: WHO Detector - Analyzes lead attributes that correlate with conversions
PHASE: 16 (Conversion Intelligence), Updated Phase 24D
TASK: 16A-003, THREAD-008
DEPENDENCIES:
  - src/detectors/base.py
  - src/models/conversion_patterns.py
  - src/models/lead.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Detectors can import from models only

WHO Pattern Outputs:
  - title_rankings: Which job titles convert best
  - industry_rankings: Which industries convert best
  - size_analysis: Employee count sweet spot
  - timing_signals: Lift from timing signals (new role, hiring, funded)
  - recommended_weights: Optimized ALS component weights
  - objection_patterns: Which segments raise which objections (Phase 24D)
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.detectors.base import BaseDetector
from src.models.base import LeadStatus
from src.models.conversion_patterns import ConversionPattern
from src.models.lead import Lead


class WhoDetector(BaseDetector):
    """
    WHO Detector - Analyzes which lead attributes predict conversions.

    Analyzes:
    - Job title effectiveness (which titles convert?)
    - Industry performance (which industries convert?)
    - Company size sweet spot (what employee range converts?)
    - Timing signals (new role, hiring, funding lifts)
    - Objection patterns by segment (Phase 24D)

    Output is used to:
    - Optimize ALS component weights
    - Prioritize leads with high-converting attributes
    - Focus outreach on proven ICP segments
    - Anticipate objections based on lead profile
    """

    pattern_type = "who"

    async def detect(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> ConversionPattern:
        """
        Run WHO pattern detection for a client.

        Analyzes all leads with outcomes to find attribute patterns.
        """
        # Get leads with outcomes
        leads = await self._get_leads_with_outcomes(db, client_id)

        if len(leads) < self.min_sample_size:
            # Not enough data - return low-confidence pattern
            return await self.save_pattern(
                db=db,
                client_id=client_id,
                patterns=self._default_patterns(),
                sample_size=len(leads),
                confidence=self.calculate_confidence(len(leads)),
            )

        # Calculate baseline conversion rate
        converted = [l for l in leads if l.status == LeadStatus.CONVERTED]
        baseline_rate = len(converted) / len(leads) if leads else 0

        # Analyze each dimension
        title_rankings = self._analyze_titles(leads, baseline_rate)
        industry_rankings = self._analyze_industries(leads, baseline_rate)
        size_analysis = self._analyze_company_size(leads, baseline_rate)
        timing_signals = self._analyze_timing_signals(leads, baseline_rate)

        # Phase 24D: Analyze objection patterns by segment
        objection_patterns = await self._analyze_objection_patterns(db, client_id)

        # Build pattern output
        patterns = {
            "type": "who",
            "version": "2.0",  # Updated for Phase 24D
            "computed_at": datetime.utcnow().isoformat(),
            "sample_size": len(leads),
            "baseline_conversion_rate": round(baseline_rate, 4),
            "title_rankings": title_rankings,
            "industry_rankings": industry_rankings,
            "size_analysis": size_analysis,
            "timing_signals": timing_signals,
            "objection_patterns": objection_patterns,  # Phase 24D
        }

        confidence = self.calculate_confidence(len(leads))

        return await self.save_pattern(
            db=db,
            client_id=client_id,
            patterns=patterns,
            sample_size=len(leads),
            confidence=confidence,
        )

    async def _get_leads_with_outcomes(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> list[Lead]:
        """Get all leads with definitive outcomes (converted or failed)."""
        # Look back 90 days for outcome data
        cutoff = datetime.utcnow() - timedelta(days=90)

        stmt = select(Lead).where(
            and_(
                Lead.client_id == client_id,
                Lead.status.in_([
                    LeadStatus.CONVERTED,
                    LeadStatus.BOUNCED,
                    LeadStatus.OPT_OUT,
                    LeadStatus.NURTURING,  # Consider as non-conversion
                ]),
                Lead.created_at >= cutoff,
                Lead.deleted_at.is_(None),
            )
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    def _analyze_titles(
        self,
        leads: list[Lead],
        baseline_rate: float,
    ) -> list[dict[str, Any]]:
        """Analyze conversion rates by job title."""
        title_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "converted": 0}
        )

        for lead in leads:
            title = self._normalize_title(lead.title)
            if not title:
                continue

            title_stats[title]["total"] += 1
            if lead.status == LeadStatus.CONVERTED:
                title_stats[title]["converted"] += 1

        # Calculate conversion rates and lift
        rankings = []
        for title, stats in title_stats.items():
            if stats["total"] < 5:  # Need minimum sample
                continue

            rate = stats["converted"] / stats["total"]
            lift = self.calculate_lift(rate, baseline_rate)

            rankings.append({
                "title": title,
                "conversion_rate": round(rate, 4),
                "sample": stats["total"],
                "lift": round(lift, 2),
            })

        # Sort by conversion rate descending
        rankings.sort(key=lambda x: x["conversion_rate"], reverse=True)

        return rankings[:10]  # Top 10

    def _analyze_industries(
        self,
        leads: list[Lead],
        baseline_rate: float,
    ) -> list[dict[str, Any]]:
        """Analyze conversion rates by industry."""
        industry_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "converted": 0}
        )

        for lead in leads:
            industry = lead.organization_industry
            if not industry:
                continue

            industry_stats[industry]["total"] += 1
            if lead.status == LeadStatus.CONVERTED:
                industry_stats[industry]["converted"] += 1

        rankings = []
        for industry, stats in industry_stats.items():
            if stats["total"] < 5:
                continue

            rate = stats["converted"] / stats["total"]
            lift = self.calculate_lift(rate, baseline_rate)

            rankings.append({
                "industry": industry,
                "conversion_rate": round(rate, 4),
                "sample": stats["total"],
                "lift": round(lift, 2),
            })

        rankings.sort(key=lambda x: x["conversion_rate"], reverse=True)

        return rankings[:10]

    def _analyze_company_size(
        self,
        leads: list[Lead],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """Analyze conversion rates by company size."""
        size_ranges = [
            ("1-5", 1, 5),
            ("6-15", 6, 15),
            ("16-30", 16, 30),
            ("31-50", 31, 50),
            ("51-100", 51, 100),
            ("101-250", 101, 250),
            ("251-500", 251, 500),
            ("501+", 501, float("inf")),
        ]

        range_stats: dict[str, dict[str, int]] = {
            r[0]: {"total": 0, "converted": 0} for r in size_ranges
        }

        for lead in leads:
            size = lead.organization_employee_count
            if not size:
                continue

            for range_name, min_size, max_size in size_ranges:
                if min_size <= size <= max_size:
                    range_stats[range_name]["total"] += 1
                    if lead.status == LeadStatus.CONVERTED:
                        range_stats[range_name]["converted"] += 1
                    break

        # Calculate rates
        distribution = []
        sweet_spot = None
        best_rate = 0

        for range_name, _, _ in size_ranges:
            stats = range_stats[range_name]
            if stats["total"] < 3:
                continue

            rate = stats["converted"] / stats["total"]
            distribution.append({
                "range": range_name,
                "conversion_rate": round(rate, 4),
                "sample": stats["total"],
            })

            if rate > best_rate:
                best_rate = rate
                sweet_spot = range_name

        return {
            "sweet_spot": sweet_spot,
            "sweet_spot_rate": round(best_rate, 4),
            "distribution": distribution,
        }

    def _analyze_timing_signals(
        self,
        leads: list[Lead],
        baseline_rate: float,
    ) -> dict[str, float]:
        """Analyze lift from timing signals in lead data."""
        # These would come from enrichment data
        signals = {
            "new_role": {"with": 0, "with_converted": 0},
            "hiring": {"with": 0, "with_converted": 0},
            "funded": {"with": 0, "with_converted": 0},
        }

        for lead in leads:
            # Check for timing signals in enriched data
            enriched = lead.enriched_data or {}

            # New role (job changed within 90 days)
            if enriched.get("job_change_90d"):
                signals["new_role"]["with"] += 1
                if lead.status == LeadStatus.CONVERTED:
                    signals["new_role"]["with_converted"] += 1

            # Hiring (has job listings)
            if enriched.get("actively_hiring"):
                signals["hiring"]["with"] += 1
                if lead.status == LeadStatus.CONVERTED:
                    signals["hiring"]["with_converted"] += 1

            # Funded (recent funding round)
            if enriched.get("recent_funding"):
                signals["funded"]["with"] += 1
                if lead.status == LeadStatus.CONVERTED:
                    signals["funded"]["with_converted"] += 1

        # Calculate lifts
        result = {}
        for signal, stats in signals.items():
            if stats["with"] >= 5:
                rate = stats["with_converted"] / stats["with"]
                result[f"{signal}_lift"] = round(
                    self.calculate_lift(rate, baseline_rate), 2
                )
            else:
                result[f"{signal}_lift"] = 1.0  # No lift if insufficient data

        return result

    def _normalize_title(self, title: str | None) -> str | None:
        """Normalize job titles for grouping."""
        if not title:
            return None

        title = title.strip().lower()

        # Map common variations to canonical forms
        title_mappings = {
            "ceo": ["chief executive", "chief exec", "c.e.o"],
            "cmo": ["chief marketing", "chief mktg", "vp marketing", "vp of marketing"],
            "cfo": ["chief financial", "chief finance"],
            "coo": ["chief operating", "chief ops"],
            "cto": ["chief technology", "chief tech"],
            "owner": ["founder", "co-founder", "cofounder", "principal"],
            "marketing director": ["director of marketing", "director marketing"],
            "sales director": ["director of sales", "director sales"],
        }

        for canonical, variations in title_mappings.items():
            if any(v in title for v in variations):
                return canonical
            if canonical in title:
                return canonical

        # Keep original if no mapping found
        return title.title()

    async def _analyze_objection_patterns(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any]:
        """
        Analyze objection patterns by lead segments (Phase 24D).

        This helps CIS learn which lead profiles tend to raise which objections,
        enabling proactive objection handling.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Objection patterns by industry, size, and title
        """
        # Analyze objections by industry
        industry_query = text("""
            SELECT
                l.organization_industry as segment,
                UNNEST(l.objections_raised) as objection_type,
                COUNT(*) as count
            FROM leads l
            WHERE l.client_id = :client_id
            AND l.objections_raised IS NOT NULL
            AND array_length(l.objections_raised, 1) > 0
            AND l.deleted_at IS NULL
            GROUP BY l.organization_industry, UNNEST(l.objections_raised)
            ORDER BY count DESC
            LIMIT 20
        """)

        industry_result = await db.execute(industry_query, {"client_id": client_id})
        industry_rows = industry_result.fetchall()

        # Organize by industry
        by_industry = defaultdict(list)
        for row in industry_rows:
            if row.segment:
                by_industry[row.segment].append({
                    "objection": row.objection_type,
                    "count": row.count,
                })

        # Analyze objections by company size
        size_query = text("""
            SELECT
                CASE
                    WHEN l.organization_employee_count <= 50 THEN 'small'
                    WHEN l.organization_employee_count <= 250 THEN 'medium'
                    ELSE 'large'
                END as segment,
                UNNEST(l.objections_raised) as objection_type,
                COUNT(*) as count
            FROM leads l
            WHERE l.client_id = :client_id
            AND l.objections_raised IS NOT NULL
            AND array_length(l.objections_raised, 1) > 0
            AND l.organization_employee_count IS NOT NULL
            AND l.deleted_at IS NULL
            GROUP BY 1, UNNEST(l.objections_raised)
            ORDER BY count DESC
        """)

        size_result = await db.execute(size_query, {"client_id": client_id})
        size_rows = size_result.fetchall()

        by_size = defaultdict(list)
        for row in size_rows:
            by_size[row.segment].append({
                "objection": row.objection_type,
                "count": row.count,
            })

        # Get overall objection distribution
        overall_query = text("""
            SELECT
                UNNEST(l.objections_raised) as objection_type,
                COUNT(*) as count,
                COUNT(DISTINCT l.id) as unique_leads
            FROM leads l
            WHERE l.client_id = :client_id
            AND l.objections_raised IS NOT NULL
            AND array_length(l.objections_raised, 1) > 0
            AND l.deleted_at IS NULL
            GROUP BY UNNEST(l.objections_raised)
            ORDER BY count DESC
        """)

        overall_result = await db.execute(overall_query, {"client_id": client_id})
        overall_rows = overall_result.fetchall()

        overall = [
            {
                "objection": row.objection_type,
                "count": row.count,
                "unique_leads": row.unique_leads,
            }
            for row in overall_rows
        ]

        return {
            "by_industry": dict(by_industry),
            "by_company_size": dict(by_size),
            "overall_distribution": overall,
        }

    def _default_patterns(self) -> dict[str, Any]:
        """Return default patterns when insufficient data."""
        return {
            "type": "who",
            "version": "2.0",
            "computed_at": datetime.utcnow().isoformat(),
            "sample_size": 0,
            "baseline_conversion_rate": 0.0,
            "title_rankings": [],
            "industry_rankings": [],
            "size_analysis": {
                "sweet_spot": None,
                "sweet_spot_rate": 0.0,
                "distribution": [],
            },
            "timing_signals": {
                "new_role_lift": 1.0,
                "hiring_lift": 1.0,
                "funded_lift": 1.0,
            },
            "objection_patterns": {  # Phase 24D
                "by_industry": {},
                "by_company_size": {},
                "overall_distribution": [],
            },
            "note": "Insufficient data for pattern detection. Need at least 30 leads with outcomes.",
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] Extends BaseDetector
# [x] pattern_type = "who"
# [x] detect() method implemented
# [x] _get_leads_with_outcomes() fetches outcome data
# [x] _analyze_titles() with normalization
# [x] _analyze_industries() ranking
# [x] _analyze_company_size() with sweet spot detection
# [x] _analyze_timing_signals() for enrichment signals
# [x] calculate_lift() used for segment comparison
# [x] calculate_confidence() from base class
# [x] Minimum sample checks
# [x] 90-day lookback window
# [x] All functions have type hints
# [x] All functions have docstrings
#
# Phase 24D Additions (THREAD-008):
# [x] _analyze_objection_patterns() for segment objection analysis
# [x] Objection patterns by industry
# [x] Objection patterns by company size
# [x] Overall objection distribution
# [x] Updated version to 2.0
