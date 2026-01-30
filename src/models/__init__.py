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
from src.models.activity import Activity, ActivityStats
from src.models.base import Base, PatternType, SoftDeleteMixin, TimestampMixin
from src.models.campaign import Campaign, CampaignResource, CampaignSequence, CampaignType
from src.models.campaign_suggestion import (
    CampaignSuggestion,
    CampaignSuggestionHistory,
    SuggestionStatus,
    SuggestionType,
)
from src.models.client import Client
from src.models.client_intelligence import ClientIntelligence
from src.models.client_persona import PERSONA_ALLOCATIONS, ClientPersona
from src.models.persona import PERSONA_TIER_ALLOCATIONS, Persona, PersonaStatus
from src.models.conversion_patterns import ConversionPattern, ConversionPatternHistory
from src.models.digest_log import DigestLog
from src.models.icp_refinement_log import IcpRefinementLog
from src.models.lead import ClientSuppression, DomainSuppression, GlobalSuppression, Lead
from src.models.lead_pool import EmailStatus, LeadPool, PoolStatus
from src.models.lead_social_post import LeadSocialPost
from src.models.linkedin_connection import LinkedInConnection, LinkedInConnectionStatus
from src.models.linkedin_credential import LinkedInCredential
from src.models.linkedin_seat import LINKEDIN_WARMUP_SCHEDULE, LinkedInSeat, LinkedInSeatStatus
from src.models.membership import Membership
from src.models.resource_pool import (
    HEALTH_DAILY_LIMITS,
    HEALTH_THRESHOLDS,
    TIER_ALLOCATIONS,
    ClientResource,
    HealthStatus,
    ResourcePool,
    ResourceStatus,
    ResourceType,
)
from src.models.sdk_usage_log import SDKUsageLog
from src.models.url_validation import URLValidationResult
from src.models.user import User

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
    # Persona Pool
    "Persona",
    "PersonaStatus",
    "PERSONA_TIER_ALLOCATIONS",
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
    # ICP Refinement (Phase 19)
    "IcpRefinementLog",
    # Digest (Phase H, Item 44)
    "DigestLog",
]
