# Claude Code Prompt: Automated E2E Pre-Flight Testing

**Copy everything below this line into Claude Code.**

---

## Your Mission

Run comprehensive automated E2E tests BEFORE human does manual browser testing. Find and fix issues programmatically.

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

## Begin

1. Read the skill file
2. Set up configuration
3. Run Journey 1
4. Continue through all journeys
5. Generate report

**Start now.**
