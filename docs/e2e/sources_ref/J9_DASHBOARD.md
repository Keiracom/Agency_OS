# J9: Client Dashboard Journey

**Status:** 🟡 Sub-tasks Defined (Pending CEO Approval)
**Priority:** P1 — Client-facing interface
**Depends On:** J1-J8 Complete (for real data to display)
**Last Updated:** January 11, 2026
**Sub-Tasks:** 14 groups, 52 individual checks

---

## Overview

Validates that the client dashboard displays accurate data matching database state.

**Key Finding from Code Review:**
- Dashboard uses React Query with real API calls (not mocked)
- Auto-refresh on 30-60 second intervals
- Stats, activity feed, ALS distribution all working
- Reports page has channel performance breakdown
- Leads page has tier filtering and pagination

**User Journey:**
```
Client Login → Dashboard Home → View Stats → Activity Feed → Leads List → Campaign Details → Reports
```

---

## Test URL

| Field | Value |
|-------|-------|
| Frontend URL | https://agency-os-liart.vercel.app |
| Dashboard | /dashboard |
| Leads | /dashboard/leads |
| Campaigns | /dashboard/campaigns |
| Reports | /dashboard/reports |

---

## Sub-Tasks

### J9.1 — Dashboard Page Load
**Purpose:** Verify dashboard page renders without errors.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.1.1 | Read `frontend/app/dashboard/page.tsx` (313 lines) | Load page in browser |
| J9.1.2 | Verify `useDashboardStats` hook used | Check network request |
| J9.1.3 | Verify `useActivityFeed` hook used | Check network request |
| J9.1.4 | Verify `useALSDistribution` hook used | Check network request |
| J9.1.5 | Verify loading states render | Check skeleton display |
| J9.1.6 | Verify error states render | Simulate API error |

**Dashboard Hooks (VERIFIED from page.tsx):**
```typescript
const { data: stats, isLoading: statsLoading, error: statsError } = useDashboardStats();
const { data: activities, isLoading: activitiesLoading } = useActivityFeed(10);
const { data: alsDistribution, isLoading: alsLoading } = useALSDistribution();
```

**Pass Criteria:**
- [ ] Dashboard renders without console errors
- [ ] All 3 data hooks fire on load
- [ ] Loading skeletons display while fetching
- [ ] Errors display with retry option

<!-- E2E_SESSION_BREAK: J9.1 complete. Next: J9.2 Dashboard Stats API -->

---

### J9.2 — Dashboard Stats API
**Purpose:** Verify dashboard stats endpoint returns accurate data.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.2.1 | Read `src/api/routes/reports.py` — verify stats endpoint | Call API |
| J9.2.2 | Verify `active_campaigns` count | Compare to DB |
| J9.2.3 | Verify `total_leads` count | Compare to DB |
| J9.2.4 | Verify `leads_contacted` count | Compare to DB |
| J9.2.5 | Verify `leads_replied` count | Compare to DB |
| J9.2.6 | Verify `leads_converted` count | Compare to DB |
| J9.2.7 | Verify `reply_rate` calculation | Check math |
| J9.2.8 | Verify `conversion_rate` calculation | Check math |

**Dashboard Stats Fields (VERIFIED from reports.py):**
- active_campaigns
- total_leads
- leads_contacted
- leads_replied
- leads_converted
- reply_rate (leads_replied / leads_contacted * 100)
- conversion_rate (leads_converted / total_leads * 100)

**Pass Criteria:**
- [ ] All counts match database queries
- [ ] Rates calculated correctly
- [ ] Client-scoped (only sees their data)

<!-- E2E_SESSION_BREAK: J9.2 complete. Next: J9.3 Activity Feed -->

---

### J9.3 — Activity Feed
**Purpose:** Verify activity feed displays recent activities.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.3.1 | Verify activity feed API endpoint | Call API |
| J9.3.2 | Verify activities sorted by created_at DESC | Check order |
| J9.3.3 | Verify channel icons display (email, sms, linkedin) | Check UI |
| J9.3.4 | Verify lead name and company shown | Check data |
| J9.3.5 | Verify time ago formatting | Check "5m ago", "2h ago" |
| J9.3.6 | Verify 30-second auto-refresh | Wait and observe |

**Activity Display (VERIFIED from page.tsx):**
- Channel icon (Mail, Phone, Linkedin)
- Lead name (first_name, last_name)
- Company name
- Action (email_sent, sms_sent, etc.)
- Time ago (formatTimeAgo function)

**Pass Criteria:**
- [ ] Activities display chronologically
- [ ] Channel icons correct
- [ ] Lead info displayed
- [ ] Auto-refresh working

<!-- E2E_SESSION_BREAK: J9.3 complete. Next: J9.4 ALS Distribution Widget -->

---

### J9.4 — ALS Distribution Widget
**Purpose:** Verify ALS tier distribution displays correctly.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.4.1 | Verify ALS distribution API endpoint | Call API |
| J9.4.2 | Verify 5 tiers displayed (Hot, Warm, Cool, Cold, Dead) | Check UI |
| J9.4.3 | Verify tier colors correct | Hot=red, Warm=orange, etc. |
| J9.4.4 | Verify percentages sum to 100% | Check math |
| J9.4.5 | Verify counts match database | Compare to query |
| J9.4.6 | Verify progress bars render | Check visual |

**Tier Colors (VERIFIED from page.tsx lines 38-44):**
```typescript
const tierColors: Record<ALSTier, string> = {
  hot: "bg-red-500",
  warm: "bg-orange-500",
  cool: "bg-blue-500",
  cold: "bg-gray-400",
  dead: "bg-gray-200",
};
```

**Pass Criteria:**
- [ ] All 5 tiers displayed
- [ ] Colors correct per tier
- [ ] Percentages accurate
- [ ] Counts match database

<!-- E2E_SESSION_BREAK: J9.4 complete. Next: J9.5 Meetings Widget -->

---

### J9.5 — Meetings Widget
**Purpose:** Verify upcoming meetings widget works.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.5.1 | Verify MeetingsWidget component rendered | Check page.tsx line 234 |
| J9.5.2 | Verify meetings API endpoint called | Check network |
| J9.5.3 | Verify upcoming meetings listed | Check data |
| J9.5.4 | Verify meeting times formatted | Check display |

**Pass Criteria:**
- [ ] Meetings widget renders
- [ ] Upcoming meetings listed
- [ ] Empty state if no meetings

<!-- E2E_SESSION_BREAK: J9.5 complete. Next: J9.6 Leads List Page -->

---

### J9.6 — Leads List Page
**Purpose:** Verify leads list displays with filtering.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.6.1 | Read `frontend/app/dashboard/leads/page.tsx` | Load page |
| J9.6.2 | Verify `useLeads` hook with pagination | Check network |
| J9.6.3 | Verify search by name/email/company | Test search |
| J9.6.4 | Verify tier filter (click tier badges) | Test filter |
| J9.6.5 | Verify pagination (20 per page) | Navigate pages |
| J9.6.6 | Verify Export button exists | Check UI |
| J9.6.7 | Verify Import button exists | Check UI |

**Pass Criteria:**
- [ ] Leads list loads
- [ ] Search works
- [ ] Tier filter works
- [ ] Pagination works

<!-- E2E_SESSION_BREAK: J9.6 complete. Next: J9.7 Lead Detail Page -->

---

### J9.7 — Lead Detail Page
**Purpose:** Verify lead detail page shows all fields.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.7.1 | Read `frontend/app/dashboard/leads/[id]/page.tsx` | Load page |
| J9.7.2 | Verify lead info displayed (name, email, company) | Check fields |
| J9.7.3 | Verify ALS score and tier displayed | Check badge |
| J9.7.4 | Verify activity history shown | Check timeline |
| J9.7.5 | Verify LinkedIn URL clickable | Test link |

**Pass Criteria:**
- [ ] Lead detail loads
- [ ] All fields displayed
- [ ] ALS tier badge correct
- [ ] Activity timeline works

<!-- E2E_SESSION_BREAK: J9.7 complete. Next: J9.8 Campaigns List Page -->

---

### J9.8 — Campaigns List Page
**Purpose:** Verify campaigns list displays correctly.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.8.1 | Read `frontend/app/dashboard/campaigns/page.tsx` | Load page |
| J9.8.2 | Verify campaigns API endpoint called | Check network |
| J9.8.3 | Verify status badges (Active, Paused, Complete) | Check display |
| J9.8.4 | Verify lead counts per campaign | Check data |
| J9.8.5 | Verify "New Campaign" button | Check UI |

**Pass Criteria:**
- [ ] Campaigns list loads
- [ ] Status badges correct
- [ ] Lead counts accurate
- [ ] Create button works

<!-- E2E_SESSION_BREAK: J9.8 complete. Next: J9.9 Campaign Detail Page -->

---

### J9.9 — Campaign Detail Page
**Purpose:** Verify campaign detail page shows all info.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.9.1 | Read `frontend/app/dashboard/campaigns/[id]/page.tsx` | Load page |
| J9.9.2 | ⚠️ **VERIFY:** Check if using mock data | Inspect network/code |
| J9.9.3 | Verify campaign metrics displayed | Check stats |
| J9.9.4 | Verify lead list for campaign | Check leads |
| J9.9.5 | Verify channel breakdown | Check metrics |

**⚠️ NOTE FROM J2:**
Campaign detail page was flagged as using mock data in J2 review. Verify this is now using real data.

**Pass Criteria:**
- [ ] Campaign detail loads
- [ ] ⚠️ Uses real data (not mock)
- [ ] Metrics accurate
- [ ] Leads list correct

<!-- E2E_SESSION_BREAK: J9.9 complete. Next: J9.10 Reports Page -->

---

### J9.10 — Reports Page
**Purpose:** Verify reports page shows analytics.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.10.1 | Read `frontend/app/dashboard/reports/page.tsx` | Load page |
| J9.10.2 | Verify channel metrics displayed | Check table |
| J9.10.3 | Verify campaign performance table | Check data |
| J9.10.4 | Verify date range selector exists | Check UI |
| J9.10.5 | Verify Export Report button exists | Check UI |

**Channel Metrics Fields (VERIFIED from reports.py):**
- sent, delivered, opened, clicked, replied, bounced
- delivery_rate, open_rate, click_rate, reply_rate

**Pass Criteria:**
- [ ] Reports page loads
- [ ] Channel metrics accurate
- [ ] Campaign performance table works
- [ ] Export functionality exists

<!-- E2E_SESSION_BREAK: J9.10 complete. Next: J9.11 Replies Page -->

---

### J9.11 — Replies Page
**Purpose:** Verify replies page shows inbound messages.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.11.1 | Read `frontend/app/dashboard/replies/page.tsx` | Load page |
| J9.11.2 | Verify replies API endpoint called | Check network |
| J9.11.3 | Verify reply content displayed | Check messages |
| J9.11.4 | Verify intent classification shown | Check badge |
| J9.11.5 | Verify sentiment displayed | Check indicator |

**Pass Criteria:**
- [ ] Replies page loads
- [ ] Reply content displayed
- [ ] Intent badges correct
- [ ] Sentiment indicators work

<!-- E2E_SESSION_BREAK: J9.11 complete. Next: J9.12 Settings Page -->

---

### J9.12 — Settings Page
**Purpose:** Verify settings pages work.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.12.1 | Read `frontend/app/dashboard/settings/page.tsx` | Load page |
| J9.12.2 | Verify ICP settings accessible | Navigate to /settings/icp |
| J9.12.3 | Verify LinkedIn settings accessible | Navigate to /settings/linkedin |

**Settings Pages (VERIFIED from glob):**
- /dashboard/settings/page.tsx
- /dashboard/settings/icp/page.tsx
- /dashboard/settings/linkedin/page.tsx

**Pass Criteria:**
- [ ] Settings page loads
- [ ] ICP settings work
- [ ] LinkedIn settings work

<!-- E2E_SESSION_BREAK: J9.12 complete. Next: J9.13 ICP Banner and Modal -->

---

### J9.13 — ICP Banner and Modal
**Purpose:** Verify ICP extraction UI works.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.13.1 | Verify ICPProgressBanner component | Check dashboard |
| J9.13.2 | Verify ICPReviewModal component | Test review |
| J9.13.3 | Verify `useICPJob` hook | Check state |
| J9.13.4 | Verify confirm ICP action | Test confirmation |

**ICP Components (VERIFIED from page.tsx):**
- ICPProgressBanner (lines 89-96)
- ICPReviewModal (lines 98-105)
- useICPJob hook for status tracking

**Pass Criteria:**
- [ ] ICP banner shows when needed
- [ ] Review modal opens
- [ ] Confirm action works
- [ ] Retry action works

<!-- E2E_SESSION_BREAK: J9.13 complete. Next: J9.14 Real-Time Updates -->

---

### J9.14 — Real-Time Updates
**Purpose:** Verify auto-refresh works.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J9.14.1 | Verify refetchInterval on hooks | Check hook config |
| J9.14.2 | Verify dashboard stats refresh (60s) | Wait and observe |
| J9.14.3 | Verify activity feed refresh (30s) | Wait and observe |
| J9.14.4 | Create activity in DB, verify appears | Test refresh |

**Refresh Intervals (VERIFIED from use-reports.ts):**
```typescript
// useDashboardStats
staleTime: 30 * 1000, // 30 seconds
refetchInterval: 60 * 1000, // 60 seconds

// useActivityFeed
staleTime: 10 * 1000, // 10 seconds
refetchInterval: 30 * 1000, // 30 seconds
```

**Pass Criteria:**
- [ ] Stats refresh every 60 seconds
- [ ] Activity feed refreshes every 30 seconds
- [ ] New activities appear without manual refresh

<!-- E2E_SESSION_BREAK: J9 JOURNEY COMPLETE. Next: J10 Admin Dashboard -->

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Dashboard Page | `frontend/app/dashboard/page.tsx` | 313 | ✅ VERIFIED |
| Leads Page | `frontend/app/dashboard/leads/page.tsx` | 200+ | ✅ VERIFIED |
| Reports Page | `frontend/app/dashboard/reports/page.tsx` | 150+ | ✅ VERIFIED |
| Reports Hooks | `frontend/hooks/use-reports.ts` | 127 | ✅ VERIFIED |
| Reports API | `src/api/routes/reports.py` | 500+ | ✅ VERIFIED |

---

## Completion Criteria

All checks must pass:

- [ ] **J9.1** Dashboard page loads without errors
- [ ] **J9.2** Dashboard stats accurate
- [ ] **J9.3** Activity feed works
- [ ] **J9.4** ALS distribution correct
- [ ] **J9.5** Meetings widget works
- [ ] **J9.6** Leads list with filtering
- [ ] **J9.7** Lead detail page works
- [ ] **J9.8** Campaigns list works
- [ ] **J9.9** Campaign detail works (verify not mock)
- [ ] **J9.10** Reports page works
- [ ] **J9.11** Replies page works
- [ ] **J9.12** Settings pages work
- [ ] **J9.13** ICP banner and modal work
- [ ] **J9.14** Real-time updates work

---

## CTO Verification Notes

**Code Review Completed:** January 11, 2026

**Key Findings:**
1. ✅ Dashboard uses real API calls (not mocked)
2. ✅ React Query with auto-refresh configured
3. ✅ Loading states and error states implemented
4. ✅ ALS tier distribution with correct colors
5. ✅ Activity feed with channel icons
6. ✅ Leads page with search and tier filtering
7. ✅ Reports page with channel breakdown
8. ⚠️ Campaign detail page flagged in J2 for mock data - verify

**Issue to Verify:**
- Campaign detail page (`/dashboard/campaigns/[id]`) was noted in J2 as using mock data. Verify this is resolved.

---

## Notes

**Authentication:**
All dashboard pages require authentication. The `useClient` hook provides the `clientId` for all API calls. Client can only see their own data.

**Performance:**
React Query caching reduces API calls. Stale time and refetch intervals are configured per hook for optimal UX without excessive API usage.

**Mobile Responsiveness:**
Dashboard uses responsive grid layouts. Test on mobile viewport to ensure usability.
