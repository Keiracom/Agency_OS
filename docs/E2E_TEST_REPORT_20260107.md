# E2E Pre-Flight Test Report

**Test Run ID:** 20260107163403
**Date:** 2026-01-07
**Environment:** Production (Railway)
**API Base:** https://agency-os-production.up.railway.app/api/v1

---

## Test Credentials (for Manual Browser Testing)

```
Email: e2e.test.20260107163403@gmail.com
Password: TestPass123
User ID: 498bec56-9a14-4cdd-8495-67855d45b5a3
Client ID: 10d1ffbc-1ff1-460d-b3d0-9eaba2c59aaf
```

---

## Summary

| Journey | Status | Pass/Fail |
|---------|--------|-----------|
| 1. Signup & Onboarding | Complete | PASS (with fixes) |
| 2. Campaign & Lead Enrichment | Partial | PARTIAL |
| 3. Content & Outreach | Partial | PARTIAL |
| 4. Reply Handling | Skipped | N/A (no actual outreach) |
| 5. Dashboard Stats | Complete | PARTIAL |
| 6. Admin Panel | Blocked | FAIL (bug found & fixed) |

**Total Bugs Found:** 4
**Total Bugs Fixed:** 1
**Bugs Requiring Backend Redeploy:** 1

---

## Journey 1: Signup & Onboarding

### Step 1.1: User Signup
| Check | Result | Details |
|-------|--------|---------|
| Create user via Supabase Auth | PASS | Used Supabase Auth REST API |
| Email auto-confirmed | PASS | Used Admin API with service key |
| Login returns JWT | PASS | Access token retrieved |

### Step 1.2: Auto-Provisioning
| Check | Result | Details |
|-------|--------|---------|
| User record created | PASS | `users` table has record |
| Client auto-provisioned | PASS | Client ID: `10d1ffbc-1ff1-460d-b3d0-9eaba2c59aaf` |
| Membership created | PASS | Role: `owner` |

### Step 1.3: ICP Extraction
| Check | Result | Details |
|-------|--------|---------|
| Submit website (umped.com.au) | PASS | Job ID returned |
| Poll status until complete | PASS | ICP extracted successfully |
| Confirm ICP | PASS | Endpoint called successfully |
| ICP profile saved | PASS | Target industries, titles extracted |

**ICP Extracted:**
- Industries: Small Business, Entrepreneurship, Marketing Services
- Titles: Founder, CEO, Director, Business Owner
- Revenue: $1M - $10M
- Location: Australia

---

## Journey 2: Campaign & Lead Enrichment

### Step 2.1: Campaign Creation
| Check | Result | Details |
|-------|--------|---------|
| Create campaign | PASS | Campaign ID: `20f2be90-f401-4eb2-8dd5-eb2bd0e93dca` |
| Campaign in database | PASS | Status: `draft` |

### Step 2.2: Pool Population
| Check | Result | Details |
|-------|--------|---------|
| Trigger pool population | PASS | HTTP 202 returned |
| Leads added to pool | **FAIL** | No leads appearing after polling |

**Issue:** Pool population runs via Prefect flow (`pool_population_flow`) but the flow doesn't seem to be executing. Leads are not appearing in the pool.

### Step 2.3: Lead Creation (Manual)
| Check | Result | Details |
|-------|--------|---------|
| Create test lead directly | PASS | Lead ID: `e96039f3-a1d0-4499-8d8d-933b929d3d76` |
| Lead in database | PASS | Status: `new` |

### Step 2.4: Lead Enrichment
| Check | Result | Details |
|-------|--------|---------|
| Trigger enrichment | **PARTIAL** | API returns success but enrichment doesn't process |
| Apollo data fetched | **FAIL** | No enrichment data populated |
| ALS score calculated | **FAIL** | Score remains 0 |

**Issue:** Lead enrichment has `# TODO: Trigger enrichment flow via Prefect` in the code. The Prefect integration is not wired up.

---

## Journey 3: Content & Outreach

### Step 3.1: Campaign Activation
| Check | Result | Details |
|-------|--------|---------|
| Activate campaign | PASS | Status changed to `active` |
| Lead assigned to campaign | PASS | Manually updated status |

### Step 3.2: Outreach Execution
| Check | Result | Details |
|-------|--------|---------|
| Outreach triggered | **N/A** | No direct API endpoint |
| Email sent | **N/A** | Runs via `hourly_outreach_flow` |
| SMS sent | **N/A** | Runs via `hourly_outreach_flow` |

