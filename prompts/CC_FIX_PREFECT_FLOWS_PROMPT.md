# Claude Code Prompt: Fix Prefect Flow Execution

**Priority:** P0 - Critical  
**Focus:** Pool population and lead enrichment flows not executing

---

## 🎯 THE PROBLEM

The E2E test revealed that:
1. `POST /pool/populate` returns 202 but leads never appear
2. Lead enrichment returns success but nothing happens
3. Prefect flows exist but aren't being triggered/executed

**Root Cause Investigation Needed:**
- Is the API actually calling Prefect?
- Is Prefect agent running on Railway?
- Are flows deployed to Prefect server?
- Are there errors in flow execution?

---

## 📋 READ THESE FILES FIRST

```bash
cd C:\AI\Agency_OS

# 1. Pool population flow
cat src/orchestration/flows/pool_population_flow.py

# 2. How flows are triggered
cat src/api/routes/pool.py 2>/dev/null || echo "File may not exist"

# 3. Campaign enrichment route
grep -A 30 "enrich" src/api/routes/campaigns.py

# 4. Prefect configuration
cat prefect.yaml

# 5. Check for TODOs
grep -rn "TODO" src/api/routes/
grep -rn "TODO" src/orchestration/flows/
```

---

## 🔍 INVESTIGATION STEPS

### Step 1: Check if Pool Route Exists

```bash
# Search for pool-related routes
grep -rn "pool" src/api/routes/
grep -rn "@router" src/api/routes/pool.py 2>/dev/null
```

**If no pool.py exists**, create it:
```python
# src/api/routes/pool.py

"""
FILE: src/api/routes/pool.py
PURPOSE: Lead pool management API endpoints
PHASE: 24A (Lead Pool Architecture)
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import ClientContext, get_current_client, get_db_session

router = APIRouter(prefix="/pool", tags=["pool"])


class PoolPopulateRequest(BaseModel):
    """Request to populate lead pool."""
    target_count: int = Field(default=100, ge=1, le=500, description="Target leads")


class PoolPopulateResponse(BaseModel):
    """Response for pool population trigger."""
    status: str
    message: str
    target_count: int


@router.post(
    "/populate",
    response_model=PoolPopulateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_pool_population(
    request: PoolPopulateRequest,
    background_tasks: BackgroundTasks,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> PoolPopulateResponse:
    """
    Trigger asynchronous pool population for the current client.
    
    This runs in the background and populates the lead pool based on
    the client's ICP configuration.
    """
    from src.orchestration.flows.pool_population_flow import pool_population_flow
    
    # Run in background
    background_tasks.add_task(
        _run_pool_population,
        client_id=ctx.client.id,
        target_count=request.target_count,
    )
    
    return PoolPopulateResponse(
        status="processing",
        message=f"Pool population started for {request.target_count} leads",
        target_count=request.target_count,
    )


async def _run_pool_population(client_id: UUID, target_count: int):
    """Execute pool population flow."""
    import asyncio
    from src.orchestration.flows.pool_population_flow import pool_population_flow
    
    # Run the Prefect flow
    await pool_population_flow(
        client_id=client_id,
        target_count=target_count,
    )
```

### Step 2: Register the Router

```bash
# Check main.py for route registration
grep -n "pool" src/main.py
```

If not registered, add to `src/main.py`:
```python
from src.api.routes import pool

app.include_router(pool.router, prefix="/api/v1")
```

### Step 3: Check Campaign Enrichment Endpoint

```bash
# Search for enrich endpoint
grep -B 5 -A 50 "enrich" src/api/routes/campaigns.py
```

**If enrichment endpoint missing or has TODO**, add:
```python
# Add to src/api/routes/campaigns.py

@router.post(
    "/clients/{client_id}/campaigns/{campaign_id}/enrich-leads",
    status_code=status.HTTP_202_ACCEPTED,
)
async def enrich_campaign_leads(
    client_id: UUID,
    campaign_id: UUID,
    count: int = Query(default=100, ge=1, le=500),
    background_tasks: BackgroundTasks = None,
    ctx: Annotated[ClientContext, Depends(require_member)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """
    Enrich leads for a campaign.
    
    1. Populates lead pool based on client ICP
    2. Assigns leads to the campaign
    3. Scores leads with ALS
    4. Triggers deep research for Hot leads
    """
    # Verify campaign exists
    campaign = await get_campaign_or_404(campaign_id, client_id, db)
    
    # Run enrichment in background
    background_tasks.add_task(
        _run_campaign_enrichment,
        client_id=client_id,
        campaign_id=campaign_id,
        count=count,
    )
    
    return {
        "status": "processing",
        "message": f"Lead enrichment started for {count} leads",
        "campaign_id": str(campaign_id),
    }


async def _run_campaign_enrichment(client_id: UUID, campaign_id: UUID, count: int):
    """Execute full campaign enrichment pipeline."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Populate pool
        logger.info(f"Starting pool population for client {client_id}")
        from src.orchestration.flows.pool_population_flow import pool_population_flow
        await pool_population_flow(client_id=client_id, target_count=count)
        
        # 2. Assign leads to campaign
        logger.info(f"Assigning leads to campaign {campaign_id}")
        from src.orchestration.flows.pool_assignment_flow import pool_campaign_assignment_flow
        await pool_campaign_assignment_flow(campaign_id=campaign_id, limit=count)
        
        # 3. Score leads (if not already done in assignment)
        logger.info(f"Scoring leads for campaign {campaign_id}")
        # Scoring happens during assignment
        
        # 4. Trigger deep research for hot leads
        logger.info(f"Triggering deep research for hot leads")
        from src.orchestration.flows.intelligence_flow import trigger_deep_research_for_hot_leads
        await trigger_deep_research_for_hot_leads(campaign_id=campaign_id)
        
        logger.info(f"Campaign enrichment complete for {campaign_id}")
        
    except Exception as e:
        logger.error(f"Campaign enrichment failed: {e}", exc_info=True)
        raise
```

