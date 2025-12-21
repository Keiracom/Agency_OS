"""
FILE: src/models/membership.py
PURPOSE: Membership model for User-Client many-to-many with roles
PHASE: 2 (Models & Schemas)
TASK: MOD-004
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

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    MembershipRole,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.client import Client
    from src.models.user import User


class Membership(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Membership model for User-Client relationships.

    Implements multi-tenancy with role-based access control.
    Users can belong to multiple clients with different roles.
    """

    __tablename__ = "memberships"

    # Foreign keys
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role
    role: Mapped[MembershipRole] = mapped_column(
        ENUM(MembershipRole, name="membership_role", create_type=False),
        nullable=False,
        default=MembershipRole.MEMBER,
    )

    # Invitation tracking
    invited_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    invited_email: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships",
        foreign_keys=[user_id],
    )
    client: Mapped["Client"] = relationship(
        "Client",
        back_populates="memberships",
    )
    inviter: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[invited_by],
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="unique_membership"),
    )

    def __repr__(self) -> str:
        return f"<Membership(user_id={self.user_id}, client_id={self.client_id}, role={self.role.value})>"

    @property
    def is_accepted(self) -> bool:
        """Check if membership has been accepted."""
        return self.accepted_at is not None

    @property
    def is_pending(self) -> bool:
        """Check if membership is pending acceptance."""
        return self.accepted_at is None and not self.is_deleted

    @property
    def is_owner(self) -> bool:
        """Check if this is an owner membership."""
        return self.role == MembershipRole.OWNER

    @property
    def is_admin(self) -> bool:
        """Check if this is an admin or owner membership."""
        return self.role in (MembershipRole.OWNER, MembershipRole.ADMIN)

    @property
    def can_manage(self) -> bool:
        """Check if user can manage resources (owner, admin, or member)."""
        return self.role in (
            MembershipRole.OWNER,
            MembershipRole.ADMIN,
            MembershipRole.MEMBER,
        )

    def accept(self) -> None:
        """Accept the membership invitation."""
        self.accepted_at = datetime.utcnow()

    def has_role(self, *roles: MembershipRole) -> bool:
        """Check if membership has any of the specified roles."""
        return self.role in roles


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] User-Client many-to-many relationship
# [x] Role-based access (owner, admin, member, viewer)
# [x] Soft delete via SoftDeleteMixin (Rule 14)
# [x] Invitation tracking (invited_by, invited_email, accepted_at)
# [x] Unique constraint on user_id + client_id
# [x] Helper properties (is_accepted, is_admin, can_manage)
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
