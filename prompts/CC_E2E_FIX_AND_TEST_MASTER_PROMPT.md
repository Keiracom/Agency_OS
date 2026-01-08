# Claude Code Master Prompt: Fix Issues & Complete E2E Testing

**Version:** 1.0  
**Created:** January 7, 2026  
**Purpose:** Fix all identified bugs and run complete E2E testing with REAL outreach

---

## 🎯 THE GOAL

Dave needs to see Agency OS working end-to-end:
1. **Onboarding works** — Sign up, ICP extracted from umped.com.au
2. **Campaign works** — Create campaign, leads enriched, ALS scored
3. **Email in inbox** — Receive personalized cold emails (judge Claude's content quality)
4. **SMS on phone** — Receive SMS messages (judge content)
5. **Phone call received** — AI voice call from Vapi (judge voice quality)
6. **All systems integrated** — Prefect, Vercel, Supabase, Railway, Python all working together

**This is the FINAL validation before launch.**

---

## 📋 CONTEXT FILES TO READ FIRST

Before writing ANY code, read these files in order:

```bash
# 1. Project overview
cat PROJECT_BLUEPRINT.md

# 2. Current status and bugs found
cat PROGRESS.md | head -300

# 3. E2E test report with bugs
cat docs/E2E_TEST_REPORT_20260107.md

# 4. Testing skill (fix patterns, file references)
cat skills/testing/E2E_TESTING_SKILL.md

# 5. Automated E2E skill (API testing patterns)
cat skills/testing/AUTOMATED_E2E_SKILL.md

# 6. Import hierarchy rules
cat docs/architecture/IMPORT_HIERARCHY.md

# 7. Development rules
cat CLAUDE.md
```

---

## 🐛 KNOWN BUGS TO FIX

From the E2E test report (January 7, 2026):

| # | Bug | Severity | Root Cause | Status |
|---|-----|----------|------------|--------|
| 1 | **User model missing `is_platform_admin`** | Critical | SQLAlchemy model missing column mapping | ✅ Fixed locally |
| 2 | **Pool population not processing** | High | Prefect flow not executing when API called | ❌ FIX NEEDED |
| 3 | **Lead enrichment not processing** | High | TODO in code, Prefect flow not wired | ❌ FIX NEEDED |
| 4 | **Campaign `total_leads` counter not updating** | Medium | Counter not incremented on lead add | ❌ FIX NEEDED |

---

## 🔧 PHASE 1: FIX THE BUGS

### Bug 1: Deploy the User Model Fix (Already Fixed)

The `is_platform_admin` column was added to `src/models/user.py`. This needs to be deployed to Railway.

```bash
# Verify the fix is in place
grep -n "is_platform_admin" src/models/user.py

# Commit if not already committed
git add src/models/user.py
git commit -m "fix(models): add is_platform_admin column mapping to User model"

# Deploy to Railway
git push origin main
# OR use Railway CLI
railway up
```

### Bug 2: Fix Pool Population Flow Execution

**Problem:** API returns 202 Accepted but leads don't appear in pool.

**Investigation Steps:**
1. Check if Prefect agent is running on Railway
2. Check if flow is being scheduled
3. Check Prefect logs for errors

**Files to check:**
- `src/api/routes/pool.py` — How is the flow triggered?
- `src/orchestration/flows/pool_population_flow.py` — The flow itself
- `prefect.yaml` — Prefect configuration

**Likely Fixes:**

Option A: Flow not being triggered (most likely)
```python
# In the API route that triggers pool population, ensure it's calling Prefect correctly
from prefect.deployments import run_deployment

# Should be calling:
await run_deployment(
    name="pool-population-flow/pool-population",
    parameters={"client_id": str(client_id), "target_count": count}
)
```

Option B: Flow trigger exists but not awaited
```python
# Make sure it's async and awaited
result = await run_deployment(...)  # Not just run_deployment(...)
```

Option C: Prefect agent not running
```bash
# Check Railway for prefect-agent service
# Ensure it's running and connected to Prefect server
```

**Create the API endpoint if missing:**
```python
# src/api/routes/pool.py (create if doesn't exist)

from fastapi import APIRouter, Depends, BackgroundTasks
from prefect.deployments import run_deployment

router = APIRouter(tags=["pool"])

@router.post("/pool/populate")
async def trigger_pool_population(
    client_id: UUID,
    target_count: int = 100,
    background_tasks: BackgroundTasks = None,
    ctx: ClientContext = Depends(get_current_client),
):
    """Trigger pool population for a client."""
    # Option 1: Run in background task
    background_tasks.add_task(
        run_pool_population,
        client_id=client_id,
        target_count=target_count
    )
    return {"status": "processing", "message": "Pool population started"}

async def run_pool_population(client_id: UUID, target_count: int):
    """Actually run the pool population."""
    from src.orchestration.flows.pool_population_flow import pool_population_flow
    await pool_population_flow(client_id=client_id, target_count=target_count)
```

### Bug 3: Fix Lead Enrichment Flow

**Problem:** Enrichment endpoint returns success but no data populated.

**Investigation:**
```bash
# Search for TODO in enrichment code
grep -rn "TODO" src/api/routes/leads.py
grep -rn "TODO" src/api/routes/campaigns.py
grep -rn "enrich" src/api/routes/
```

**Fix Pattern:**
```python
# After creating campaign, trigger enrichment flow
from src.orchestration.flows.enrichment_flow import lead_enrichment_flow

@router.post("/clients/{client_id}/campaigns/{campaign_id}/enrich-leads")
async def enrich_campaign_leads(
    client_id: UUID,
    campaign_id: UUID,
    count: int = 100,
    background_tasks: BackgroundTasks = None,
    ctx: ClientContext = Depends(require_member),
    db: AsyncSession = Depends(get_db_session),
):
    """Trigger lead enrichment for a campaign."""
    # Verify campaign exists
    campaign = await get_campaign_or_404(campaign_id, client_id, db)
    
    # Trigger enrichment flow
    background_tasks.add_task(
        run_enrichment,
        client_id=client_id,
        campaign_id=campaign_id,
        count=count
    )
    
    return {"status": "processing", "count": count}

async def run_enrichment(client_id: UUID, campaign_id: UUID, count: int):
    from src.orchestration.flows.pool_population_flow import pool_population_flow
    from src.orchestration.flows.pool_assignment_flow import pool_campaign_assignment_flow
    
    # 1. Populate pool with leads matching ICP
    await pool_population_flow(client_id=client_id, target_count=count)
    
    # 2. Assign leads to campaign
    await pool_campaign_assignment_flow(campaign_id=campaign_id, limit=count)
```

### Bug 4: Fix Campaign Total Leads Counter

**Problem:** Campaign shows 0 leads despite having leads assigned.

**Investigation:**
```bash
# Check where total_leads is updated
grep -rn "total_leads" src/
```

**Fix:** Add trigger or update logic when leads are assigned:
```python
# In lead assignment flow or service
async def assign_leads_to_campaign(campaign_id: UUID, lead_ids: list[UUID], db: AsyncSession):
    # ... assign leads ...
    
    # Update campaign counter
    stmt = (
        update(Campaign)
        .where(Campaign.id == campaign_id)
        .values(total_leads=Campaign.total_leads + len(lead_ids))
    )
    await db.execute(stmt)
    await db.commit()
```

Or create a database trigger:
```sql
-- In new migration: xxx_fix_campaign_lead_counter.sql
CREATE OR REPLACE FUNCTION update_campaign_lead_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE campaigns 
        SET total_leads = total_leads + 1
        WHERE id = NEW.campaign_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE campaigns 
        SET total_leads = total_leads - 1
        WHERE id = OLD.campaign_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER lead_assignment_counter
AFTER INSERT OR DELETE ON lead_assignments
FOR EACH ROW
EXECUTE FUNCTION update_campaign_lead_count();
```

---

## 🧪 PHASE 2: VERIFY TEST_MODE IS WORKING

**CRITICAL:** Before ANY outreach testing, verify TEST_MODE redirects work.

### Check Configuration
```bash
# Verify settings.py has TEST_MODE
grep -A 10 "TEST_MODE" src/config/settings.py

# Verify each engine has redirect logic
grep -n "TEST_MODE" src/engines/email.py
grep -n "TEST_MODE" src/engines/sms.py
grep -n "TEST_MODE" src/engines/voice.py
grep -n "TEST_MODE" src/engines/linkedin.py
```

### Verify Railway Environment Variables
```bash
# These must be set in Railway
railway variables

# Should show:
# TEST_MODE=true
# TEST_EMAIL_RECIPIENT=david.stephens@keiracom.com
# TEST_SMS_RECIPIENT=+61457543392
# TEST_VOICE_RECIPIENT=+61457543392
# TEST_LINKEDIN_RECIPIENT=https://www.linkedin.com/in/david-stephens-8847a636a/
# TEST_DAILY_EMAIL_LIMIT=15
```

### Test Send Redirect (Unit Test)
```python
# Quick test to verify redirect works
import asyncio
from src.config.settings import settings
from src.engines.email import get_email_engine

async def test_redirect():
    print(f"TEST_MODE: {settings.TEST_MODE}")
    print(f"TEST_EMAIL_RECIPIENT: {settings.TEST_EMAIL_RECIPIENT}")
    
    if settings.TEST_MODE:
        print("✅ TEST_MODE is ON - outreach will redirect")
    else:
        print("❌ TEST_MODE is OFF - DANGER: will email real leads!")

asyncio.run(test_redirect())
```

---

## 🚀 PHASE 3: RUN COMPLETE E2E TEST

Once bugs are fixed, run the full E2E test sequence.

### Test Configuration
```bash
export TEST_RUN_ID=$(date +%Y%m%d%H%M%S)
export TEST_EMAIL="e2e.test.${TEST_RUN_ID}@gmail.com"
export TEST_PASSWORD="TestPass123"
export TEST_WEBSITE="https://umped.com.au"
export API_BASE="https://agency-os-production.up.railway.app/api/v1"
```

### Journey 1: Signup & Onboarding

**Goal:** Create account, extract ICP from umped.com.au

```bash
# 1.1 Create account via Supabase Auth
curl -X POST "${API_BASE}/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${TEST_EMAIL}\",
    \"password\": \"${TEST_PASSWORD}\"
  }"

# Save the returned access_token
export ACCESS_TOKEN="<token from response>"

# 1.2 Check onboarding status
curl -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/onboarding/status"

# 1.3 Submit website for ICP extraction
curl -X POST "${API_BASE}/onboarding/analyze" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"website_url\": \"${TEST_WEBSITE}\"}"

# Save the job_id
export JOB_ID="<job_id from response>"

# 1.4 Poll for ICP extraction completion (may take 30-60 seconds)
while true; do
  STATUS=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "${API_BASE}/onboarding/status/${JOB_ID}" | jq -r '.status')
  echo "ICP Status: $STATUS"
  if [ "$STATUS" = "completed" ]; then break; fi
  sleep 5
done

# 1.5 Confirm ICP
curl -X POST "${API_BASE}/onboarding/confirm" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"confirmed\": true}"

# Verify in database
# Use Supabase MCP: SELECT * FROM clients WHERE email = '${TEST_EMAIL}'
# Use Supabase MCP: SELECT * FROM client_icp_profiles WHERE client_id = '<client_id>'
```

### Journey 2: Campaign & Lead Enrichment

**Goal:** Create campaign, get 25 leads enriched with ALS scores

```bash
# Get client_id from previous step
export CLIENT_ID="<client_id>"

# 2.1 Create campaign
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"E2E Test Campaign - ${TEST_RUN_ID}\",
    \"description\": \"Automated E2E test\",
    \"target_leads\": 25,
    \"allocation_email\": 60,
    \"allocation_sms\": 20,
    \"allocation_voice\": 10,
    \"allocation_linkedin\": 10,
    \"allocation_mail\": 0,
    \"daily_limit\": 50
  }"

export CAMPAIGN_ID="<campaign_id from response>"

# 2.2 Trigger lead enrichment
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/enrich-leads" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"count\": 25}"

# 2.3 Poll for leads (may take 1-2 minutes)
while true; do
  LEADS=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/leads" | jq '.total // .count // 0')
  echo "Leads: $LEADS"
  if [ "$LEADS" -ge 20 ]; then break; fi
  sleep 10
done

# 2.4 Verify ALS scoring
curl -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/leads?limit=10" | jq '.leads[] | {email, als_score, tier}'

# Verify in database
# Use Supabase MCP: SELECT pool_status, COUNT(*) FROM lead_pool WHERE client_id = '${CLIENT_ID}' GROUP BY pool_status
# Use Supabase MCP: SELECT als_tier, COUNT(*) FROM lead_assignments WHERE campaign_id = '${CAMPAIGN_ID}' GROUP BY als_tier
```

### Journey 3: Outreach Execution (THE BIG TEST)

**Goal:** Send REAL emails, SMS, and voice call to Dave

⚠️ **BEFORE RUNNING:** Verify TEST_MODE=true in Railway!

```bash
# 3.1 Activate campaign
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/activate" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"

# 3.2 Generate content for outreach
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/generate-content" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"channels\": [\"email\", \"sms\", \"voice\"]}"

# 3.3 Send EMAIL (3 test emails to dave)
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/send" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"channel\": \"email\", \"limit\": 3}"

echo "📧 Check inbox: david.stephens@keiracom.com"

# 3.4 Send SMS (2 test SMS to dave)
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/send" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"channel\": \"sms\", \"limit\": 2}"

echo "📱 Check phone: +61457543392"

# 3.5 Send VOICE (1 test call to dave)
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/send" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"channel\": \"voice\", \"limit\": 1}"

echo "📞 Expect call to: +61457543392"

# 3.6 Verify activities logged
curl -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/clients/${CLIENT_ID}/activities?campaign_id=${CAMPAIGN_ID}" | jq '.activities[] | {channel, status, created_at}'
```

### Journey 4, 5, 6: Dashboard & Admin

```bash
# 4. Reply handling (simulate)
curl -X POST "${API_BASE}/webhooks/email/reply" \
  -H "Content-Type: application/json" \
  -d "{
    \"lead_id\": \"<lead_id>\",
    \"message\": \"I am interested, let us schedule a call\",
    \"from_email\": \"test@example.com\"
  }"

# 5. Dashboard stats
curl -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/dashboard/stats"

# 6. Admin stats
curl "${API_BASE}/admin/stats"
```

---

## 📊 EXPECTED OUTCOME

After completing all phases, Dave will have:

| Channel | Quantity | Recipient | What Dave Judges |
|---------|----------|-----------|------------------|
| **Email** | 3 | david.stephens@keiracom.com | Claude's email writing, personalization |
| **SMS** | 2 | +61457543392 | Claude's SMS copywriting |
| **Voice** | 1 | +61457543392 | Vapi voice quality, script quality |

**Success Criteria:**
- [ ] Emails received with personalized content (lead name, company, icebreaker)
- [ ] SMS received with compelling, short copy
- [ ] Phone call received from AI agent
- [ ] All activities logged in database
- [ ] Dashboard shows accurate metrics
- [ ] Admin panel accessible and accurate

---

## 🛠️ FIX DOCUMENTATION

Document every fix in `docs/audits/E2E_FIXES_FINAL.md`:

```markdown
### Fix #X: [Title]

**Problem:** What failed
**Root Cause:** Why it failed
**Fix Applied:** What was changed
**Files Modified:**
- file1.py
- file2.py
**Verified:** How you confirmed it works
**Deployed:** Yes/No
```

---

## 🚨 ESCALATION TRIGGERS

Stop and ask Dave if:
1. **Missing API credentials** — Need Twilio/Vapi/Apollo keys
2. **Database migration needed** — Affects production schema
3. **Third-party service down** — Supabase, Railway, Apollo outage
4. **TEST_MODE unclear** — Not sure if redirects are working
5. **About to send to real leads** — Confirm TEST_MODE before outreach

---

## ✅ COMPLETION CHECKLIST

Before declaring E2E complete:

- [ ] Bug 1 fixed and deployed (User model)
- [ ] Bug 2 fixed and deployed (Pool population)
- [ ] Bug 3 fixed and deployed (Lead enrichment)
- [ ] Bug 4 fixed and deployed (Campaign counter)
- [ ] TEST_MODE verified working
- [ ] J1 passed: Signup + ICP extraction
- [ ] J2 passed: Campaign + leads enriched + ALS scored
- [ ] J3 passed: Dave received emails, SMS, voice call
- [ ] J4 passed: Reply handling works
- [ ] J5 passed: Dashboard accurate
- [ ] J6 passed: Admin panel works
- [ ] All fixes documented
- [ ] PROGRESS.md updated

---

## 🎬 START HERE

```bash
cd C:\AI\Agency_OS

# 1. Read context files
cat PROJECT_BLUEPRINT.md
cat PROGRESS.md | head -300
cat docs/E2E_TEST_REPORT_20260107.md

# 2. Start fixing bugs in order:
#    - Bug 1: Verify User model fix, deploy
#    - Bug 2: Fix pool population flow
#    - Bug 3: Fix lead enrichment trigger
#    - Bug 4: Fix campaign counter

# 3. After bugs fixed, run E2E tests

# GO!
```
