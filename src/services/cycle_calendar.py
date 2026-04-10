"""
Contract: src/services/cycle_calendar.py
Purpose: Per-customer cycle calendar — maps cycle days to calendar dates,
         handles weekends, AU public holidays, Friday reduction, Monday boost.
Layer: services
Imports: stdlib, holidays
Consumers: sequence_engine, orchestration
"""
import holidays
from datetime import date, timedelta
from typing import Optional


AU_HOLIDAYS = holidays.Australia()


class CycleCalendar:
    def __init__(self, cycle_start_date: date, customer_state: str = "NSW"):
        self.start_date = cycle_start_date
        self.state = customer_state
        self._state_holidays = holidays.Australia(state=customer_state)

    def cycle_day_to_date(self, cycle_day: int) -> date:
        """Given cycle day N (1-based), return the calendar date."""
        current_date = self.start_date
        days_counted = 1
        while days_counted < cycle_day:
            current_date += timedelta(days=1)
            if self.is_working_day(current_date):
                days_counted += 1
        return current_date

    def is_working_day(self, d: date) -> bool:
        """Is this a working day? (not weekend, not public holiday in customer's state)"""
        if d.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        if d in self._state_holidays:
            return False
        return True

    def get_day_volume_multiplier(self, d: date) -> float:
        """Volume multiplier for this calendar day."""
        dow = d.weekday()
        if dow == 0:
            return 1.20  # Monday
        if dow == 1:
            return 1.10  # Tuesday
        if dow == 2:
            return 1.05  # Wednesday
        if dow == 3:
            return 1.05  # Thursday
        if dow == 4:
            return 0.60  # Friday
        return 0.0  # Weekend

    def get_working_days_in_cycle(self, target_days: int = 30) -> int:
        """Count how many calendar days it takes to get target_days working days."""
        count = 0
        d = self.start_date
        working = 0
        while working < target_days:
            if self.is_working_day(d):
                working += 1
            d += timedelta(days=1)
            count += 1
        return count

    def next_working_day(self, d: date) -> date:
        """Return the next working day on or after d."""
        while not self.is_working_day(d):
            d += timedelta(days=1)
        return d
