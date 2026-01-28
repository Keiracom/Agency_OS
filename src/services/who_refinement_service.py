"""
Contract: src/services/who_refinement_service.py
Purpose: Apply WHO conversion patterns to refine ICP search criteria
Layer: 3 - services
Imports: models
Consumers: scout engine, pool population flow

FILE: src/services/who_refinement_service.py
PURPOSE: Apply WHO conversion patterns to refine ICP search criteria
PHASE: 19 (ICP Refinement from CIS)
TASK: Item 19
DEPENDENCIES:
  - src/models/conversion_patterns.py
  - src/models/client.py
LAYER: 3 (services)
CONSUMERS: scout.py, pool_population_flow.py

This service automatically refines Apollo search criteria based on WHO conversion
patterns. It merges learned patterns (which titles/industries/sizes convert best)
with the original ICP to improve lead quality over time.

Key Design Decisions:
- Original ICP preserved (never modified)
- Refinements applied dynamically at search time
- All refinements logged for transparency (Phase H dashboard integration)
- Customer can lock fields from auto-refinement
- Minimum confidence threshold (0.6) required to apply refinements
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversion_patterns import ConversionPattern

logger = logging.getLogger(__name__)

# Minimum confidence to apply WHO refinements
MIN_CONFIDENCE_THRESHOLD = 0.6

# Minimum lift to boost a title/industry (must be meaningfully better than baseline)
MIN_LIFT_THRESHOLD = 1.2

# Maximum titles/industries to boost (prevent over-narrowing)
MAX_BOOST_ITEMS = 5


class WhoRefinementService:
    """
    Service for applying WHO conversion patterns to search criteria.

    Provides transparent, automated refinement of ICP criteria based on
    what's actually converting for each client.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the WHO Refinement service.

        Args:
            session: Async database session
        """
        self.session = session

    async def get_refined_criteria(
        self,
        client_id: UUID,
        base_criteria: dict[str, Any],
        locked_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Apply WHO pattern refinements to base ICP criteria.

        Args:
            client_id: Client UUID
            base_criteria: Original ICP criteria dict with keys:
                - titles: list[str]
                - industries: list[str]
                - employee_min: int | None
                - employee_max: int | None
                - countries: list[str]
                - seniorities: list[str]
            locked_fields: Fields to exclude from refinement (customer override)

        Returns:
            Refined criteria dict (same structure as input)
        """
        locked_fields = locked_fields or []

        # Load valid WHO pattern
        pattern = await self._load_valid_who_pattern(client_id)

        if not pattern:
            logger.debug(f"No valid WHO pattern for client {client_id}, using base criteria")
            return base_criteria

        if pattern.confidence < MIN_CONFIDENCE_THRESHOLD:
            logger.debug(
                f"WHO pattern confidence {pattern.confidence:.2f} below threshold "
                f"{MIN_CONFIDENCE_THRESHOLD}, using base criteria"
            )
            return base_criteria

        # Start with base criteria
        refined = dict(base_criteria)
        refinements_applied = []

        patterns_data = pattern.patterns

        # Apply title refinements
        if "titles" not in locked_fields:
            title_result = self._boost_high_lift_titles(
                base_titles=base_criteria.get("titles", []),
                title_rankings=patterns_data.get("title_rankings", []),
            )
            if title_result["boosted"]:
                refined["titles"] = title_result["titles"]
                refinements_applied.append({
                    "field": "titles",
                    "action": "boosted",
                    "added": title_result["added"],
                    "reason": "High-converting titles from WHO patterns",
                })

        # Apply industry refinements
        if "industries" not in locked_fields:
            industry_result = self._prioritize_industries(
                base_industries=base_criteria.get("industries", []),
                industry_rankings=patterns_data.get("industry_rankings", []),
            )
            if industry_result["prioritized"]:
                refined["industries"] = industry_result["industries"]
                refinements_applied.append({
                    "field": "industries",
                    "action": "prioritized",
                    "prioritized": industry_result["top_industries"],
                    "reason": "High-converting industries from WHO patterns",
                })

        # Apply company size refinements
        if "employee_min" not in locked_fields and "employee_max" not in locked_fields:
            size_result = self._apply_size_sweet_spot(
                base_min=base_criteria.get("employee_min"),
                base_max=base_criteria.get("employee_max"),
                size_analysis=patterns_data.get("size_analysis", {}),
            )
            if size_result["adjusted"]:
                refined["employee_min"] = size_result["employee_min"]
                refined["employee_max"] = size_result["employee_max"]
                refinements_applied.append({
                    "field": "company_size",
                    "action": "narrowed_to_sweet_spot",
                    "sweet_spot": size_result["sweet_spot"],
                    "reason": f"Sweet spot range has {size_result['conversion_rate']:.0%} conversion",
                })

        # Log refinements for transparency (Phase H dashboard integration)
        if refinements_applied:
            await self._log_refinement(
                client_id=client_id,
                pattern_id=pattern.id,
                base_criteria=base_criteria,
                refined_criteria=refined,
                refinements=refinements_applied,
                confidence=pattern.confidence,
            )

            logger.info(
                f"Applied {len(refinements_applied)} WHO refinements for client {client_id}: "
                f"{[r['field'] for r in refinements_applied]}"
            )

        return refined

    async def _load_valid_who_pattern(
        self,
        client_id: UUID,
    ) -> ConversionPattern | None:
        """
        Load the current valid WHO pattern for a client.

        Args:
            client_id: Client UUID

        Returns:
            ConversionPattern if valid one exists, None otherwise
        """
        stmt = select(ConversionPattern).where(
            and_(
                ConversionPattern.client_id == client_id,
                ConversionPattern.pattern_type == "who",
                ConversionPattern.valid_until > datetime.utcnow(),
            )
        ).order_by(ConversionPattern.computed_at.desc()).limit(1)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _boost_high_lift_titles(
        self,
        base_titles: list[str],
        title_rankings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Boost high-converting titles into the search criteria.

        Strategy:
        - Keep all base titles (respect original ICP)
        - Add high-lift titles not already in base (up to MAX_BOOST_ITEMS)
        - Move high-lift titles to front of list (Apollo may prioritize)

        Args:
            base_titles: Original ICP titles
            title_rankings: WHO pattern title rankings with lift scores

        Returns:
            Dict with:
                - titles: Final title list
                - boosted: Whether any boost was applied
                - added: Titles that were added
        """
        if not title_rankings:
            return {"titles": base_titles, "boosted": False, "added": []}

        # Normalize base titles for comparison
        base_lower = {t.lower().strip() for t in base_titles}

        # Find high-lift titles not already in base
        high_lift_titles = []
        for ranking in title_rankings[:10]:  # Top 10 from WHO
            title = ranking.get("title", "")
            lift = ranking.get("lift", 1.0)
            sample = ranking.get("sample", 0)

            # Must have meaningful lift and sample size
            if lift >= MIN_LIFT_THRESHOLD and sample >= 5:
                if title.lower().strip() not in base_lower:
                    high_lift_titles.append(title)

        if not high_lift_titles:
            return {"titles": base_titles, "boosted": False, "added": []}

        # Limit to MAX_BOOST_ITEMS new titles
        titles_to_add = high_lift_titles[:MAX_BOOST_ITEMS]

        # Reorder: high-lift titles first, then original base titles
        # This prioritizes high-converting titles in Apollo search
        final_titles = titles_to_add + list(base_titles)

        return {
            "titles": final_titles,
            "boosted": True,
            "added": titles_to_add,
        }

    def _prioritize_industries(
        self,
        base_industries: list[str],
        industry_rankings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Prioritize high-converting industries in search criteria.

        Strategy:
        - If base has industries: reorder to put high-lift ones first
        - If base empty: use top high-lift industries from WHO

        Args:
            base_industries: Original ICP industries
            industry_rankings: WHO pattern industry rankings with lift scores

        Returns:
            Dict with:
                - industries: Final industry list
                - prioritized: Whether any prioritization was applied
                - top_industries: Industries that were prioritized
        """
        if not industry_rankings:
            return {"industries": base_industries, "prioritized": False, "top_industries": []}

        # Get high-lift industries
        high_lift = []
        for ranking in industry_rankings[:10]:
            industry = ranking.get("industry", "")
            lift = ranking.get("lift", 1.0)
            sample = ranking.get("sample", 0)

            if lift >= MIN_LIFT_THRESHOLD and sample >= 5 and industry:
                high_lift.append(industry)

        if not high_lift:
            return {"industries": base_industries, "prioritized": False, "top_industries": []}

        if not base_industries:
            # No base industries - use WHO-recommended ones
            final = high_lift[:MAX_BOOST_ITEMS]
            return {
                "industries": final,
                "prioritized": True,
                "top_industries": final,
            }

        # Reorder base industries: high-lift first, then others
        {i.lower().strip(): i for i in base_industries}
        high_lift_lower = {i.lower().strip() for i in high_lift}

        # Split base into high-lift and others
        prioritized = []
        others = []
        for industry in base_industries:
            if industry.lower().strip() in high_lift_lower:
                prioritized.append(industry)
            else:
                others.append(industry)

        # If no overlap, add top high-lift to front
        if not prioritized:
            # Add high-lift industries that Apollo understands
            # (keep original base, prepend high-lift)
            final = high_lift[:3] + list(base_industries)
            return {
                "industries": final,
                "prioritized": True,
                "top_industries": high_lift[:3],
            }

        # Reorder: prioritized first, then others
        final = prioritized + others
        return {
            "industries": final,
            "prioritized": True,
            "top_industries": prioritized,
        }

    def _apply_size_sweet_spot(
        self,
        base_min: int | None,
        base_max: int | None,
        size_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Narrow company size to conversion sweet spot.

        Strategy:
        - Only narrow if WHO sweet spot has significantly higher conversion
        - Don't widen beyond original ICP (customer intent)
        - Require sweet spot to be within original range

        Args:
            base_min: Original minimum employee count
            base_max: Original maximum employee count
            size_analysis: WHO pattern size analysis with sweet_spot

        Returns:
            Dict with:
                - employee_min: Final min
                - employee_max: Final max
                - adjusted: Whether adjustment was made
                - sweet_spot: The sweet spot range applied
                - conversion_rate: Conversion rate of sweet spot
        """
        sweet_spot = size_analysis.get("sweet_spot", "")
        sweet_spot_rate = size_analysis.get("sweet_spot_rate", 0)
        baseline_rate = size_analysis.get("baseline_conversion_rate", 0)

        if not sweet_spot or sweet_spot_rate <= 0:
            return {
                "employee_min": base_min,
                "employee_max": base_max,
                "adjusted": False,
                "sweet_spot": None,
                "conversion_rate": 0,
            }

        # Parse sweet spot range (e.g., "16-30" or "101-250")
        try:
            sweet_min, sweet_max = self._parse_size_range(sweet_spot)
        except ValueError:
            return {
                "employee_min": base_min,
                "employee_max": base_max,
                "adjusted": False,
                "sweet_spot": None,
                "conversion_rate": 0,
            }

        # Only adjust if sweet spot is meaningfully better (20%+ lift)
        if baseline_rate > 0:
            lift = sweet_spot_rate / baseline_rate
            if lift < 1.2:
                return {
                    "employee_min": base_min,
                    "employee_max": base_max,
                    "adjusted": False,
                    "sweet_spot": None,
                    "conversion_rate": 0,
                }

        # Apply sweet spot, but only narrow (don't widen beyond original ICP)
        final_min = base_min
        final_max = base_max

        if base_min is not None and base_max is not None:
            # Narrow to intersection of base range and sweet spot
            final_min = max(base_min, sweet_min)
            final_max = min(base_max, sweet_max)

            # Ensure valid range
            if final_min > final_max:
                # Sweet spot doesn't overlap with base - don't adjust
                return {
                    "employee_min": base_min,
                    "employee_max": base_max,
                    "adjusted": False,
                    "sweet_spot": None,
                    "conversion_rate": 0,
                }
        elif base_min is None and base_max is None:
            # No base constraints - use sweet spot
            final_min = sweet_min
            final_max = sweet_max
        elif base_min is not None:
            # Only min specified
            final_min = max(base_min, sweet_min)
            final_max = sweet_max
        else:
            # Only max specified (base_min is None, base_max is not None)
            final_min = sweet_min
            # base_max is guaranteed non-None here by the elif chain logic
            final_max = min(base_max, sweet_max) if base_max is not None else sweet_max

        # Check if we actually changed anything
        if final_min == base_min and final_max == base_max:
            return {
                "employee_min": base_min,
                "employee_max": base_max,
                "adjusted": False,
                "sweet_spot": None,
                "conversion_rate": 0,
            }

        return {
            "employee_min": final_min,
            "employee_max": final_max,
            "adjusted": True,
            "sweet_spot": sweet_spot,
            "conversion_rate": sweet_spot_rate,
        }

    def _parse_size_range(self, range_str: str) -> tuple[int, int]:
        """
        Parse a size range string like "16-30" or "501+" into min/max.

        Args:
            range_str: Range string (e.g., "16-30", "501+", "1-5")

        Returns:
            Tuple of (min, max)

        Raises:
            ValueError: If range string cannot be parsed
        """
        range_str = range_str.strip()

        if "+" in range_str:
            # Open-ended range like "501+"
            min_val = int(range_str.replace("+", "").strip())
            return (min_val, 1000000)  # Large max for open-ended

        if "-" in range_str:
            parts = range_str.split("-")
            if len(parts) == 2:
                return (int(parts[0].strip()), int(parts[1].strip()))

        raise ValueError(f"Cannot parse size range: {range_str}")

    async def _log_refinement(
        self,
        client_id: UUID,
        pattern_id: UUID,
        base_criteria: dict[str, Any],
        refined_criteria: dict[str, Any],
        refinements: list[dict[str, Any]],
        confidence: float,
    ) -> None:
        """
        Log applied refinements for transparency and audit.

        This data will be displayed in the Phase H dashboard
        to show customers what refinements were applied.

        Args:
            client_id: Client UUID
            pattern_id: WHO pattern UUID that informed the refinement
            base_criteria: Original ICP criteria
            refined_criteria: Final refined criteria
            refinements: List of refinement actions taken
            confidence: WHO pattern confidence score
        """
        from sqlalchemy import text

        # Insert into icp_refinement_log table
        stmt = text("""
            INSERT INTO icp_refinement_log (
                id, client_id, pattern_id, base_criteria, refined_criteria,
                refinements_applied, confidence, applied_at
            ) VALUES (
                gen_random_uuid(), :client_id, :pattern_id, :base_criteria::jsonb,
                :refined_criteria::jsonb, :refinements::jsonb, :confidence, NOW()
            )
        """)

        import json
        await self.session.execute(
            stmt,
            {
                "client_id": str(client_id),
                "pattern_id": str(pattern_id),
                "base_criteria": json.dumps(base_criteria),
                "refined_criteria": json.dumps(refined_criteria),
                "refinements": json.dumps(refinements),
                "confidence": confidence,
            }
        )
        # Note: Commit handled by caller's session management

    async def get_locked_fields(self, client_id: UUID) -> list[str]:
        """
        Get fields that the customer has locked from auto-refinement.

        Args:
            client_id: Client UUID

        Returns:
            List of locked field names
        """
        from sqlalchemy import text

        stmt = text("""
            SELECT targeting_locked_fields
            FROM clients
            WHERE id = :client_id AND deleted_at IS NULL
        """)

        result = await self.session.execute(stmt, {"client_id": str(client_id)})
        row = result.fetchone()

        if row and row[0]:
            return list(row[0])
        return []


# Convenience function for use without instantiating class
async def get_who_refined_criteria(
    db: AsyncSession,
    client_id: UUID,
    base_criteria: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply WHO pattern refinements to ICP criteria.

    This is the main entry point for integrating WHO refinement
    into search flows (scout.py, pool_population_flow.py).

    Args:
        db: Database session
        client_id: Client UUID
        base_criteria: Original ICP criteria dict

    Returns:
        Refined criteria dict
    """
    service = WhoRefinementService(db)

    # Get customer's locked fields
    locked_fields = await service.get_locked_fields(client_id)

    # Apply refinements
    return await service.get_refined_criteria(
        client_id=client_id,
        base_criteria=base_criteria,
        locked_fields=locked_fields,
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top of file
# [x] Layer 3 service (imports models only)
# [x] Async methods with type hints
# [x] Docstrings on all public methods
# [x] Logging at appropriate levels
# [x] Minimum confidence threshold (0.6)
# [x] Locked fields support (customer control)
# [x] Refinement logging for transparency
# [x] Convenience function for easy integration
# [x] No hardcoded credentials
