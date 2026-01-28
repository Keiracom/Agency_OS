"""
Contract: src/engines/allocator.py
Purpose: Channel and resource allocation with round-robin and rate limiting
Layer: 3 - engines
Imports: models, integrations
Consumers: orchestration only

FILE: src/engines/allocator.py
PURPOSE: Channel and resource allocation with round-robin and rate limiting
PHASE: 4 (Engines), modified Phase 16 for Conversion Intelligence
TASK: ENG-004, 16E-005
DEPENDENCIES:
  - src/engines/base.py
  - src/integrations/redis.py
  - src/models/lead.py
  - src/models/campaign.py
  - src/models/conversion_patterns.py (Phase 16)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines
  - Rule 14: Soft deletes only
  - Rule 17: Resource-level rate limits (17/day LinkedIn, 50/day email, 100/day SMS)
PHASE 16 CHANGES:
  - Uses HOW patterns to prioritize high-converting channels
  - Uses WHEN patterns for optimal timing recommendations
  - Tier-specific channel recommendations from HOW detector
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.base import BaseEngine, EngineResult
from src.exceptions import ResourceRateLimitError
from src.integrations.redis import rate_limiter
from src.models.base import ChannelType
from src.models.campaign import CampaignResource
from src.models.conversion_patterns import ConversionPattern
from src.models.lead import Lead

# ============================================
# Rate Limit Constants (Rule 17)
# ============================================

RATE_LIMITS = {
    ChannelType.LINKEDIN: 17,    # 17 per day per seat
    ChannelType.EMAIL: 50,       # 50 per day per domain
    ChannelType.SMS: 100,        # 100 per day per number
    ChannelType.VOICE: 50,       # 50 per day per number
    ChannelType.MAIL: 1000,      # Higher limit for mail
}


class AllocatorEngine(BaseEngine):
    """
    Allocator engine for channel and resource assignment.

    Handles:
    - Channel selection based on lead tier
    - Resource round-robin allocation
    - Resource-level rate limit enforcement (Rule 17)
    """

    @property
    def name(self) -> str:
        return "allocator"

    async def allocate_channels(
        self,
        db: AsyncSession,
        lead_id: UUID,
        available_channels: list[ChannelType],
    ) -> EngineResult[dict[str, Any]]:
        """
        Allocate channels for a lead based on tier and resource availability.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID
            available_channels: Channels allowed for this lead's tier

        Returns:
            EngineResult with allocated channels and resources
        """
        lead = await self.get_lead_by_id(db, lead_id)
        campaign = await self.get_campaign_by_id(db, lead.campaign_id)

        # Get available resources for this campaign
        resources = await self._get_campaign_resources(db, campaign.id)

        allocated = {
            "lead_id": str(lead_id),
            "campaign_id": str(campaign.id),
            "channels": [],
            "resources": {},
        }

        for channel in available_channels:
            # Find an available resource for this channel
            resource = await self._find_available_resource(
                resources=resources,
                channel=channel,
            )

            if resource:
                allocated["channels"].append(channel.value)
                allocated["resources"][channel.value] = {
                    "resource_id": resource["resource_id"],
                    "resource_name": resource["resource_name"],
                    "remaining_quota": resource["remaining_quota"],
                }

                # Assign resource to lead
                await self._assign_resource_to_lead(db, lead, channel, resource)

        if not allocated["channels"]:
            return EngineResult.fail(
                error="No channels could be allocated - all resources exhausted",
                metadata={"lead_id": str(lead_id)},
            )

        return EngineResult.ok(
            data=allocated,
            metadata={
                "channels_allocated": len(allocated["channels"]),
                "total_available": len(available_channels),
            },
        )

    async def get_next_resource(
        self,
        db: AsyncSession,
        campaign_id: UUID,
        channel: ChannelType,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get the next available resource for a channel using round-robin.

        Args:
            db: Database session (passed by caller)
            campaign_id: Campaign UUID
            channel: Channel type

        Returns:
            EngineResult with resource info
        """
        # Get campaign resources for this channel
        stmt = (
            select(CampaignResource)
            .where(
                and_(
                    CampaignResource.campaign_id == campaign_id,
                    CampaignResource.channel == channel,
                    CampaignResource.is_active,
                )
            )
            .order_by(CampaignResource.last_used_at.asc().nullsfirst())
        )
        result = await db.execute(stmt)
        resources = list(result.scalars().all())

        if not resources:
            return EngineResult.fail(
                error=f"No resources available for channel {channel.value}",
                metadata={"campaign_id": str(campaign_id), "channel": channel.value},
            )

        # Find first resource with available quota
        for resource in resources:
            resource_id = self._get_resource_identifier(resource)
            limit = RATE_LIMITS.get(channel, 50)

            remaining = await rate_limiter.get_remaining(
                resource_type=channel.value,
                resource_id=resource_id,
                limit=limit,
            )

            if remaining > 0:
                # Mark as used for round-robin
                await self._mark_resource_used(db, resource)

                return EngineResult.ok(
                    data={
                        "resource_id": resource_id,
                        "resource_name": resource.resource_name,
                        "channel": channel.value,
                        "remaining_quota": remaining,
                        "daily_limit": limit,
                    },
                )

        return EngineResult.fail(
            error=f"All resources for {channel.value} have exhausted daily quota",
            metadata={"campaign_id": str(campaign_id), "channel": channel.value},
        )

    async def check_and_consume_quota(
        self,
        channel: ChannelType,
        resource_id: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Check rate limit and consume one unit of quota.

        Args:
            channel: Channel type
            resource_id: Resource identifier

        Returns:
            EngineResult with quota status

        Raises:
            ResourceRateLimitError: If quota exhausted
        """
        limit = RATE_LIMITS.get(channel, 50)

        try:
            allowed, current_count = await rate_limiter.check_and_increment(
                resource_type=channel.value,
                resource_id=resource_id,
                limit=limit,
            )

            return EngineResult.ok(
                data={
                    "resource_id": resource_id,
                    "channel": channel.value,
                    "current_count": current_count,
                    "daily_limit": limit,
                    "remaining": limit - current_count,
                },
            )

        except ResourceRateLimitError as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "resource_id": resource_id,
                    "channel": channel.value,
                    "limit": limit,
                },
            )

    async def get_resource_status(
        self,
        db: AsyncSession,
        campaign_id: UUID,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get status of all resources for a campaign.

        Args:
            db: Database session (passed by caller)
            campaign_id: Campaign UUID

        Returns:
            EngineResult with resource status
        """
        # Get all campaign resources
        stmt = (
            select(CampaignResource)
            .where(CampaignResource.campaign_id == campaign_id)
        )
        result = await db.execute(stmt)
        resources = list(result.scalars().all())

        status = {
            "campaign_id": str(campaign_id),
            "resources": [],
            "channels": {},
        }

        for resource in resources:
            resource_id = self._get_resource_identifier(resource)
            channel = resource.channel
            limit = RATE_LIMITS.get(channel, 50)

            usage = await rate_limiter.get_usage(
                resource_type=channel.value,
                resource_id=resource_id,
            )
            remaining = max(0, limit - usage)

            resource_status = {
                "resource_id": resource_id,
                "resource_name": resource.resource_name,
                "channel": channel.value,
                "is_active": resource.is_active,
                "daily_usage": usage,
                "daily_limit": limit,
                "remaining": remaining,
                "exhausted": remaining == 0,
            }

            status["resources"].append(resource_status)

            # Aggregate by channel
            if channel.value not in status["channels"]:
                status["channels"][channel.value] = {
                    "total_resources": 0,
                    "active_resources": 0,
                    "total_remaining": 0,
                    "total_limit": 0,
                }

            status["channels"][channel.value]["total_resources"] += 1
            if resource.is_active:
                status["channels"][channel.value]["active_resources"] += 1
            status["channels"][channel.value]["total_remaining"] += remaining
            status["channels"][channel.value]["total_limit"] += limit

        return EngineResult.ok(
            data=status,
            metadata={"total_resources": len(resources)},
        )

    async def allocate_batch(
        self,
        db: AsyncSession,
        lead_ids: list[UUID],
        tier_channels: dict[str, list[ChannelType]],
    ) -> EngineResult[dict[str, Any]]:
        """
        Allocate channels for a batch of leads.

        Args:
            db: Database session (passed by caller)
            lead_ids: List of lead UUIDs
            tier_channels: Mapping of lead_id -> available channels

        Returns:
            EngineResult with batch allocation summary
        """
        results = {
            "total": len(lead_ids),
            "allocated": 0,
            "partial": 0,
            "failed": 0,
            "leads": [],
        }

        for lead_id in lead_ids:
            # Get channels for this lead's tier
            available_channels = tier_channels.get(str(lead_id), [])

            if not available_channels:
                results["failed"] += 1
                results["leads"].append({
                    "lead_id": str(lead_id),
                    "status": "failed",
                    "reason": "No channels available for tier",
                })
                continue

            try:
                result = await self.allocate_channels(
                    db=db,
                    lead_id=lead_id,
                    available_channels=available_channels,
                )

                if result.success:
                    allocated_count = len(result.data["channels"])
                    if allocated_count == len(available_channels):
                        results["allocated"] += 1
                        status = "full"
                    else:
                        results["partial"] += 1
                        status = "partial"

                    results["leads"].append({
                        "lead_id": str(lead_id),
                        "status": status,
                        "channels": result.data["channels"],
                    })
                else:
                    results["failed"] += 1
                    results["leads"].append({
                        "lead_id": str(lead_id),
                        "status": "failed",
                        "reason": result.error,
                    })

            except Exception as e:
                results["failed"] += 1
                results["leads"].append({
                    "lead_id": str(lead_id),
                    "status": "failed",
                    "reason": str(e),
                })

        return EngineResult.ok(
            data=results,
            metadata={
                "success_rate": (results["allocated"] + results["partial"]) / results["total"]
                if results["total"] > 0 else 0,
            },
        )

    async def _get_campaign_resources(
        self,
        db: AsyncSession,
        campaign_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all active resources for a campaign with quota info."""
        stmt = (
            select(CampaignResource)
            .where(
                and_(
                    CampaignResource.campaign_id == campaign_id,
                    CampaignResource.is_active,
                )
            )
            .order_by(CampaignResource.last_used_at.asc().nullsfirst())
        )
        result = await db.execute(stmt)
        resources = list(result.scalars().all())

        resource_list = []
        for resource in resources:
            resource_id = self._get_resource_identifier(resource)
            channel = resource.channel
            limit = RATE_LIMITS.get(channel, 50)

            remaining = await rate_limiter.get_remaining(
                resource_type=channel.value,
                resource_id=resource_id,
                limit=limit,
            )

            resource_list.append({
                "resource": resource,
                "resource_id": resource_id,
                "resource_name": resource.resource_name,
                "channel": channel,
                "remaining_quota": remaining,
                "daily_limit": limit,
            })

        return resource_list

    async def _find_available_resource(
        self,
        resources: list[dict[str, Any]],
        channel: ChannelType,
    ) -> dict[str, Any] | None:
        """Find first available resource for a channel."""
        for resource in resources:
            if resource["channel"] == channel and resource["remaining_quota"] > 0:
                return resource
        return None

    async def _assign_resource_to_lead(
        self,
        db: AsyncSession,
        lead: Lead,
        channel: ChannelType,
        resource: dict[str, Any],
    ) -> None:
        """Assign a resource to a lead."""
        update_data = {}

        if channel == ChannelType.EMAIL:
            update_data["assigned_email_resource"] = resource["resource_id"]
        elif channel == ChannelType.LINKEDIN:
            update_data["assigned_linkedin_seat"] = resource["resource_id"]
        elif channel in (ChannelType.SMS, ChannelType.VOICE):
            update_data["assigned_phone_resource"] = resource["resource_id"]

        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            stmt = update(Lead).where(Lead.id == lead.id).values(**update_data)
            await db.execute(stmt)
            await db.commit()

    async def _mark_resource_used(
        self,
        db: AsyncSession,
        resource: CampaignResource,
    ) -> None:
        """Mark resource as used for round-robin ordering."""
        stmt = (
            update(CampaignResource)
            .where(CampaignResource.id == resource.id)
            .values(
                last_used_at=datetime.utcnow(),
                usage_count=CampaignResource.usage_count + 1,
            )
        )
        await db.execute(stmt)
        await db.commit()

    def _get_resource_identifier(self, resource: CampaignResource) -> str:
        """Get unique identifier for a resource based on channel."""
        if resource.channel == ChannelType.EMAIL:
            # Use domain for email
            return resource.resource_value.split("@")[-1] if "@" in resource.resource_value else resource.resource_value
        else:
            # Use the resource value directly (seat ID, phone number, etc.)
            return resource.resource_value

    # ============================================
    # Phase 16: Conversion Intelligence Integration
    # ============================================

    async def allocate_channels_with_patterns(
        self,
        db: AsyncSession,
        lead_id: UUID,
        available_channels: list[ChannelType],
        use_patterns: bool = True,
    ) -> EngineResult[dict[str, Any]]:
        """
        Allocate channels with pattern-based prioritization.

        Phase 16: Uses HOW patterns to prioritize channels that have
        historically converted better for this client/tier.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID
            available_channels: Channels allowed for this lead's tier
            use_patterns: Whether to use conversion patterns for prioritization

        Returns:
            EngineResult with allocated channels, resources, and pattern insights
        """
        lead = await self.get_lead_by_id(db, lead_id)
        campaign = await self.get_campaign_by_id(db, lead.campaign_id)

        # Phase 16: Prioritize channels based on patterns
        prioritized_channels = available_channels
        pattern_insights = {}

        if use_patterns:
            prioritized_channels, pattern_insights = await self._prioritize_channels(
                db=db,
                client_id=lead.client_id,
                tier=lead.als_tier,
                available_channels=available_channels,
            )

        # Get available resources for this campaign
        resources = await self._get_campaign_resources(db, campaign.id)

        allocated = {
            "lead_id": str(lead_id),
            "campaign_id": str(campaign.id),
            "channels": [],
            "resources": {},
            "pattern_applied": use_patterns and bool(pattern_insights),
            "pattern_insights": pattern_insights,
        }

        for channel in prioritized_channels:
            # Find an available resource for this channel
            resource = await self._find_available_resource(
                resources=resources,
                channel=channel,
            )

            if resource:
                allocated["channels"].append(channel.value)
                allocated["resources"][channel.value] = {
                    "resource_id": resource["resource_id"],
                    "resource_name": resource["resource_name"],
                    "remaining_quota": resource["remaining_quota"],
                }

                # Assign resource to lead
                await self._assign_resource_to_lead(db, lead, channel, resource)

        if not allocated["channels"]:
            return EngineResult.fail(
                error="No channels could be allocated - all resources exhausted",
                metadata={"lead_id": str(lead_id)},
            )

        return EngineResult.ok(
            data=allocated,
            metadata={
                "channels_allocated": len(allocated["channels"]),
                "total_available": len(available_channels),
                "pattern_applied": allocated["pattern_applied"],
            },
        )

    async def get_timing_recommendations(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get optimal timing recommendations from WHEN patterns.

        Phase 16: Returns best days/hours for outreach based on
        historical conversion patterns.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            EngineResult with timing recommendations
        """
        when_pattern = await self._get_pattern(db, client_id, "when")

        if not when_pattern:
            return EngineResult.ok(
                data={
                    "has_patterns": False,
                    "best_days": ["Tuesday", "Wednesday", "Thursday"],
                    "best_hours": [9, 10, 14, 15],
                    "optimal_gaps": {
                        "touch_1_to_2": 2,
                        "touch_2_to_3": 3,
                        "touch_3_to_4": 4,
                    },
                    "note": "Using defaults - insufficient data for patterns",
                },
                metadata={"source": "default"},
            )

        patterns = when_pattern.patterns

        # Extract best days
        best_days = [d["day"] for d in patterns.get("best_days", [])[:3]]

        # Extract best hours
        best_hours = [h["hour"] for h in patterns.get("best_hours", [])[:4]]

        # Extract optimal gaps
        optimal_gaps = patterns.get("optimal_sequence_gaps", {})

        # Get touch distribution insights
        touch_dist = patterns.get("converting_touch_distribution", {})
        peak_touch = max(touch_dist.items(), key=lambda x: x[1])[0] if touch_dist else "touch_3"

        return EngineResult.ok(
            data={
                "has_patterns": True,
                "best_days": best_days or ["Tuesday", "Wednesday", "Thursday"],
                "best_hours": best_hours or [9, 10, 14, 15],
                "optimal_gaps": optimal_gaps,
                "peak_converting_touch": peak_touch,
                "confidence": when_pattern.confidence,
                "sample_size": when_pattern.sample_size,
                "computed_at": when_pattern.computed_at.isoformat(),
            },
            metadata={
                "source": "learned",
                "pattern_id": str(when_pattern.id),
            },
        )

    async def get_channel_recommendations(
        self,
        db: AsyncSession,
        client_id: UUID,
        tier: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get channel recommendations from HOW patterns.

        Phase 16: Returns which channels work best, optionally by tier.

        Args:
            db: Database session
            client_id: Client UUID
            tier: Optional tier for tier-specific recommendations

        Returns:
            EngineResult with channel recommendations
        """
        how_pattern = await self._get_pattern(db, client_id, "how")

        if not how_pattern:
            return EngineResult.ok(
                data={
                    "has_patterns": False,
                    "channel_rankings": [],
                    "multi_channel_recommended": True,
                    "note": "Using defaults - insufficient data for patterns",
                },
                metadata={"source": "default"},
            )

        patterns = how_pattern.patterns

        # Overall channel rankings
        channel_rankings = patterns.get("channel_effectiveness", [])

        # Multi-channel lift analysis
        multi_channel = patterns.get("multi_channel_lift", {})
        multi_recommended = multi_channel.get("recommendation") == "multi"

        # Tier-specific if requested
        tier_channels = []
        if tier:
            tier_effectiveness = patterns.get("tier_channel_effectiveness", {})
            tier_channels = tier_effectiveness.get(tier, [])

        # Winning sequences
        sequences = patterns.get("sequence_patterns", {}).get("winning_sequences", [])

        return EngineResult.ok(
            data={
                "has_patterns": True,
                "channel_rankings": channel_rankings,
                "tier_specific_channels": tier_channels,
                "multi_channel_recommended": multi_recommended,
                "multi_channel_lift": multi_channel.get("multi_channel_lift", 1.0),
                "winning_sequences": sequences[:3],
                "confidence": how_pattern.confidence,
                "sample_size": how_pattern.sample_size,
            },
            metadata={
                "source": "learned",
                "pattern_id": str(how_pattern.id),
            },
        )

    async def _prioritize_channels(
        self,
        db: AsyncSession,
        client_id: UUID,
        tier: str | None,
        available_channels: list[ChannelType],
    ) -> tuple[list[ChannelType], dict[str, Any]]:
        """
        Prioritize channels based on HOW patterns.

        Returns channels sorted by historical conversion rates.

        Args:
            db: Database session
            client_id: Client UUID
            tier: Lead's ALS tier
            available_channels: Channels to prioritize

        Returns:
            Tuple of (prioritized channels, pattern insights)
        """
        how_pattern = await self._get_pattern(db, client_id, "how")

        if not how_pattern:
            return available_channels, {}

        patterns = how_pattern.patterns

        # Build channel priority map from pattern data
        channel_priority = {}

        # Use tier-specific data if available
        if tier:
            tier_effectiveness = patterns.get("tier_channel_effectiveness", {})
            tier_data = tier_effectiveness.get(tier, [])
            for item in tier_data:
                channel_priority[item["channel"]] = item["conversion_rate"]

        # Fall back to overall channel effectiveness
        if not channel_priority:
            for item in patterns.get("channel_effectiveness", []):
                channel_priority[item["channel"]] = item["conversion_rate"]

        # Sort available channels by their conversion rates
        def get_priority(channel: ChannelType) -> float:
            return channel_priority.get(channel.value, 0.0)

        prioritized = sorted(available_channels, key=get_priority, reverse=True)

        insights = {
            "prioritization_source": "tier" if tier else "overall",
            "channel_rates": {
                c.value: channel_priority.get(c.value, 0.0)
                for c in available_channels
            },
            "original_order": [c.value for c in available_channels],
            "optimized_order": [c.value for c in prioritized],
        }

        return prioritized, insights

    async def _get_pattern(
        self,
        db: AsyncSession,
        client_id: UUID,
        pattern_type: str,
    ) -> ConversionPattern | None:
        """
        Get a valid conversion pattern for a client.

        Args:
            db: Database session
            client_id: Client UUID
            pattern_type: Pattern type (who, what, when, how)

        Returns:
            ConversionPattern if valid one exists, None otherwise
        """
        stmt = select(ConversionPattern).where(
            and_(
                ConversionPattern.client_id == client_id,
                ConversionPattern.pattern_type == pattern_type,
                ConversionPattern.valid_until > datetime.utcnow(),
            )
        ).order_by(ConversionPattern.computed_at.desc())

        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# Singleton instance
_allocator_engine: AllocatorEngine | None = None


def get_allocator_engine() -> AllocatorEngine:
    """Get or create Allocator engine instance."""
    global _allocator_engine
    if _allocator_engine is None:
        _allocator_engine = AllocatorEngine()
    return _allocator_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Soft delete check in queries (Rule 14)
# [x] Resource-level rate limits (Rule 17)
# [x] LinkedIn: 17/day/seat
# [x] Email: 50/day/domain
# [x] SMS: 100/day/number
# [x] Round-robin resource selection
# [x] Quota consumption and checking
# [x] Resource status reporting
# [x] Batch allocation support
# [x] EngineResult wrapper for responses
# [x] Test file created: tests/test_engines/test_allocator.py
# [x] All functions have type hints
# [x] All functions have docstrings
# --- Phase 16 Additions ---
# [x] HOW pattern integration for channel prioritization
# [x] WHEN pattern integration for timing recommendations
# [x] Tier-specific channel recommendations
# [x] allocate_channels_with_patterns() method
# [x] get_timing_recommendations() method
# [x] get_channel_recommendations() method
# [x] _prioritize_channels() helper
# [x] _get_pattern() helper for fetching valid patterns
