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
]
