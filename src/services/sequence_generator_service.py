"""
Contract: src/services/sequence_generator_service.py
Purpose: Auto-generate default 5-step campaign sequences
Layer: 3 - services
Imports: models only
Consumers: orchestration, API routes
Spec: docs/architecture/AUTOMATED_DISTRIBUTION_DEFAULTS.md

This service:
1. Generates the default 5-step sequence for new campaigns
2. Adapts based on available channels (skip unavailable)
3. Uses {{SMART_PROMPT}} template for content generation
4. No AI API call - deterministic logic only
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import ChannelType
from src.models.campaign import CampaignSequence

# Default sequence template per spec
DEFAULT_SEQUENCE = [
    {
        "step_number": 1,
        "day": 0,
        "channel": ChannelType.EMAIL,
        "purpose": "intro",
        "skip_if": None,
        "subject_template": "{{SMART_PROMPT_SUBJECT}}",
        "body_template": "{{SMART_PROMPT}}",
    },
    {
        "step_number": 2,
        "day": 3,
        "channel": ChannelType.VOICE,
        "purpose": "connect",
        "skip_if": "phone_missing",
        "subject_template": None,
        "body_template": "{{SMART_PROMPT}}",
    },
    {
        "step_number": 3,
        "day": 5,
        "channel": ChannelType.LINKEDIN,
        "purpose": "connect",
        "skip_if": "linkedin_url_missing",
        "subject_template": None,
        "body_template": "{{SMART_PROMPT}}",
    },
    {
        "step_number": 4,
        "day": 8,
        "channel": ChannelType.EMAIL,
        "purpose": "value_add",
        "skip_if": None,
        "subject_template": "{{SMART_PROMPT_SUBJECT}}",
        "body_template": "{{SMART_PROMPT}}",
    },
    {
        "step_number": 5,
        "day": 12,
        "channel": ChannelType.SMS,
        "purpose": "breakup",
        "skip_if": "phone_missing",
        "subject_template": None,
        "body_template": "{{SMART_PROMPT}}",
    },
]


class SequenceGeneratorService:
    """
    Service for auto-generating default campaign sequences.

    Default 5-Step Sequence (per AUTOMATED_DISTRIBUTION_DEFAULTS.md):
    1. Day 0:  Email - Initial outreach
    2. Day 3:  Voice - Follow-up call (if no reply)
    3. Day 5:  LinkedIn - Connection request (if no reply)
    4. Day 8:  Email - Value-add touchpoint (if no reply)
    5. Day 12: SMS - Final nudge (if no reply)

    Sequence Rules:
    - Skip on reply: If lead replies at any step, sequence stops
    - Skip on bounce: If email bounces, skip remaining email steps
    - Channel fallback: If channel unavailable, skip that step
    """

    async def generate_default_sequence(
        self,
        db: AsyncSession,
        campaign_id: UUID,
        available_channels: list[ChannelType] | None = None,
    ) -> list[CampaignSequence]:
        """
        Generate the default 5-step sequence for a campaign.

        Args:
            db: Database session
            campaign_id: Campaign UUID to attach sequences to
            available_channels: Optional list of available channels.
                               If None, all channels are assumed available.

        Returns:
            List of CampaignSequence objects (already added to session)
        """
        # Default to all channels if not specified
        if available_channels is None:
            available_channels = [
                ChannelType.EMAIL,
                ChannelType.VOICE,
                ChannelType.LINKEDIN,
                ChannelType.SMS,
            ]

        sequences = []
        step_counter = 1

        for step in DEFAULT_SEQUENCE:
            channel = step["channel"]

            # Skip if channel not available
            if channel not in available_channels:
                continue

            sequence = CampaignSequence(
                campaign_id=campaign_id,
                step_number=step_counter,
                channel=channel,
                delay_days=step["day"],
                subject_template=step["subject_template"],
                body_template=step["body_template"],
                skip_if_replied=True,
                skip_if_bounced=(channel == ChannelType.EMAIL),
                purpose=step["purpose"],
                skip_if=step["skip_if"],
            )

            db.add(sequence)
            sequences.append(sequence)
            step_counter += 1

        await db.flush()

        return sequences

    async def regenerate_sequence(
        self,
        db: AsyncSession,
        campaign_id: UUID,
        available_channels: list[ChannelType] | None = None,
    ) -> list[CampaignSequence]:
        """
        Regenerate sequences for an existing campaign.

        Deletes existing sequences and creates new default ones.

        Args:
            db: Database session
            campaign_id: Campaign UUID
            available_channels: Optional list of available channels

        Returns:
            List of new CampaignSequence objects
        """
        from sqlalchemy import delete

        # Delete existing sequences
        await db.execute(
            delete(CampaignSequence).where(
                CampaignSequence.campaign_id == campaign_id
            )
        )

        # Generate new sequences
        return await self.generate_default_sequence(
            db, campaign_id, available_channels
        )

    def get_available_channels_for_client(
        self,
        has_email_domain: bool = True,
        has_phone_number: bool = False,
        has_linkedin_seat: bool = False,
    ) -> list[ChannelType]:
        """
        Determine available channels based on client resources.

        Args:
            has_email_domain: Client has email domain assigned
            has_phone_number: Client has phone number assigned
            has_linkedin_seat: Client has LinkedIn seat assigned

        Returns:
            List of available ChannelType values
        """
        channels = []

        if has_email_domain:
            channels.append(ChannelType.EMAIL)

        if has_phone_number:
            channels.append(ChannelType.VOICE)
            channels.append(ChannelType.SMS)

        if has_linkedin_seat:
            channels.append(ChannelType.LINKEDIN)

        return channels


# Singleton instance
_sequence_generator_service: SequenceGeneratorService | None = None


def get_sequence_generator_service() -> SequenceGeneratorService:
    """Get the sequence generator service singleton."""
    global _sequence_generator_service
    if _sequence_generator_service is None:
        _sequence_generator_service = SequenceGeneratorService()
    return _sequence_generator_service


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] DEFAULT_SEQUENCE matches spec (5 steps)
# [x] generate_default_sequence() creates sequences
# [x] regenerate_sequence() replaces existing
# [x] get_available_channels_for_client() helper
# [x] Channel fallback (skip unavailable)
# [x] skip_if_replied=True on all steps
# [x] skip_if_bounced=True on email steps only
# [x] {{SMART_PROMPT}} template for content
# [x] Singleton pattern for service access
# [x] All functions have type hints and docstrings
