---
name: Fix 15 - Business Hours Validation
description: Adds business hours check before placing calls
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 15: Business Hours Validation

## Gap Reference
- **TODO.md Item:** #15
- **Priority:** P3 Medium (Voice Engine)
- **Location:** `src/engines/voice.py`
- **Issue:** No check before placing calls

## Pre-Flight Checks

1. Check existing timing logic:
   ```bash
   grep -rn "business.*hour\|timing\|schedule" src/engines/voice.py
   ```

2. Check timing engine:
   ```bash
   grep -rn "business.*hour" src/engines/timing.py
   ```

3. Review VOICE.md for business hours rules:
   ```bash
   grep -n "business\|hours\|9.*5\|timezone" docs/architecture/distribution/VOICE.md
   ```

## Implementation Steps

1. **Add business hours constants:**
   ```python
   # In src/engines/voice.py or src/config/settings.py
   BUSINESS_HOURS = {
       "start": 9,   # 9 AM
       "end": 17,    # 5 PM
       "days": [0, 1, 2, 3, 4],  # Monday-Friday
       "timezone": "Australia/Sydney"
   }
   ```

2. **Create business hours checker:**
   ```python
   from datetime import datetime
   import pytz

   def is_within_business_hours(
       timezone: str = "Australia/Sydney",
       lead_timezone: Optional[str] = None
   ) -> bool:
       """Check if current time is within business hours.

       Uses lead's timezone if available, otherwise default.
       """
       tz = pytz.timezone(lead_timezone or timezone)
       now = datetime.now(tz)

       # Check day of week (Monday=0, Sunday=6)
       if now.weekday() not in BUSINESS_HOURS["days"]:
           return False

       # Check hour
       if not (BUSINESS_HOURS["start"] <= now.hour < BUSINESS_HOURS["end"]):
           return False

       return True

   def get_next_business_hour(
       timezone: str = "Australia/Sydney"
   ) -> datetime:
       """Calculate next available business hour."""
       tz = pytz.timezone(timezone)
       now = datetime.now(tz)

       # If within business hours, return now
       if is_within_business_hours(timezone):
           return now

       # Find next business day/hour
       next_time = now.replace(
           hour=BUSINESS_HOURS["start"],
           minute=0,
           second=0,
           microsecond=0
       )

       # If past end of day, move to tomorrow
       if now.hour >= BUSINESS_HOURS["end"]:
           next_time += timedelta(days=1)

       # Skip to Monday if weekend
       while next_time.weekday() not in BUSINESS_HOURS["days"]:
           next_time += timedelta(days=1)

       return next_time
   ```

3. **Integrate into call initiation:**
   ```python
   async def initiate_call(db: Session, lead_id: UUID, ...) -> CallResult:
       # Get lead's timezone
       lead = db.query(Lead).get(lead_id)
       lead_tz = lead.timezone or "Australia/Sydney"

       # Check business hours
       if not is_within_business_hours(lead_timezone=lead_tz):
           next_available = get_next_business_hour(lead_tz)
           return CallResult(
               status="scheduled",
               scheduled_for=next_available,
               reason="outside_business_hours"
           )

       # Proceed with call
       ...
   ```

## Acceptance Criteria

- [ ] BUSINESS_HOURS constant defined (9-5, Mon-Fri)
- [ ] is_within_business_hours() function implemented
- [ ] Respects lead's timezone when available
- [ ] get_next_business_hour() calculates next valid time
- [ ] Call initiation checks business hours first
- [ ] Outside hours: returns scheduled status, not error

## Validation

```bash
# Check functions exist
grep -n "business_hours\|is_within_business\|get_next_business" src/engines/voice.py

# Verify no syntax errors
python -m py_compile src/engines/voice.py

# Type check
mypy src/engines/voice.py --ignore-missing-imports

# Quick test (run in Python)
# from src.engines.voice import is_within_business_hours
# print(is_within_business_hours())  # Should return True/False based on current time
```

## Post-Fix

1. Update TODO.md — delete gap row #15
2. Report: "Fixed #15. Business hours validation added to voice engine (9-5 Mon-Fri, timezone-aware)."
