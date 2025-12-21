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
from src.models.base import Base, SoftDeleteMixin, TimestampMixin
from src.models.client import Client
from src.models.user import User
from src.models.membership import Membership
from src.models.campaign import Campaign, CampaignResource, CampaignSequence
from src.models.lead import Lead, GlobalSuppression, ClientSuppression, DomainSuppression
from src.models.activity import Activity, ActivityStats

__all__ = [
    # Base
    "Base",
    "SoftDeleteMixin",
    "TimestampMixin",
    # Models
    "Client",
    "User",
    "Membership",
    "Campaign",
    "CampaignResource",
    "CampaignSequence",
    "Lead",
    "GlobalSuppression",
    "ClientSuppression",
    "DomainSuppression",
    "Activity",
    "ActivityStats",
]
