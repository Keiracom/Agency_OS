"""
Contract: src/services/mock_crm_service.py
Purpose: Seed mock CRM data for E2E testing when MOCK_CRM=true
Layer: 3 - services
Phase: Test Infrastructure

When MOCK_CRM is enabled, this service seeds realistic test data for ONE client
covering multiple scenarios for agency exclusion, deals, and meetings.

Data seeded:
- agency_exclusion_list: 8 rows (5 crm_client, 2 crm_pipeline, 1 crm_lost_deal)
- deals: 6 rows (2 closed_won, 2 closed_lost, 2 open/active)
- meetings: 3 rows (1 confirmed+showed, 1 no-show, 1 scheduled)
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MockCRMService:
    """Service to seed mock CRM data for testing."""

    async def seed_mock_data(
        self,
        db: AsyncSession,
        client_id: UUID,
        campaign_id: UUID,
    ) -> dict:
        """
        Seed mock CRM data for a single test client.

        Args:
            db: Database session
            client_id: Client UUID to seed data for
            campaign_id: Campaign UUID for the leads

        Returns:
            Dict with counts of seeded records
        """
        logger.info(f"Seeding mock CRM data for client {client_id}")

        # Check if already seeded (idempotent)
        result = await db.execute(
            text("""
                SELECT COUNT(*) FROM agency_exclusion_list
                WHERE client_id = :client_id AND notes LIKE 'MOCK_CRM%'
            """),
            {"client_id": str(client_id)},
        )
        existing_count = result.scalar()
        if existing_count and existing_count > 0:
            logger.info(f"Mock data already exists for client {client_id}, skipping")
            return {"status": "already_seeded", "exclusion_count": existing_count}

        # Get or create test leads for deals/meetings
        lead_ids = await self._ensure_test_leads(db, client_id, campaign_id)

        # Seed the data
        exclusion_count = await self._seed_exclusion_list(db, client_id)
        deal_count = await self._seed_deals(db, client_id, lead_ids)
        meeting_count = await self._seed_meetings(db, client_id, lead_ids)

        await db.commit()

        logger.info(
            f"Seeded mock CRM data: {exclusion_count} exclusions, "
            f"{deal_count} deals, {meeting_count} meetings"
        )

        return {
            "status": "seeded",
            "exclusion_count": exclusion_count,
            "deal_count": deal_count,
            "meeting_count": meeting_count,
        }

    async def _ensure_test_leads(
        self,
        db: AsyncSession,
        client_id: UUID,
        campaign_id: UUID,
    ) -> list[UUID]:
        """Ensure we have test leads for deals and meetings."""
        # Check for existing leads
        result = await db.execute(
            text("""
                SELECT id FROM leads
                WHERE client_id = :client_id
                LIMIT 6
            """),
            {"client_id": str(client_id)},
        )
        rows = result.fetchall()
        lead_ids = [row.id for row in rows]

        # Create test leads if we don't have enough
        while len(lead_ids) < 6:
            lead_id = uuid4()
            await db.execute(
                text("""
                    INSERT INTO leads (id, client_id, campaign_id, first_name, last_name, email, company, title, status)
                    VALUES (:id, :client_id, :campaign_id, :first_name, :last_name, :email, :company, :title, 'enriched')
                """),
                {
                    "id": str(lead_id),
                    "client_id": str(client_id),
                    "campaign_id": str(campaign_id),
                    "first_name": f"TestLead{len(lead_ids) + 1}",
                    "last_name": "MockData",
                    "email": f"testlead{len(lead_ids) + 1}@mocktest.example",
                    "company": f"Test Company {len(lead_ids) + 1}",
                    "title": "Decision Maker",
                },
            )
            lead_ids.append(lead_id)

        return lead_ids

    async def _seed_exclusion_list(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> int:
        """
        Seed agency_exclusion_list with 8 rows.

        - 5 source='crm_client' (existing clients)
        - 2 source='crm_pipeline' (open deals)
        - 1 source='crm_lost_deal'
        """
        exclusions = [
            # 5 CRM Clients (existing customers)
            {
                "company_name": "Acme Corporation",
                "domain": "acme-corp.example",
                "source": "crm_client",
                "external_crm_id": "hubspot_12345",
                "notes": "MOCK_CRM: Long-standing client since 2023",
            },
            {
                "company_name": "TechVentures Pty Ltd",
                "domain": "techventures.example",
                "source": "crm_client",
                "external_crm_id": "hubspot_12346",
                "notes": "MOCK_CRM: SaaS industry client",
            },
            {
                "company_name": "Global Logistics AU",
                "domain": "globallogistics.example",
                "source": "crm_client",
                "external_crm_id": "hubspot_12347",
                "notes": "MOCK_CRM: Enterprise logistics client",
            },
            {
                "company_name": "HealthFirst Medical",
                "domain": "healthfirst.example",
                "source": "crm_client",
                "external_crm_id": "pipedrive_8891",
                "notes": "MOCK_CRM: Healthcare sector client",
            },
            {
                "company_name": "Sunrise Real Estate",
                "domain": "sunriserealty.example",
                "source": "crm_client",
                "external_crm_id": "close_4421",
                "notes": "MOCK_CRM: Property management client",
            },
            # 2 CRM Pipeline (open deals)
            {
                "company_name": "InnovateTech Solutions",
                "domain": "innovatetech.example",
                "source": "crm_pipeline",
                "external_crm_id": "hubspot_deal_7891",
                "notes": "MOCK_CRM: Open deal - proposal stage",
            },
            {
                "company_name": "Melbourne Manufacturing Co",
                "domain": "melbmfg.example",
                "source": "crm_pipeline",
                "external_crm_id": "hubspot_deal_7892",
                "notes": "MOCK_CRM: Open deal - negotiation stage",
            },
            # 1 CRM Lost Deal
            {
                "company_name": "Budget Builders Inc",
                "domain": "budgetbuilders.example",
                "source": "crm_lost_deal",
                "external_crm_id": "hubspot_deal_5001",
                "notes": "MOCK_CRM: Lost deal - chose competitor, cooling-off period",
            },
        ]

        for exc in exclusions:
            await db.execute(
                text("""
                    INSERT INTO agency_exclusion_list
                    (id, client_id, company_name, domain, source, external_crm_id, notes)
                    VALUES (:id, :client_id, :company_name, :domain, :source, :external_crm_id, :notes)
                    ON CONFLICT (client_id, domain) DO NOTHING
                """),
                {
                    "id": str(uuid4()),
                    "client_id": str(client_id),
                    **exc,
                },
            )

        return len(exclusions)

    async def _seed_deals(
        self,
        db: AsyncSession,
        client_id: UUID,
        lead_ids: list[UUID],
    ) -> int:
        """
        Seed deals table with 6 rows.

        - 2 closed_won (different industries, different values)
        - 2 closed_lost (with lost_reason populated)
        - 2 open/active
        """
        now = datetime.utcnow()

        deals = [
            # 2 Closed Won
            {
                "lead_id": str(lead_ids[0]),
                "name": "Enterprise SaaS Implementation",
                "value": Decimal("45000.00"),
                "stage": "closed_won",
                "won": True,
                "closed_at": now - timedelta(days=15),
                "days_to_close": 45,
                "probability": 100,
            },
            {
                "lead_id": str(lead_ids[1]),
                "name": "Manufacturing Automation Project",
                "value": Decimal("125000.00"),
                "stage": "closed_won",
                "won": True,
                "closed_at": now - timedelta(days=7),
                "days_to_close": 90,
                "probability": 100,
            },
            # 2 Closed Lost
            {
                "lead_id": str(lead_ids[2]),
                "name": "Retail POS System",
                "value": Decimal("28000.00"),
                "stage": "closed_lost",
                "won": False,
                "closed_at": now - timedelta(days=20),
                "days_to_close": 60,
                "lost_reason": "price_too_high",
                "lost_notes": "MOCK_CRM: Client went with cheaper offshore solution",
                "probability": 0,
            },
            {
                "lead_id": str(lead_ids[3]),
                "name": "Healthcare Integration",
                "value": Decimal("75000.00"),
                "stage": "closed_lost",
                "won": False,
                "closed_at": now - timedelta(days=10),
                "days_to_close": 120,
                "lost_reason": "chose_competitor",
                "lost_notes": "MOCK_CRM: Lost to major competitor with existing relationship",
                "probability": 0,
            },
            # 2 Open/Active
            {
                "lead_id": str(lead_ids[4]),
                "name": "Financial Services Platform",
                "value": Decimal("85000.00"),
                "stage": "proposal",
                "won": None,
                "closed_at": None,
                "days_to_close": None,
                "probability": 60,
            },
            {
                "lead_id": str(lead_ids[5]),
                "name": "Education Tech Solution",
                "value": Decimal("52000.00"),
                "stage": "negotiation",
                "won": None,
                "closed_at": None,
                "days_to_close": None,
                "probability": 75,
            },
        ]

        for deal in deals:
            await db.execute(
                text("""
                    INSERT INTO deals
                    (id, client_id, lead_id, name, value, currency, stage, probability,
                     won, closed_at, days_to_close, lost_reason, lost_notes)
                    VALUES (:id, :client_id, :lead_id, :name, :value, 'AUD', :stage, :probability,
                            :won, :closed_at, :days_to_close, :lost_reason, :lost_notes)
                """),
                {
                    "id": str(uuid4()),
                    "client_id": str(client_id),
                    "lead_id": deal["lead_id"],
                    "name": deal["name"],
                    "value": deal["value"],
                    "stage": deal["stage"],
                    "probability": deal["probability"],
                    "won": deal["won"],
                    "closed_at": deal.get("closed_at"),
                    "days_to_close": deal.get("days_to_close"),
                    "lost_reason": deal.get("lost_reason"),
                    "lost_notes": deal.get("lost_notes"),
                },
            )

        return len(deals)

    async def _seed_meetings(
        self,
        db: AsyncSession,
        client_id: UUID,
        lead_ids: list[UUID],
    ) -> int:
        """
        Seed meetings table with 3 rows.

        - 1 confirmed, showed_up=true, meeting_outcome='positive' (good)
        - 1 confirmed, showed_up=false (no show)
        - 1 scheduled, not yet confirmed
        """
        now = datetime.utcnow()

        meetings = [
            # 1 Confirmed + Showed Up (positive outcome)
            {
                "lead_id": str(lead_ids[0]),
                "booked_at": now - timedelta(days=5),
                "scheduled_at": now - timedelta(days=3),
                "meeting_type": "discovery",
                "confirmed": True,
                "confirmed_at": now - timedelta(days=4),
                "showed_up": True,
                "showed_up_confirmed_at": now - timedelta(days=3),
                "meeting_outcome": "good",
                "meeting_notes": "MOCK_CRM: Great initial conversation, strong interest in solution",
            },
            # 1 Confirmed + No Show
            {
                "lead_id": str(lead_ids[1]),
                "booked_at": now - timedelta(days=4),
                "scheduled_at": now - timedelta(days=2),
                "meeting_type": "demo",
                "confirmed": True,
                "confirmed_at": now - timedelta(days=3),
                "showed_up": False,
                "showed_up_confirmed_at": now - timedelta(days=2),
                "meeting_outcome": "no_show",
                "no_show_reason": "No response to follow-up attempts",
                "meeting_notes": "MOCK_CRM: Attempted reschedule twice, no reply",
            },
            # 1 Scheduled (future, not confirmed)
            {
                "lead_id": str(lead_ids[2]),
                "booked_at": now - timedelta(days=1),
                "scheduled_at": now + timedelta(days=3),
                "meeting_type": "discovery",
                "confirmed": False,
                "confirmed_at": None,
                "showed_up": None,
                "showed_up_confirmed_at": None,
                "meeting_outcome": None,
                "meeting_notes": "MOCK_CRM: Pending confirmation, reminder scheduled",
            },
        ]

        for meeting in meetings:
            await db.execute(
                text("""
                    INSERT INTO meetings
                    (id, client_id, lead_id, booked_at, scheduled_at, meeting_type,
                     confirmed, confirmed_at, showed_up, showed_up_confirmed_at,
                     meeting_outcome, no_show_reason, meeting_notes)
                    VALUES (:id, :client_id, :lead_id, :booked_at, :scheduled_at, :meeting_type,
                            :confirmed, :confirmed_at, :showed_up, :showed_up_confirmed_at,
                            :meeting_outcome, :no_show_reason, :meeting_notes)
                """),
                {
                    "id": str(uuid4()),
                    "client_id": str(client_id),
                    **meeting,
                },
            )

        return len(meetings)

    async def clear_mock_data(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict:
        """
        Clear mock CRM data for a client.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Dict with counts of deleted records
        """
        # Delete exclusions with MOCK_CRM marker
        result = await db.execute(
            text("""
                DELETE FROM agency_exclusion_list
                WHERE client_id = :client_id AND notes LIKE 'MOCK_CRM%'
            """),
            {"client_id": str(client_id)},
        )
        exclusion_deleted = result.rowcount

        # Delete test leads with mock marker
        result = await db.execute(
            text("""
                DELETE FROM leads
                WHERE client_id = :client_id AND email LIKE '%@mocktest.example'
            """),
            {"client_id": str(client_id)},
        )
        leads_deleted = result.rowcount

        await db.commit()

        logger.info(
            f"Cleared mock CRM data: {exclusion_deleted} exclusions, {leads_deleted} leads"
        )

        return {
            "status": "cleared",
            "exclusion_deleted": exclusion_deleted,
            "leads_deleted": leads_deleted,
        }


# Singleton instance
mock_crm_service = MockCRMService()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Seeds 8 agency_exclusion_list rows
#     - 5 source='crm_client'
#     - 2 source='crm_pipeline'
#     - 1 source='crm_lost_deal'
# [x] Seeds 6 deals rows
#     - 2 closed_won (different values/industries)
#     - 2 closed_lost (with lost_reason)
#     - 2 open/active
# [x] Seeds 3 meetings rows
#     - 1 confirmed + showed_up + positive outcome
#     - 1 confirmed + no-show
#     - 1 scheduled (not confirmed)
# [x] Idempotent (checks for existing mock data)
# [x] Clear method to remove mock data
# [x] All functions have type hints
# [x] All functions have docstrings
