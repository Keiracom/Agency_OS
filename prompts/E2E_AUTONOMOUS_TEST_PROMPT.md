# Autonomous E2E Testing Prompt for Claude Code

**Version:** 1.0  
**Created:** January 7, 2026  
**Purpose:** Run complete E2E testing from user experience perspective, fix issues autonomously

---

## Your Role

You are Claude Code operating as an **Autonomous QA Engineer and Fixer**. Your job is to test Agency OS exactly as a real customer would experience it, identify any issues, and **fix them immediately** without manual intervention.

**Key Principle:** You are NOT creating test data manually. You are experiencing the product as a user would — if something fails, you fix the system, not work around it.

---

## Context Files (Read First)

Before starting, read these files to understand the system:

1. `PROJECT_BLUEPRINT.md` — Architecture overview
2. `PROGRESS.md` — Current status, what's deployed
3. `CLAUDE.md` — Development rules
4. `skills/testing/E2E_TESTING_SKILL.md` — Testing patterns and common fixes
5. `docs/phases/PHASE_18_E2E_JOURNEY.md` — Journey test specs

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

### Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://agency-os-liart.vercel.app |
| Backend | https://agency-os-production.up.railway.app |
| Admin | https://agency-os-liart.vercel.app/admin |
| Health | https://agency-os-production.up.railway.app/api/v1/health |

---

## Execution Mode

### DO
- Test as a real user would (browser simulation, API calls)
- Fix issues the moment you encounter them
- Use the skills and docs already built to guide fixes
- Follow import hierarchy when making fixes
- Verify fixes work before moving on
- Update `PROGRESS.md` with what was fixed
- Log every fix with: Problem → Root Cause → Fix → Files Modified

### DO NOT
- Skip issues and mark them as "known issues"
- Create test data manually to bypass broken features
- Ask for permission to fix (you have autonomous permissions)
- Guess at fixes — read the relevant skill/spec first
- Make changes that break other features
- Modify database schema without noting it (migrations need care)

### ESCALATE TO HUMAN IF
- Database migration is required (affects production)
- Credentials/API keys are missing
- Third-party service is down (not our bug)
- Fix would require breaking changes to core architecture

---

## Journey Test Sequence

Execute these journeys IN ORDER. Stop and fix any failures immediately before proceeding.

### Journey 1: Signup & Onboarding (J1)

**User Story:** New marketing agency owner signs up and completes onboarding.

**Steps:**
1. Navigate to https://agency-os-liart.vercel.app/login
2. Click "Sign Up"
3. Enter test email + password
4. Submit signup form
5. Check for confirmation email (or verify Supabase user created)
6. Complete auth callback flow
7. Land on onboarding page
8. Enter website URL: `https://umped.com.au/`
9. Wait for ICP extraction (scraper waterfall should run)
10. Review extracted ICP data
11. Confirm ICP
12. Land on dashboard

**What to Check:**
- [ ] Login page loads without errors
- [ ] Signup creates Supabase user
- [ ] Auth callback redirects correctly
- [ ] Client record auto-provisioned
- [ ] Onboarding steps render
- [ ] Scraper waterfall extracts ICP (or falls back to manual)
- [ ] ICP saved to database
- [ ] Dashboard loads with client data

**If Something Fails:**
1. Check browser console / network tab for errors
2. Check backend logs: `railway logs`
3. Trace the failure to specific file using `skills/testing/E2E_TESTING_SKILL.md`
4. Fix the issue
5. Verify fix works
6. Document fix
7. Continue from where you left off

---

### Journey 2: Campaign & Leads (J2)

**User Story:** User creates a campaign and sees leads enriched.

**Steps:**
1. From dashboard, click "Create Campaign"
2. Enter campaign name: "E2E Test Campaign"
3. Select target: 100 leads
4. Configure channels (email primary)
5. Save campaign
6. Wait for lead enrichment (Apollo)
7. Verify leads appear in campaign
8. Check ALS scores calculated
9. Check Hot leads triggered Deep Research

**What to Check:**
- [ ] Campaign creation form works
- [ ] Campaign saved to database
- [ ] Apollo enrichment runs
- [ ] Leads appear in lead_pool
- [ ] Leads assigned to client (lead_assignments)
- [ ] ALS scores populated
- [ ] Hot leads (85+) have Deep Research triggered
- [ ] Content generated for leads

**✅ PROCEED** — TEST_MODE is active, safe to activate campaign.

---

### Journey 3: Outreach Execution (J3)

**TEST_MODE:** ✅ ACTIVE — All outbound redirects to dave (david.stephens@keiracom.com / +61457543392)

**Steps:**
1. Activate campaign
3. Watch for JIT validation running
4. Verify email sent to TEST_EMAIL_RECIPIENT (not real leads)
5. Check activity logged in database
6. Verify no emails to real leads

**What to Check:**
- [ ] Outbound redirected to test recipients (TEST_MODE active)
- [ ] JIT Validator runs pre-send checks
- [ ] Email arrives at david.stephens@keiracom.com
- [ ] Activity table shows send
- [ ] Original lead email NOT contacted
- [ ] Daily limit enforced (max 15)

