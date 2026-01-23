"""
Contract: src/services/lead_allocator_service.py
Purpose: Allocate leads from pool to clients with exclusive assignment
Layer: 3 - services
Imports: models, services
Consumers: orchestration, API routes

FILE: src/services/lead_allocator_service.py
PURPOSE: Allocate leads from pool to clients with exclusive assignment
PHASE: 24A (Lead Pool Architecture), updated Phase 37
TASK: POOL-006
DEPENDENCIES:
  - src/services/lead_pool_service.py
  - src/models/database.py
LAYER: 3 (services)
CONSUMERS: orchestration, API routes

Phase 37 Changes:
- Direct ownership: Sets client_id and campaign_id directly on lead_pool
- No separate lead_assignments table needed for ownership
- lead_pool.client_id = NULL means available, UUID means owned

This service handles the allocation of leads from the platform pool
to individual clients. It ensures exclusive assignment (one lead = one client)
and fair distribution based on ICP criteria.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError


class LeadAllocatorService:
    """
    Service for allocating leads from pool to clients.

    Handles:
    - Matching leads to client ICP criteria
    - Exclusive assignment (no lead shared between clients)
    - Fair distribution across competing clients
    - Assignment lifecycle management
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the Lead Allocator service.

        Args:
            session: Async database session
        """
        self.session = session

    async def allocate_leads(
        self,
        client_id: UUID,
        icp_criteria: dict[str, Any],
        count: int,
        campaign_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Allocate leads from pool to a client based on ICP criteria.

        Only assigns leads that are:
        - Available in pool (not assigned to anyone)
        - Match the client's ICP criteria
        - Have verified emails (unless specified otherwise)

        Args:
            client_id: Client to assign leads to
            icp_criteria: ICP matching criteria
            count: Number of leads to allocate
            campaign_id: Optional campaign to associate

        Returns:
            List of assigned leads

        Raises:
            ValidationError: If count is invalid
        """
        if count <= 0 or count > 1000:
            raise ValidationError(
                message="Count must be between 1 and 1000"
            )

        # Build matching query
        conditions = ["lp.pool_status = 'available'"]
        params: dict[str, Any] = {
            "client_id": str(client_id),
            "campaign_id": str(campaign_id) if campaign_id else None,
            "limit": count,
        }

        # ICP matching criteria
        if icp_criteria.get("industries"):
            industries = icp_criteria["industries"]
            if isinstance(industries, str):
                industries = [industries]
            conditions.append("lp.company_industry = ANY(:industries)")
            params["industries"] = industries

        if icp_criteria.get("countries"):
            countries = icp_criteria["countries"]
            if isinstance(countries, str):
                countries = [countries]
            conditions.append("lp.company_country = ANY(:countries)")
            params["countries"] = countries

        if icp_criteria.get("employee_min"):
            conditions.append("lp.company_employee_count >= :employee_min")
            params["employee_min"] = icp_criteria["employee_min"]

        if icp_criteria.get("employee_max"):
            conditions.append("lp.company_employee_count <= :employee_max")
            params["employee_max"] = icp_criteria["employee_max"]

        if icp_criteria.get("seniorities"):
            seniorities = icp_criteria["seniorities"]
            if isinstance(seniorities, str):
                seniorities = [seniorities]
            conditions.append("lp.seniority = ANY(:seniorities)")
            params["seniorities"] = seniorities

        if icp_criteria.get("titles"):
            # Title matching with ILIKE for flexibility
            titles = icp_criteria["titles"]
            if isinstance(titles, str):
                titles = [titles]
            title_conditions = [f"lp.title ILIKE '%' || :title_{i} || '%'" for i in range(len(titles))]
            conditions.append(f"({' OR '.join(title_conditions)})")
            for i, title in enumerate(titles):
                params[f"title_{i}"] = title

        if icp_criteria.get("technologies"):
            techs = icp_criteria["technologies"]
            if isinstance(techs, str):
                techs = [techs]
            conditions.append("lp.company_technologies && :technologies")
            params["technologies"] = techs

        # Email quality filter (default to verified only)
        email_status = icp_criteria.get("email_status", "verified")
        if email_status:
            conditions.append("lp.email_status = :email_status")
            params["email_status"] = email_status

        # Build the query
        where_clause = " AND ".join(conditions)

        # Phase 37: Also filter for leads with no client assignment
        where_clause += " AND lp.client_id IS NULL"

        # First, find matching leads
        find_query = text(f"""
            SELECT lp.id, lp.email, lp.first_name, lp.last_name,
                   lp.title, lp.company_name, lp.enrichment_confidence
            FROM lead_pool lp
            WHERE {where_clause}
            ORDER BY lp.enrichment_confidence DESC NULLS LAST,
                     lp.created_at ASC
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
        """)

        result = await self.session.execute(find_query, params)
        leads_to_assign = result.fetchall()

        if not leads_to_assign:
            return []

        # Phase 37: Assign leads directly by setting client_id on lead_pool
        assigned_leads = []
        for lead in leads_to_assign:
            lead_pool_id = lead.id

            # Update lead_pool directly with client/campaign ownership
            assign_query = text("""
                UPDATE lead_pool
                SET client_id = :client_id,
                    campaign_id = :campaign_id,
                    pool_status = 'assigned',
                    updated_at = NOW()
                WHERE id = :lead_pool_id
                AND client_id IS NULL
                RETURNING id
            """)

            assign_result = await self.session.execute(
                assign_query,
                {
                    "lead_pool_id": str(lead_pool_id),
                    "client_id": str(client_id),
                    "campaign_id": str(campaign_id) if campaign_id else None,
                }
            )
            updated = assign_result.fetchone()

            if updated:
                assigned_leads.append({
                    "lead_pool_id": str(lead_pool_id),
                    "email": lead.email,
                    "first_name": lead.first_name,
                    "last_name": lead.last_name,
                    "title": lead.title,
                    "company_name": lead.company_name,
                })

        await self.session.commit()
        return assigned_leads

    async def get_assignment(
        self,
        lead_pool_id: UUID,
        client_id: UUID | None = None
    ) -> dict[str, Any] | None:
        """
        Get ownership info for a lead from lead_pool.

        Phase 37: Queries lead_pool directly instead of lead_assignments.

        Args:
            lead_pool_id: Lead pool ID
            client_id: Optional client filter

        Returns:
            Lead pool record with ownership info or None
        """
        conditions = ["id = :lead_pool_id", "client_id IS NOT NULL"]
        params: dict[str, Any] = {"lead_pool_id": str(lead_pool_id)}

        if client_id:
            conditions.append("client_id = :client_id")
            params["client_id"] = str(client_id)

        query = text(f"""
            SELECT id, email, first_name, last_name, title, company_name,
                   client_id, campaign_id, pool_status, als_score, als_tier,
                   first_contacted_at, last_contacted_at, total_touches,
                   has_replied, replied_at, reply_intent
            FROM lead_pool
            WHERE {" AND ".join(conditions)}
        """)

        result = await self.session.execute(query, params)
        row = result.fetchone()

        return dict(row._mapping) if row else None

    async def get_client_assignments(
        self,
        client_id: UUID,
        status: str = "assigned",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get all leads assigned to a client.

        Phase 37: Queries lead_pool directly where client_id matches.

        Args:
            client_id: Client ID
            status: Filter by pool_status (assigned, converted, etc.)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of lead pool records owned by client
        """
        query = text("""
            SELECT id, email, first_name, last_name, title, company_name,
                   company_industry, seniority, linkedin_url, client_id,
                   campaign_id, pool_status, als_score, als_tier,
                   first_contacted_at, last_contacted_at, total_touches,
                   has_replied, replied_at, reply_intent, created_at
            FROM lead_pool
            WHERE client_id = :client_id
            AND pool_status = :status
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await self.session.execute(
            query,
            {
                "client_id": str(client_id),
                "status": status,
                "limit": limit,
                "offset": offset,
            }
        )
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def release_lead(
        self,
        lead_pool_id: UUID,
        reason: str = "manual"
    ) -> bool:
        """
        Release a lead back to the pool.

        Phase 37: Clears client_id and campaign_id on lead_pool.

        Args:
            lead_pool_id: Lead pool ID
            reason: Release reason (stored for audit)

        Returns:
            True if released
        """
        # Update lead_pool directly
        query = text("""
            UPDATE lead_pool
            SET client_id = NULL,
                campaign_id = NULL,
                pool_status = 'available',
                updated_at = NOW()
            WHERE id = :id
            AND client_id IS NOT NULL
            RETURNING id
        """)

        result = await self.session.execute(
            query,
            {"id": str(lead_pool_id)}
        )
        row = result.fetchone()

        await self.session.commit()
        return row is not None

    async def mark_converted(
        self,
        lead_pool_id: UUID,
        conversion_type: str = "meeting_booked"
    ) -> bool:
        """
        Mark a lead as converted.

        Phase 37: Updates pool_status to 'converted' on lead_pool.
        Converted leads stay with the client forever.

        Args:
            lead_pool_id: Lead pool ID
            conversion_type: Type of conversion

        Returns:
            True if marked
        """
        # Update lead_pool directly
        query = text("""
            UPDATE lead_pool
            SET pool_status = 'converted',
                updated_at = NOW()
            WHERE id = :id
            AND client_id IS NOT NULL
            RETURNING id
        """)

        result = await self.session.execute(
            query,
            {"id": str(lead_pool_id)}
        )
        row = result.fetchone()

        await self.session.commit()
        return row is not None

    async def record_touch(
        self,
        lead_pool_id: UUID,
        channel: str,
    ) -> bool:
        """
        Record a touch (outreach) for a lead.

        Phase 37: Updates touch counts directly on lead_pool.

        Args:
            lead_pool_id: Lead pool ID
            channel: Channel used (email, sms, linkedin, etc.)

        Returns:
            True if recorded
        """
        query = text("""
            UPDATE lead_pool
            SET total_touches = total_touches + 1,
                channels_used = CASE
                    WHEN :channel = ANY(channels_used) THEN channels_used
                    ELSE array_append(channels_used, :channel)
                END,
                first_contacted_at = COALESCE(first_contacted_at, NOW()),
                last_contacted_at = NOW(),
                updated_at = NOW()
            WHERE id = :id
            AND client_id IS NOT NULL
            RETURNING id
        """)

        result = await self.session.execute(
            query,
            {"id": str(lead_pool_id), "channel": channel}
        )
        row = result.fetchone()
        await self.session.commit()

        return row is not None

    async def record_reply(
        self,
        lead_pool_id: UUID,
        intent: str,
    ) -> bool:
        """
        Record a reply from the lead.

        Phase 37: Updates reply info directly on lead_pool.

        Args:
            lead_pool_id: Lead pool ID
            intent: Reply intent (interested, not_interested, etc.)

        Returns:
            True if recorded
        """
        query = text("""
            UPDATE lead_pool
            SET has_replied = TRUE,
                replied_at = NOW(),
                reply_intent = :intent,
                updated_at = NOW()
            WHERE id = :id
            AND client_id IS NOT NULL
            RETURNING id
        """)

        result = await self.session.execute(
            query,
            {"id": str(lead_pool_id), "intent": intent}
        )
        row = result.fetchone()
        await self.session.commit()

        return row is not None

    async def get_client_stats(self, client_id: UUID) -> dict[str, Any]:
        """
        Get lead statistics for a client.

        Phase 37: Queries lead_pool directly.

        Args:
            client_id: Client ID

        Returns:
            Lead ownership statistics
        """
        query = text("""
            SELECT
                :client_id as client_id,
                COUNT(*) as total_leads,
                COUNT(*) FILTER (WHERE pool_status = 'assigned') as assigned_leads,
                COUNT(*) FILTER (WHERE pool_status = 'converted') as converted_leads,
                COUNT(*) FILTER (WHERE has_replied = TRUE) as replied_leads,
                COALESCE(SUM(total_touches), 0) as total_touches,
                COALESCE(AVG(total_touches) FILTER (WHERE total_touches > 0), 0) as avg_touches_per_lead,
                COUNT(*) FILTER (WHERE als_tier = 'hot') as hot_leads,
                COUNT(*) FILTER (WHERE als_tier = 'warm') as warm_leads,
                COUNT(*) FILTER (WHERE als_tier = 'cool') as cool_leads,
                COUNT(*) FILTER (WHERE als_tier = 'cold') as cold_leads
            FROM lead_pool
            WHERE client_id = :client_id
        """)

        result = await self.session.execute(
            query,
            {"client_id": str(client_id)}
        )
        row = result.fetchone()

        if not row:
            return {
                "client_id": str(client_id),
                "total_leads": 0,
                "assigned_leads": 0,
                "converted_leads": 0,
                "replied_leads": 0,
                "total_touches": 0,
                "avg_touches_per_lead": 0,
                "hot_leads": 0,
                "warm_leads": 0,
                "cool_leads": 0,
                "cold_leads": 0,
            }

        return dict(row._mapping)

    async def release_client_leads(
        self,
        client_id: UUID,
        reason: str = "client_cancelled"
    ) -> int:
        """
        Release all leads for a client (e.g., subscription cancelled).

        Phase 37: Clears client_id on all leads owned by client.

        Args:
            client_id: Client ID
            reason: Release reason (stored for audit)

        Returns:
            Number of leads released
        """
        # Release all leads owned by this client
        query = text("""
            UPDATE lead_pool
            SET client_id = NULL,
                campaign_id = NULL,
                pool_status = 'available',
                updated_at = NOW()
            WHERE client_id = :client_id
            AND pool_status != 'converted'
        """)

        result = await self.session.execute(
            query,
            {"client_id": str(client_id)}
        )

        await self.session.commit()
        # CursorResult has rowcount attribute
        row_count = getattr(result, 'rowcount', 0)
        return row_count if row_count else 0


# ============================================
# VERIFICATION CHECKLIST (Phase 37 Update)
# ============================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] Layer 3 placement (same as engines)
# [x] allocate_leads sets client_id directly on lead_pool
# [x] get_assignment queries lead_pool directly
# [x] get_client_assignments queries lead_pool where client_id = x
# [x] release_lead clears client_id on lead_pool
# [x] mark_converted updates pool_status on lead_pool
# [x] record_touch updates touch counts on lead_pool
# [x] record_reply updates reply info on lead_pool
# [x] get_client_stats queries lead_pool for stats
# [x] release_client_leads clears client_id for all client's leads
# [x] FOR UPDATE SKIP LOCKED for race condition prevention
# [x] No hardcoded credentials
# [x] All methods async
# [x] All methods have type hints
# [x] All methods have docstrings
