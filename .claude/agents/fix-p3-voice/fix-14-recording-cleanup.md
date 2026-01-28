---
name: Fix 14 - Recording Lifecycle Cleanup
description: Implements 90-day recording deletion
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 14: Recording Lifecycle Cleanup

## Gap Reference
- **TODO.md Item:** #14
- **Priority:** P3 Medium (Voice Engine)
- **Location:** `src/engines/voice.py` or background task
- **Issue:** 90-day recording deletion not implemented

## Pre-Flight Checks

1. Check existing recording handling:
   ```bash
   grep -rn "recording\|Recording" src/
   ```

2. Check if cleanup task exists:
   ```bash
   grep -rn "cleanup\|retention\|delete.*old" src/orchestration/
   ```

3. Review VOICE.md for retention requirements:
   ```bash
   grep -n "retention\|90.*day\|recording" docs/architecture/distribution/VOICE.md
   ```

## Implementation Steps

1. **Create recording cleanup task:**
   ```python
   # In src/orchestration/maintenance_tasks.py or similar
   from prefect import task, flow
   from datetime import datetime, timedelta

   RECORDING_RETENTION_DAYS = 90

   @task
   async def cleanup_old_recordings(db: Session) -> dict:
       """Delete voice recordings older than retention period."""
       cutoff_date = datetime.utcnow() - timedelta(days=RECORDING_RETENTION_DAYS)

       # Find old recordings
       old_recordings = db.query(VoiceRecording).filter(
           VoiceRecording.created_at < cutoff_date,
           VoiceRecording.deleted_at.is_(None)
       ).all()

       deleted_count = 0
       failed_count = 0

       for recording in old_recordings:
           try:
               # Delete from Twilio
               await twilio.delete_recording(recording.twilio_recording_sid)

               # Soft delete in database
               recording.deleted_at = datetime.utcnow()
               recording.deletion_reason = "retention_policy"
               deleted_count += 1

           except Exception as e:
               logger.error(f"Failed to delete recording {recording.id}: {e}")
               failed_count += 1

       db.commit()

       return {
           "checked": len(old_recordings),
           "deleted": deleted_count,
           "failed": failed_count,
           "cutoff_date": cutoff_date.isoformat()
       }

   @flow
   async def recording_cleanup_flow():
       """Daily flow to clean up old recordings."""
       async with get_db_session() as db:
           result = await cleanup_old_recordings(db)
           logger.info(f"Recording cleanup complete: {result}")
           return result
   ```

2. **Add Prefect schedule:**
   ```python
   # Run daily at 3 AM
   from prefect.schedules import CronSchedule

   recording_cleanup_flow.serve(
       name="recording-cleanup",
       schedule=CronSchedule(cron="0 3 * * *")
   )
   ```

3. **Add retention constant to config:**
   ```python
   # In src/config/settings.py
   RECORDING_RETENTION_DAYS = 90
   ```

## Acceptance Criteria

- [ ] RECORDING_RETENTION_DAYS constant defined (90)
- [ ] cleanup_old_recordings task identifies recordings > 90 days
- [ ] Deletes from Twilio storage
- [ ] Soft deletes in database (preserves audit trail)
- [ ] Logs deletion activity
- [ ] Scheduled to run daily
- [ ] Handles failures gracefully (continues with other recordings)

## Validation

```bash
# Check task exists
grep -n "cleanup_old_recordings\|recording_cleanup" src/orchestration/*.py

# Check retention constant
grep -n "RECORDING_RETENTION" src/

# Verify no syntax errors
python -m py_compile src/orchestration/maintenance_tasks.py

# Type check
mypy src/orchestration/maintenance_tasks.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #14
2. Report: "Fixed #14. Recording cleanup implemented: 90-day retention with daily Prefect task."
