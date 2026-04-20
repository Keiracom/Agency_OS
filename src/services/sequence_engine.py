"""
Contract: src/services/sequence_engine.py
Purpose: JSONB-driven sequence template engine. Given a prospect entering outreach
         on cycle day N, calculates all scheduled_at timestamps for every step.
Layer: services
Imports: stdlib, src.models
Consumers: orchestration
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cycle import OutreachAction, SequenceTemplate

if TYPE_CHECKING:
    from src.models.cycle import Cycle, CycleProspect
    from src.services.cycle_calendar import CycleCalendar
    from src.services.time_window_engine import TimeWindowEngine


class SequenceEngine:
    async def load_template(self, db: AsyncSession, template_name: str) -> dict[str, Any]:
        """Fetch a sequence template from the DB by name."""
        result = await db.execute(
            select(SequenceTemplate).where(SequenceTemplate.name == template_name)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ValueError(f"Sequence template not found: {template_name!r}")
        return {"name": row.name, "sequence_type": row.sequence_type, "steps": row.steps}

    async def schedule_prospect(
        self,
        cycle: "Cycle",
        prospect: "CycleProspect",
        calendar: "CycleCalendar",
        template: dict[str, Any],
        time_window_engine: "TimeWindowEngine",
        prospect_timezone: str = "Australia/Sydney",
    ) -> list[OutreachAction]:
        """Generate all outreach_actions for a prospect entering the cycle."""
        actions: list[OutreachAction] = []

        for step in template["steps"]:
            target_cycle_day = prospect.entered_cycle_on_day + step["day_offset"]
            target_date = calendar.cycle_day_to_date(target_cycle_day)

            scheduled_at = time_window_engine.get_time(
                window=step["window"],
                target_date=target_date,
                prospect_timezone=prospect_timezone,
                channel=step["channel"],
            )

            actions.append(
                OutreachAction(
                    cycle_id=cycle.id,
                    cycle_prospect_id=prospect.id,
                    prospect_id=prospect.prospect_id,
                    channel=step["channel"],
                    action_type=step["action_type"],
                    step_number=step["step"],
                    scheduled_at=scheduled_at,
                    status="scheduled",
                    dry_run=True,
                )
            )

        return actions

    async def bulk_schedule(
        self,
        db: AsyncSession,
        cycle: "Cycle",
        prospects: list["CycleProspect"],
        calendar: "CycleCalendar",
        time_window_engine: "TimeWindowEngine",
    ) -> list[OutreachAction]:
        """Schedule all prospects in a cycle. Loads template once per sequence_type."""
        template_cache: dict[str, dict[str, Any]] = {}
        all_actions: list[OutreachAction] = []

        for prospect in prospects:
            seq_type = prospect.sequence_type
            if seq_type not in template_cache:
                template_cache[seq_type] = await self.load_template(db, seq_type)
            template = template_cache[seq_type]

            actions = await self.schedule_prospect(
                cycle=cycle,
                prospect=prospect,
                calendar=calendar,
                template=template,
                time_window_engine=time_window_engine,
            )
            all_actions.extend(actions)

        return all_actions
