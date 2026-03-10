"""
Contract: src/services/onboarding_gate_service.py
Purpose: Mandatory onboarding gate checks for LinkedIn and CRM connections
Layer: 3 - services
Imports: models, integrations
Consumers: orchestration flows, API routes

FILE: src/services/onboarding_gate_service.py
TASK: Mandatory onboarding gates
PHASE: Architecture Decision - LinkedIn + CRM mandatory
PURPOSE: Enforce LinkedIn and CRM connection requirements before onboarding completion

RULES APPLIED:
- Rule 1: Follow blueprint exactly
- Rule 11: Session passed as argument
- Rule 14: Soft deletes only
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ============================================
# EXCEPTIONS
# ============================================


class OnboardingGateError(Exception):
    """Base exception for onboarding gate failures."""

    def __init__(self, message: str, gate: str, client_id: UUID):
        self.message = message
        self.gate = gate
        self.client_id = client_id
        super().__init__(message)


class LinkedInConnectionRequired(OnboardingGateError):
    """LinkedIn connection is required to proceed."""

    def __init__(self, client_id: UUID):
        super().__init__(
            message="LinkedIn connection required to proceed",
            gate="linkedin",
            client_id=client_id,
        )


class CRMConnectionRequired(OnboardingGateError):
    """CRM connection is required to proceed."""

    def __init__(self, client_id: UUID):
        super().__init__(
            message="CRM connection required to proceed",
            gate="crm",
            client_id=client_id,
        )


# ============================================
# DATA MODELS
# ============================================


@dataclass
class OnboardingGateStatus:
    """Status of onboarding gates for a client."""

    client_id: UUID
    linkedin_connected: bool
    linkedin_connected_at: datetime | None
    linkedin_seat_count: int
    crm_connected: bool
    crm_connected_at: datetime | None
    crm_type: str | None
    can_proceed: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "client_id": str(self.client_id),
            "linkedin_connected": self.linkedin_connected,
            "linkedin_connected_at": self.linkedin_connected_at.isoformat()
            if self.linkedin_connected_at
            else None,
            "linkedin_seat_count": self.linkedin_seat_count,
            "crm_connected": self.crm_connected,
            "crm_connected_at": self.crm_connected_at.isoformat()
            if self.crm_connected_at
            else None,
            "crm_type": self.crm_type,
            "can_proceed": self.can_proceed,
            "missing_gates": self._get_missing_gates(),
        }

    def _get_missing_gates(self) -> list[str]:
        """Get list of missing gates."""
        missing = []
        if not self.linkedin_connected:
            missing.append("linkedin")
        if not self.crm_connected:
            missing.append("crm")
        return missing


# ============================================
# GATE CHECK FUNCTIONS
# ============================================


async def check_onboarding_gates(
    db: AsyncSession,
    client_id: UUID,
) -> OnboardingGateStatus:
    """
    Check both LinkedIn and CRM connection gates for a client.

    Mandatory gates:
    - LinkedIn: At least one linkedin_seat with unipile_account_id set
      and status not in ('disconnected', 'restricted')
    - CRM: At least one client_crm_configs record with is_active = true

    Args:
        db: Database session
        client_id: Client UUID to check

    Returns:
        OnboardingGateStatus with connection status for both gates
    """
    # Check LinkedIn seats - need at least one active connection
    linkedin_result = await db.execute(
        text("""
            SELECT
                COUNT(*) as seat_count,
                MIN(created_at) as first_connected_at
            FROM linkedin_seats
            WHERE client_id = :client_id
            AND unipile_account_id IS NOT NULL
            AND status NOT IN ('disconnected', 'restricted', 'pending')
        """),
        {"client_id": str(client_id)},
    )
    linkedin_row = linkedin_result.fetchone()
    linkedin_seat_count = linkedin_row.seat_count if linkedin_row else 0
    linkedin_connected = linkedin_seat_count > 0
    linkedin_connected_at = (
        linkedin_row.first_connected_at if linkedin_row and linkedin_connected else None
    )

    # Check CRM configuration - need at least one active config
    crm_result = await db.execute(
        text("""
            SELECT
                crm_type,
                created_at as connected_at
            FROM client_crm_configs
            WHERE client_id = :client_id
            AND is_active = true
            ORDER BY created_at ASC
            LIMIT 1
        """),
        {"client_id": str(client_id)},
    )
    crm_row = crm_result.fetchone()
    crm_connected = crm_row is not None
    crm_type = crm_row.crm_type if crm_row else None
    crm_connected_at = crm_row.connected_at if crm_row else None

    # Both must be connected to proceed
    can_proceed = linkedin_connected and crm_connected

    logger.info(
        f"Onboarding gates for client {client_id}: "
        f"LinkedIn={linkedin_connected} ({linkedin_seat_count} seats), "
        f"CRM={crm_connected} ({crm_type or 'none'}), "
        f"can_proceed={can_proceed}"
    )

    return OnboardingGateStatus(
        client_id=client_id,
        linkedin_connected=linkedin_connected,
        linkedin_connected_at=linkedin_connected_at,
        linkedin_seat_count=linkedin_seat_count,
        crm_connected=crm_connected,
        crm_connected_at=crm_connected_at,
        crm_type=crm_type,
        can_proceed=can_proceed,
    )


async def enforce_onboarding_gates(
    db: AsyncSession,
    client_id: UUID,
) -> OnboardingGateStatus:
    """
    Check onboarding gates and raise exception if either is missing.

    This is the enforcement function - use in flows that require
    both connections to be present.

    Args:
        db: Database session
        client_id: Client UUID to check

    Returns:
        OnboardingGateStatus if both gates pass

    Raises:
        LinkedInConnectionRequired: If LinkedIn is not connected
        CRMConnectionRequired: If CRM is not connected
    """
    status = await check_onboarding_gates(db, client_id)

    if not status.linkedin_connected:
        logger.warning(f"Client {client_id} missing LinkedIn connection - blocking onboarding")
        raise LinkedInConnectionRequired(client_id)

    if not status.crm_connected:
        logger.warning(f"Client {client_id} missing CRM connection - blocking onboarding")
        raise CRMConnectionRequired(client_id)

    return status


async def update_client_connection_timestamps(
    db: AsyncSession,
    client_id: UUID,
) -> None:
    """
    Update client record with connection timestamps from linked tables.

    Called when connections are established to update the denormalized
    linkedin_connected_at and crm_connected_at columns on clients table.

    Args:
        db: Database session
        client_id: Client UUID to update
    """
    # Get LinkedIn connection timestamp
    linkedin_result = await db.execute(
        text("""
            SELECT MIN(created_at) as first_connected
            FROM linkedin_seats
            WHERE client_id = :client_id
            AND unipile_account_id IS NOT NULL
            AND status NOT IN ('disconnected', 'restricted', 'pending')
        """),
        {"client_id": str(client_id)},
    )
    linkedin_row = linkedin_result.fetchone()
    linkedin_connected_at = linkedin_row.first_connected if linkedin_row else None

    # Get CRM connection timestamp
    crm_result = await db.execute(
        text("""
            SELECT MIN(created_at) as first_connected
            FROM client_crm_configs
            WHERE client_id = :client_id
            AND is_active = true
        """),
        {"client_id": str(client_id)},
    )
    crm_row = crm_result.fetchone()
    crm_connected_at = crm_row.first_connected if crm_row else None

    # Update client record
    await db.execute(
        text("""
            UPDATE clients
            SET linkedin_connected_at = :linkedin_at,
                crm_connected_at = :crm_at,
                updated_at = NOW()
            WHERE id = :client_id
            AND deleted_at IS NULL
        """),
        {
            "client_id": str(client_id),
            "linkedin_at": linkedin_connected_at,
            "crm_at": crm_connected_at,
        },
    )
    await db.commit()

    logger.info(
        f"Updated connection timestamps for client {client_id}: "
        f"LinkedIn={linkedin_connected_at}, CRM={crm_connected_at}"
    )


# ============================================
# GATE MESSAGES (for frontend/API)
# ============================================

GATE_MESSAGES = {
    "linkedin": {
        "title": "LinkedIn Connection Required",
        "description": "Required — enables LinkedIn outreach channel and protects your network from outreach",
        "consequence": "Without LinkedIn connection, you cannot use LinkedIn outreach or protect your existing connections from being contacted.",
    },
    "crm": {
        "title": "CRM Connection Required",
        "description": "Required — protects your existing clients from outreach and tracks booked meetings",
        "consequence": "Without CRM connection, your existing clients may be contacted and meeting tracking will not sync to your CRM.",
    },
}


def get_gate_message(gate: str) -> dict[str, str]:
    """Get user-facing message for a gate."""
    return GATE_MESSAGES.get(gate, {"title": "Connection Required", "description": ""})


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] check_onboarding_gates() function checks both tables
- [x] enforce_onboarding_gates() raises clear exceptions
- [x] OnboardingGateStatus dataclass with to_dict()
- [x] Custom exceptions for LinkedIn and CRM gates
- [x] update_client_connection_timestamps() helper
- [x] GATE_MESSAGES for frontend/API consumption
- [x] Proper logging
- [x] Type hints on all functions
- [x] Docstrings on all functions
"""
