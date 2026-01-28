"""
Contract: src/models/linkedin_credential.py
Purpose: LinkedIn credential model for HeyReach integration
Layer: 1 - models
Imports: base only
Consumers: services, API routes

Phase: 24H - LinkedIn Credential Connection
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.client import Client


class LinkedInCredential(Base, UUIDMixin, TimestampMixin):
    """
    LinkedIn credential storage for HeyReach automation.

    Stores encrypted LinkedIn credentials and connection status
    for automated LinkedIn outreach via HeyReach.
    """

    __tablename__ = "client_linkedin_credentials"

    # Foreign key to client
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Encrypted credentials (Fernet AES-256)
    linkedin_email_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="AES-256 encrypted LinkedIn email",
    )
    linkedin_password_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="AES-256 encrypted LinkedIn password",
    )

    # Connection status
    connection_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        doc="Status: pending, connecting, awaiting_2fa, connected, failed, disconnected",
    )

    # HeyReach integration
    heyreach_sender_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="HeyReach sender ID after successful connection",
    )
    heyreach_account_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="HeyReach account ID",
    )

    # LinkedIn profile info (populated after connection)
    linkedin_profile_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="LinkedIn profile URL",
    )
    linkedin_profile_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="LinkedIn display name",
    )
    linkedin_headline: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="LinkedIn headline",
    )
    linkedin_connection_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Number of LinkedIn connections",
    )

    # 2FA handling
    two_fa_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="2FA method: sms, email, authenticator",
    )
    two_fa_requested_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="When 2FA was requested",
    )

    # Error tracking
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Last error message",
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of connection errors",
    )
    last_error_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="When last error occurred",
    )

    # Connection timestamps
    connected_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="When connection was established",
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="When account was disconnected",
    )

    # Relationship
    client: Mapped["Client"] = relationship(
        "Client",
        back_populates="linkedin_credential",
    )

    def __repr__(self) -> str:
        return f"<LinkedInCredential(client_id={self.client_id}, status={self.connection_status})>"

    @property
    def is_connected(self) -> bool:
        """Check if LinkedIn is successfully connected."""
        return self.connection_status == "connected" and self.heyreach_sender_id is not None

    @property
    def is_awaiting_2fa(self) -> bool:
        """Check if waiting for 2FA verification."""
        return self.connection_status == "awaiting_2fa"

    @property
    def has_error(self) -> bool:
        """Check if connection has failed."""
        return self.connection_status == "failed"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Table name matches migration
# [x] All columns from migration
# [x] Proper type hints
# [x] Encrypted fields documented
# [x] Relationship to Client
# [x] Helper properties
# [x] No imports from engines/integrations