**Issue:** Outreach runs on a schedule via Prefect (`hourly_outreach_flow`), not directly triggerable via API. Would need to wait for scheduled flow or manually invoke.

---

## Journey 4: Reply Handling

**Status:** SKIPPED - No actual outreach occurred, so no replies to process.

---

## Journey 5: Dashboard Stats

### Step 5.1: Campaign Stats
| Check | Result | Details |
|-------|--------|---------|
| Campaign in list | PASS | Shows with status `active` |
| Campaign total_leads | **FAIL** | Shows `0` despite 1 lead existing |

**Bug:** Campaign `total_leads` counter not updating when leads are added.

### Step 5.2: Lead Stats
| Check | Result | Details |
|-------|--------|---------|
| Lead in list | PASS | Test lead appears |
| Lead has correct status | PASS | Status: `in_sequence` |

---

## Journey 6: Admin Panel

### Step 6.1: Admin Access
| Check | Result | Details |
|-------|--------|---------|
| Set user as platform admin | PASS | `is_platform_admin = true` in DB |
| Get fresh JWT | PASS | New token obtained |
| Access /admin/stats | **FAIL** | Returns "Platform admin access required" |

**Root Cause Found:** The `User` SQLAlchemy model in `src/models/user.py` was missing the `is_platform_admin` column mapping. The database has the column (from migration 010), but the model didn't map it, so `getattr(user, 'is_platform_admin', False)` always returned `False`.

**Fix Applied:** Added `is_platform_admin` column to `src/models/user.py:76-80`.

---

## Bugs Found & Fixed

### Bug 1: User model missing is_platform_admin column (FIXED)

**File:** `src/models/user.py:76-80`
**Severity:** Critical (Admin panel completely broken)
**Status:** FIXED locally, needs production redeploy

```python
# Added:
is_platform_admin: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
)
```

---

## Bugs Found (Pending Fix)

### Bug 2: Pool Population Not Processing

**Location:** `src/orchestration/flows/pool_population_flow.py`
**Severity:** High
**Symptom:** API returns 202 Accepted but leads don't appear
**Likely Cause:** Prefect flow not being scheduled/executed

### Bug 3: Lead Enrichment Not Processing

**Location:** `src/api/routes/leads.py` (TODO comment at enrichment trigger)
**Severity:** High
**Symptom:** Enrichment endpoint returns success but no data populated
**Likely Cause:** Prefect flow not wired up

### Bug 4: Campaign total_leads Counter Not Updating

**Location:** Campaign model or lead assignment logic
**Severity:** Medium
**Symptom:** Campaign shows 0 leads despite having leads assigned
**Likely Cause:** Counter not incremented when leads added

---

## Test Data Created

| Entity | ID | Status |
|--------|-----|--------|
| User | `498bec56-9a14-4cdd-8495-67855d45b5a3` | Active |
| Client | `10d1ffbc-1ff1-460d-b3d0-9eaba2c59aaf` | Active |
| Campaign | `20f2be90-f401-4eb2-8dd5-eb2bd0e93dca` | Active |
| Lead | `e96039f3-a1d0-4499-8d8d-933b929d3d76` | In Sequence |

---

## Recommendations

### Immediate (Before Manual Testing)

1. **Redeploy backend** to pick up User model fix for admin access
2. Verify admin panel works after redeploy

### Short-term (This Sprint)

1. Fix pool population flow execution
2. Wire up lead enrichment to Prefect flow
3. Fix campaign total_leads counter

### For Manual Browser Testing

Use the test credentials above. The following should work:

- [x] Login
- [x] View ICP profile
- [x] Create campaigns
- [x] View campaigns list
- [x] Create leads manually
- [x] View leads list
- [ ] Admin panel (blocked until redeploy)
- [ ] Pool population (blocked - Prefect issue)
- [ ] Lead enrichment (blocked - Prefect issue)

---

## Appendix: API Endpoints Tested

| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | 200 OK |
| `/onboarding/analyze` | POST | 200 OK |
| `/onboarding/status/{job_id}` | GET | 200 OK |
| `/onboarding/confirm` | POST | 200 OK |
| `/clients/{id}/campaigns` | POST | 201 Created |
| `/clients/{id}/campaigns` | GET | 200 OK |
| `/clients/{id}/campaigns/{id}` | GET | 200 OK |
| `/clients/{id}/campaigns/{id}/activate` | POST | 200 OK |
| `/clients/{id}/leads` | POST | 201 Created |
| `/clients/{id}/leads` | GET | 200 OK |
| `/pool/populate` | POST | 202 Accepted |
| `/admin/stats` | GET | 401 (bug) |
