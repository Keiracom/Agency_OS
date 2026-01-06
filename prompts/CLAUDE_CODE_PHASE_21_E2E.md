# Claude Code Prompt: Phase 21 E2E Testing

**Copy this entire prompt into a new Claude Code session.**

---

## Your Role

You are the QA & Fix Agent for Agency OS Phase 21 E2E testing. Your job is to:

1. Run test journeys (J1-J6)
2. Identify failures and root causes
3. Fix issues autonomously
4. Verify fixes work
5. Document everything

**Philosophy:** We're not testing "does page load" checkboxes. We're dogfooding — using Agency OS to test Agency OS as a real user would.

---

## Before You Start

### Read These Files (In Order)

```bash
# 1. Full E2E specification with test configuration
cat docs/phases/PHASE_21_E2E_SPEC.md

# 2. Testing skill with fix patterns and file references
cat skills/testing/E2E_TESTING_SKILL.md

# 3. Current progress and Quick Status
head -100 PROGRESS.md
```

### Verify Environment

```bash
# Check backend health
curl https://agency-os-production.up.railway.app/api/v1/health

# Check frontend
curl -I https://agency-os-liart.vercel.app

# Should both return 200 OK
```

---

## Test Configuration

| Field | Value |
|-------|-------|
| **Test Agency** | Umped |
| **Website** | https://umped.com.au/ |
| **Test Email** | david.stephens@keiracom.com |
| **Test Phone** | +61457543392 |
| **Test LinkedIn** | https://www.linkedin.com/in/david-stephens-8847a636a/ |
| **Lead Volume** | 100 leads |

---

## Test Journeys

| Journey | Description | Time | Status |
|---------|-------------|------|--------|
| **J1** | Signup & Onboarding | 30m | 🟢 Ready |
| **J2** | Campaign & Leads | 45m | 🟢 Ready (stop before activation) |
| **J3** | Outreach Execution | 60m | 🔴 Blocked (needs TEST_MODE) |
| **J4** | Reply & Meeting | 30m | 🔴 Blocked (needs J3) |
| **J5** | Dashboard Validation | 15m | 🟢 Ready |
| **J6** | Admin Dashboard | 15m | 🟢 Ready |

### Current Execution Order

**Phase 1: Safe Testing (No outbound) — DO NOW**
1. J1: Signup & Onboarding
2. J2: Campaign & Leads (stop before "Start Campaign")
3. J5: Dashboard Validation  
4. J6: Admin Dashboard

**Phase 2: Implement TEST_MODE — BEFORE J3/J4**
- See TEST_MODE section below

**Phase 3: Outreach Testing — AFTER TEST_MODE**
- J3: All channels (email, SMS, voice, LinkedIn)
- J4: Reply handling and meeting booking

---

## Journey Details

### J1: Signup & Onboarding (30 min) 🟢 READY

**Goal:** New user signs up as Umped, completes onboarding, reaches dashboard.

**Steps:**
1. Go to https://agency-os-liart.vercel.app/login
2. Click "Sign Up"
3. Enter: david.stephens@keiracom.com + password
4. Check email for confirmation (or confirm manually in Supabase)
5. Complete onboarding:
   - Skip CRM connect (or test HubSpot if available)
   - Confirm sender profile
   - Skip customer import
   - Enter website: https://umped.com.au/
   - Watch ICP extraction (5-tier scraper waterfall)
   - Review and confirm ICP
   - Skip LinkedIn connect
   - Skip webhook URL
6. Verify redirect to dashboard
7. Verify in Supabase: `clients` and `client_icp_profiles` tables have records

**Verification Checklist:**
- [ ] Auth callback works (no redirect loop)
- [ ] Client record created with correct user_id
- [ ] ICP extraction completes (or manual fallback works)
- [ ] ICP profile saved to database
- [ ] Dashboard loads without errors

### J2: Campaign & Leads (45 min) 🟢 READY

**Goal:** Create campaign, source leads, verify scoring and distribution.

**Steps:**
1. From dashboard, click "Create Campaign"
2. Enter:
   - Name: "Test Campaign - Umped"
   - Target: 100 leads
   - Channels: Email, SMS, LinkedIn, Voice (all enabled)
3. Save campaign
4. Verify Apollo enrichment runs (may take 1-2 minutes)
5. Check `lead_pool` table: Should have 100 records with all Apollo fields
6. Check `lead_assignments` table: 100 records linked to Umped client
7. Verify ALS scoring:
   - Hot (85-100): ~10-15 leads
   - Warm (60-84): ~30-40 leads
   - Cool (0-59): ~45-55 leads
8. Verify Deep Research triggers for Hot leads (ALS ≥ 85)
9. **STOP HERE** — Do not click "Start Campaign" until TEST_MODE is implemented

**Verification Checklist:**
- [ ] Campaign created in `campaigns` table
- [ ] 100 leads in `lead_pool` with Apollo data
- [ ] 100 assignments in `lead_assignments`
- [ ] ALS scores distributed correctly
- [ ] Deep research running for Hot leads
- [ ] Content Engine generated sequences (check `activities` or content tables)

### J3: Outreach Execution (60 min) 🔴 BLOCKED

**Blocked by:** TEST_MODE not implemented

**Why blocked:** Without TEST_MODE, clicking "Start Campaign" would email/SMS/call 100 real people.

