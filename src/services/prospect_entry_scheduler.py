"""
Contract: src/services/prospect_entry_scheduler.py
Purpose: Distributes cycle's target prospects across working days
Layer: services
Imports: models, integrations
Consumers: orchestration only
"""
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.cycle_calendar import CycleCalendar


class ProspectEntryScheduler:
    """Distributes prospects across cycle working days with weekly rhythm."""

    def calculate_daily_entries(
        self,
        target_total: int,
        calendar: 'CycleCalendar',
        cycle_start: date,
        total_working_days: int = 22,
    ) -> dict[int, int]:
        """
        Returns {cycle_day: num_prospects_to_enter} for each working day.
        Applies weekly distribution (Mon 120%, Fri 60%).
        """
        base_rate = target_total / total_working_days

        schedule: dict[int, int] = {}
        total_allocated = 0

        for day in range(1, total_working_days + 1):
            cal_date = calendar.cycle_day_to_date(day)
            multiplier = calendar.get_day_volume_multiplier(cal_date)
            count = round(base_rate * multiplier)
            schedule[day] = count
            total_allocated += count

        # Adjust for rounding — distribute remainder across Tue-Thu
        remainder = target_total - total_allocated
        if remainder != 0:
            mid_days = [
                d for d in schedule
                if calendar.cycle_day_to_date(d).weekday() in (1, 2, 3)
            ]
            for d in mid_days:
                if remainder == 0:
                    break
                if remainder > 0:
                    schedule[d] += 1
                    remainder -= 1
                else:
                    schedule[d] -= 1
                    remainder += 1

        return schedule

    async def get_prospects_for_today(
        self,
        cycle_id: str,
        cycle_day: int,
        count: int,
        db=None,
    ) -> list:
        """
        Pull `count` prospects from the pool that haven't been assigned
        to this cycle yet. Sorted by composite score (highest first).

        Production query:
            SELECT lp.* FROM lead_pool lp
            WHERE lp.client_id = (SELECT client_id FROM cycles WHERE id = cycle_id)
            AND NOT EXISTS (
                SELECT 1 FROM cycle_prospects cp
                WHERE cp.prospect_id = lp.id AND cp.cycle_id = cycle_id
            )
            ORDER BY lp.propensity_score DESC
            LIMIT count
            FOR UPDATE SKIP LOCKED
        """
        return []
