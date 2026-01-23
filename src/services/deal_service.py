"""
Contract: src/services/deal_service.py
Purpose: Service for managing deals and downstream outcomes
Layer: 3 - services
Imports: models, exceptions
Consumers: orchestration, API routes, CIS detectors

FILE: src/services/deal_service.py
PURPOSE: Service for managing deals and downstream outcomes
PHASE: 24E (Downstream Outcomes)
TASK: OUTCOME-002
DEPENDENCIES:
  - src/models/database.py
LAYER: 3 (services)
CONSUMERS: orchestration, API routes, CIS detectors

This service manages deals through their lifecycle from creation
to close, tracking value, stages, and outcomes for CIS learning.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError


# Valid deal stages
DEAL_STAGES = [
    "qualification",
    "proposal",
    "negotiation",
    "verbal_commit",
    "contract_sent",
    "closed_won",
    "closed_lost",
]

# Valid lost reasons
LOST_REASONS = [
    "price_too_high",
    "chose_competitor",
    "no_budget",
    "timing_not_right",
    "no_decision",
    "champion_left",
    "project_cancelled",
    "went_silent",
    "bad_fit",
    "other",
]


class DealService:
    """
    Service for managing deals.

    Tracks deals through their lifecycle and provides
    analytics for CIS learning.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the Deal service.

        Args:
            session: Async database session
        """
        self.session = session

    async def create(
        self,
        client_id: UUID,
        lead_id: UUID,
        name: str,
        value: Decimal | float | None = None,
        currency: str = "AUD",
        meeting_id: UUID | None = None,
        stage: str = "qualification",
        expected_close_date: datetime | None = None,
        probability: int = 50,
        converting_activity_id: UUID | None = None,
        converting_channel: str | None = None,
        external_crm: str | None = None,
        external_deal_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new deal.

        Args:
            client_id: Client UUID
            lead_id: Lead UUID
            name: Deal name
            value: Deal value
            currency: Currency code
            meeting_id: Optional meeting that created this deal
            stage: Initial stage
            expected_close_date: Expected close date
            probability: Win probability (0-100)
            converting_activity_id: Activity that led to deal
            converting_channel: Channel that led to deal
            external_crm: External CRM name
            external_deal_id: External CRM deal ID

        Returns:
            Created deal record

        Raises:
            ValidationError: If inputs are invalid
        """
        if stage not in DEAL_STAGES:
            raise ValidationError(message=f"Invalid stage. Must be one of: {DEAL_STAGES}")

        if probability < 0 or probability > 100:
            raise ValidationError(message="Probability must be between 0 and 100")

        # Calculate touches before deal
        touches_query = text("""
            SELECT COUNT(*) as count, MIN(channel) as first_channel
            FROM activities
            WHERE lead_id = :lead_id
        """)
        touches_result = await self.session.execute(touches_query, {"lead_id": lead_id})
        touches_row = touches_result.fetchone()
        touches_before = touches_row.count if touches_row else 0
        first_channel = touches_row.first_channel if touches_row else None

        query = text("""
            INSERT INTO deals (
                client_id, lead_id, meeting_id, name, value, currency,
                stage, expected_close_date, probability,
                converting_activity_id, converting_channel, first_touch_channel,
                touches_before_deal, external_crm, external_deal_id,
                created_at, updated_at
            ) VALUES (
                :client_id, :lead_id, :meeting_id, :name, :value, :currency,
                :stage, :expected_close_date, :probability,
                :converting_activity_id, :converting_channel, :first_touch_channel,
                :touches_before_deal, :external_crm, :external_deal_id,
                NOW(), NOW()
            )
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "lead_id": lead_id,
            "meeting_id": meeting_id,
            "name": name,
            "value": value,
            "currency": currency,
            "stage": stage,
            "expected_close_date": expected_close_date,
            "probability": probability,
            "converting_activity_id": converting_activity_id,
            "converting_channel": converting_channel,
            "first_touch_channel": first_channel,
            "touches_before_deal": touches_before,
            "external_crm": external_crm,
            "external_deal_id": external_deal_id,
        })

        row = result.fetchone()
        await self.session.commit()

        if not row:
            return {}

        # Update lead with deal info
        await self.session.execute(
            text("""
                UPDATE leads SET
                    deal_id = :deal_id,
                    deal_value = :value,
                    updated_at = NOW()
                WHERE id = :lead_id
            """),
            {"deal_id": row.id, "value": value, "lead_id": lead_id}
        )
        await self.session.commit()

        return dict(row._mapping)

    async def get_by_id(self, deal_id: UUID) -> dict[str, Any] | None:
        """
        Get a deal by ID.

        Args:
            deal_id: Deal UUID

        Returns:
            Deal record or None if not found
        """
        query = text("""
            SELECT d.*, l.email as lead_email, l.first_name as lead_first_name,
                   l.last_name as lead_last_name, l.company as lead_company
            FROM deals d
            LEFT JOIN leads l ON l.id = d.lead_id
            WHERE d.id = :deal_id
        """)

        result = await self.session.execute(query, {"deal_id": deal_id})
        row = result.fetchone()

        if not row:
            return None

        return dict(row._mapping)

    async def get_by_external_id(
        self,
        external_crm: str,
        external_deal_id: str,
    ) -> dict[str, Any] | None:
        """
        Get a deal by external CRM ID.

        Args:
            external_crm: External CRM name
            external_deal_id: External deal ID

        Returns:
            Deal record or None if not found
        """
        query = text("""
            SELECT * FROM deals
            WHERE external_crm = :external_crm
            AND external_deal_id = :external_deal_id
        """)

        result = await self.session.execute(query, {
            "external_crm": external_crm,
            "external_deal_id": external_deal_id,
        })
        row = result.fetchone()

        if not row:
            return None

        return dict(row._mapping)

    async def update_stage(
        self,
        deal_id: UUID,
        stage: str,
        probability: int | None = None,
        notes: str | None = None,
        changed_by: str = "system",
    ) -> dict[str, Any]:
        """
        Update deal stage.

        The trigger will automatically:
        - Record stage history
        - Update stage_changed_at
        - Handle closing if stage is closed_won/closed_lost

        Args:
            deal_id: Deal UUID
            stage: New stage
            probability: Updated probability (optional)
            notes: Notes about the change
            changed_by: Who made the change

        Returns:
            Updated deal record

        Raises:
            NotFoundError: If deal not found
            ValidationError: If stage is invalid
        """
        if stage not in DEAL_STAGES:
            raise ValidationError(message=f"Invalid stage. Must be one of: {DEAL_STAGES}")

        deal = await self.get_by_id(deal_id)
        if not deal:
            raise NotFoundError(resource_type="deal", resource_id=str(deal_id))

        # Auto-adjust probability based on stage
        if probability is None:
            stage_probabilities = {
                "qualification": 20,
                "proposal": 40,
                "negotiation": 60,
                "verbal_commit": 80,
                "contract_sent": 90,
                "closed_won": 100,
                "closed_lost": 0,
            }
            probability = stage_probabilities.get(stage, deal.get("probability", 50))

        query = text("""
            UPDATE deals
            SET stage = :stage,
                probability = :probability,
                updated_at = NOW()
            WHERE id = :deal_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "deal_id": deal_id,
            "stage": stage,
            "probability": probability,
        })

        row = result.fetchone()
        await self.session.commit()

        if not row:
            return {}
        return dict(row._mapping)

    async def close_won(
        self,
        deal_id: UUID,
        value: Decimal | float | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Close a deal as won.

        Args:
            deal_id: Deal UUID
            value: Final deal value (optional update)
            notes: Closing notes

        Returns:
            Updated deal record
        """
        deal = await self.get_by_id(deal_id)
        if not deal:
            raise NotFoundError(resource_type="deal", resource_id=str(deal_id))

        update_value = value if value is not None else deal.get("value")

        query = text("""
            UPDATE deals
            SET stage = 'closed_won',
                won = TRUE,
                closed_at = NOW(),
                value = :value,
                probability = 100,
                updated_at = NOW()
            WHERE id = :deal_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "deal_id": deal_id,
            "value": update_value,
        })

        row = result.fetchone()
        await self.session.commit()

        if not row:
            return {}

        # Update lead with win
        await self.session.execute(
            text("""
                UPDATE leads SET
                    deal_won = TRUE,
                    deal_won_at = NOW(),
                    deal_value = :value,
                    status = 'converted',
                    updated_at = NOW()
                WHERE id = :lead_id
            """),
            {"value": update_value, "lead_id": deal["lead_id"]}
        )
        await self.session.commit()

        # Calculate revenue attribution
        await self.calculate_attribution(deal_id)

        return dict(row._mapping)

    async def close_lost(
        self,
        deal_id: UUID,
        lost_reason: str,
        lost_notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Close a deal as lost.

        Args:
            deal_id: Deal UUID
            lost_reason: Reason for losing
            lost_notes: Additional notes

        Returns:
            Updated deal record

        Raises:
            ValidationError: If lost_reason is invalid
        """
        if lost_reason not in LOST_REASONS:
            raise ValidationError(message=f"Invalid lost reason. Must be one of: {LOST_REASONS}")

        deal = await self.get_by_id(deal_id)
        if not deal:
            raise NotFoundError(resource_type="deal", resource_id=str(deal_id))

        query = text("""
            UPDATE deals
            SET stage = 'closed_lost',
                won = FALSE,
                closed_at = NOW(),
                lost_reason = :lost_reason,
                lost_notes = :lost_notes,
                probability = 0,
                updated_at = NOW()
            WHERE id = :deal_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "deal_id": deal_id,
            "lost_reason": lost_reason,
            "lost_notes": lost_notes,
        })

        row = result.fetchone()
        await self.session.commit()

        if not row:
            return {}
        return dict(row._mapping)

    async def update_value(
        self,
        deal_id: UUID,
        value: Decimal | float,
        currency: str | None = None,
    ) -> dict[str, Any]:
        """
        Update deal value.

        Args:
            deal_id: Deal UUID
            value: New deal value
            currency: Optional currency update

        Returns:
            Updated deal record
        """
        deal = await self.get_by_id(deal_id)
        if not deal:
            raise NotFoundError(resource_type="deal", resource_id=str(deal_id))

        if currency:
            query = text("""
                UPDATE deals
                SET value = :value, currency = :currency, updated_at = NOW()
                WHERE id = :deal_id
                RETURNING *
            """)
            result = await self.session.execute(query, {
                "deal_id": deal_id,
                "value": value,
                "currency": currency,
            })
        else:
            query = text("""
                UPDATE deals
                SET value = :value, updated_at = NOW()
                WHERE id = :deal_id
                RETURNING *
            """)
            result = await self.session.execute(query, {
                "deal_id": deal_id,
                "value": value,
            })

        row = result.fetchone()
        await self.session.commit()

        if not row:
            return {}

        # Update lead value
        await self.session.execute(
            text("UPDATE leads SET deal_value = :value WHERE id = :lead_id"),
            {"value": value, "lead_id": deal["lead_id"]}
        )
        await self.session.commit()

        return dict(row._mapping)

    async def list_for_client(
        self,
        client_id: UUID,
        stage: str | None = None,
        won: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        List deals for a client.

        Args:
            client_id: Client UUID
            stage: Optional stage filter
            won: Optional won/lost filter
            limit: Max results
            offset: Pagination offset

        Returns:
            List of deal records
        """
        conditions = ["d.client_id = :client_id"]
        params: dict[str, Any] = {
            "client_id": client_id,
            "limit": limit,
            "offset": offset,
        }

        if stage:
            conditions.append("d.stage = :stage")
            params["stage"] = stage

        if won is not None:
            conditions.append("d.won = :won")
            params["won"] = won

        query = text(f"""
            SELECT d.*, l.email as lead_email, l.first_name as lead_first_name,
                   l.last_name as lead_last_name, l.company as lead_company
            FROM deals d
            LEFT JOIN leads l ON l.id = d.lead_id
            WHERE {" AND ".join(conditions)}
            ORDER BY d.created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def get_pipeline(
        self,
        client_id: UUID,
    ) -> dict[str, Any]:
        """
        Get pipeline summary for a client.

        Args:
            client_id: Client UUID

        Returns:
            Pipeline summary with stage counts and values
        """
        query = text("""
            SELECT
                stage,
                COUNT(*) as count,
                COALESCE(SUM(value), 0) as total_value,
                ROUND(AVG(probability), 0) as avg_probability
            FROM deals
            WHERE client_id = :client_id
            AND stage NOT IN ('closed_won', 'closed_lost')
            GROUP BY stage
            ORDER BY
                CASE stage
                    WHEN 'qualification' THEN 1
                    WHEN 'proposal' THEN 2
                    WHEN 'negotiation' THEN 3
                    WHEN 'verbal_commit' THEN 4
                    WHEN 'contract_sent' THEN 5
                END
        """)

        result = await self.session.execute(query, {"client_id": client_id})
        rows = result.fetchall()

        stages: dict[str, dict[str, int | float]] = {row.stage: {
            "count": int(row.count) if row.count else 0,
            "total_value": float(row.total_value) if row.total_value else 0.0,
            "avg_probability": int(row.avg_probability) if row.avg_probability else 0,
        } for row in rows}

        # Calculate totals
        total_count = sum(int(s["count"]) for s in stages.values())
        total_value = sum(float(s["total_value"]) for s in stages.values())
        weighted_value = sum(
            float(s["total_value"]) * int(s["avg_probability"]) / 100
            for s in stages.values()
        )

        return {
            "stages": stages,
            "total_count": total_count,
            "total_value": total_value,
            "weighted_value": round(weighted_value, 2),
        }

    async def get_stage_history(
        self,
        deal_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        Get stage history for a deal.

        Args:
            deal_id: Deal UUID

        Returns:
            List of stage changes
        """
        query = text("""
            SELECT * FROM deal_stage_history
            WHERE deal_id = :deal_id
            ORDER BY changed_at ASC
        """)

        result = await self.session.execute(query, {"deal_id": deal_id})
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def calculate_attribution(
        self,
        deal_id: UUID,
        model: str = "first_touch",
    ) -> None:
        """
        Calculate revenue attribution for a deal.

        Args:
            deal_id: Deal UUID
            model: Attribution model (first_touch, last_touch, linear, time_decay)
        """
        query = text("""
            SELECT calculate_revenue_attribution(:deal_id, :model)
        """)

        await self.session.execute(query, {
            "deal_id": deal_id,
            "model": model,
        })
        await self.session.commit()

    async def get_funnel_analytics(
        self,
        client_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get funnel analytics for a client.

        Args:
            client_id: Client UUID
            days: Number of days to analyze

        Returns:
            Funnel analytics data
        """
        query = text("""
            SELECT * FROM get_funnel_analytics(:client_id, :days)
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "days": days,
        })
        row = result.fetchone()

        if not row:
            return {
                "total_leads": 0,
                "meetings_booked": 0,
                "meetings_showed": 0,
                "deals_created": 0,
                "deals_won": 0,
                "show_rate": 0,
                "deal_win_rate": 0,
            }

        return dict(row._mapping)

    async def get_channel_attribution(
        self,
        client_id: UUID,
        days: int = 90,
        model: str = "first_touch",
    ) -> list[dict[str, Any]]:
        """
        Get channel revenue attribution.

        Args:
            client_id: Client UUID
            days: Number of days to analyze
            model: Attribution model

        Returns:
            List of channel attribution data
        """
        query = text("""
            SELECT * FROM get_channel_revenue_attribution(:client_id, :days, :model)
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "days": days,
            "model": model,
        })
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def get_lost_analysis(
        self,
        client_id: UUID,
        days: int = 90,
    ) -> list[dict[str, Any]]:
        """
        Get lost deal analysis.

        Args:
            client_id: Client UUID
            days: Number of days to analyze

        Returns:
            List of lost reason analysis
        """
        query = text("""
            SELECT * FROM get_lost_deal_analysis(:client_id, :days)
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "days": days,
        })
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def sync_from_external(
        self,
        client_id: UUID,
        external_crm: str,
        external_deal_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Sync a deal from an external CRM.

        Creates or updates a deal based on external CRM data.

        Args:
            client_id: Client UUID
            external_crm: CRM name (hubspot, salesforce, pipedrive)
            external_deal_id: External deal ID
            data: Deal data from external CRM

        Returns:
            Created or updated deal record
        """
        # Check if deal exists
        existing = await self.get_by_external_id(external_crm, external_deal_id)

        # Map external stage to our stages
        stage_map = {
            # HubSpot
            "appointmentscheduled": "qualification",
            "qualifiedtobuy": "proposal",
            "presentationscheduled": "proposal",
            "decisionmakerboughtin": "negotiation",
            "contractsent": "contract_sent",
            "closedwon": "closed_won",
            "closedlost": "closed_lost",
            # Salesforce
            "prospecting": "qualification",
            "qualification": "qualification",
            "needs analysis": "qualification",
            "value proposition": "proposal",
            "id. decision makers": "negotiation",
            "perception analysis": "negotiation",
            "proposal/price quote": "proposal",
            "negotiation/review": "negotiation",
            "closed won": "closed_won",
            "closed lost": "closed_lost",
            # Pipedrive
            "lead in": "qualification",
            "contact made": "qualification",
            "proposal made": "proposal",
            "negotiations started": "negotiation",
        }

        external_stage = data.get("stage", "").lower()
        our_stage = stage_map.get(external_stage, "qualification")

        if existing:
            # Update existing deal
            won = None
            if our_stage == "closed_won":
                won = True
            elif our_stage == "closed_lost":
                won = False

            query = text("""
                UPDATE deals
                SET stage = :stage,
                    value = COALESCE(:value, value),
                    won = COALESCE(:won, won),
                    closed_at = CASE WHEN :stage IN ('closed_won', 'closed_lost') THEN COALESCE(closed_at, NOW()) ELSE closed_at END,
                    external_synced_at = NOW(),
                    updated_at = NOW()
                WHERE id = :deal_id
                RETURNING *
            """)

            result = await self.session.execute(query, {
                "deal_id": existing["id"],
                "stage": our_stage,
                "value": data.get("value"),
                "won": won,
            })

            row = result.fetchone()
            await self.session.commit()

            if not row:
                return {}
            return dict(row._mapping)
        else:
            # Need lead_id to create deal
            lead_id = data.get("lead_id")
            if not lead_id:
                # Try to find lead by email
                lead_email = data.get("contact_email")
                if lead_email:
                    lead_query = text("""
                        SELECT id FROM leads
                        WHERE client_id = :client_id AND email = :email
                        LIMIT 1
                    """)
                    lead_result = await self.session.execute(lead_query, {
                        "client_id": client_id,
                        "email": lead_email,
                    })
                    lead_row = lead_result.fetchone()
                    if lead_row:
                        lead_id = lead_row.id

            if not lead_id:
                raise ValidationError(
                    message="Cannot create deal without lead_id or matching contact_email"
                )

            # Create new deal
            return await self.create(
                client_id=client_id,
                lead_id=lead_id,
                name=data.get("name", f"Deal from {external_crm}"),
                value=data.get("value"),
                stage=our_stage,
                external_crm=external_crm,
                external_deal_id=external_deal_id,
            )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Session passed as argument
# [x] No imports from engines/integrations/orchestration
# [x] CRUD operations for deals
# [x] Stage management with automatic history
# [x] Close won/lost with proper updates
# [x] Pipeline summary
# [x] Funnel analytics integration
# [x] Channel attribution integration
# [x] Lost deal analysis integration
# [x] External CRM sync
# [x] Lead updates when deal changes
# [x] All functions have type hints
# [x] All functions have docstrings
