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
from src.models.base import Base, PatternType, SoftDeleteMixin, TimestampMixin
from src.models.client import Client
from src.models.membership import Membership
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
    # Vendor cost tracking (E1 R3)
    "VendorUsageLog",
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
    # Voice Calls (CIS Gap 1 Fix)
    "VoiceCall",
    "VoiceCallContext",
    "VoiceCallOutcome",
]

# [repo_split curation] dead-BDR submodule imports removed (20); kept only: ['base', 'client', 'membership', 'user']
