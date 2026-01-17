# Issues Found During E2E Testing

**Last Updated:** January 12, 2026
**Total Issues:** 2
**Critical:** 1 | **Warning:** 1 | **Info:** 0

---

## How to Use This File

When an issue is found during E2E testing:

1. Assign next available ID (ISS-E2E-XXX)
2. Add to appropriate severity section
3. Fill in all fields
4. Update E2E_MASTER.md summary
5. If Critical → Stop and report to CEO

---

## Critical (Blocks Progress)

*Issues that prevent testing from continuing. Require immediate resolution.*

| ID | Found In | Description | Status |
|----|----------|-------------|--------|
| ISS-E2E-001 | J0.1.2 | Prefect server returning 502 errors | ✅ Resolved |
| ISS-E2E-003 | J1.3 | Verification emails not sending from agencyxos.ai | ✅ Resolved |

### ISS-E2E-003: Auth Verification Emails Not Working
- **Found:** J1.3 — Auto-Provisioning Trigger (email verification test)
- **Severity:** CRITICAL
- **Date Found:** 2026-01-12
- **Description:**
  Supabase Auth is configured to use default SMTP (`noreply@mail.app.supabase.io`). Test verification email to `david.stephens@keiracom.com` did not arrive. Even if it did arrive, emails must come from `agencyxos.ai` for brand trust.
- **Steps to Reproduce:**
  1. Call POST `/auth/v1/signup` with real email
  2. Response shows `confirmation_sent_at` timestamp
  3. Email never arrives (or goes to spam from supabase.io domain)
- **Expected Behavior:**
  Verification email arrives from `noreply@agencyxos.ai` within 1-2 minutes
- **Actual Behavior:**
  No email received. Supabase using default unreliable SMTP.
- **Impact:**
  - Real users CANNOT sign up (no verification = no access)
  - Launch blocked until fixed
  - Brand trust issue (emails from supabase.io not agencyxos.ai)
- **Root Cause:**
  Supabase Auth not configured with custom SMTP. Default SMTP has rate limits and poor deliverability.
- **Proposed Fix:**
  1. Verify `agencyxos.ai` domain in Resend
  2. Get full-access Resend API key
  3. Configure custom SMTP in Supabase Auth settings
- **Requires:** CEO Action (Resend + Supabase dashboard access)
- **Status:** ✅ Resolved
- **Resolved By:** FIX-E2E-007
- **Resolution Date:** January 12, 2026
- **Resolution:**
  1. Verified `agencyxos.ai` domain in Resend (DKIM + SPF)
  2. Configured Supabase Auth SMTP via Management API
  3. Test email received from `noreply@agencyxos.ai`

### ISS-E2E-001: Prefect Server Unhealthy (502 Bad Gateway)
- **Found:** J0.1.2 — Prefect server health check
- **Severity:** CRITICAL
- **Date Found:** 2026-01-12
- **Description:**
  The Prefect server at `https://prefect-server-production-f9b1.up.railway.app` is returning 502 Bad Gateway errors. The API's `/api/v1/health/ready` endpoint confirms Prefect is unhealthy with "Connection failed" message.
- **Steps to Reproduce:**
  1. Call `https://prefect-server-production-f9b1.up.railway.app/api/health`
  2. Observe: 502 Bad Gateway
  3. Call `https://agency-os-production.up.railway.app/api/v1/health/ready`
  4. Observe: `"prefect": {"status": "unhealthy", "message": "Connection failed"}`
- **Expected Behavior:**
  Prefect server returns `{"status": "ok"}` or similar healthy response
- **Actual Behavior:**
  502 Bad Gateway, service unreachable
- **Impact:**
  - All Prefect flows cannot execute
  - Worker cannot connect to deploy/run flows
  - Campaign, outreach, enrichment pipelines blocked
  - J0.1 cannot pass; all subsequent journeys blocked
- **Root Cause:**
  **IDENTIFIED:** `ModuleNotFoundError: No module named 'psycopg2'` — The Dockerfile.prefect was missing the PostgreSQL driver. Server tried to use PostgreSQL (via `PREFECT_API_DATABASE_CONNECTION_URL`) but couldn't connect without the driver.
- **Files Involved:**
  - `Dockerfile.prefect` — Missing psycopg2-binary
  - `scripts/start-prefect-server.sh`
  - Railway `prefect-server` service configuration
- **Fix Applied:** FIX-E2E-002
  Added to Dockerfile.prefect:
  ```dockerfile
  RUN apt-get update && apt-get install -y curl libpq-dev && rm -rf /var/lib/apt/lists/*
  RUN pip install --no-cache-dir psycopg2-binary asyncpg
  ```
