---
name: Fix 03 - Voice Retry Logic
description: Implements voice retry for busy/no_answer calls
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 03: Voice Retry Logic Missing

## Gap Reference
- **TODO.md Item:** #3
- **Priority:** P0/P1 Critical
- **Location:** `src/engines/voice.py`
- **Issue:** No busy/no_answer retry (busy=2hr, no_answer=next day)

## Pre-Flight Checks

1. Read voice.py to understand current call handling
2. Check if retry logic exists anywhere (might be partial)
3. Review VOICE.md spec for retry requirements

```bash
grep -n "retry\|busy\|no.answer" src/engines/voice.py
```

## Implementation Steps

1. **Add retry configuration constants:**
   ```python
   RETRY_DELAYS = {
       "busy": timedelta(hours=2),
       "no_answer": timedelta(days=1),
   }
   MAX_RETRIES = 3
   ```

2. **Create retry scheduling function:**
   ```python
   async def schedule_voice_retry(
       db: Session,
       call_id: UUID,
       disposition: str,
       attempt_number: int
   ) -> Optional[datetime]:
       """Schedule retry based on call disposition."""
       if attempt_number >= MAX_RETRIES:
           return None

       delay = RETRY_DELAYS.get(disposition)
       if not delay:
           return None

       retry_at = datetime.utcnow() + delay
       # Update call record with retry_at
       return retry_at
   ```

3. **Integrate into call completion handler:**
   - After call ends, check disposition
   - If busy/no_answer, call schedule_voice_retry()
   - Store retry_at in database

4. **Add retry pickup in outreach flow:**
   - Query for calls where retry_at <= now
   - Re-initiate those calls

## Acceptance Criteria

- [ ] RETRY_DELAYS constant defined with busy=2hr, no_answer=1day
- [ ] MAX_RETRIES constant defined (recommend 3)
- [ ] schedule_voice_retry() function implemented
- [ ] Call completion handler checks disposition and schedules retry
- [ ] Retry calls are picked up by outreach flow

## Validation

```bash
# Check constants exist
grep -n "RETRY_DELAYS\|MAX_RETRIES" src/engines/voice.py

# Check function exists
grep -n "def.*retry" src/engines/voice.py

# Verify no syntax errors
python -m py_compile src/engines/voice.py

# Type check
mypy src/engines/voice.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #3
2. Report: "Fixed #3. Voice retry implemented: busy=2hr, no_answer=next day, max 3 retries."