**When ready:** After TEST-001 to TEST-006 are complete, this journey tests:
- Email: 10-15 personalized emails → your inbox
- SMS: 3-5 messages → your phone
- Voice: 1-2 AI calls → your phone
- LinkedIn: 10-20 messages → your profile

### J4: Reply & Meeting (30 min) 🔴 BLOCKED

**Blocked by:** J3 must complete first (need emails to reply to)

### J5: Dashboard Validation (15 min) 🟢 READY

**Goal:** Verify dashboard shows accurate real-time data.

**Steps:**
1. Go to https://agency-os-liart.vercel.app/dashboard
2. Verify overview metrics match database:
   - Total leads count
   - Campaign stats
   - Activity feed
3. Verify charts render (not blank)
4. Test date range filters
5. Test campaign filter (if multiple campaigns)

**Verification Checklist:**
- [ ] Dashboard loads < 3 seconds
- [ ] Metrics match DB queries
- [ ] Activity feed shows recent actions
- [ ] Charts render correctly
- [ ] Filters work

### J6: Admin Dashboard (15 min) 🟢 READY

**Goal:** Verify admin panel shows platform-wide metrics.

**Steps:**
1. Go to https://agency-os-liart.vercel.app/admin
2. Verify Command Center loads with:
   - MRR card
   - Active clients card
   - Leads today card
   - AI spend card
3. Verify System Status shows all services healthy
4. Check Clients page shows Umped
5. Check Activity shows test activities

**Verification Checklist:**
- [ ] Admin auth works (may need admin role in Supabase)
- [ ] KPIs display correctly
- [ ] System health shows green
- [ ] Client list includes test client
- [ ] Activity log populates

---

## TEST_MODE Implementation

**What it does:** Redirects ALL outbound messages to test recipients during testing.

**Why needed:** Without it, "Start Campaign" emails real people.

### Tasks (Do before J3)

| Task | Description | File |
|------|-------------|------|
| TEST-001 | Add TEST_MODE env vars | `src/config/settings.py` |
| TEST-002 | Email Engine redirect | `src/engines/email.py` |
| TEST-003 | SMS Engine redirect | `src/engines/sms.py` |
| TEST-004 | Voice Engine redirect | `src/engines/voice.py` |
| TEST-005 | LinkedIn Engine redirect | `src/engines/linkedin.py` |
| TEST-006 | Daily send limit safeguard | `src/services/send_limiter.py` |

### Implementation Pattern

```python
# In src/config/settings.py
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Test Mode
    TEST_MODE: bool = False
    TEST_EMAIL_RECIPIENT: str = "david.stephens@keiracom.com"
    TEST_SMS_RECIPIENT: str = "+61457543392"
    TEST_VOICE_RECIPIENT: str = "+61457543392"
    TEST_LINKEDIN_RECIPIENT: str = "https://www.linkedin.com/in/david-stephens-8847a636a/"
    TEST_DAILY_EMAIL_LIMIT: int = 15
```

```python
# In each engine (email, sms, voice, linkedin)
from src.config.settings import settings

async def send_email(lead: Lead, content: EmailContent):
    recipient = lead.email
    
    if settings.TEST_MODE:
        logger.info(f"TEST_MODE: Redirecting {lead.email} → {settings.TEST_EMAIL_RECIPIENT}")
        recipient = settings.TEST_EMAIL_RECIPIENT
    
    # ... rest of send logic using recipient ...
```

### After Implementation

1. Set `TEST_MODE=true` in Railway environment
2. Deploy: `railway up`
3. Proceed to J3

---

## Fix Workflow

When a test fails:

```
1. IDENTIFY → What failed? What was expected vs actual?
2. DIAGNOSE → Check logs, database, network tab
3. LOCATE → Find the file(s) responsible (use skill file references)
4. FIX → Apply minimal fix
5. VERIFY → Re-run the test
6. DOCUMENT → Add to session log
```

### Fix Documentation Template

```markdown
### Fix: [Journey].[Step] - [Brief Description]

**Problem:** [What failed]
**Root Cause:** [Why it failed]  
**Fix:** [What you changed]
**Files:** [List files modified]
**Verified:** [Yes/No + how]
```

---

## Key Rules

### DO:
- ✅ Fix issues in the codebase directly
- ✅ Test fixes before marking complete
- ✅ Document every fix
- ✅ Update PROGRESS.md after each journey
- ✅ Escalate if you need credentials or schema changes

### DON'T:
- ❌ Run J3/J4 without TEST_MODE (will contact real people!)
- ❌ Skip verification steps
- ❌ Change database schema without approval
- ❌ Delete production data
- ❌ Modify production env vars without asking

---

## Escalation

Stop and ask human if:
- Need new API credentials
- Database migration required
- Third-party service is down (Supabase, Apollo, etc.)
- Test requirement unclear
- Fix might break other features
- J3/J4 and TEST_MODE not confirmed working

---

## Start Here

```bash
# 1. Read the E2E spec
cat docs/phases/PHASE_21_E2E_SPEC.md

# 2. Read the testing skill
cat skills/testing/E2E_TESTING_SKILL.md

# 3. Verify backend is up
curl https://agency-os-production.up.railway.app/api/v1/health

# 4. Start J1: Go to /login in browser
# 5. Follow J1 steps above
# 6. Fix any issues found
# 7. Report status after J1 complete
```

**Begin with J1!**
