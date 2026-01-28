"""
FILE: src/detectors/base.py
PURPOSE: Base class for all Conversion Intelligence Detectors
PHASE: 16 (Conversion Intelligence)
TASK: 16A-003
DEPENDENCIES:
  - src/models/conversion_patterns.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Detectors can import from models only
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversion_patterns import ConversionPattern

T = TypeVar("T")


class BaseDetector(ABC):
    """
    Abstract base class for Conversion Intelligence Detectors.

    Detectors analyze historical conversion data to find patterns that
    can improve future scoring and outreach decisions.

    Pattern Types:
    - WHO: Analyze which lead attributes correlate with conversions
    - WHAT: Analyze which content patterns convert best
    - WHEN: Analyze timing patterns (day, hour, touch number)
    - HOW: Analyze channel sequences and combinations
    """

    # Pattern type identifier
    pattern_type: str = ""

    # Minimum sample size for confident patterns
    min_sample_size: int = 30

    # Pattern validity period in days
    validity_days: int = 14

    @abstractmethod
    async def detect(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> ConversionPattern:
        """
        Run pattern detection for a client.

        Args:
            db: Database session
            client_id: Client UUID to analyze

        Returns:
            ConversionPattern with detected patterns
        """
        pass

    async def get_existing_pattern(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> ConversionPattern | None:
        """
        Get the existing pattern for this client if valid.

        Returns None if no pattern exists or pattern is expired.
        """
        stmt = select(ConversionPattern).where(
            ConversionPattern.client_id == client_id,
            ConversionPattern.pattern_type == self.pattern_type,
            ConversionPattern.valid_until > datetime.utcnow(),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def save_pattern(
        self,
        db: AsyncSession,
        client_id: UUID,
        patterns: dict[str, Any],
        sample_size: int,
        confidence: float,
    ) -> ConversionPattern:
        """
        Save a new pattern, replacing any existing one.

        Args:
            db: Database session
            client_id: Client UUID
            patterns: Detected patterns as dict
            sample_size: Number of samples used
            confidence: Confidence score 0.0-1.0

        Returns:
            Saved ConversionPattern
        """
        # Create new pattern
        pattern = ConversionPattern.create(
            client_id=client_id,
            pattern_type=self.pattern_type,
            patterns=patterns,
            sample_size=sample_size,
            confidence=confidence,
            validity_days=self.validity_days,
        )

        # Merge to handle upsert (unique constraint on client_id + pattern_type)
        await db.merge(pattern)
        await db.commit()

        return pattern

    def calculate_confidence(self, sample_size: int) -> float:
        """
        Calculate confidence score based on sample size.

        Uses a logarithmic scale:
        - 30 samples = 0.5 confidence
        - 100 samples = 0.7 confidence
        - 500 samples = 0.85 confidence
        - 1000+ samples = 0.95 confidence
        """
        import math

        if sample_size < 10:
            return 0.2
        if sample_size < self.min_sample_size:
            return 0.3 + (sample_size / self.min_sample_size) * 0.2

        # Logarithmic scaling from 30 to 1000+
        log_score = math.log10(sample_size) / math.log10(1000)
        confidence = 0.5 + log_score * 0.45

        return min(0.95, max(0.5, confidence))

    def calculate_lift(
        self,
        segment_rate: float,
        baseline_rate: float,
    ) -> float:
        """
        Calculate lift (improvement over baseline).

        Args:
            segment_rate: Conversion rate for segment
            baseline_rate: Overall baseline conversion rate

        Returns:
            Lift multiplier (1.0 = no lift, 2.0 = 100% improvement)
        """
        if baseline_rate <= 0:
            return 1.0
        return segment_rate / baseline_rate

    def conversion_rate_by(
        self,
        items: list[T],
        key_fn: Callable[[T], Any],
        is_converted_fn: Callable[[T], bool],
        min_sample: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Calculate conversion rates grouped by a key function.

        This is the core analysis function used by all detectors to
        compute segment-level conversion rates.

        Args:
            items: List of items to analyze (leads, activities, etc.)
            key_fn: Function to extract grouping key from item
            is_converted_fn: Function to check if item is a conversion
            min_sample: Minimum samples required to include segment

        Returns:
            List of dicts with key, conversion_rate, sample, and converted counts

        Example:
            # Analyze by job title
            results = detector.conversion_rate_by(
                items=leads,
                key_fn=lambda l: l.title,
                is_converted_fn=lambda l: l.status == LeadStatus.CONVERTED,
            )
            # Returns: [{"key": "CEO", "conversion_rate": 0.25, "sample": 100, ...}, ...]
        """
        stats: dict[Any, dict[str, int]] = defaultdict(lambda: {"total": 0, "converted": 0})

        for item in items:
            key = key_fn(item)
            if key is None:
                continue

            stats[key]["total"] += 1
            if is_converted_fn(item):
                stats[key]["converted"] += 1

        # Calculate rates for segments with sufficient sample
        results = []
        total_items = len(items)
        total_converted = sum(1 for i in items if is_converted_fn(i))
        baseline_rate = total_converted / total_items if total_items > 0 else 0

        for key, segment_stats in stats.items():
            if segment_stats["total"] < min_sample:
                continue

            rate = segment_stats["converted"] / segment_stats["total"]
            lift = self.calculate_lift(rate, baseline_rate)

            results.append(
                {
                    "key": key,
                    "conversion_rate": round(rate, 4),
                    "sample": segment_stats["total"],
                    "converted": segment_stats["converted"],
                    "lift": round(lift, 2),
                }
            )

        # Sort by conversion rate descending
        results.sort(key=lambda x: x["conversion_rate"], reverse=True)

        return results


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] Abstract base class with detect() method
# [x] get_existing_pattern() for pattern retrieval
# [x] save_pattern() for persistence
# [x] calculate_confidence() with logarithmic scale
# [x] calculate_lift() for segment analysis
# [x] conversion_rate_by() for segment analysis
# [x] min_sample_size and validity_days configurable
# [x] All functions have type hints
# [x] All functions have docstrings
