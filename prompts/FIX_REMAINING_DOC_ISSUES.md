# Fix Remaining Documentation Issues

**Priority:** High
**Estimated Time:** 15 minutes
**Context:** Documentation cleanup audit found 3 issues not resolved

---

## Issue 1: SCHEMA_OVERVIEW.md Missing Migrations

**File:** `docs/specs/database/SCHEMA_OVERVIEW.md`
**Problem:** Shows migrations 001-018, actual range is 001-031 (with gaps)

**Actual migrations in `supabase/migrations/`:**
```
001_foundation.sql
002_clients_users_memberships.sql
003_campaigns.sql
004_leads_suppression.sql
005_activities.sql
006_permission_modes.sql
007_webhook_configs.sql
008_audit_logs.sql
009_rls_policies.sql
010_platform_admin.sql
011_fix_user_insert_policy.sql
012_client_icp_profile.sql
013_campaign_templates.sql
014_conversion_intelligence.sql
015_founding_spots.sql
016_auto_provision_client.sql
017_fix_trigger_schema.sql
021_deep_research.sql
024_lead_pool.sql
025_content_tracking.sql
026_email_engagement.sql
027_conversation_threads.sql
028_downstream_outcomes.sql
029_crm_push.sql
030_customer_import.sql
031_linkedin_credentials.sql
```

**Action:** 
1. Update the "Migration Order" section at the bottom of SCHEMA_OVERVIEW.md to include all migrations
2. Add new table sections for Phase 24 (CIS Data) tables:
   - `lead_pool` (024)
   - `content_tracking` (025)
   - `email_engagement` (026)
   - `conversation_threads` (027)
   - `downstream_outcomes` (028)
   - `crm_push` (029)
   - `customer_import` (030)
   - `linkedin_credentials` (031)
3. Add `deep_research` table (021)

---

## Issue 2: Synthflow → Vapi (8 files)

**Problem:** 8 files still reference "Synthflow" — should be "Vapi"

**Files to fix:**

1. `docs/specs/FULL_SYSTEM_ARCHITECTURE.md`
   - Line ~97: Change "Synthflow" to "Vapi"
   - Line ~137: Change "Synthflow" to "Vapi" 
   - Line ~601: Change "Synthflow" to "Vapi"
   - Line ~895: Change "synthflow.py" to "vapi.py"

2. `docs/user-journey-diagram.html`
   - Line ~325: Change "Synthflow" to "Vapi"

3. `docs/progress/COMPLETED_PHASES.md`
   - Line ~85: Change "Synthflow" to "Vapi"

4. `docs/marketing/EXPERT_PANEL_LANDING_PAGE.md`
   - Line ~228: Change "Synthflow" to "Vapi"

5. `docs/manuals/user-manual.html`
   - Line ~617: Change "Synthflow" to "Vapi"

**Action:** Find and replace all "Synthflow" with "Vapi" in these files. Also replace "synthflow.py" with "vapi.py" where it appears.

---

## Issue 3: FILE_STRUCTURE.md Migration List

**File:** `docs/architecture/FILE_STRUCTURE.md`
**Problem:** Shows migrations 001-018, should show actual migrations 001-031

**Action:** Update the "Database Migrations" section to match actual migrations in `supabase/migrations/`.

---

## Verification Checklist

After completing all fixes:

- [ ] SCHEMA_OVERVIEW.md shows all 25 migrations (001-017, 021, 024-031)
- [ ] SCHEMA_OVERVIEW.md has table documentation for Phase 24 tables
- [ ] `grep -r "Synthflow" docs/` returns 0 results
- [ ] `grep -r "synthflow" docs/` returns 0 results
- [ ] FILE_STRUCTURE.md migration list matches actual migrations
- [ ] Mark ISS-001 and ISS-003 as RESOLVED in `docs/progress/ISSUES.md`

---

## Session Log Entry

After completion, append to `docs/progress/SESSION_LOG.md`:

```markdown
### Jan 8, 2026 — Fix Remaining Doc Issues
**Completed:** ISS-001 (SCHEMA_OVERVIEW migrations), ISS-003 (Synthflow→Vapi)
**Summary:** Updated SCHEMA_OVERVIEW.md with migrations 021-031 and Phase 24 tables. Replaced all Synthflow references with Vapi across 5 files. Updated FILE_STRUCTURE.md migration list.
**Files Changed:** 7
**Blockers:** None
**Next:** E2E testing (Phase 21)
```
