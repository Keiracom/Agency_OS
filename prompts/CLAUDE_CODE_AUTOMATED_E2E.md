# Claude Code Prompt: Automated E2E Pre-Flight Testing

**Copy everything below this line into Claude Code.**

---

## Your Mission

Run comprehensive automated E2E tests BEFORE human does manual browser testing. Find and fix issues programmatically.

---

## ⛔ CRITICAL RULES — NO SHORTCUTS

**You MUST follow these rules. Violations will invalidate the entire test.**

### DO NOT:
- ❌ **Manually insert data** into the database to fake test results
- ❌ **Skip API calls** and pretend they succeeded
- ❌ **Create mock leads** or fake enrichment data
- ❌ **Hardcode IDs** instead of using values returned from APIs
- ❌ **Skip polling** and assume async operations completed
- ❌ **Do code review only** — you must make REAL API calls
- ❌ **Summarize what you would do** — actually DO IT
- ❌ **Say "the endpoint should work"** — CALL IT and verify
- ❌ **Bypass the enrichment process** by inserting leads directly
- ❌ **Skip waiting** for ICP extraction, lead enrichment, or content generation
- ❌ **Assume TEST_MODE is working** — verify outreach actually redirects

### YOU MUST:
- ✅ **Make real curl/API calls** to production endpoints
- ✅ **Wait for async operations** (ICP extraction, lead enrichment) with polling
- ✅ **Use actual response data** (IDs, tokens) for subsequent calls
- ✅ **Verify database state** matches API responses using Supabase MCP
- ✅ **Actually trigger outreach** so emails/SMS arrive at test recipients
- ✅ **Report actual HTTP status codes** and response bodies
- ✅ **Fail tests honestly** if something doesn't work
- ✅ **Fix real issues** in code when tests fail, then re-run

### The Point of This Test:
The human will receive REAL emails, SMS, and a phone call. If you skip steps or fake data, the human won't receive anything and the test is worthless. The goal is to verify the ENTIRE system works end-to-end, not to produce a green report.

---

## Read the Skill First

```bash
cd C:\AI\Agency_OS
cat skills/testing/AUTOMATED_E2E_SKILL.md
```

This skill contains:
- Full test configuration
- All 6 journey definitions with steps
- Implementation patterns for API calls, DB validation, polling
- Complete bash implementations for each journey
- Report template
- Troubleshooting guide

---

## Quick Start

### 1. Set Up Test Configuration

```bash
cd C:\AI\Agency_OS

export TEST_RUN_ID=$(date +%Y%m%d%H%M%S)
export TEST_EMAIL="e2e_${TEST_RUN_ID}@agencyos-test.com"
export TEST_PASSWORD="TestPass123!@#"
export TEST_AGENCY="E2E Test Agency ${TEST_RUN_ID}"
export TEST_WEBSITE="https://umped.com.au"
export API_BASE="https://agency-os-production.up.railway.app/api/v1"

echo "Test Run: ${TEST_RUN_ID}"
echo "Email: ${TEST_EMAIL}"
```

### 2. Run All 6 Journeys

Follow the skill to execute:

| Journey | What It Tests |
|---------|---------------|
| J1 | Signup, onboarding, ICP extraction |
| J2 | Campaign creation, lead enrichment, ALS scoring |
| J3 | Content generation, campaign activation, outreach (TEST_MODE) |
| J4 | Reply handling, conversation threads, meeting booking |
| J5 | Dashboard stats accuracy |
| J6 | Admin panel data |

### 3. Use MCP Tools for Database Validation

For each journey, use Supabase MCP to verify:

```
supabase:execute_sql
query: "SELECT * FROM clients WHERE email = '${TEST_EMAIL}'"

supabase:execute_sql  
query: "SELECT * FROM campaigns WHERE id = '${CAMPAIGN_ID}'"

supabase:execute_sql
query: "SELECT COUNT(*), tier FROM lead_pool WHERE campaign_id = '${CAMPAIGN_ID}' GROUP BY tier"

supabase:execute_sql
query: "SELECT * FROM activities WHERE campaign_id = '${CAMPAIGN_ID}' LIMIT 10"
```

### 4. Fix Issues Found

For each failure:
1. Diagnose the root cause
2. Check if it's code, config, or data issue
3. Apply fix
4. Re-run that journey step
5. Continue

### 5. Generate Report

After all journeys, create report following template in skill.

---

## Success Criteria

All 6 journeys pass:
- [ ] J1: Account created, onboarding complete, ICP saved
- [ ] J2: Campaign created, leads enriched, ALS scores correct
- [ ] J3: Content generated, campaign active, emails sent (to test inbox)
- [ ] J4: Reply recorded, thread created, meeting booked
- [ ] J5: Dashboard stats match database
- [ ] J6: Admin stats accurate

---

## Output

1. **Test Report** — Full results with pass/fail for each step
2. **Test Credentials** — Email/password for human to use in browser
3. **Fix Log** — Any issues found and fixed
4. **Recommendation** — Ready for manual testing or not

---

## Verification Checklist (Human Will Confirm)

After you complete the test, the human will verify:

| Check | How Human Verifies |
|-------|-------------------|
| Emails sent | Check david.stephens@keiracom.com inbox |
| SMS sent | Check +61457543392 for text messages |
| Voice call | Phone rang from Vapi AI agent |
| Account works | Login with TEST_EMAIL / TEST_PASSWORD in browser |
| Leads real | View campaign leads in dashboard — not empty |
| ICP extracted | View ICP profile — populated from umped.com.au |

**If ANY of these fail, you took shortcuts.**

---

## Begin

1. Read the skill file
2. Set up configuration
3. Run Journey 1 — make REAL API calls
4. Continue through all journeys — no skipping
5. Generate report with ACTUAL results

**Start now. No shortcuts.**
