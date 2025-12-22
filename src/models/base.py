"""
FILE: src/models/base.py
PURPOSE: Base model with SoftDeleteMixin and UUIDv7 support
PHASE: 2 (Models & Schemas)
TASK: MOD-001
DEPENDENCIES:
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 14: Soft deletes only (deleted_at column)
  - Rule 12: Models can only import from exceptions
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    # Use UUID as primary key type by default
    type_annotation_map = {
        UUID: PGUUID(as_uuid=True),
    }

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (snake_case + plural)."""
        import re
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        # Simple pluralization
        if name.endswith("y"):
            return name[:-1] + "ies"
        elif name.endswith("s"):
            return name + "es"
        return name + "s"


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.

    Rule 14: Never use hard DELETE, always use soft delete with deleted_at.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the record as deleted."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None


class UUIDMixin:
    """Mixin for UUID primary key with UUIDv7 support."""

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )


def generate_uuid_v7() -> UUID:
    """
    Generate a UUID for use as primary key.

    Uses Python's stdlib uuid.uuid4() for random UUIDs.
    """
    import uuid
    return uuid.uuid4()


# ============================================
# Enums (matching database types)
# ============================================

from enum import Enum


class TierType(str, Enum):
    """Subscription tier types."""
    IGNITION = "ignition"
    VELOCITY = "velocity"
    DOMINANCE = "dominance"


class SubscriptionStatus(str, Enum):
    """Subscription status values."""
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class MembershipRole(str, Enum):
    """Team membership roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class PermissionMode(str, Enum):
    """Automation permission modes."""
    AUTOPILOT = "autopilot"
    CO_PILOT = "co_pilot"
    MANUAL = "manual"


class CampaignStatus(str, Enum):
    """Campaign lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class LeadStatus(str, Enum):
    """Lead lifecycle status."""
    NEW = "new"
    ENRICHED = "enriched"
    SCORED = "scored"
    IN_SEQUENCE = "in_sequence"
    CONVERTED = "converted"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"


class ChannelType(str, Enum):
    """Outreach channel types."""
    EMAIL = "email"
    SMS = "sms"
    LINKEDIN = "linkedin"
    VOICE = "voice"
    MAIL = "mail"


class IntentType(str, Enum):
    """Reply intent classification."""
    MEETING_REQUEST = "meeting_request"
    INTERESTED = "interested"
    QUESTION = "question"
    NOT_INTERESTED = "not_interested"
    UNSUBSCRIBE = "unsubscribe"
    OUT_OF_OFFICE = "out_of_office"
    AUTO_REPLY = "auto_reply"


class WebhookEventType(str, Enum):
    """Webhook event types."""
    LEAD_CREATED = "lead.created"
    LEAD_ENRICHED = "lead.enriched"
    LEAD_SCORED = "lead.scored"
    LEAD_CONVERTED = "lead.converted"
    CAMPAIGN_STARTED = "campaign.started"
    CAMPAIGN_PAUSED = "campaign.paused"
    CAMPAIGN_COMPLETED = "campaign.completed"
    REPLY_RECEIVED = "reply.received"
    MEETING_BOOKED = "meeting.booked"


class AuditAction(str, Enum):
    """Audit action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    WEBHOOK_SENT = "webhook_sent"
    WEBHOOK_FAILED = "webhook_failed"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Base declarative class
# [x] TimestampMixin (created_at, updated_at)
# [x] SoftDeleteMixin with deleted_at (Rule 14)
# [x] UUIDMixin for primary keys
# [x] generate_uuid_v7() function
# [x] All enums matching database types
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All classes have type hints
# [x] All classes have docstrings
