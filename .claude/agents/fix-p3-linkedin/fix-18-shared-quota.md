---
name: Fix 18 - LinkedIn Shared Quota Tracking
description: Combines manual + auto activity in quota tracking
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 18: Shared Quota Tracking

## Gap Reference
- **TODO.md Item:** #18
- **Priority:** P3 Medium (LinkedIn Engine)
- **Location:** `src/engines/linkedin.py`
- **Issue:** Manual + auto activity not combined in quota

## Pre-Flight Checks

1. Check existing quota logic:
   ```bash
   grep -rn "quota\|daily.*limit\|activity.*count" src/engines/linkedin.py
   ```

2. Check how activity is tracked:
   ```bash
   grep -rn "LinkedInActivity\|activity.*log" src/models/
   ```

3. Review LINKEDIN.md for quota rules:
   ```bash
   grep -n "quota\|limit\|daily" docs/architecture/distribution/LINKEDIN.md
   ```

## Implementation Steps

1. **Define quota constants:**
   ```python
   LINKEDIN_DAILY_QUOTAS = {
       "connection_requests": 20,  # Max new connections per day
       "messages": 50,             # Max messages per day
       "profile_views": 100,       # Max profile views per day
       "total_actions": 150,       # Overall daily cap
   }
   ```

2. **Create unified quota tracker:**
   ```python
   async def get_daily_activity_count(
       db: Session,
       linkedin_profile_id: UUID,
       activity_type: Optional[str] = None,
       include_manual: bool = True
   ) -> int:
       """Get total activity count for today (manual + automated).

       Args:
           activity_type: Specific type or None for all
           include_manual: Whether to include manual activity
       """
       today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)

       query = db.query(LinkedInActivity).filter(
           LinkedInActivity.profile_id == linkedin_profile_id,
           LinkedInActivity.created_at >= today_start
       )

       if activity_type:
           query = query.filter(LinkedInActivity.activity_type == activity_type)

       if not include_manual:
           query = query.filter(LinkedInActivity.source == "automated")

       return query.count()

   async def get_remaining_quota(
       db: Session,
       linkedin_profile_id: UUID,
       activity_type: str
   ) -> int:
       """Get remaining quota for an activity type."""
       used = await get_daily_activity_count(
           db, linkedin_profile_id, activity_type, include_manual=True
       )
       limit = LINKEDIN_DAILY_QUOTAS.get(activity_type, 0)
       return max(0, limit - used)

   async def can_perform_action(
       db: Session,
       linkedin_profile_id: UUID,
       activity_type: str
   ) -> tuple[bool, str]:
       """Check if action is allowed within quota.

       Returns (allowed, reason).
       """
       # Check specific quota
       remaining = await get_remaining_quota(db, linkedin_profile_id, activity_type)
       if remaining <= 0:
           return False, f"Daily {activity_type} quota exhausted"

       # Check total actions quota
       total_used = await get_daily_activity_count(
           db, linkedin_profile_id, None, include_manual=True
       )
       if total_used >= LINKEDIN_DAILY_QUOTAS["total_actions"]:
           return False, "Daily total actions quota exhausted"

       return True, "ok"
   ```

3. **Log both manual and automated activity:**
   ```python
   async def log_linkedin_activity(
       db: Session,
       profile_id: UUID,
       activity_type: str,
       source: str,  # "automated" or "manual"
       target_url: Optional[str] = None,
       metadata: Optional[dict] = None
   ):
       """Log any LinkedIn activity for quota tracking."""
       activity = LinkedInActivity(
           profile_id=profile_id,
           activity_type=activity_type,
           source=source,
           target_url=target_url,
           metadata=metadata,
           created_at=datetime.utcnow()
       )
       db.add(activity)
       db.commit()
   ```

4. **Update action functions to check quota:**
   ```python
   async def send_connection_request(db, profile_id, target_url):
       # Check quota first
       allowed, reason = await can_perform_action(
           db, profile_id, "connection_requests"
       )
       if not allowed:
           return {"status": "blocked", "reason": reason}

       # Proceed with action...
       result = await linkedin_client.send_connection(...)

       # Log the activity
       await log_linkedin_activity(
           db, profile_id, "connection_requests", "automated", target_url
       )

       return result
   ```

## Acceptance Criteria

- [ ] LINKEDIN_DAILY_QUOTAS defines limits per activity type
- [ ] get_daily_activity_count() includes both manual and automated
- [ ] get_remaining_quota() calculates available quota
- [ ] can_perform_action() validates before any action
- [ ] log_linkedin_activity() records source (manual/automated)
- [ ] All action functions check quota before executing

## Validation

```bash
# Check quota functions exist
grep -n "quota\|remaining\|can_perform_action" src/engines/linkedin.py

# Check activity logging includes source
grep -n "source.*manual\|source.*automated" src/engines/linkedin.py

# Verify no syntax errors
python -m py_compile src/engines/linkedin.py

# Type check
mypy src/engines/linkedin.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #18
2. Report: "Fixed #18. LinkedIn shared quota tracking now combines manual + automated activity."
