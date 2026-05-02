"""
FILE: src/config/tiers.py
PURPOSE: Canonical tier configuration for Agency OS pricing
SOURCE: docs/specs/PRICING_TIERS.md (LOCKED)
DATE: January 2026

DO NOT MODIFY without CEO approval.
All tier limits are business decisions documented in PRICING_TIERS.md
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.base import ChannelType


class TierName(StrEnum):
    """Subscription tier names."""

    SPARK = "spark"
    IGNITION = "ignition"
    VELOCITY = "velocity"
    DOMINANCE = (
        "dominance"  # DEPRECATED — kept for DB migration safety. Do not assign to new clients.
    )


@dataclass(frozen=True)
class TierConfig:
    """Configuration for a subscription tier."""

    name: TierName
    price_aud: int  # Monthly price in AUD
    founding_price_aud: int  # Founding member price (50% off)
    leads_per_month: int  # Lead pool quota
    max_campaigns: int  # Max active campaigns
    ai_suggested_campaigns: int  # AI-suggested campaign slots
    custom_campaigns: int  # Custom campaign slots
    linkedin_seats: int  # HeyReach seats
    daily_outreach: int  # Max daily outreach actions


# =============================================================================
# OFFICIAL TIER CONFIGURATION
# Source: Manual SSOT (ratified Mar 26 2026) — TIERS-002
# =============================================================================

# Canonical pricing — ratified Mar 26 2026 per Manual SSOT
SPARK = TierConfig(
    name=TierName.SPARK,
    price_aud=750,
    founding_price_aud=375,
    leads_per_month=150,
    max_campaigns=3,
    ai_suggested_campaigns=2,
    custom_campaigns=1,
    linkedin_seats=1,
    daily_outreach=25,
)

# Canonical pricing — ratified Mar 26 2026 per Manual SSOT
IGNITION = TierConfig(
    name=TierName.IGNITION,
    price_aud=2500,
    founding_price_aud=1250,
    leads_per_month=600,  # Fixed TIERS-002: was 1250, now 600 per Manual SSOT
    max_campaigns=5,
    ai_suggested_campaigns=3,
    custom_campaigns=2,
    linkedin_seats=1,
    daily_outreach=50,
)

# Canonical pricing — ratified Mar 26 2026 per Manual SSOT
VELOCITY = TierConfig(
    name=TierName.VELOCITY,
    price_aud=5000,  # Fixed TIERS-002: was 4000, now 5000 per Manual SSOT
    founding_price_aud=2500,  # Fixed TIERS-002: was 2000, now 2500 per Manual SSOT
    leads_per_month=1500,  # Fixed TIERS-002: was 2500, now 1500 per Manual SSOT
    max_campaigns=10,
    ai_suggested_campaigns=6,
    custom_campaigns=4,
    linkedin_seats=3,
    daily_outreach=100,
)

# Lookup by tier name — active tiers only
TIER_CONFIG: dict[str, TierConfig] = {
    "spark": SPARK,
    "ignition": IGNITION,
    "velocity": VELOCITY,
    # DOMINANCE REMOVED from launch — TIERS-002. Enum value kept for DB migration safety only.
}


def get_active_tiers() -> list[str]:
    """Return only active (non-deprecated) tier names."""
    return list(TIER_CONFIG.keys())


def get_tier_config(tier_name: str) -> TierConfig:
    """
    Get tier configuration by name.

    Args:
        tier_name: Tier name (spark, ignition, velocity)

    Returns:
        TierConfig for the specified tier

    Raises:
        ValueError: If tier name is invalid or deprecated (dominance)
    """
    name_lower = tier_name.lower()
    if name_lower == "dominance":
        raise ValueError(
            "Tier 'dominance' is deprecated and removed from launch. "
            "Valid tiers: spark, ignition, velocity"
        )
    config = TIER_CONFIG.get(name_lower)
    if not config:
        valid_tiers = ", ".join(TIER_CONFIG.keys())
        raise ValueError(f"Invalid tier '{tier_name}'. Valid tiers: {valid_tiers}")
    return config


def get_leads_for_tier(tier_name: str) -> int:
    """Get lead quota for a tier."""
    return get_tier_config(tier_name).leads_per_month


def get_max_campaigns_for_tier(tier_name: str) -> int:
    """Get max campaigns for a tier."""
    return get_tier_config(tier_name).max_campaigns


def get_campaign_slots(tier_name: str) -> tuple[int, int]:
    """
    Get campaign slots for a tier.

    Returns:
        Tuple of (ai_suggested_slots, custom_slots)
    """
    config = get_tier_config(tier_name)
    return config.ai_suggested_campaigns, config.custom_campaigns


# =============================================================================
# CHANNEL ACCESS BY ALS SCORE
# Source: docs/specs/PRICING_TIERS.md
# =============================================================================

ALS_TIER_THRESHOLDS = {
    "hot": 85,  # 85-100
    "warm": 60,  # 60-84
    "cool": 35,  # 35-59
    "cold": 20,  # 20-34
    "dead": 0,  # 0-19
}

CHANNEL_ACCESS_BY_ALS = {
    "hot": ["email", "sms", "linkedin", "voice", "mail"],
    "warm": ["email", "sms", "linkedin", "voice"],  # SMS added 2026-02-06 per CEO approval
    "cool": ["email", "linkedin"],
    "cold": ["email"],
    "dead": [],
}


def get_als_tier(score: int) -> str:
    """Get ALS tier name from score."""
    if score >= 85:
        return "hot"
    elif score >= 60:
        return "warm"
    elif score >= 35:
        return "cool"
    elif score >= 20:
        return "cold"
    else:
        return "dead"


def get_available_channels(reachability_score: int) -> list[str]:
    """Get available channels for a given reachability score."""
    tier = get_als_tier(reachability_score)
    return CHANNEL_ACCESS_BY_ALS.get(tier, [])


def get_available_channels_enum(reachability_score: int) -> list["ChannelType"]:
    """
    Get available channels as ChannelType enums for a given reachability score.

    Use this in orchestration flows where ChannelType enums are needed.
    Canonical source - replaces any hardcoded tier_channel_map.
    """
    from src.models.base import ChannelType

    channel_str_to_enum = {
        "email": ChannelType.EMAIL,
        "linkedin": ChannelType.LINKEDIN,
        "voice": ChannelType.VOICE,
        "sms": ChannelType.SMS,
        "mail": ChannelType.MAIL,
    }

    channels_str = get_available_channels(reachability_score)
    return [channel_str_to_enum[ch] for ch in channels_str if ch in channel_str_to_enum]


# =============================================================================
# VERIFICATION
# =============================================================================
# [x] Matches Manual SSOT ratified Mar 26 2026 (TIERS-002)
# [x] Spark: $750, 150 leads, 3 campaigns (2 AI + 1 custom), 1 LinkedIn seat
# [x] Ignition: $2,500, 600 leads, 5 campaigns (3 AI + 2 custom), 1 LinkedIn seat
# [x] Velocity: $5,000, 1,500 leads, 10 campaigns (6 AI + 4 custom), 3 LinkedIn seats
# [x] Dominance: REMOVED from launch. TierName enum value kept for DB migration safety.
# [x] Founding prices at 50% discount
# [x] get_active_tiers() returns spark/ignition/velocity only
# [x] get_tier_config("dominance") raises clear ValueError
# [x] ALS tier thresholds: Hot 85+, Warm 60+, Cool 35+, Cold 20+, Dead <20
# [x] Channel access rules match spec
