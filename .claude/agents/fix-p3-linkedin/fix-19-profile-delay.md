---
name: Fix 19 - LinkedIn Profile View Delay
description: Adds 10-30 min delay before connect request
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 19: Profile View Delay

## Gap Reference
- **TODO.md Item:** #19
- **Priority:** P3 Medium (LinkedIn Engine)
- **Location:** `src/engines/linkedin.py`
- **Issue:** No 10-30 min delay before connect request

## Pre-Flight Checks

1. Check existing connection flow:
   ```bash
   grep -rn "profile.*view\|connect.*request\|delay" src/engines/linkedin.py
   ```

2. Check if timing/scheduling exists:
   ```bash
   grep -rn "schedule\|delay\|wait" src/engines/linkedin.py
   ```

3. Review LINKEDIN.md for delay requirements:
   ```bash
   grep -n "delay\|view.*connect\|natural" docs/architecture/distribution/LINKEDIN.md
   ```

## Implementation Steps

1. **Add delay constants:**
   ```python
   import random

   PROFILE_VIEW_DELAY = {
       "min_minutes": 10,
       "max_minutes": 30,
   }

   def get_random_delay() -> int:
       """Get random delay in seconds (10-30 minutes)."""
       min_sec = PROFILE_VIEW_DELAY["min_minutes"] * 60
       max_sec = PROFILE_VIEW_DELAY["max_minutes"] * 60
       return random.randint(min_sec, max_sec)
   ```

2. **Implement two-step connection flow:**
   ```python
   async def initiate_connection_sequence(
       db: Session,
       profile_id: UUID,
       target_profile_url: str,
       message: Optional[str] = None
   ) -> dict:
       """Start connection sequence: view profile, then schedule connect.

       Flow:
       1. View profile immediately
       2. Schedule connection request for 10-30 min later
       """
       # Step 1: View profile now
       view_result = await view_profile(db, profile_id, target_profile_url)

       if view_result.get("status") != "success":
           return {"status": "failed", "step": "profile_view", "error": view_result}

       # Step 2: Schedule connection request
       delay_seconds = get_random_delay()
       scheduled_at = datetime.utcnow() + timedelta(seconds=delay_seconds)

       # Create pending connection record
       pending = PendingLinkedInAction(
           profile_id=profile_id,
           action_type="connection_request",
           target_url=target_profile_url,
           message=message,
           scheduled_at=scheduled_at,
           status="pending"
       )
       db.add(pending)
       db.commit()

       return {
           "status": "scheduled",
           "profile_viewed": True,
           "connect_scheduled_at": scheduled_at.isoformat(),
           "delay_minutes": delay_seconds // 60
       }

   async def view_profile(
       db: Session,
       profile_id: UUID,
       target_url: str
   ) -> dict:
       """View a LinkedIn profile."""
       result = await linkedin_client.view_profile(profile_id, target_url)

       # Log activity
       await log_linkedin_activity(
           db, profile_id, "profile_views", "automated", target_url
       )

       return result
   ```

3. **Create scheduled action processor:**
   ```python
   @task
   async def process_pending_linkedin_actions(db: Session):
       """Process LinkedIn actions that are due."""
       now = datetime.utcnow()

       pending_actions = db.query(PendingLinkedInAction).filter(
           PendingLinkedInAction.status == "pending",
           PendingLinkedInAction.scheduled_at <= now
       ).all()

       for action in pending_actions:
           try:
               if action.action_type == "connection_request":
                   result = await send_connection_request(
                       db,
                       action.profile_id,
                       action.target_url,
                       action.message
                   )
                   action.status = "completed" if result["status"] == "success" else "failed"
                   action.result = result

           except Exception as e:
               action.status = "failed"
               action.error = str(e)

           action.processed_at = datetime.utcnow()

       db.commit()
   ```

4. **Schedule processor to run frequently:**
   ```python
   # Run every 5 minutes to process due actions
   from prefect.schedules import IntervalSchedule

   @flow
   async def linkedin_action_processor_flow():
       async with get_db_session() as db:
           await process_pending_linkedin_actions(db)
   ```

## Acceptance Criteria

- [ ] PROFILE_VIEW_DELAY constants (10-30 min)
- [ ] get_random_delay() returns random delay in range
- [ ] initiate_connection_sequence() views profile first
- [ ] Connection request scheduled for 10-30 min later
- [ ] PendingLinkedInAction model tracks scheduled actions
- [ ] Processor runs regularly to execute due actions
- [ ] All activity logged for quota tracking

## Validation

```bash
# Check delay constants
grep -n "PROFILE_VIEW_DELAY\|delay" src/engines/linkedin.py

# Check two-step flow
grep -n "initiate_connection_sequence\|view_profile" src/engines/linkedin.py

# Check scheduler
grep -n "pending.*action\|scheduled_at" src/engines/linkedin.py

# Verify no syntax errors
python -m py_compile src/engines/linkedin.py

# Type check
mypy src/engines/linkedin.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #19
2. Report: "Fixed #19. LinkedIn profile view delay (10-30 min) before connection request."
