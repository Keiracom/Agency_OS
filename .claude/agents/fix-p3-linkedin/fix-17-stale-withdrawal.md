---
name: Fix 17 - LinkedIn Stale Withdrawal
description: Implements 30-day stale connection withdrawal
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 17: 30-Day Stale Withdrawal

## Gap Reference
- **TODO.md Item:** #17
- **Priority:** P3 Medium (LinkedIn Engine)
- **Location:** `src/engines/linkedin.py`
- **Issue:** Stale connections not withdrawn after 30 days

## Pre-Flight Checks

1. Check existing connection management:
   ```bash
   grep -rn "withdraw\|stale\|pending.*connection" src/engines/linkedin.py
   ```

2. Check LinkedIn automation integration:
   ```bash
   grep -rn "connection.*request\|pending" src/integrations/linkedin*.py
   ```

3. Review LINKEDIN.md spec:
   ```bash
   grep -n "stale\|withdraw\|30.*day" docs/architecture/distribution/LINKEDIN.md
   ```

## Implementation Steps

1. **Add stale connection constant:**
   ```python
   STALE_CONNECTION_DAYS = 30
   ```

2. **Create stale connection finder:**
   ```python
   from datetime import datetime, timedelta

   async def get_stale_connection_requests(
       db: Session,
       linkedin_profile_id: UUID
   ) -> List[LinkedInConnection]:
       """Find pending connection requests older than 30 days."""
       cutoff_date = datetime.utcnow() - timedelta(days=STALE_CONNECTION_DAYS)

       return db.query(LinkedInConnection).filter(
           LinkedInConnection.profile_id == linkedin_profile_id,
           LinkedInConnection.status == "pending",
           LinkedInConnection.sent_at < cutoff_date
       ).all()
   ```

3. **Create withdrawal function:**
   ```python
   async def withdraw_stale_connections(
       db: Session,
       linkedin_profile_id: UUID,
       max_withdrawals: int = 10  # Daily limit
   ) -> dict:
       """Withdraw pending connections older than 30 days.

       Withdrawing frees up connection request slots.
       """
       stale = await get_stale_connection_requests(db, linkedin_profile_id)

       withdrawn = 0
       failed = 0

       for connection in stale[:max_withdrawals]:
           try:
               # Call LinkedIn API to withdraw
               await linkedin_client.withdraw_connection_request(
                   profile_id=linkedin_profile_id,
                   connection_id=connection.linkedin_connection_id
               )

               # Update database
               connection.status = "withdrawn"
               connection.withdrawn_at = datetime.utcnow()
               connection.withdrawal_reason = "stale_30_days"
               withdrawn += 1

               # Respect rate limits
               await asyncio.sleep(2)

           except Exception as e:
               logger.error(f"Failed to withdraw connection {connection.id}: {e}")
               failed += 1

       db.commit()

       return {
           "stale_found": len(stale),
           "withdrawn": withdrawn,
           "failed": failed,
           "remaining": max(0, len(stale) - max_withdrawals)
       }
   ```

4. **Add to daily maintenance flow:**
   ```python
   @task
   async def linkedin_maintenance_task(db: Session):
       """Daily LinkedIn maintenance including stale withdrawal."""
       profiles = await get_active_linkedin_profiles(db)

       for profile in profiles:
           result = await withdraw_stale_connections(db, profile.id)
           logger.info(f"Profile {profile.id}: withdrew {result['withdrawn']} stale connections")
   ```

## Acceptance Criteria

- [ ] STALE_CONNECTION_DAYS constant = 30
- [ ] get_stale_connection_requests() finds old pending requests
- [ ] withdraw_stale_connections() calls LinkedIn API
- [ ] Updates connection status to "withdrawn"
- [ ] Respects daily withdrawal limit
- [ ] Rate limiting between withdrawals
- [ ] Integrated into daily maintenance flow

## Validation

```bash
# Check functions exist
grep -n "stale\|withdraw" src/engines/linkedin.py

# Check constant
grep -n "STALE_CONNECTION_DAYS" src/engines/linkedin.py

# Verify no syntax errors
python -m py_compile src/engines/linkedin.py

# Type check
mypy src/engines/linkedin.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #17
2. Report: "Fixed #17. Stale connection withdrawal implemented (30-day threshold)."
