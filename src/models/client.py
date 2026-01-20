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

from sqlalchemy import Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import ARRAY, ENUM
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
    from src.models.client_persona import ClientPersona
    from src.models.lead import Lead
    from src.models.lead_pool import LeadPool
    from src.models.linkedin_credential import LinkedInCredential
    from src.models.linkedin_seat import LinkedInSeat
    from src.models.membership import Membership
    from src.models.resource_pool import ClientResource


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

    # Company info (from onboarding)
    website_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    services_offered: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    years_in_business: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    team_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    value_proposition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_offer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ICP fields (from onboarding)
    icp_industries: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    icp_company_sizes: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    icp_revenue_range: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icp_locations: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    icp_titles: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    icp_pain_points: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    icp_keywords: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    icp_exclusions: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)

    # ALS weights (customized scoring)
    als_weights: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Branding (for signatures, personalization)
    branding: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # ICP extraction tracking
    icp_extracted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    icp_extraction_source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icp_confirmed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    icp_extraction_job_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

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
    linkedin_credential: Mapped[Optional["LinkedInCredential"]] = relationship(
        "LinkedInCredential",
        back_populates="client",
        uselist=False,
        lazy="selectin",
    )
    pool_leads: Mapped[list["LeadPool"]] = relationship(
        "LeadPool",
        back_populates="client",
        foreign_keys="LeadPool.client_id",
        lazy="selectin",
    )
    resources: Mapped[list["ClientResource"]] = relationship(
        "ClientResource",
        back_populates="client",
        lazy="selectin",
    )
    personas: Mapped[list["ClientPersona"]] = relationship(
        "ClientPersona",
        back_populates="client",
        lazy="selectin",
    )
    linkedin_seats: Mapped[list["LinkedInSeat"]] = relationship(
        "LinkedInSeat",
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