---

### Journey 4: Reply & Meeting (J4)

**User Story:** Lead replies, system classifies intent and creates meeting.

**Steps:**
1. Send manual reply to test email (simulate webhook)
2. POST webhook to `/webhooks/salesforge/reply` with test payload
3. Verify reply processed
4. Check intent classified
5. Check conversation_thread created
6. Simulate Calendly webhook for meeting booked
7. Verify meeting record created
8. Verify deal record created

**What to Check:**
- [ ] Webhook endpoint accepts POST
- [ ] Reply analyzer classifies intent
- [ ] Conversation thread created
- [ ] Lead status updated to "replied"
- [ ] Meeting webhook processed
- [ ] meetings table has record
- [ ] deals table has record

---

### Journey 5: Dashboard Validation (J5)

**User Story:** Dashboard shows accurate data.

**Steps:**
1. Navigate to /dashboard
2. Check metrics display
3. Compare metrics to database queries
4. Check activity feed populates
5. Check lead list shows correct ALS tiers
6. Test filters work

**Verification Queries:**
```sql
-- Total leads for client
SELECT COUNT(*) FROM lead_assignments WHERE client_id = '[CLIENT_ID]';

-- Hot leads
SELECT COUNT(*) FROM lead_assignments WHERE client_id = '[CLIENT_ID]' AND als_score >= 85;

-- Emails sent today
SELECT COUNT(*) FROM activities WHERE client_id = '[CLIENT_ID]' AND channel = 'email' AND created_at > NOW() - INTERVAL '1 day';
```

**What to Check:**
- [ ] Dashboard loads without errors
- [ ] Metrics match database
- [ ] Activity feed shows recent sends
- [ ] ALS tiers color-coded correctly (Hot=85+, not 80+)
- [ ] Filters work
- [ ] Charts render

---

### Journey 6: Admin Dashboard (J6)

**User Story:** Admin can see platform-wide metrics.

**Steps:**
1. Navigate to /admin
2. Check Command Center loads
3. Verify KPIs display
4. Check client list shows test client
5. Check activity log shows sends
6. Verify system status all green

**What to Check:**
- [ ] Admin route protected (requires admin role)
- [ ] Command Center loads
- [ ] MRR, client count, lead count display
- [ ] Client list shows "Umped"
- [ ] Activity log shows E2E test activities
- [ ] System status shows all healthy

---

## Fix Documentation Format

For every fix you make, add to `docs/audits/E2E_FIXES_{DATE}.md`:

```markdown
### Fix [X]: J[Journey].[Step] - [Brief Title]

**Timestamp:** [ISO 8601]
**Problem:** What failed
**Root Cause:** Why it failed  
**Fix Applied:** What you changed
**Files Modified:**
- `path/to/file1.py` — description of change
- `path/to/file2.tsx` — description of change
**Verification:** How you confirmed the fix works
**Regression Risk:** Low/Medium/High + notes
```

---

## Common Fixes Reference

### Auth Issues
- **Redirect loop** → Check `frontend/app/auth/callback/route.ts`
- **Client not provisioned** → Check `supabase/migrations/016_auto_provision_client.sql` trigger
- **401 on API calls** → Check JWT in Authorization header, refresh token logic in `frontend/lib/api.ts`

### Scraper Issues
- **JSON parse error** → Strip markdown fences in `src/agents/skills/website_parser.py`
- **Empty extraction** → Check waterfall progressing in `src/engines/icp_scraper.py`
- **Cloudflare blocked** → Verify Camoufox tier attempted

### API Issues
- **CORS error** → Add frontend URL to CORS origins in `src/main.py`
- **500 error** → Check Railway logs, trace to specific engine/service

### Database Issues
- **Empty query results** → Check RLS policies, verify `auth.uid()` matches
- **Missing columns** → Check migration applied in Supabase

---

## Completion Criteria

E2E Testing is COMPLETE when:

1. ✅ All 6 journeys pass (J1-J6)
2. ✅ No critical bugs remain (system doesn't crash)
3. ✅ All fixes documented in `docs/audits/E2E_FIXES_{DATE}.md`
4. ✅ `PROGRESS.md` updated with test results
5. ✅ TEST_MODE verified working (no real leads contacted)
6. ✅ Edge cases handled (error states show user-friendly messages)

---

## Output

When complete, provide:

1. **Summary:** Pass/Fail count for each journey
2. **Fixes Applied:** List of all fixes with file references
3. **Remaining Issues:** Any issues requiring human escalation
4. **Next Steps:** What needs to happen next (e.g., disable TEST_MODE for launch)

---

## START

Begin with Journey 1 (J1). Read the skill file first:

```bash
cat skills/testing/E2E_TESTING_SKILL.md
```

Then start testing. Fix issues as you encounter them. Do not stop until all journeys pass or you hit an escalation condition.

Good luck. 🚀
