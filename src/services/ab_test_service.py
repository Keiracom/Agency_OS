"""
FILE: src/services/ab_test_service.py
PURPOSE: Service for managing A/B tests for content optimization
PHASE: 24B (Content & Template Tracking)
TASK: CONTENT-005
DEPENDENCIES:
  - src/models/database.py
LAYER: 3 (services)
CONSUMERS: orchestration, API routes, content engines

This service manages A/B tests for email subjects, message bodies,
and other content variations to optimize conversion rates.
"""

from datetime import datetime
from typing import Any
from uuid import UUID
import random

from sqlalchemy import and_, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError


class ABTestService:
    """
    Service for managing A/B tests.

    A/B tests allow comparing different content variants
    to identify which performs better for conversions.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the A/B Test service.

        Args:
            session: Async database session
        """
        self.session = session

    async def create(
        self,
        client_id: UUID,
        campaign_id: UUID,
        name: str,
        variant_a_description: str,
        variant_b_description: str,
        hypothesis: str | None = None,
        metric: str = "reply_rate",
        sample_size_target: int | None = None,
        split_percentage: int = 50,
        created_by: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Create a new A/B test.

        Args:
            client_id: Client UUID
            campaign_id: Campaign UUID
            name: Test name
            variant_a_description: Description of variant A
            variant_b_description: Description of variant B
            hypothesis: Test hypothesis
            metric: Metric to measure (reply_rate, open_rate, click_rate, conversion_rate, meeting_rate)
            sample_size_target: Target sample size for statistical significance
            split_percentage: Percentage of traffic to variant A (rest goes to B)
            created_by: User who created the test

        Returns:
            Created A/B test record

        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate metric
        valid_metrics = ["reply_rate", "open_rate", "click_rate", "conversion_rate", "meeting_rate"]
        if metric not in valid_metrics:
            raise ValidationError(message=f"Invalid metric. Must be one of: {valid_metrics}")

        # Validate split percentage
        if not 1 <= split_percentage <= 99:
            raise ValidationError(message="Split percentage must be between 1 and 99")

        query = text("""
            INSERT INTO ab_tests (
                client_id, campaign_id, name, description, hypothesis,
                variant_a_description, variant_b_description,
                metric, sample_size_target, split_percentage,
                status, created_by, created_at, updated_at
            ) VALUES (
                :client_id, :campaign_id, :name, :description, :hypothesis,
                :variant_a_description, :variant_b_description,
                :metric, :sample_size_target, :split_percentage,
                'draft', :created_by, NOW(), NOW()
            )
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "campaign_id": campaign_id,
            "name": name,
            "description": f"A/B test: {name}",
            "hypothesis": hypothesis,
            "variant_a_description": variant_a_description,
            "variant_b_description": variant_b_description,
            "metric": metric,
            "sample_size_target": sample_size_target,
            "split_percentage": split_percentage,
            "created_by": created_by,
        })

        row = result.fetchone()
        await self.session.commit()

        return dict(row._mapping)

    async def get_by_id(self, test_id: UUID) -> dict[str, Any] | None:
        """
        Get an A/B test by ID.

        Args:
            test_id: A/B test UUID

        Returns:
            A/B test record or None if not found
        """
        query = text("""
            SELECT * FROM ab_tests WHERE id = :test_id
        """)

        result = await self.session.execute(query, {"test_id": test_id})
        row = result.fetchone()

        if not row:
            return None

        return dict(row._mapping)

    async def get_active_for_campaign(self, campaign_id: UUID) -> dict[str, Any] | None:
        """
        Get the currently running A/B test for a campaign.

        Args:
            campaign_id: Campaign UUID

        Returns:
            Active A/B test or None if none running
        """
        query = text("""
            SELECT * FROM ab_tests
            WHERE campaign_id = :campaign_id
            AND status = 'running'
            ORDER BY started_at DESC
            LIMIT 1
        """)

        result = await self.session.execute(query, {"campaign_id": campaign_id})
        row = result.fetchone()

        if not row:
            return None

        return dict(row._mapping)

    async def list_for_client(
        self,
        client_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        List A/B tests for a client.

        Args:
            client_id: Client UUID
            status: Optional status filter
            limit: Max results
            offset: Pagination offset

        Returns:
            List of A/B test records
        """
        if status:
            query = text("""
                SELECT * FROM ab_tests
                WHERE client_id = :client_id AND status = :status
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            result = await self.session.execute(query, {
                "client_id": client_id,
                "status": status,
                "limit": limit,
                "offset": offset,
            })
        else:
            query = text("""
                SELECT * FROM ab_tests
                WHERE client_id = :client_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            result = await self.session.execute(query, {
                "client_id": client_id,
                "limit": limit,
                "offset": offset,
            })

        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    async def start(self, test_id: UUID) -> dict[str, Any]:
        """
        Start an A/B test.

        Args:
            test_id: A/B test UUID

        Returns:
            Updated A/B test record

        Raises:
            NotFoundError: If test not found
            ValidationError: If test cannot be started
        """
        test = await self.get_by_id(test_id)
        if not test:
            raise NotFoundError(resource="ab_test", resource_id=str(test_id))

        if test["status"] not in ("draft", "paused"):
            raise ValidationError(
                message=f"Cannot start test in '{test['status']}' status. Must be 'draft' or 'paused'."
            )

        # Check for other running tests on same campaign
        existing = await self.get_active_for_campaign(test["campaign_id"])
        if existing and existing["id"] != test_id:
            raise ValidationError(
                message=f"Campaign already has a running A/B test: {existing['name']}"
            )

        query = text("""
            UPDATE ab_tests
            SET status = 'running',
                started_at = COALESCE(started_at, NOW()),
                updated_at = NOW()
            WHERE id = :test_id
            RETURNING *
        """)

        result = await self.session.execute(query, {"test_id": test_id})
        row = result.fetchone()
        await self.session.commit()

        return dict(row._mapping)

    async def pause(self, test_id: UUID) -> dict[str, Any]:
        """
        Pause an A/B test.

        Args:
            test_id: A/B test UUID

        Returns:
            Updated A/B test record
        """
        test = await self.get_by_id(test_id)
        if not test:
            raise NotFoundError(resource="ab_test", resource_id=str(test_id))

        if test["status"] != "running":
            raise ValidationError(
                message=f"Cannot pause test in '{test['status']}' status. Must be 'running'."
            )

        query = text("""
            UPDATE ab_tests
            SET status = 'paused', updated_at = NOW()
            WHERE id = :test_id
            RETURNING *
        """)

        result = await self.session.execute(query, {"test_id": test_id})
        row = result.fetchone()
        await self.session.commit()

        return dict(row._mapping)

    async def complete(
        self,
        test_id: UUID,
        winner: str | None = None,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        """
        Complete an A/B test.

        Args:
            test_id: A/B test UUID
            winner: Winner variant ('A', 'B', 'no_difference')
            confidence: Statistical confidence (0-1)

        Returns:
            Updated A/B test record
        """
        test = await self.get_by_id(test_id)
        if not test:
            raise NotFoundError(resource="ab_test", resource_id=str(test_id))

        if test["status"] not in ("running", "paused"):
            raise ValidationError(
                message=f"Cannot complete test in '{test['status']}' status."
            )

        # If no winner provided, calculate it
        if not winner:
            results = await self.calculate_results(test_id)
            winner = results.get("winner")
            confidence = results.get("confidence")

        query = text("""
            UPDATE ab_tests
            SET status = 'completed',
                ended_at = NOW(),
                winner = :winner,
                confidence = :confidence,
                updated_at = NOW()
            WHERE id = :test_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "test_id": test_id,
            "winner": winner,
            "confidence": confidence,
        })
        row = result.fetchone()
        await self.session.commit()

        return dict(row._mapping)

    async def cancel(self, test_id: UUID) -> dict[str, Any]:
        """
        Cancel an A/B test.

        Args:
            test_id: A/B test UUID

        Returns:
            Updated A/B test record
        """
        test = await self.get_by_id(test_id)
        if not test:
            raise NotFoundError(resource="ab_test", resource_id=str(test_id))

        if test["status"] == "completed":
            raise ValidationError(message="Cannot cancel a completed test.")

        query = text("""
            UPDATE ab_tests
            SET status = 'cancelled',
                ended_at = NOW(),
                updated_at = NOW()
            WHERE id = :test_id
            RETURNING *
        """)

        result = await self.session.execute(query, {"test_id": test_id})
        row = result.fetchone()
        await self.session.commit()

        return dict(row._mapping)

    async def assign_variant(
        self,
        test_id: UUID,
        lead_id: UUID | None = None,
    ) -> str:
        """
        Assign a variant for a new participant.

        Uses the split_percentage to determine assignment.

        Args:
            test_id: A/B test UUID
            lead_id: Optional lead ID for consistent assignment

        Returns:
            Assigned variant ('A' or 'B')
        """
        test = await self.get_by_id(test_id)
        if not test:
            raise NotFoundError(resource="ab_test", resource_id=str(test_id))

        if test["status"] != "running":
            raise ValidationError(
                message=f"Cannot assign variant for test in '{test['status']}' status."
            )

        # Use lead_id for consistent assignment if provided
        if lead_id:
            # Hash-based assignment for consistency
            hash_value = hash(str(lead_id) + str(test_id)) % 100
            return "A" if hash_value < test["split_percentage"] else "B"

        # Random assignment
        return "A" if random.randint(1, 100) <= test["split_percentage"] else "B"

    async def record_success(
        self,
        test_id: UUID,
        variant: str,
    ) -> None:
        """
        Record a success event for a variant.

        Called when the target metric is achieved (e.g., reply received).

        Args:
            test_id: A/B test UUID
            variant: Variant ('A' or 'B')
        """
        if variant not in ("A", "B"):
            raise ValidationError(message="Variant must be 'A' or 'B'")

        if variant == "A":
            query = text("""
                UPDATE ab_tests
                SET variant_a_success = variant_a_success + 1, updated_at = NOW()
                WHERE id = :test_id
            """)
        else:
            query = text("""
                UPDATE ab_tests
                SET variant_b_success = variant_b_success + 1, updated_at = NOW()
                WHERE id = :test_id
            """)

        await self.session.execute(query, {"test_id": test_id})
        await self.session.commit()

    async def calculate_results(self, test_id: UUID) -> dict[str, Any]:
        """
        Calculate the current results of an A/B test.

        Uses the database function for statistical calculation.

        Args:
            test_id: A/B test UUID

        Returns:
            Results including winner, confidence, and rates
        """
        query = text("""
            SELECT * FROM calculate_ab_test_winner(:test_id)
        """)

        result = await self.session.execute(query, {"test_id": test_id})
        row = result.fetchone()

        if not row:
            # If function returns nothing, calculate manually
            test = await self.get_by_id(test_id)
            if not test:
                raise NotFoundError(resource="ab_test", resource_id=str(test_id))

            variant_a_rate = 0.0
            variant_b_rate = 0.0
            if test["variant_a_count"] > 0:
                variant_a_rate = test["variant_a_success"] / test["variant_a_count"]
            if test["variant_b_count"] > 0:
                variant_b_rate = test["variant_b_success"] / test["variant_b_count"]

            return {
                "winner": None,
                "confidence": 0.0,
                "variant_a_rate": variant_a_rate,
                "variant_b_rate": variant_b_rate,
                "is_significant": False,
                "variant_a_count": test["variant_a_count"],
                "variant_b_count": test["variant_b_count"],
                "variant_a_success": test["variant_a_success"],
                "variant_b_success": test["variant_b_success"],
            }

        return {
            "winner": row.winner,
            "confidence": row.confidence,
            "variant_a_rate": row.variant_a_rate,
            "variant_b_rate": row.variant_b_rate,
            "is_significant": row.is_significant,
        }

    async def get_stats(self, test_id: UUID) -> dict[str, Any]:
        """
        Get detailed statistics for an A/B test.

        Args:
            test_id: A/B test UUID

        Returns:
            Test statistics including counts, rates, and significance
        """
        test = await self.get_by_id(test_id)
        if not test:
            raise NotFoundError(resource="ab_test", resource_id=str(test_id))

        results = await self.calculate_results(test_id)

        return {
            "test_id": test["id"],
            "name": test["name"],
            "status": test["status"],
            "metric": test["metric"],
            "started_at": test["started_at"],
            "ended_at": test["ended_at"],
            "variant_a": {
                "description": test["variant_a_description"],
                "count": test["variant_a_count"],
                "success": test["variant_a_success"],
                "rate": results["variant_a_rate"],
            },
            "variant_b": {
                "description": test["variant_b_description"],
                "count": test["variant_b_count"],
                "success": test["variant_b_success"],
                "rate": results["variant_b_rate"],
            },
            "winner": results.get("winner"),
            "confidence": results.get("confidence"),
            "is_significant": results.get("is_significant", False),
            "sample_size_target": test["sample_size_target"],
            "total_samples": test["variant_a_count"] + test["variant_b_count"],
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Session passed as argument
# [x] No imports from engines/integrations/orchestration
# [x] CRUD operations for A/B tests
# [x] Test lifecycle management (start, pause, complete, cancel)
# [x] Variant assignment with split percentage
# [x] Statistical significance calculation
# [x] Success recording for both variants
# [x] Campaign-level test enforcement (only one active)
# [x] All functions have type hints
# [x] All functions have docstrings
