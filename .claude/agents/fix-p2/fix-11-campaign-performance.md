---
name: Fix 11 - getCampaignPerformance Implementation
description: Implements getCampaignPerformance() backend endpoint
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 11: getCampaignPerformance() Stub

## Gap Reference
- **TODO.md Item:** #11
- **Priority:** P2 High
- **Location:** `frontend/lib/api/reports.ts` (frontend stub) + backend
- **Issue:** Returns empty array, needs backend endpoint

## Pre-Flight Checks

1. Find the frontend stub:
   ```bash
   grep -rn "getCampaignPerformance" frontend/
   ```

2. Check if backend endpoint exists:
   ```bash
   grep -rn "campaign.*performance\|performance.*campaign" src/api/routes/
   ```

3. Check reports routes:
   ```bash
   cat src/api/routes/reports.py
   ```

## Implementation Steps

### Backend (Create endpoint)

1. **Add route to reports.py** (or campaigns.py):
   ```python
   from fastapi import APIRouter, Depends
   from sqlalchemy.orm import Session
   from typing import List
   from uuid import UUID

   @router.get("/campaigns/{campaign_id}/performance")
   async def get_campaign_performance(
       campaign_id: UUID,
       db: Session = Depends(get_db),
       current_user = Depends(get_current_user)
   ) -> CampaignPerformanceResponse:
       """Get performance metrics for a campaign."""

       # Verify campaign access
       campaign = await verify_campaign_access(db, campaign_id, current_user)

       # Get metrics
       metrics = await reporter.get_campaign_metrics(db, campaign_id)

       return CampaignPerformanceResponse(
           campaign_id=campaign_id,
           total_leads=metrics.total_leads,
           contacted=metrics.contacted,
           responded=metrics.responded,
           converted=metrics.converted,
           conversion_rate=metrics.conversion_rate,
           by_channel={
               "email": metrics.email_stats,
               "linkedin": metrics.linkedin_stats,
               "voice": metrics.voice_stats,
               "sms": metrics.sms_stats,
           },
           by_day=metrics.daily_breakdown,
       )
   ```

2. **Create response schema:**
   ```python
   class CampaignPerformanceResponse(BaseModel):
       campaign_id: UUID
       total_leads: int
       contacted: int
       responded: int
       converted: int
       conversion_rate: float
       by_channel: Dict[str, ChannelStats]
       by_day: List[DailyStats]
   ```

### Frontend (Update stub)

3. **Update frontend/lib/api/reports.ts:**
   ```typescript
   export async function getCampaignPerformance(
     campaignId: string
   ): Promise<CampaignPerformance> {
     const response = await fetch(
       `${API_BASE}/campaigns/${campaignId}/performance`,
       {
         headers: getAuthHeaders(),
       }
     );
     if (!response.ok) throw new Error('Failed to fetch performance');
     return response.json();
   }
   ```

## Acceptance Criteria

- [ ] Backend endpoint GET /campaigns/{id}/performance exists
- [ ] Returns: total_leads, contacted, responded, converted, conversion_rate
- [ ] Includes by_channel breakdown
- [ ] Includes by_day breakdown
- [ ] Frontend getCampaignPerformance() calls real endpoint
- [ ] Proper auth/access control

## Validation

```bash
# Check backend endpoint exists
grep -n "campaign.*performance" src/api/routes/*.py

# Check frontend updated
grep -n "getCampaignPerformance" frontend/lib/api/reports.ts

# Verify backend syntax
python -m py_compile src/api/routes/reports.py

# Type check
mypy src/api/routes/reports.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #11
2. Report: "Fixed #11. getCampaignPerformance() endpoint implemented with full metrics."
