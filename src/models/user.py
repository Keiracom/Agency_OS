"""
FILE: src/models/user.py
PURPOSE: User profile model linked to Supabase auth.users
PHASE: 2 (Models & Schemas)
TASK: MOD-003
DEPENDENCIES:
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 12: No imports from engines/integrations/orchestration
"""

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.membership import Membership


class User(Base, TimestampMixin):
    """
    User profile model.

    Linked to Supabase auth.users via the id field.
    Created automatically via database trigger on auth signup.
    """

    __tablename__ = "users"

    # Primary key references auth.users(id)
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )

    # Basic info
    email: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Preferences
    timezone: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Australia/Sydney",
    )
    notification_email: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    notification_sms: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Relationships
    memberships: Mapped[list["Membership"]] = relationship(
        "Membership",
        back_populates="user",
        lazy="selectin",
        foreign_keys="Membership.user_id",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"

    @property
    def display_name(self) -> str:
        """Get display name (full name or email)."""
        return self.full_name or self.email.split("@")[0]

    @property
    def first_name(self) -> str:
        """Get first name from full name."""
        if self.full_name:
            return self.full_name.split()[0]
        return self.email.split("@")[0]


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] ID references auth.users
# [x] Email, full_name, avatar_url fields
# [x] Timezone default to Australia/Sydney
# [x] Notification preferences
# [x] Relationship to memberships
# [x] display_name and first_name properties
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