- **Requires:** CEO Approval to deploy changes to Railway
- **Status:** ✅ Resolved
- **Assigned To:** —
- **Resolved By:** FIX-E2E-003 (Railway PostgreSQL for Prefect metadata)
- **Resolution Date:** January 12, 2026

---

<!--
### ISS-E2E-XXX: [Title]
- **Found:** J[X].[Y].[Z]
- **Severity:** CRITICAL
- **Description:** [What's wrong]
- **Impact:** [What can't work because of this]
- **Root Cause:** [Why it's happening]
- **Proposed Fix:** [How to fix it]
- **Requires:** [CEO approval / Claude Code can fix]
- **Status:** 🔴 Open | 🟡 In Progress | ✅ Resolved
- **Resolved By:** [Fix ID if resolved]
-->

---

## Warning (Should Fix Before Launch)

*Issues that don't block testing but should be fixed before production use.*

| ID | Found In | Description | Status |
|----|----------|-------------|--------|
| ISS-E2E-002 | J0.2 | High database latency due to Railway region mismatch | ✅ Partially Resolved |

### ISS-E2E-002: High Database Latency (Region Mismatch)
- **Found:** J0.2 — Environment Variables Audit
- **Severity:** WARNING
- **Date Found:** 2026-01-12
- **Description:**
  Health check showed database latency of 3835ms for a simple `SELECT 1` query. Redis latency was 1077ms. Both unacceptably high for production use.
- **Root Cause:**
  Railway services were deployed in `us-west2` (California, USA) while Supabase database is in `aws-1-ap-southeast-1` (Singapore). Cross-Pacific latency caused the high response times.
- **Impact:**
  - All database queries take 2-4 seconds longer than necessary
  - API response times significantly degraded
  - User experience affected
- **Fix Applied:** FIX-E2E-004
  - Changed all Railway services to `asia-southeast1-eqsg3a` (Singapore Metal)
  - Redeployed agency-os, prefect-server, prefect-worker
- **Results After Fix:**
  | Component | Before | After | Improvement |
  |-----------|--------|-------|-------------|
  | Database | 3835ms | 1640ms | -57% |
  | Redis | 1077ms | 242ms | -77% |
  | Prefect | 55ms | 25ms | -55% |
- **Remaining Issue:**
  Database latency still ~1640ms despite same-region deployment. Likely causes:
  - Supabase Supavisor (transaction pooler) overhead
  - TLS + SCRAM-SHA-256 authentication per connection
  - `pool_pre_ping=True` sending extra queries
- **Status:** ✅ Partially Resolved (region fixed, pooler overhead remains)
- **Follow-up:** Consider investigating session pooler vs transaction pooler for persistent connections

<!--
### ISS-E2E-XXX: [Title]
- **Found:** J[X].[Y].[Z]
- **Severity:** WARNING
- **Description:** [What's wrong]
- **Impact:** [What's affected]
- **Proposed Fix:** [How to fix it]
- **Status:** 🔴 Open | ✅ Resolved
-->

---

## Info (Nice to Fix)

*Minor issues, improvements, or technical debt discovered during testing.*

| ID | Found In | Description | Status |
|----|----------|-------------|--------|
| — | — | No info issues | — |

<!--
### ISS-E2E-XXX: [Title]
- **Found:** J[X].[Y].[Z]
- **Severity:** INFO
- **Description:** [What could be improved]
- **Status:** 🔴 Open | ✅ Resolved
-->

---

## Resolved Issues

*Issues that have been fixed. Kept for historical reference.*

| ID | Description | Resolved By | Date |
|----|-------------|-------------|------|
| — | No resolved issues yet | — | — |

---

## Issue Template

Copy this template when adding new issues:

```markdown
### ISS-E2E-XXX: [Brief Title]
- **Found:** J[X].[Y].[Z] — [Sub-task name]
- **Severity:** CRITICAL | WARNING | INFO
- **Date Found:** [YYYY-MM-DD]
- **Description:**
  [Detailed description of what's wrong]
- **Steps to Reproduce:**
  1. [Step 1]
  2. [Step 2]
  3. [Observe: what happens]
- **Expected Behavior:**
  [What should happen]
- **Actual Behavior:**
  [What actually happens]
- **Impact:**
  [What functionality is affected]
- **Root Cause:**
  [Why this is happening, if known]
- **Files Involved:**
  - `path/to/file.py`
  - `path/to/other.ts`
- **Proposed Fix:**
  [How to fix it]
- **Requires:** CEO Approval | Claude Code Can Fix
- **Status:** 🔴 Open
- **Assigned To:** [Claude Code | CEO | TBD]
- **Resolved By:** [FIX-E2E-XXX when resolved]
```
