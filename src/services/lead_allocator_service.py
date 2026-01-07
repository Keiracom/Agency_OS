"""
FILE: src/services/lead_allocator_service.py
PURPOSE: Allocate leads from pool to clients with exclusive assignment
PHASE: 24A (Lead Pool Architecture)
TASK: POOL-006
DEPENDENCIES:
  - src/services/lead_pool_service.py
  - src/models/database.py
LAYER: 3 (services)
CONSUMERS: orchestration, API routes

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

        # Assign each lead
        assigned_leads = []
        for lead in leads_to_assign:
            lead_pool_id = lead.id

            # Create assignment
            assign_query = text("""
                INSERT INTO lead_assignments (
                    lead_pool_id, client_id, campaign_id,
                    assigned_by, assignment_reason
                ) VALUES (
                    :lead_pool_id, :client_id, :campaign_id,
                    'allocator', :reason
                )
                ON CONFLICT (lead_pool_id) DO NOTHING
                RETURNING *
            """)

            assign_result = await self.session.execute(
                assign_query,
                {
                    "lead_pool_id": str(lead_pool_id),
                    "client_id": str(client_id),
                    "campaign_id": str(campaign_id) if campaign_id else None,
                    "reason": f"ICP match: {icp_criteria.get('industries', ['any'])[0] if icp_criteria.get('industries') else 'general'}",
                }
            )
            assignment = assign_result.fetchone()

            if assignment:
                # Update pool status
                await self.session.execute(
                    text("""
                    UPDATE lead_pool
                    SET pool_status = 'assigned', updated_at = NOW()
                    WHERE id = :id
                    """),
                    {"id": str(lead_pool_id)}
                )

                assigned_leads.append({
                    "lead_pool_id": str(lead_pool_id),
                    "assignment_id": str(assignment.id),
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
        Get assignment for a lead.

        Args:
            lead_pool_id: Lead pool ID
            client_id: Optional client filter

        Returns:
            Assignment record or None
        """
        conditions = ["lead_pool_id = :lead_pool_id", "status = 'active'"]
        params: dict[str, Any] = {"lead_pool_id": str(lead_pool_id)}

        if client_id:
            conditions.append("client_id = :client_id")
            params["client_id"] = str(client_id)

        query = text(f"""
            SELECT * FROM lead_assignments
            WHERE {" AND ".join(conditions)}
        """)

        result = await self.session.execute(query, params)
        row = result.fetchone()

        return dict(row._mapping) if row else None

    async def get_client_assignments(
        self,
        client_id: UUID,
        status: str = "active",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get all assignments for a client.

        Args:
            client_id: Client ID
            status: Filter by status (active, released, converted)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of assignments with lead data
        """
        query = text("""
            SELECT la.*, lp.email, lp.first_name, lp.last_name,
                   lp.title, lp.company_name, lp.company_industry,
                   lp.seniority, lp.linkedin_url
            FROM lead_assignments la
            JOIN lead_pool lp ON lp.id = la.lead_pool_id
            WHERE la.client_id = :client_id
            AND la.status = :status
            ORDER BY la.assigned_at DESC
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
        assignment_id: UUID,
        reason: str = "manual"
    ) -> bool:
        """
        Release a lead back to the pool.

        Args:
            assignment_id: Assignment ID
            reason: Release reason

        Returns:
            True if released
        """
        # Get assignment first
        query = text("""
            SELECT lead_pool_id FROM lead_assignments
            WHERE id = :id AND status = 'active'
        """)
        result = await self.session.execute(
            query,
            {"id": str(assignment_id)}
        )
        row = result.fetchone()

        if not row:
            return False

        lead_pool_id = row.lead_pool_id

        # Update assignment
        await self.session.execute(
            text("""
            UPDATE lead_assignments
            SET status = 'released',
                released_at = NOW(),
                release_reason = :reason,
                updated_at = NOW()
            WHERE id = :id
            """),
            {"id": str(assignment_id), "reason": reason}
        )

        # Update pool status
        await self.session.execute(
            text("""
            UPDATE lead_pool
            SET pool_status = 'available', updated_at = NOW()
            WHERE id = :id
            """),
            {"id": str(lead_pool_id)}
        )

        await self.session.commit()
        return True

    async def mark_converted(
        self,
        assignment_id: UUID,
        conversion_type: str = "meeting_booked"
    ) -> bool:
        """
        Mark a lead as converted.

        Converted leads stay with the client forever.

        Args:
            assignment_id: Assignment ID
            conversion_type: Type of conversion

        Returns:
            True if marked
        """
        # Get assignment first
        query = text("""
            SELECT lead_pool_id FROM lead_assignments
            WHERE id = :id AND status = 'active'
        """)
        result = await self.session.execute(
            query,
            {"id": str(assignment_id)}
        )
        row = result.fetchone()

        if not row:
            return False

        lead_pool_id = row.lead_pool_id

        # Update assignment
        await self.session.execute(
            text("""
            UPDATE lead_assignments
            SET status = 'converted',
                converted_at = NOW(),
                conversion_type = :conversion_type,
                updated_at = NOW()
            WHERE id = :id
            """),
            {"id": str(assignment_id), "conversion_type": conversion_type}
        )

        # Update pool status
        await self.session.execute(
            text("""
            UPDATE lead_pool
            SET pool_status = 'converted', updated_at = NOW()
            WHERE id = :id
            """),
            {"id": str(lead_pool_id)}
        )

        await self.session.commit()
        return True

    async def record_touch(
        self,
        assignment_id: UUID,
        channel: str,
    ) -> bool:
        """
        Record a touch (outreach) for an assignment.

        Args:
            assignment_id: Assignment ID
            channel: Channel used (email, sms, linkedin, etc.)

        Returns:
            True if recorded
        """
        query = text("""
            UPDATE lead_assignments
            SET total_touches = total_touches + 1,
                channels_used = array_append(
                    CASE WHEN :channel = ANY(channels_used)
                         THEN channels_used
                         ELSE channels_used
                    END,
                    CASE WHEN :channel = ANY(channels_used)
                         THEN NULL
                         ELSE :channel::channel_type
                    END
                ),
                first_contacted_at = COALESCE(first_contacted_at, NOW()),
                last_contacted_at = NOW(),
                updated_at = NOW()
            WHERE id = :id AND status = 'active'
            RETURNING id
        """)

        result = await self.session.execute(
            query,
            {"id": str(assignment_id), "channel": channel}
        )
        row = result.fetchone()
        await self.session.commit()

        return row is not None

    async def record_reply(
        self,
        assignment_id: UUID,
        intent: str,
    ) -> bool:
        """
        Record a reply from the lead.

        Args:
            assignment_id: Assignment ID
            intent: Reply intent (interested, not_interested, etc.)

        Returns:
            True if recorded
        """
        query = text("""
            UPDATE lead_assignments
            SET has_replied = TRUE,
                replied_at = NOW(),
                reply_intent = :intent,
                updated_at = NOW()
            WHERE id = :id AND status = 'active'
            RETURNING id
        """)

        result = await self.session.execute(
            query,
            {"id": str(assignment_id), "intent": intent}
        )
        row = result.fetchone()
        await self.session.commit()

        return row is not None

    async def set_cooling_period(
        self,
        assignment_id: UUID,
        days: int = 7,
    ) -> bool:
        """
        Set a cooling period for an assignment.

        During cooling, no outreach is allowed.

        Args:
            assignment_id: Assignment ID
            days: Cooling period in days

        Returns:
            True if set
        """
        cooling_until = datetime.now() + timedelta(days=days)

        query = text("""
            UPDATE lead_assignments
            SET cooling_until = :cooling_until,
                updated_at = NOW()
            WHERE id = :id AND status = 'active'
            RETURNING id
        """)

        result = await self.session.execute(
            query,
            {"id": str(assignment_id), "cooling_until": cooling_until}
        )
        row = result.fetchone()
        await self.session.commit()

        return row is not None

    async def get_client_stats(self, client_id: UUID) -> dict[str, Any]:
        """
        Get assignment statistics for a client.

        Args:
            client_id: Client ID

        Returns:
            Assignment statistics
        """
        query = text("""
            SELECT * FROM v_client_assignment_stats
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
                "total_assignments": 0,
                "active_assignments": 0,
                "converted_assignments": 0,
                "released_assignments": 0,
                "replied_leads": 0,
                "total_touches": 0,
                "avg_touches_per_lead": 0,
            }

        return dict(row._mapping)

    async def release_client_leads(
        self,
        client_id: UUID,
        reason: str = "client_cancelled"
    ) -> int:
        """
        Release all leads for a client (e.g., subscription cancelled).

        Args:
            client_id: Client ID
            reason: Release reason

        Returns:
            Number of leads released
        """
        # Get all active assignments
        query = text("""
            UPDATE lead_assignments
            SET status = 'released',
                released_at = NOW(),
                release_reason = :reason,
                updated_at = NOW()
            WHERE client_id = :client_id
            AND status = 'active'
            RETURNING lead_pool_id
        """)

        result = await self.session.execute(
            query,
            {"client_id": str(client_id), "reason": reason}
        )
        released = result.fetchall()

        if released:
            # Update pool status for all released leads
            lead_ids = [str(r.lead_pool_id) for r in released]
            await self.session.execute(
                text("""
                UPDATE lead_pool
                SET pool_status = 'available', updated_at = NOW()
                WHERE id = ANY(:ids)
                """),
                {"ids": lead_ids}
            )

        await self.session.commit()
        return len(released)


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] Layer 3 placement (same as engines)
# [x] allocate_leads with ICP matching
# [x] get_assignment for single lead lookup
# [x] get_client_assignments for client dashboard
# [x] release_lead back to pool
# [x] mark_converted for conversions
# [x] record_touch for outreach tracking
# [x] record_reply for reply tracking
# [x] set_cooling_period for lead cooling
# [x] get_client_stats for analytics
# [x] release_client_leads for subscription cancellation
# [x] FOR UPDATE SKIP LOCKED for race condition prevention
# [x] No hardcoded credentials
# [x] All methods async
# [x] All methods have type hints
# [x] All methods have docstrings
