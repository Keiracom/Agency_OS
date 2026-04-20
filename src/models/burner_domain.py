"""
Contract: src/models/burner_domain.py
Purpose: Burner domain and mailbox models for Salesforge domain pool
Layer: 1 - models
Imports: exceptions only
Consumers: ALL layers
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as UUID_DB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.client import Client


class BurnerDomainStatus(StrEnum):
    """Lifecycle states for a burner domain."""

    CANDIDATE = "candidate"
    APPROVED = "approved"
    PURCHASING = "purchasing"
    DNS_CONFIGURING = "dns_configuring"
    WARMING = "warming"
    READY = "ready"
    ASSIGNED = "assigned"
    QUARANTINED = "quarantined"
    RETIRED = "retired"


class BurnerMailboxStatus(StrEnum):
    """Lifecycle states for a burner mailbox."""

    CREATING = "creating"
    WARMING = "warming"
    READY = "ready"
    ASSIGNED = "assigned"
    RETIRED = "retired"


class BurnerDomain(Base, TimestampMixin):
    """
    A customer-agnostic sending domain managed by the domain pool.

    Lifecycle: candidate -> approved -> purchasing -> dns_configuring ->
               warming -> ready -> assigned -> (quarantined | retired)
    """

    __tablename__ = "burner_domains"

    id: Mapped[UUID] = mapped_column(
        UUID_DB(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    domain_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    tld: Mapped[str] = mapped_column(String(20), nullable=False, default="com.au")
    salesforge_domain_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=BurnerDomainStatus.CANDIDATE,
    )
    pattern_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    purchased_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    warmup_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to_client_id: Mapped[Optional[UUID]] = mapped_column(
        UUID_DB(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    quarantine_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sender_reputation_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    daily_send_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    mailboxes: Mapped[list["BurnerMailbox"]] = relationship(
        "BurnerMailbox",
        back_populates="domain",
        cascade="all, delete-orphan",
    )


class BurnerMailbox(Base):
    """
    A sending mailbox on a burner domain. Two mailboxes per domain.

    Lifecycle: creating -> warming -> ready -> assigned -> retired
    """

    __tablename__ = "burner_mailboxes"

    id: Mapped[UUID] = mapped_column(
        UUID_DB(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    domain_id: Mapped[UUID] = mapped_column(
        UUID_DB(as_uuid=True),
        ForeignKey("burner_domains.id", ondelete="CASCADE"),
        nullable=False,
    )
    mailbox_address: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{first_name} {last_name}",
    )
    salesforge_mailbox_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=BurnerMailboxStatus.CREATING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    # Relationships
    domain: Mapped["BurnerDomain"] = relationship("BurnerDomain", back_populates="mailboxes")


class DomainNamingPattern(Base):
    """
    Approved naming pattern configuration for generating burner domain candidates.

    Seeds and suffixes are combined to produce pronounceable, professional domain names.
    """

    __tablename__ = "domain_naming_patterns"

    id: Mapped[UUID] = mapped_column(
        UUID_DB(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    pattern_type: Mapped[str] = mapped_column(Text, nullable=False)
    seeds: Mapped[list] = mapped_column(JSONB, nullable=False)
    suffixes: Mapped[list] = mapped_column(JSONB, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )
