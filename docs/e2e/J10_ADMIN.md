# J10: Admin Dashboard Journey

**Status:** 🟢 Ready for Testing
**Priority:** P1 — Platform management interface
**Depends On:** J1-J9 Complete (for platform data)
**Last Updated:** January 11, 2026
**Sub-Tasks:** 15 groups, 60 individual checks

---

## Overview

Tests platform-wide admin functionality — the CEO/operator view of all clients and system health.

**Key Finding from Code Review:**
- Admin dashboard uses live data via `useAdminStats`, `useSystemHealth`, `useAlerts`, `useGlobalActivity`
- Command Center shows MRR, active clients, leads today, AI spend
- Client directory with health scores and tier/status badges
- 21 admin pages total covering all aspects

**✅ RESOLVED (January 11, 2026):**
AI Costs page now uses real API data:
- Backend endpoint `/admin/costs/ai` updated to use real Redis data
- Today's spend from `ai_spend_tracker.get_spend()`
- Daily limit from `settings.anthropic_daily_spend_limit`
- Frontend updated to use `useAISpend` hook instead of mock data
- Agent/client breakdown estimated (full tracking needs ai_usage_logs table)

**User Journey:**
```
Admin Login → Command Center → Client Directory → Client Detail → System Health → Costs → Compliance
```

---

## Test URL

| Field | Value |
|-------|-------|
| Frontend URL | https://agency-os-liart.vercel.app |
| Admin | /admin |
| Clients | /admin/clients |
| Revenue | /admin/revenue |
| System | /admin/system |
| AI Costs | /admin/costs/ai |

---

## Sub-Tasks

### J10.1 — Admin Access Control
**Purpose:** Verify admin access is restricted to platform admins.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.1.1 | Read `require_platform_admin` dependency | Check code |
| J10.1.2 | Verify `is_platform_admin` check in dependencies | N/A |
| J10.1.3 | Verify admin layout checks role | Check frontend |
| J10.1.4 | Test access without admin role | Verify blocked |
| J10.1.5 | Test access with admin role | Verify allowed |

**Admin Dependency (VERIFIED from admin.py):**
```python
from src.api.dependencies import (
    AdminContext,
    get_admin_context,
    require_platform_admin,
)
```

**Pass Criteria:**
- [ ] Non-admin users blocked
- [ ] Admin users allowed
- [ ] RLS policies enforced

<!-- E2E_SESSION_BREAK: J10.1 complete. Next: J10.2 Command Center Page -->

---

### J10.2 — Command Center Page
**Purpose:** Verify Command Center loads with live data.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.2.1 | Read `frontend/app/admin/page.tsx` (309 lines) | Load page |
| J10.2.2 | Verify `useAdminStats` hook | Check API call |
| J10.2.3 | Verify `useSystemHealth` hook | Check API call |
| J10.2.4 | Verify `useAlerts` hook | Check API call |
| J10.2.5 | Verify `useGlobalActivity` hook | Check API call |
| J10.2.6 | Verify error/loading states | Test states |

**Command Center Hooks (VERIFIED from page.tsx):**
```typescript
const { data: stats } = useAdminStats();
const { data: health } = useSystemHealth();
const { data: alertsData } = useAlerts();
const { data: activities } = useGlobalActivity(10);
```

**Pass Criteria:**
- [ ] Page renders without errors
- [ ] All hooks fire
- [ ] Data displays correctly

<!-- E2E_SESSION_BREAK: J10.2 complete. Next: J10.3 KPI Section -->

---

### J10.3 — KPI Section
**Purpose:** Verify KPI cards show accurate platform metrics.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.3.1 | Verify MRR calculation | Compare to DB |
| J10.3.2 | Verify MRR change MoM | Check calculation |
| J10.3.3 | Verify active clients count | Compare to DB |
| J10.3.4 | Verify new clients this month | Check count |
| J10.3.5 | Verify leads today count | Compare to DB |
| J10.3.6 | Verify leads change vs yesterday | Check math |
| J10.3.7 | Verify AI spend today | Compare to Redis |
| J10.3.8 | Verify AI spend limit | Check config |

**KPI Fields (VERIFIED from admin.py KPIStats model):**
- mrr: Monthly Recurring Revenue in AUD
- mrr_change: MRR change percentage MoM
- active_clients: Count of active clients
- new_clients_this_month: New clients this month
- leads_today: Leads created today
- leads_change: Leads change vs yesterday
- ai_spend_today: AI spend today in AUD
- ai_spend_limit: Daily AI spend limit in AUD

**Pass Criteria:**
- [ ] MRR matches sum of client MRRs
- [ ] Active clients count accurate
- [ ] Leads today matches database
- [ ] AI spend matches Redis tracking

<!-- E2E_SESSION_BREAK: J10.3 complete. Next: J10.4 System Status Section -->

---

### J10.4 — System Status Section
**Purpose:** Verify system health status displays.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.4.1 | Verify `/admin/system/health` endpoint | Call API |
| J10.4.2 | Verify service statuses (API, Prefect, DB, Redis) | Check display |
| J10.4.3 | Verify latency displayed | Check values |
| J10.4.4 | Verify status colors (healthy=green, degraded=yellow, down=red) | Check UI |

**Service Status (VERIFIED from admin.py):**
```python
class ServiceStatus(BaseModel):
    name: str
    status: str  # healthy, degraded, or down
    latency_ms: Optional[float] = None
    message: Optional[str] = None
```

**Pass Criteria:**
- [ ] All services shown
- [ ] Status colors correct
- [ ] Latencies displayed
- [ ] Matches actual health checks

<!-- E2E_SESSION_BREAK: J10.4 complete. Next: J10.5 Alerts Section -->

---

### J10.5 — Alerts Section
**Purpose:** Verify platform alerts display.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.5.1 | Verify alerts API endpoint | Call API |
| J10.5.2 | Verify alert severity (critical, warning, info) | Check badges |
| J10.5.3 | Verify alert dismissal | Test dismiss |
| J10.5.4 | Verify alert links | Click through |

**Pass Criteria:**
- [ ] Alerts display
- [ ] Severity badges correct
- [ ] Dismissal works
- [ ] Critical alerts highlighted

<!-- E2E_SESSION_BREAK: J10.5 complete. Next: J10.6 Live Activity Feed -->

---

### J10.6 — Live Activity Feed
**Purpose:** Verify global activity feed shows platform-wide activity.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.6.1 | Verify global activity API endpoint | Call API |
| J10.6.2 | Verify activities from all clients | Check data |
| J10.6.3 | Verify client name displayed | Check column |
| J10.6.4 | Verify channel displayed | Check icon/badge |
| J10.6.5 | Verify auto-refresh | Wait and observe |

**Pass Criteria:**
- [ ] Activities from all clients shown
- [ ] Client names displayed
- [ ] Channel icons correct
- [ ] Auto-refresh working

<!-- E2E_SESSION_BREAK: J10.6 complete. Next: J10.7 Client Directory -->

---

### J10.7 — Client Directory
**Purpose:** Verify client list with filtering.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.7.1 | Read `frontend/app/admin/clients/page.tsx` | Load page |
| J10.7.2 | Verify `useAdminClients` hook | Check API call |
| J10.7.3 | Verify search by client name | Test search |
| J10.7.4 | Verify status filter (active, trialing, cancelled) | Test filter |
| J10.7.5 | Verify tier display (Ignition, Velocity, Dominance) | Check badges |
| J10.7.6 | Verify health score badge | Check display |
| J10.7.7 | Verify pagination | Navigate pages |

**Tier Colors (VERIFIED from clients/page.tsx):**
```typescript
const tierColors: Record<string, string> = {
  ignition: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  velocity: "bg-purple-500/10 text-purple-700 border-purple-500/20",
  dominance: "bg-amber-500/10 text-amber-700 border-amber-500/20",
};
```

**Pass Criteria:**
- [ ] All clients listed
- [ ] Search works
- [ ] Filters work
- [ ] Tier badges correct
- [ ] Health scores displayed

<!-- E2E_SESSION_BREAK: J10.7 complete. Next: J10.8 Client Detail Page -->

---

### J10.8 — Client Detail Page
**Purpose:** Verify client detail view.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.8.1 | Read `frontend/app/admin/clients/[id]/page.tsx` | Load page |
| J10.8.2 | Verify client info displayed | Check fields |
| J10.8.3 | Verify campaigns list | Check table |
| J10.8.4 | Verify team members list | Check table |
| J10.8.5 | Verify recent activity | Check timeline |

**Client Detail Fields (VERIFIED from admin.py):**
- id, name, tier, subscription_status
- credits_remaining, default_permission_mode
- stripe_customer_id
- health_score
- campaigns, team_members, recent_activity

**Pass Criteria:**
- [ ] Client info accurate
- [ ] Campaigns shown
- [ ] Team members shown
- [ ] Activity timeline works

<!-- E2E_SESSION_BREAK: J10.8 complete. Next: J10.9 Revenue Page -->

---

### J10.9 — Revenue Page
**Purpose:** Verify revenue tracking.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.9.1 | Read `frontend/app/admin/revenue/page.tsx` | Load page |
| J10.9.2 | Verify MRR breakdown by tier | Check table |
| J10.9.3 | Verify churn tracking | Check metrics |
| J10.9.4 | Verify LTV calculation | Check value |

**Pass Criteria:**
- [ ] MRR breakdown accurate
- [ ] Tier split correct
- [ ] Churn tracked
- [ ] Revenue trends work

<!-- E2E_SESSION_BREAK: J10.9 complete. Next: J10.10 AI Costs Page -->

---

### J10.10 — AI Costs Page
**Purpose:** Verify AI spend tracking.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.10.1 | Read `frontend/app/admin/costs/ai/page.tsx` | Load page |
| J10.10.2 | ⚠️ **VERIFY:** Check if using mock data | Inspect code |
| J10.10.3 | Verify today spend vs limit | Check values |
| J10.10.4 | Verify spend by agent breakdown | Check table |
| J10.10.5 | Verify spend by client breakdown | Check table |
| J10.10.6 | Verify daily trend chart | Check display |

**⚠️ ISSUE FOUND:**
```typescript
// frontend/app/admin/costs/ai/page.tsx line 24
const mockSpendData = {
  // ... hardcoded mock data
};
```

**Pass Criteria:**
- [ ] ⚠️ **AI Costs page uses MOCK DATA** - must connect to real API
- [ ] Today spend accurate (when fixed)
- [ ] Agent breakdown works
- [ ] Client breakdown works

<!-- E2E_SESSION_BREAK: J10.10 complete. Next: J10.11 System Errors Page -->

---

### J10.11 — System Errors Page
**Purpose:** Verify Sentry error integration.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.11.1 | Read `frontend/app/admin/system/errors/page.tsx` | Load page |
| J10.11.2 | Verify errors displayed from Sentry | Check list |
| J10.11.3 | Verify error details link | Click through |
| J10.11.4 | Trigger test error, verify appears | Test flow |

**Pass Criteria:**
- [ ] Errors page loads
- [ ] Recent errors listed
- [ ] Links to Sentry work
- [ ] New errors appear

<!-- E2E_SESSION_BREAK: J10.11 complete. Next: J10.12 System Queues Page -->

---

### J10.12 — System Queues Page
**Purpose:** Verify Prefect flow status display.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.12.1 | Read `frontend/app/admin/system/queues/page.tsx` | Load page |
| J10.12.2 | Verify flow runs listed | Check table |
| J10.12.3 | Verify flow status (completed, failed, running) | Check badges |
| J10.12.4 | Verify links to Prefect UI | Click through |

**Pass Criteria:**
- [ ] Queues page loads
- [ ] Flow runs displayed
- [ ] Status badges correct
- [ ] Prefect UI accessible

<!-- E2E_SESSION_BREAK: J10.12 complete. Next: J10.13 Rate Limits Page -->

---

### J10.13 — Rate Limits Page
**Purpose:** Verify rate limit monitoring.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.13.1 | Read `frontend/app/admin/system/rate-limits/page.tsx` | Load page |
| J10.13.2 | Verify current rate limit usage | Check values |
| J10.13.3 | Verify limits per resource type | Check breakdown |

**Pass Criteria:**
- [ ] Rate limits page loads
- [ ] Current usage displayed
- [ ] Per-resource breakdown works

<!-- E2E_SESSION_BREAK: J10.13 complete. Next: J10.14 Compliance Pages -->

---

### J10.14 — Compliance Pages
**Purpose:** Verify compliance management (suppression list, bounces).

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.14.1 | Read `frontend/app/admin/compliance/page.tsx` | Load page |
| J10.14.2 | Read `compliance/suppression/page.tsx` | Load page |
| J10.14.3 | Read `compliance/bounces/page.tsx` | Load page |
| J10.14.4 | Verify suppression list displays | Check table |
| J10.14.5 | Verify add to suppression list | Test action |
| J10.14.6 | Verify bounce list displays | Check table |

**Suppression Entry (VERIFIED from admin.py):**
```python
class SuppressionEntry(BaseModel):
    id: UUID
    email: str
    reason: str  # unsubscribe, bounce, spam, manual
    source: Optional[str]
    added_by_email: Optional[str]
    notes: Optional[str]
    created_at: datetime
```

**Pass Criteria:**
- [ ] Suppression list works
- [ ] Add suppression works
- [ ] Bounces listed
- [ ] Reasons displayed

<!-- E2E_SESSION_BREAK: J10.14 complete. Next: J10.15 Admin Settings -->

---

### J10.15 — Admin Settings
**Purpose:** Verify platform settings management.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J10.15.1 | Read `frontend/app/admin/settings/page.tsx` | Load page |
| J10.15.2 | Read `admin/settings/users/page.tsx` | Load page |
| J10.15.3 | Verify user management | Check table |
| J10.15.4 | Verify role assignment | Test action |

**Pass Criteria:**
- [ ] Settings page loads
- [ ] User management works
- [ ] Roles assignable

<!-- E2E_SESSION_BREAK: J10.15 complete. J10 JOURNEY COMPLETE. E2E TESTING COMPLETE. -->

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Admin Layout | `frontend/app/admin/layout.tsx` | - | ✅ VERIFIED |
| Command Center | `frontend/app/admin/page.tsx` | 309 | ✅ VERIFIED |
| Clients Page | `frontend/app/admin/clients/page.tsx` | 200+ | ✅ VERIFIED |
| AI Costs Page | `frontend/app/admin/costs/ai/page.tsx` | 150+ | ⚠️ MOCK DATA |
| Admin API | `src/api/routes/admin.py` | 500+ | ✅ VERIFIED |

---

## Admin Pages Inventory

| Page | Path | Status |
|------|------|--------|
| Command Center | /admin | ✅ Live Data |
| Clients | /admin/clients | ✅ Live Data |
| Client Detail | /admin/clients/[id] | ✅ Live Data |
| Campaigns | /admin/campaigns | TBD |
| Leads | /admin/leads | TBD |
| Replies | /admin/replies | TBD |
| Activity | /admin/activity | ✅ Live Data |
| Revenue | /admin/revenue | TBD |
| Costs | /admin/costs | TBD |
| AI Costs | /admin/costs/ai | ⚠️ Mock Data |
| Channel Costs | /admin/costs/channels | TBD |
| System | /admin/system | TBD |
| Errors | /admin/system/errors | TBD |
| Queues | /admin/system/queues | TBD |
| Rate Limits | /admin/system/rate-limits | TBD |
| Compliance | /admin/compliance | TBD |
| Suppression | /admin/compliance/suppression | TBD |
| Bounces | /admin/compliance/bounces | TBD |
| Settings | /admin/settings | TBD |
| Users | /admin/settings/users | TBD |

---

## Completion Criteria

All checks must pass:

- [ ] **J10.1** Admin access control working
- [ ] **J10.2** Command Center loads
- [ ] **J10.3** KPIs accurate
- [ ] **J10.4** System status accurate
- [ ] **J10.5** Alerts display
- [ ] **J10.6** Live activity works
- [ ] **J10.7** Client directory works
- [ ] **J10.8** Client detail works
- [ ] **J10.9** Revenue tracking works
- [ ] **J10.10** ⚠️ AI costs (MOCK DATA - needs fix)
- [ ] **J10.11** System errors work
- [ ] **J10.12** System queues work
- [ ] **J10.13** Rate limits work
- [ ] **J10.14** Compliance pages work
- [ ] **J10.15** Admin settings work

---

## CTO Verification Notes

**Code Review Completed:** January 11, 2026

**Key Findings:**
1. ✅ Command Center uses live data
2. ✅ Client directory with health scores
3. ✅ System health monitoring
4. ✅ Global activity feed
5. ✅ Alerts system
6. ⚠️ **AI Costs page uses MOCK DATA**
7. ✅ Admin API with proper access control
8. ✅ 21 admin pages covering all areas

**Issues Found:**
1. ⚠️ `frontend/app/admin/costs/ai/page.tsx` uses `mockSpendData` (line 24) instead of real API

**Required Fix:**
Connect AI Costs page to real API endpoint that queries `ai_usage_logs` table and Redis AI spend tracking.

---

## Notes

**Admin Access:**
Admin access requires `is_platform_admin = true` on the user record. This is enforced via `require_platform_admin` dependency on all admin routes.

**AI Cost Tracking:**
AI costs are tracked in Redis (`v1:ai_spend:daily:{date}`) and should be stored in `ai_usage_logs` table. The AI Costs page needs to be connected to this data.

**Health Scores:**
Client health scores are calculated based on:
- Campaign activity
- Lead engagement
- Payment status
- Support tickets

Health score colors: Green (80+), Yellow (50-79), Red (<50)
