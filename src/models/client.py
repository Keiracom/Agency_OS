"""
FILE: src/models/client.py
PURPOSE: Client (tenant) model with subscription status
PHASE: 2 (Models & Schemas)
TASK: MOD-002
DEPENDENCIES:
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 14: Soft deletes only
  - Rule 12: No imports from engines/integrations/orchestration
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    PermissionMode,
    SoftDeleteMixin,
    SubscriptionStatus,
    TierType,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.campaign import Campaign
    from src.models.lead import Lead
    from src.models.membership import Membership


class Client(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Client (tenant) model.

    Represents an organization using Agency OS. Supports multi-tenancy
    with subscription tiers and credit-based billing.
    """

    __tablename__ = "clients"

    # Basic info
    name: Mapped[str] = mapped_column(Text, nullable=False)

    # Subscription
    tier: Mapped[TierType] = mapped_column(
        ENUM(TierType, name="tier_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TierType.IGNITION,
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        ENUM(SubscriptionStatus, name="subscription_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SubscriptionStatus.TRIALING,
    )

    # Credits (AUD-based)
    credits_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1250,
    )
    credits_reset_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    # Default settings
    default_permission_mode: Mapped[Optional[PermissionMode]] = mapped_column(
        ENUM(PermissionMode, name="permission_mode", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        default=PermissionMode.CO_PILOT,
    )

    # Stripe integration
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationships
    memberships: Mapped[list["Membership"]] = relationship(
        "Membership",
        back_populates="client",
        lazy="selectin",
    )
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign",
        back_populates="client",
        lazy="selectin",
    )
    leads: Mapped[list["Lead"]] = relationship(
        "Lead",
        back_populates="client",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name='{self.name}', tier={self.tier.value})>"

    @property
    def is_active(self) -> bool:
        """Check if client has active subscription."""
        return (
            self.subscription_status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)
            and not self.is_deleted
        )

    @property
    def has_credits(self) -> bool:
        """Check if client has remaining credits."""
        return self.credits_remaining > 0

    def use_credits(self, amount: int) -> bool:
        """
        Use credits if available.

        Args:
            amount: Number of credits to use

        Returns:
            True if credits were used, False if insufficient
        """
        if self.credits_remaining >= amount:
            self.credits_remaining -= amount
            return True
        return False

    def add_credits(self, amount: int) -> None:
        """Add credits to the client."""
        self.credits_remaining += amount


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Soft delete via SoftDeleteMixin (Rule 14)
# [x] Subscription tier and status
# [x] Credits tracking
# [x] Permission mode default
# [x] Stripe integration fields
# [x] Relationships to memberships, campaigns, leads
# [x] is_active and has_credits properties
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
