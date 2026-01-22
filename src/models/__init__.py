# FIXED by fixer-agent: added contract comment
"""
FILE: src/models/__init__.py
PURPOSE: Models package - SQLAlchemy models and Pydantic schemas (LAYER 1)
PHASE: 2
TASK: MOD-001 to MOD-007
DEPENDENCIES:
  - src/exceptions.py
RULES APPLIED:
  - Rule 12: Cannot import from engines/integrations/orchestration
  - Rule 14: Soft deletes only (SoftDeleteMixin)
"""

# Agency OS - Models Package
from src.models.base import Base, SoftDeleteMixin, TimestampMixin, PatternType
from src.models.client import Client
from src.models.user import User
from src.models.membership import Membership
from src.models.campaign import Campaign, CampaignResource, CampaignSequence, CampaignType
from src.models.lead import Lead, GlobalSuppression, ClientSuppression, DomainSuppression
from src.models.lead_pool import LeadPool, PoolStatus, EmailStatus
from src.models.lead_social_post import LeadSocialPost
from src.models.activity import Activity, ActivityStats
from src.models.conversion_patterns import ConversionPattern, ConversionPatternHistory
from src.models.url_validation import URLValidationResult
from src.models.linkedin_credential import LinkedInCredential
from src.models.sdk_usage_log import SDKUsageLog
from src.models.client_intelligence import ClientIntelligence
from src.models.resource_pool import (
    ResourcePool,
    ClientResource,
    ResourceType,
    ResourceStatus,
    HealthStatus,
    TIER_ALLOCATIONS,
    HEALTH_THRESHOLDS,
    HEALTH_DAILY_LIMITS,
)
from src.models.client_persona import ClientPersona, PERSONA_ALLOCATIONS
from src.models.linkedin_seat import LinkedInSeat, LinkedInSeatStatus, LINKEDIN_WARMUP_SCHEDULE
from src.models.linkedin_connection import LinkedInConnection, LinkedInConnectionStatus
from src.models.campaign_suggestion import CampaignSuggestion, CampaignSuggestionHistory, SuggestionType, SuggestionStatus

__all__ = [
    # Base
    "Base",
    "SoftDeleteMixin",
    "TimestampMixin",
    "PatternType",
    # Models
    "Client",
    "User",
    "Membership",
    "Campaign",
    "CampaignResource",
    "CampaignSequence",
    "CampaignType",
    "Lead",
    "GlobalSuppression",
    "ClientSuppression",
    "DomainSuppression",
    "LeadPool",
    "PoolStatus",
    "EmailStatus",
    "LeadSocialPost",
    "Activity",
    "ActivityStats",
    # Conversion Intelligence
    "ConversionPattern",
    "ConversionPatternHistory",
    # URL Validation
    "URLValidationResult",
    # LinkedIn
    "LinkedInCredential",
    # SDK Brain
    "SDKUsageLog",
    # Client Intelligence
    "ClientIntelligence",
    # Resource Pool
    "ResourcePool",
    "ClientResource",
    "ResourceType",
    "ResourceStatus",
    "HealthStatus",
    "TIER_ALLOCATIONS",
    "HEALTH_THRESHOLDS",
    "HEALTH_DAILY_LIMITS",
    # Client Personas
    "ClientPersona",
    "PERSONA_ALLOCATIONS",
    # LinkedIn
    "LinkedInSeat",
    "LinkedInSeatStatus",
    "LINKEDIN_WARMUP_SCHEDULE",
    "LinkedInConnection",
    "LinkedInConnectionStatus",
    # Campaign Suggestions
    "CampaignSuggestion",
    "CampaignSuggestionHistory",
    "SuggestionType",
    "SuggestionStatus",
]