### Step 4: Verify Prefect Flows Work Locally

```bash
# Test pool population flow directly
python -c "
import asyncio
from uuid import UUID
from src.orchestration.flows.pool_population_flow import pool_population_flow

# Use a real client_id from database
CLIENT_ID = UUID('10d1ffbc-1ff1-460d-b3d0-9eaba2c59aaf')  # From E2E test

async def test():
    result = await pool_population_flow(client_id=CLIENT_ID, target_count=5)
    print(f'Result: {result}')

asyncio.run(test())
"
```

### Step 5: Check Apollo Integration

```bash
# Verify Apollo is called in pool population
grep -n "apollo" src/orchestration/flows/pool_population_flow.py
grep -n "Apollo" src/integrations/apollo.py
```

Ensure Apollo search is being called:
```python
# In pool_population_flow.py, should have:
from src.integrations.apollo import get_apollo_client

apollo = get_apollo_client()
leads = await apollo.search_people(
    titles=icp_titles,
    industries=icp_industries,
    locations=icp_locations,
    employee_count_min=min_employees,
    employee_count_max=max_employees,
    limit=target_count,
)
```

---

## 🔧 FIX IMPLEMENTATION

### Option A: Direct Function Call (Simplest)

If Prefect deployments are complex, use direct function calls:

```python
# In API route, call flow function directly
from src.orchestration.flows.pool_population_flow import pool_population_flow

@router.post("/pool/populate")
async def trigger_pool_population(...):
    background_tasks.add_task(
        run_flow_directly,
        client_id=ctx.client.id,
        count=request.target_count,
    )
    return {"status": "processing"}

async def run_flow_directly(client_id: UUID, count: int):
    # Call the flow function directly (not as Prefect deployment)
    await pool_population_flow(client_id=client_id, target_count=count)
```

### Option B: Prefect Deployment (Production-Ready)

If using Prefect deployments:

```python
from prefect.deployments import run_deployment

@router.post("/pool/populate")
async def trigger_pool_population(...):
    # Trigger via Prefect deployment
    flow_run = await run_deployment(
        name="pool-population-flow/pool-population",
        parameters={
            "client_id": str(ctx.client.id),
            "target_count": request.target_count,
        },
        timeout=0,  # Don't wait for completion
    )
    return {"status": "processing", "flow_run_id": str(flow_run.id)}
```

---

## ✅ VERIFICATION

After implementing fixes:

### 1. Test Pool Population
```bash
curl -X POST "https://agency-os-production.up.railway.app/api/v1/pool/populate" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"target_count": 5}'

# Wait 30 seconds, then check
curl "https://agency-os-production.up.railway.app/api/v1/clients/${CLIENT_ID}/leads?limit=10" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### 2. Check Database
```sql
-- Use Supabase MCP
SELECT COUNT(*) FROM lead_pool WHERE client_id = '${CLIENT_ID}';
SELECT pool_status, COUNT(*) FROM lead_pool WHERE client_id = '${CLIENT_ID}' GROUP BY pool_status;
```

### 3. Check Railway Logs
```bash
railway logs --tail 100
```

Look for:
- "Starting pool population"
- "Apollo search returned X leads"
- Any error messages

---

## 📊 SUCCESS CRITERIA

- [ ] `POST /pool/populate` creates leads in `lead_pool` table
- [ ] `POST /campaigns/{id}/enrich-leads` populates and assigns leads
- [ ] Leads have ALS scores calculated
- [ ] Hot leads (ALS >= 85) trigger deep research
- [ ] Campaign `total_leads` counter updates

---

## 🚀 DEPLOY

After fixing:

```bash
# Commit changes
git add -A
git commit -m "fix(orchestration): wire up pool population and enrichment flows"

# Deploy to Railway
git push origin main
# OR
railway up
```

---

## 📝 DOCUMENT

Add to `docs/audits/E2E_FIXES_FINAL.md`:

```markdown
### Fix: Pool Population and Lead Enrichment

**Problem:** API returned 202 but no leads were created
**Root Cause:** [What you found]
**Fix Applied:** [What you changed]
**Files Modified:**
- src/api/routes/pool.py (created/modified)
- src/api/routes/campaigns.py (added enrichment endpoint)
- src/main.py (registered router)
**Verified:** Successfully created X leads in pool
**Deployed:** Yes - commit XXXXXX
```
