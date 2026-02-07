"""
FILE: src/config/tiers.py
PURPOSE: Canonical tier configuration for Agency OS pricing
SOURCE: docs/specs/PRICING_TIERS.md (LOCKED)
DATE: January 2026

DO NOT MODIFY without CEO approval.
All tier limits are business decisions documented in PRICING_TIERS.md
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.base import ChannelType


class TierName(str, Enum):
    """Subscription tier names."""

    IGNITION = "ignition"
    VELOCITY = "velocity"
    DOMINANCE = "dominance"


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
# Source: docs/specs/PRICING_TIERS.md (LOCKED - January 2026)
# =============================================================================

IGNITION = TierConfig(
    name=TierName.IGNITION,
    price_aud=2500,
    founding_price_aud=1250,
    leads_per_month=1250,
    max_campaigns=5,
    ai_suggested_campaigns=3,
    custom_campaigns=2,
    linkedin_seats=1,
    daily_outreach=50,
)

VELOCITY = TierConfig(
    name=TierName.VELOCITY,
    price_aud=4000,  # Updated 2026-02-06 per CEO confirmation
    founding_price_aud=2000,
    leads_per_month=2250,
    max_campaigns=10,
    ai_suggested_campaigns=6,
    custom_campaigns=4,
    linkedin_seats=3,
    daily_outreach=100,
)

DOMINANCE = TierConfig(
    name=TierName.DOMINANCE,
    price_aud=7500,
    founding_price_aud=3750,
    leads_per_month=4500,
    max_campaigns=20,
    ai_suggested_campaigns=12,
    custom_campaigns=8,
    linkedin_seats=5,
    daily_outreach=200,
)

# Lookup by tier name
TIER_CONFIG: dict[str, TierConfig] = {
    "ignition": IGNITION,
    "velocity": VELOCITY,
    "dominance": DOMINANCE,
}


def get_tier_config(tier_name: str) -> TierConfig:
    """
    Get tier configuration by name.

    Args:
        tier_name: Tier name (ignition, velocity, dominance)

    Returns:
        TierConfig for the specified tier

    Raises:
        ValueError: If tier name is invalid
    """
    config = TIER_CONFIG.get(tier_name.lower())
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


def get_available_channels(als_score: int) -> list[str]:
    """Get available channels for a given ALS score."""
    tier = get_als_tier(als_score)
    return CHANNEL_ACCESS_BY_ALS.get(tier, [])


def get_available_channels_enum(als_score: int) -> list["ChannelType"]:
    """
    Get available channels as ChannelType enums for a given ALS score.

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

    channels_str = get_available_channels(als_score)
    return [channel_str_to_enum[ch] for ch in channels_str if ch in channel_str_to_enum]


# =============================================================================
# VERIFICATION
# =============================================================================
# [x] Matches PRICING_TIERS.md exactly
# [x] Ignition: 1,250 leads, 5 campaigns (3 AI + 2 custom), 1 LinkedIn seat
# [x] Velocity: 2,250 leads, 10 campaigns (6 AI + 4 custom), 3 LinkedIn seats
# [x] Dominance: 4,500 leads, 20 campaigns (12 AI + 8 custom), 5 LinkedIn seats
# [x] Founding prices at 50% discount
# [x] ALS tier thresholds: Hot 85+, Warm 60+, Cool 35+, Cold 20+, Dead <20
# [x] Channel access rules match spec
