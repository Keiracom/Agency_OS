"""
Contract: src/services/suppression_service.py
Purpose: Check and manage suppression list for leads
Layer: 3 - services
Imports: models, config
Consumers: JIT validator, scout engine, API routes

FILE: src/services/suppression_service.py
TASK: CUST-008
PHASE: 24F - Customer Import
PURPOSE: Check and manage suppression list for leads
LAYER: 3 - services
IMPORTS: models, config
CONSUMERS: JIT Validator, Scout Engine, API routes
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


class SuppressionResult(BaseModel):
    """Result of suppression check."""

    suppressed: bool = False
    reason: str | None = None
    details: str | None = None


class SuppressionEntry(BaseModel):
    """Suppression list entry."""

    id: UUID
    domain: str | None
    email: str | None
    company_name: str | None
    reason: str
    source: str
    notes: str | None
    expires_at: datetime | None
    created_at: datetime


# ============================================================================
# SUPPRESSION SERVICE
# ============================================================================


class SuppressionService:
    """
    Check and manage suppression list.

    Called by JIT validator before every send and by Scout engine
    when filtering leads.

    Supports:
    - Domain-level suppression (blocks entire company)
    - Email-level suppression (blocks individual)
    - Multiple reasons (existing_customer, competitor, etc.)
    - Expiring suppressions
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    # =========================================================================
    # SUPPRESSION CHECKING
    # =========================================================================

    async def is_suppressed(
        self,
        client_id: UUID,
        email: str | None = None,
        domain: str | None = None,
    ) -> SuppressionResult | None:
        """
        Check if email/domain is suppressed for this client.
        Called by JIT validator before every send.

        Args:
            client_id: Client UUID
            email: Email address to check
            domain: Domain to check (extracted from email if not provided)

        Returns:
            SuppressionResult if suppressed, None otherwise
        """
        # Extract domain from email if not provided
        if email and not domain:
            domain = self._extract_domain(email)

        # Use the database function for efficient checking
        result = await self.db.execute(
            text("SELECT * FROM is_suppressed(:client_id, :email, :domain)"),
            {
                "client_id": str(client_id),
                "email": email.lower() if email else None,
                "domain": domain.lower() if domain else None,
            },
        )
        row = result.fetchone()

        if row and row.suppressed:
            return SuppressionResult(
                suppressed=True,
                reason=row.reason,
                details=row.details,
            )

        return None

    async def is_suppressed_batch(
        self,
        client_id: UUID,
        emails: list[str],
    ) -> dict[str, SuppressionResult | None]:
        """
        Check suppression for multiple emails at once.
        More efficient for bulk filtering.

        Args:
            client_id: Client UUID
            emails: List of email addresses

        Returns:
            Dict mapping email to SuppressionResult (None if not suppressed)
        """
        results: dict[str, SuppressionResult | None] = {}

        # Extract unique domains
        domains = set()
        email_domain_map: dict[str, str] = {}
        for email in emails:
            domain = self._extract_domain(email)
            if domain:
                domains.add(domain)
                email_domain_map[email.lower()] = domain

        # Check domains in batch
        suppressed_domains: dict[str, str] = {}
        if domains:
            query_result = await self.db.execute(
                text("""
                    SELECT domain, reason
                    FROM suppression_list
                    WHERE client_id = :client_id
                    AND domain = ANY(:domains)
                    AND (expires_at IS NULL OR expires_at > NOW())
                """),
                {
                    "client_id": str(client_id),
                    "domains": list(domains),
                },
            )
            for row in query_result.fetchall():
                suppressed_domains[row.domain] = row.reason

        # Check individual emails
        suppressed_emails: dict[str, str] = {}
        if emails:
            query_result = await self.db.execute(
                text("""
                    SELECT email, reason
                    FROM suppression_list
                    WHERE client_id = :client_id
                    AND email = ANY(:emails)
                    AND (expires_at IS NULL OR expires_at > NOW())
                """),
                {
                    "client_id": str(client_id),
                    "emails": [e.lower() for e in emails],
                },
            )
            for row in query_result.fetchall():
                suppressed_emails[row.email] = row.reason

        # Build results
        for email in emails:
            email_lower = email.lower()
            domain = email_domain_map.get(email_lower)

            # Check domain suppression first
            if domain and domain in suppressed_domains:
                results[email] = SuppressionResult(
                    suppressed=True,
                    reason=suppressed_domains[domain],
                    details=f"Domain {domain} is suppressed",
                )
            # Check email suppression
            elif email_lower in suppressed_emails:
                results[email] = SuppressionResult(
                    suppressed=True,
                    reason=suppressed_emails[email_lower],
                    details=f"Email {email} is suppressed",
                )
            else:
                results[email] = None

        return results

    # =========================================================================
    # SUPPRESSION MANAGEMENT
    # =========================================================================

    async def add_suppression(
        self,
        client_id: UUID,
        domain: str | None = None,
        email: str | None = None,
        company_name: str | None = None,
        reason: str = "manual",
        source: str = "manual",
        notes: str | None = None,
        expires_at: datetime | None = None,
        customer_id: UUID | None = None,
    ) -> UUID:
        """
        Add to suppression list.

        Args:
            client_id: Client UUID
            domain: Domain to suppress (preferred)
            email: Email to suppress (for individual blocks)
            company_name: Company name for fuzzy matching
            reason: Reason for suppression
            source: How it was added
            notes: Additional notes
            expires_at: Optional expiration
            customer_id: Link to client_customers record

        Returns:
            Suppression entry UUID
        """
        result = await self.db.execute(
            text("""
                INSERT INTO suppression_list (
                    client_id, domain, email, company_name,
                    reason, source, notes, expires_at, customer_id
                ) VALUES (
                    :client_id, :domain, :email, :company_name,
                    :reason, :source, :notes, :expires_at, :customer_id
                )
                ON CONFLICT (client_id, domain) DO UPDATE SET
                    reason = EXCLUDED.reason,
                    source = EXCLUDED.source,
                    notes = EXCLUDED.notes,
                    expires_at = EXCLUDED.expires_at
                RETURNING id
            """),
            {
                "client_id": str(client_id),
                "domain": domain.lower() if domain else None,
                "email": email.lower() if email else None,
                "company_name": company_name,
                "reason": reason,
                "source": source,
                "notes": notes,
                "expires_at": expires_at,
                "customer_id": str(customer_id) if customer_id else None,
            },
        )
        row = result.fetchone()
        await self.db.commit()

        if not row:
            raise ValueError(f"Failed to create suppression entry for client {client_id}")

        logger.info(
            f"Added suppression for client {client_id}: domain={domain}, email={email}, reason={reason}"
        )
        return row.id

    async def remove_suppression(
        self,
        client_id: UUID,
        suppression_id: UUID | None = None,
        domain: str | None = None,
        email: str | None = None,
    ) -> bool:
        """
        Remove from suppression list.

        Args:
            client_id: Client UUID
            suppression_id: Suppression entry ID
            domain: Or domain to remove
            email: Or email to remove

        Returns:
            True if removed, False if not found
        """
        # Soft delete (Rule 14) - set deleted_at instead of DELETE
        if suppression_id:
            result = await self.db.execute(
                text("""
                    UPDATE suppression_list
                    SET deleted_at = NOW()
                    WHERE id = :id AND client_id = :client_id AND deleted_at IS NULL
                    RETURNING id
                """),
                {"id": str(suppression_id), "client_id": str(client_id)},
            )
        elif domain:
            result = await self.db.execute(
                text("""
                    UPDATE suppression_list
                    SET deleted_at = NOW()
                    WHERE client_id = :client_id AND domain = :domain AND deleted_at IS NULL
                    RETURNING id
                """),
                {"client_id": str(client_id), "domain": domain.lower()},
            )
        elif email:
            result = await self.db.execute(
                text("""
                    UPDATE suppression_list
                    SET deleted_at = NOW()
                    WHERE client_id = :client_id AND email = :email AND deleted_at IS NULL
                    RETURNING id
                """),
                {"client_id": str(client_id), "email": email.lower()},
            )
        else:
            return False

        row = result.fetchone()
        await self.db.commit()

        if row:
            logger.info(f"Removed suppression {row.id} for client {client_id}")
            return True

        return False

    async def list_suppressions(
        self,
        client_id: UUID,
        reason: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SuppressionEntry]:
        """
        List suppression entries for a client.

        Args:
            client_id: Client UUID
            reason: Filter by reason
            limit: Max results
            offset: Pagination offset

        Returns:
            List of suppression entries
        """
        query = """
            SELECT id, domain, email, company_name, reason, source,
                   notes, expires_at, created_at
            FROM suppression_list
            WHERE client_id = :client_id AND deleted_at IS NULL
        """

        if reason:
            query += " AND reason = :reason"

        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        result = await self.db.execute(
            text(query),
            {
                "client_id": str(client_id),
                "reason": reason,
                "limit": limit,
                "offset": offset,
            },
        )
        rows = result.fetchall()

        return [
            SuppressionEntry(
                id=row.id,
                domain=row.domain,
                email=row.email,
                company_name=row.company_name,
                reason=row.reason,
                source=row.source,
                notes=row.notes,
                expires_at=row.expires_at,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def get_suppression_count(self, client_id: UUID) -> int:
        """Get count of suppression entries for a client."""
        result = await self.db.execute(
            text("""
                SELECT COUNT(*) as cnt
                FROM suppression_list
                WHERE client_id = :client_id AND deleted_at IS NULL
            """),
            {"client_id": str(client_id)},
        )
        row = result.fetchone()
        return int(row[0]) if row else 0

    # =========================================================================
    # AUTOMATIC SUPPRESSION
    # =========================================================================

    async def add_from_bounce(
        self,
        client_id: UUID,
        email: str,
        bounce_type: str = "hard",
    ) -> UUID:
        """
        Add suppression from email bounce.

        Args:
            client_id: Client UUID
            email: Bounced email
            bounce_type: Type of bounce (hard, soft)

        Returns:
            Suppression entry UUID
        """
        domain = self._extract_domain(email)

        # For hard bounces, suppress the email
        # For soft bounces, we might want to add with expiration
        expires_at = None
        if bounce_type == "soft":
            from datetime import timedelta

            expires_at = datetime.utcnow() + timedelta(days=7)

        return await self.add_suppression(
            client_id=client_id,
            email=email,
            domain=domain if bounce_type == "hard" else None,  # Block domain for hard bounces
            reason="bounced",
            source="bounce",
            notes=f"{bounce_type} bounce",
            expires_at=expires_at,
        )

    async def add_from_unsubscribe(
        self,
        client_id: UUID,
        email: str,
        lead_id: UUID | None = None,
    ) -> UUID:
        """
        Add suppression from unsubscribe request.

        Args:
            client_id: Client UUID
            email: Email that unsubscribed
            lead_id: Optional lead UUID

        Returns:
            Suppression entry UUID
        """
        return await self.add_suppression(
            client_id=client_id,
            email=email,
            reason="unsubscribed",
            source="unsubscribe",
            notes=f"Lead ID: {lead_id}" if lead_id else None,
        )

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _extract_domain(self, email: str) -> str | None:
        """Extract domain from email address."""
        if not email or "@" not in email:
            return None
        return email.split("@")[1].lower()
