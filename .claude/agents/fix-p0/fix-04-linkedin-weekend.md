---
name: Fix 04 - LinkedIn Weekend Reduction
description: Enforces Sat 50%/Sun 0% activity rule
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 04: LinkedIn Weekend Reduction Missing

## Gap Reference
- **TODO.md Item:** #4
- **Priority:** P0/P1 Critical
- **Location:** `src/engines/linkedin.py`
- **Issue:** Sat 50%/Sun 0% rule not enforced

## Pre-Flight Checks

1. Read linkedin.py to find daily quota/limit handling
2. Check if any weekend logic exists
3. Review LINKEDIN.md spec for weekend rules

```bash
grep -n "weekend\|saturday\|sunday\|weekday" src/engines/linkedin.py
grep -n "quota\|limit\|daily" src/engines/linkedin.py
```

## Implementation Steps

1. **Add weekend detection helper:**
   ```python
   from datetime import datetime

   def get_weekend_multiplier() -> float:
       """Returns activity multiplier based on day of week.

       Saturday: 0.5 (50% activity)
       Sunday: 0.0 (no activity)
       Weekdays: 1.0 (full activity)
       """
       weekday = datetime.now().weekday()
       if weekday == 6:  # Sunday
           return 0.0
       elif weekday == 5:  # Saturday
           return 0.5
       return 1.0
   ```

2. **Apply multiplier to daily quota calculation:**
   ```python
   def get_daily_quota(base_quota: int) -> int:
       multiplier = get_weekend_multiplier()
       return int(base_quota * multiplier)
   ```

3. **Apply at activity initiation points:**
   - Connection requests
   - Messages
   - Profile views
   - Any other automated actions

4. **Add early return for Sunday:**
   ```python
   if get_weekend_multiplier() == 0.0:
       logger.info("LinkedIn activity paused for Sunday")
       return {"status": "skipped", "reason": "sunday_pause"}
   ```

## Acceptance Criteria

- [ ] get_weekend_multiplier() function implemented
- [ ] Returns 0.0 for Sunday
- [ ] Returns 0.5 for Saturday
- [ ] Returns 1.0 for weekdays
- [ ] All LinkedIn activity functions apply the multiplier
- [ ] Sunday returns early without taking action

## Validation

```bash
# Check weekend functions exist
grep -n "weekend\|multiplier" src/engines/linkedin.py

# Check Sunday/Saturday handling
grep -n "sunday\|saturday\|weekday" src/engines/linkedin.py

# Verify no syntax errors
python -m py_compile src/engines/linkedin.py

# Type check
mypy src/engines/linkedin.py --ignore-missing-imports
```

## Unit Test (Optional)

```python
from unittest.mock import patch
from datetime import datetime

def test_weekend_multiplier():
    # Test Sunday
    with patch('src.engines.linkedin.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 7)  # Sunday
        assert get_weekend_multiplier() == 0.0

    # Test Saturday
    with patch('src.engines.linkedin.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 6)  # Saturday
        assert get_weekend_multiplier() == 0.5

    # Test Monday
    with patch('src.engines.linkedin.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 8)  # Monday
        assert get_weekend_multiplier() == 1.0
```

## Post-Fix

1. Update TODO.md — delete gap row #4
2. Report: "Fixed #4. LinkedIn weekend reduction: Sat 50%, Sun 0%."
