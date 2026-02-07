"""
Contract: src/engines/base.py
Purpose: Abstract base engine with dependency injection pattern
Layer: 3 - engines
Imports: models, exceptions
Consumers: all engines

FILE: src/engines/base.py
PURPOSE: Abstract base engine with dependency injection pattern
PHASE: 4 (Engines)
TASK: ENG-001
DEPENDENCIES:
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Dependency Injection - Engines accept `db: AsyncSession` as argument
  - Rule 12: Import Hierarchy - models → integrations → engines → orchestration
  - Rule 14: Soft deletes only
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ResourceNotFoundError as NotFoundError
from src.exceptions import ValidationError
from src.models.base import ChannelType, LeadStatus

# Type variable for engine result types
T = TypeVar("T")


class EngineResult(Generic[T]):
    """
    Standardized result wrapper for engine operations.

    Provides consistent success/failure handling across all engines.
    """

    def __init__(
        self,
        success: bool,
        data: T | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def ok(cls, data: T, metadata: dict[str, Any] | None = None) -> "EngineResult[T]":
        """Create successful result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, metadata: dict[str, Any] | None = None) -> "EngineResult[T]":
        """Create failed result."""
        return cls(success=False, error=error, metadata=metadata)


class BaseEngine(ABC):
    """
    Abstract base class for all engines.

    All engines MUST:
    1. Accept `db: AsyncSession` as argument to methods (Rule 11)
    2. Never import from other engines (Rule 12)
    3. Use soft deletes only (Rule 14)
    4. Return EngineResult for operation results

    Example:
        class ScoutEngine(BaseEngine):
            async def enrich(
                self,
                db: AsyncSession,  # Passed by caller
                domain: str,
                client_id: str
            ) -> EngineResult[EnrichedLead]:
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name for logging and metrics."""
        pass

    async def validate_client_active(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> bool:
        """
        Validate that a client is active (not deleted, subscription valid).

        Args:
            db: Database session (passed by caller)
            client_id: Client UUID to validate

        Returns:
            True if client is active

        Raises:
            NotFoundError: If client not found
            ValidationError: If client is inactive
        """
        from src.models.client import Client

        stmt = select(Client).where(
            and_(
                Client.id == client_id,
                Client.deleted_at.is_(None),  # Soft delete check
            )
        )
        result = await db.execute(stmt)
        client = result.scalar_one_or_none()

        if not client:
            raise NotFoundError(
                resource_type="Client",
                resource_id=str(client_id),
            )

        # Check subscription status
        if client.subscription_status in ("cancelled", "past_due"):
            raise ValidationError(
                field="subscription_status",
                message=f"Client subscription is {client.subscription_status}",
            )

        return True

    async def validate_campaign_active(
        self,
        db: AsyncSession,
        campaign_id: UUID,
    ) -> bool:
        """
        Validate that a campaign is active.

        Args:
            db: Database session (passed by caller)
            campaign_id: Campaign UUID to validate

        Returns:
            True if campaign is active

        Raises:
            NotFoundError: If campaign not found
            ValidationError: If campaign is not active
        """
        from src.models.base import CampaignStatus
        from src.models.campaign import Campaign

        stmt = select(Campaign).where(
            and_(
                Campaign.id == campaign_id,
                Campaign.deleted_at.is_(None),  # Soft delete check
            )
        )
        result = await db.execute(stmt)
        campaign = result.scalar_one_or_none()

        if not campaign:
            raise NotFoundError(
                resource_type="Campaign",
                resource_id=str(campaign_id),
            )

        if campaign.status != CampaignStatus.ACTIVE:
            raise ValidationError(
                field="status",
                message=f"Campaign status is {campaign.status}, expected active",
            )

        return True

    async def validate_lead_for_outreach(
        self,
        db: AsyncSession,
        lead_id: UUID,
        channel: ChannelType,
    ) -> bool:
        """
        Validate that a lead can receive outreach on a channel.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID to validate
            channel: Channel to use for outreach

        Returns:
            True if lead can receive outreach

        Raises:
            NotFoundError: If lead not found
            ValidationError: If lead cannot receive outreach
        """
        from src.models.lead import Lead

        stmt = select(Lead).where(
            and_(
                Lead.id == lead_id,
                Lead.deleted_at.is_(None),  # Soft delete check
            )
        )
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()

        if not lead:
            raise NotFoundError(
                resource_type="Lead",
                resource_id=str(lead_id),
            )

        # Check suppression status
        if lead.status in (LeadStatus.UNSUBSCRIBED, LeadStatus.BOUNCED):
            raise ValidationError(
                field="status",
                message=f"Lead is {lead.status}, cannot send outreach",
            )

        # Check channel-specific requirements
        if channel == ChannelType.EMAIL and not lead.email:
            raise ValidationError(
                field="email",
                message="Lead has no email address",
            )
        elif channel == ChannelType.SMS and not lead.phone:
            raise ValidationError(
                field="phone",
                message="Lead has no phone number",
            )
        elif channel == ChannelType.LINKEDIN and not lead.linkedin_url:
            raise ValidationError(
                field="linkedin_url",
                message="Lead has no LinkedIn URL",
            )

        return True

    async def get_lead_by_id(
        self,
        db: AsyncSession,
        lead_id: UUID,
    ) -> Any:
        """
        Get a lead by ID.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID

        Returns:
            Lead model instance

        Raises:
            NotFoundError: If lead not found
        """
        from src.models.lead import Lead

        stmt = select(Lead).where(
            and_(
                Lead.id == lead_id,
                Lead.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()

        if not lead:
            raise NotFoundError(
                resource_type="Lead",
                resource_id=str(lead_id),
            )

        return lead

    async def get_campaign_by_id(
        self,
        db: AsyncSession,
        campaign_id: UUID,
    ) -> Any:
        """
        Get a campaign by ID.

        Args:
            db: Database session (passed by caller)
            campaign_id: Campaign UUID

        Returns:
            Campaign model instance

        Raises:
            NotFoundError: If campaign not found
        """
        from src.models.campaign import Campaign

        stmt = select(Campaign).where(
            and_(
                Campaign.id == campaign_id,
                Campaign.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        campaign = result.scalar_one_or_none()

        if not campaign:
            raise NotFoundError(
                resource_type="Campaign",
                resource_id=str(campaign_id),
            )

        return campaign

    async def get_client_by_id(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> Any:
        """
        Get a client by ID.

        Args:
            db: Database session (passed by caller)
            client_id: Client UUID

        Returns:
            Client model instance

        Raises:
            NotFoundError: If client not found
        """
        from src.models.client import Client

        stmt = select(Client).where(
            and_(
                Client.id == client_id,
                Client.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        client = result.scalar_one_or_none()

        if not client:
            raise NotFoundError(
                resource_type="Client",
                resource_id=str(client_id),
            )

        return client

    def log_operation(
        self,
        operation: str,
        client_id: UUID | None = None,
        lead_id: UUID | None = None,
        campaign_id: UUID | None = None,
        channel: ChannelType | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a log entry for engine operation.

        This is a helper for consistent logging across engines.

        Args:
            operation: Name of the operation
            client_id: Optional client UUID
            lead_id: Optional lead UUID
            campaign_id: Optional campaign UUID
            channel: Optional channel type
            metadata: Additional metadata

        Returns:
            Log entry dictionary
        """
        entry: dict[str, Any] = {
            "engine": self.name,
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if client_id:
            entry["client_id"] = str(client_id)
        if lead_id:
            entry["lead_id"] = str(lead_id)
        if campaign_id:
            entry["campaign_id"] = str(campaign_id)
        if channel:
            entry["channel"] = channel.value
        if metadata:
            entry["metadata"] = metadata

        return entry

    async def log_operation_to_db(
        self,
        db: AsyncSession,
        operation: str,
        client_id: UUID | None = None,
        lead_id: UUID | None = None,
        campaign_id: UUID | None = None,
        channel: ChannelType | None = None,
        success: bool = True,
        cost_aud: float = 0.0,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Log engine operation to audit_logs table for full traceability.

        This persists the log entry to the database for audit trail,
        cost tracking, and debugging.

        Args:
            db: Database session (passed by caller)
            operation: Name of the operation
            client_id: Optional client UUID
            lead_id: Optional lead UUID
            campaign_id: Optional campaign UUID
            channel: Optional channel type
            success: Whether operation succeeded
            cost_aud: Cost in AUD (LAW II compliance)
            error_message: Error message if failed
            metadata: Additional metadata
        """
        try:
            from sqlalchemy import text as sql_text
            import json

            entry = self.log_operation(
                operation=operation,
                client_id=client_id,
                lead_id=lead_id,
                campaign_id=campaign_id,
                channel=channel,
                metadata=metadata,
            )
            entry["success"] = success
            entry["cost_aud"] = cost_aud
            entry["error_message"] = error_message

            # Insert into audit_logs table
            await db.execute(
                sql_text("""
                    INSERT INTO audit_logs (
                        engine, operation, client_id, lead_id, campaign_id,
                        channel, success, cost_aud, error_message, metadata,
                        created_at
                    ) VALUES (
                        :engine, :operation, :client_id, :lead_id, :campaign_id,
                        :channel, :success, :cost_aud, :error_message, 
                        CAST(:metadata AS jsonb), NOW()
                    )
                """),
                {
                    "engine": entry.get("engine"),
                    "operation": entry.get("operation"),
                    "client_id": entry.get("client_id"),
                    "lead_id": entry.get("lead_id"),
                    "campaign_id": entry.get("campaign_id"),
                    "channel": entry.get("channel"),
                    "success": success,
                    "cost_aud": cost_aud,
                    "error_message": error_message,
                    "metadata": json.dumps(metadata) if metadata else "{}",
                },
            )
            # Note: Don't commit here - let the caller manage the transaction
            
        except Exception as e:
            # Don't fail the operation if logging fails
            import logging
            logging.getLogger(__name__).warning(f"Audit log failed: {e}")


class OutreachEngine(BaseEngine):
    """
    Base class for outreach engines (Email, SMS, LinkedIn, Voice, Mail).

    Provides common patterns for sending messages across channels.
    """

    @property
    @abstractmethod
    def channel(self) -> ChannelType:
        """The channel this engine handles."""
        pass

    @abstractmethod
    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        content: str,
        **kwargs: Any,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a message to a lead.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            content: Message content
            **kwargs: Channel-specific options

        Returns:
            EngineResult with send result
        """
        pass

    async def validate_and_send(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        content: str,
        **kwargs: Any,
    ) -> EngineResult[dict[str, Any]]:
        """
        Validate prerequisites and send message.

        This wraps send() with standard validations.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            content: Message content
            **kwargs: Channel-specific options

        Returns:
            EngineResult with send result or validation error
        """
        try:
            # Get campaign for client_id
            campaign = await self.get_campaign_by_id(db, campaign_id)

            # Validate client, campaign, and lead
            await self.validate_client_active(db, campaign.client_id)
            await self.validate_campaign_active(db, campaign_id)
            await self.validate_lead_for_outreach(db, lead_id, self.channel)

            # If validations pass, send the message
            return await self.send(db, lead_id, campaign_id, content, **kwargs)

        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "engine": self.name,
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                    "channel": self.channel.value,
                },
            )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] EngineResult wrapper for consistent results
# [x] BaseEngine abstract base class
# [x] DI pattern: db: AsyncSession passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Soft delete checks in all queries (Rule 14)
# [x] Common validation methods (client, campaign, lead)
# [x] OutreachEngine for channel-based engines
# [x] All functions have type hints
# [x] All functions have docstrings
