# audit_verify_aiden.md — V6 / V7 / V8 Trust Verification

**To: Dave (CEO), via Max (COO)**
**From: Aiden**
**Compiled: 2026-05-07**
**Method:** Primary-source verification only — raw terminal output, no interpretation, no estimates.

---

## ACKNOWLEDGEMENT OF PHASE 2 OVERSTATEMENT

My Phase 2 audit said all 32 frontend routes WORK and all 20 admin routes WORK. That was a **file-existence claim, not a runs-with-real-data claim**. V6/V7/V8 below corrects the record against primary sources.

**Single biggest correction:** of 20 admin pages, only **3** call backend APIs. The other 17 render hardcoded `mockXxx` const arrays inline — UI works, data is fake. My "WORKS" verdict was wrong by definition of working.

---

## V6 — Frontend deployed verification

### Vercel deployment status (primary source: Vercel API via MCP)

| Project | State | Domain | Framework | Region |
|---|---|---|---|---|
| frontend | READY (PROMOTED) | app.agencyxos.ai | Next.js | syd1 |
| agencyxos-marketing | READY (PROMOTED) | agencyxos.ai | (none) | default |
| admin-dashboard | READY (PROMOTED) | admin.agencyxos.ai | Next.js | default |

Project IDs verified: prj_MJ5bRn9utnPHr21CnrIXOUEaBnt0 (frontend), prj_8HXmkBEefcksKAHks7RKTOYEDZtW (marketing), prj_DDWp9BLFSuDFlvP4zyPSgQJS6Flt (admin).

### HTTP probes (raw curl, max-time 10s)

```
$ for url in https://app.agencyxos.ai https://agencyxos.ai https://admin.agencyxos.ai https://app.agencyxos.ai/signup https://app.agencyxos.ai/dashboard; do
    code=$(curl -s -o /dev/null -w "%{http_code}" -L --max-time 10 "$url")
    echo "$url -> HTTP $code"
  done

https://app.agencyxos.ai            -> HTTP 200
https://agencyxos.ai                -> HTTP 200
https://admin.agencyxos.ai          -> HTTP 200
https://app.agencyxos.ai/signup     -> HTTP 200
https://app.agencyxos.ai/dashboard  -> HTTP 200
```

### Auth gate verification

```
$ curl -sI -L --max-time 10 https://app.agencyxos.ai/dashboard | grep -E "HTTP|location:"
HTTP/2 307
location: /login?returnTo=%2Fdashboard
HTTP/2 200
```

Unauthenticated `/dashboard` correctly redirects to `/login?returnTo=%2Fdashboard`. **Auth gate is enforced.**

### Signup page rendering

```
$ curl -s -L --max-time 10 https://app.agencyxos.ai/signup | grep -oE '<title[^>]*>[^<]+</title>'
<title>Agency OS - Automated Acquisition Engine</title>
```

The page **HTML responds 200 with title set**. However, the body contains:
```
<template data-dgst="BAILOUT_TO_CLIENT_SIDE_RENDERING"></template>
```

This means the form is rendered client-side via JS bundle. **Without a browser I cannot confirm the form inputs actually render or that submit succeeds.** I confirmed the JS chunk exists (`/_next/static/chunks/app/(auth)/signup/page-133bd6669795ea6f.js`) but I did not execute it.

### Honest verdict

| Check | Status | Evidence |
|---|---|---|
| Frontend deployed on Vercel | **VERIFIED** | 3 projects READY, syd1 region for app |
| Public URLs respond 200 | **VERIFIED** | curl HTTP 200 on all 5 probed URLs |
| Auth gate enforced | **VERIFIED** | /dashboard 307→/login when unauthed |
| Signup page renders form | **UNVERIFIED — NO BROWSER** | HTML loads, form is CSR — I have no headless browser to confirm inputs render or submit succeeds |
| Authed dashboard renders content | **UNVERIFIED — NO BROWSER + NO TEST ACCOUNT** | I do not have browser access AND I do not have a test login. Cannot prove the dashboard renders meaningful content rather than 500'ing post-auth |

**You'll need to find another way for the two UNVERIFIED items** — a headless smoke test (Playwright) and a seeded test account would close them.

---

## V7 — Onboarding wiring (raw output)

### Command 1: supabase imports in onboarding
```
$ grep -r "supabase" frontend/app/onboarding/ --include="*.tsx" --include="*.ts" -l
(empty — 0 files)
```

**Onboarding pages do NOT import the Supabase client directly.** They write via backend API endpoints (correct pattern — frontend should not have service-role keys).

### Command 2: fetch / api / mutation calls
```
$ grep -r "fetch\|api\|mutation" frontend/app/onboarding/ --include="*.tsx" --include="*.ts" -l
frontend/app/onboarding/service-area/page.tsx
frontend/app/onboarding/agency/page.tsx
frontend/app/onboarding/crm/page.tsx
frontend/app/onboarding/linkedin/page.tsx
```

### Endpoint detail (drill into the 4 wired pages)
```
--- crm/page.tsx ---
25: const res = await fetch(`${API_BASE}/api/v1/crm/connect/hubspot`, { ... })

--- agency/page.tsx ---
78:  const res = await fetch(`${API_BASE}/api/v1/onboarding/status/${id}`, ...)
86:  const res = await fetch(`${API_BASE}/api/v1/onboarding/result/${id}`, ...)
137: const res = await fetch(`${API_BASE}/api/v1/onboarding/analyze`, ...)
172: const res = await fetch(`${API_BASE}/api/v1/onboarding/confirm`, ...)

--- service-area/page.tsx ---
54: const res = await fetch(`${API_BASE}/api/v1/onboarding/confirm`, ...)
74: void fetch(`${API_BASE}/api/v1/pipeline/trigger`, ...)

--- linkedin/page.tsx ---
25: const res = await fetch(`${API_BASE}/api/v1/linkedin/connect`, ...)
```

### V7 honest verdict

| Question | Answer |
|---|---|
| Do onboarding pages call backends? | **YES — 4 pages call POST /api/v1/onboarding/{analyze,confirm,status,result} + /api/v1/{crm,linkedin}/connect + /api/v1/pipeline/trigger** |
| Do they write to Supabase? | **NOT DIRECTLY — via FastAPI backend** (architecturally correct) |
| Is the persistence loop verified end-to-end? | **UNVERIFIED — I confirmed the page issues a fetch, NOT that the backend handler exists, accepts the payload, and writes a row to Supabase.** Verifying that requires a backend smoke test against the analyze/confirm endpoints with a real signup account |

**Caveat:** the spec I wrote in `docs/specs/onboarding_email_provisioning.md` (Variant A) describes a 7-step flow with **domain provisioning, DNS, mailbox, self-test send**. None of those steps exist in the 4 wired onboarding pages. Current onboarding is `agency → service-area → linkedin → crm`. The spec is design-stage; the live UI is a different (older) flow.

---

## V8 — Admin data sources (raw output)

### Command (literal, as Dave specified)
```
$ grep -rn "mockData\|sampleData\|demoData\|seed\|placeholder\|TODO\|FIXME" frontend/app/admin/ --include="*.tsx" --include="*.ts" | head -30
```

Literal output: 23 hits — all matched on the substring `placeholder=` (the HTML attribute on `<Input>` and `<SelectValue>` components, e.g. `placeholder="Search leads..."`). These are **legitimate UI hints**, not mock data. Zero hits for `mockData`, `sampleData`, `demoData`, `seed`, `TODO`, or `FIXME`.

### **BUT — Dave's grep missed the actual mock variables**

The admin pages declare mock data with names like `mockCampaigns`, `mockReplies`, `mockUsers`, `mockSuppressionList` — none of which match `mockData|sampleData|demoData`. Broader grep:

```
$ grep -rnE "^const mock|// Mock data" frontend/app/admin/ --include="*.tsx" --include="*.ts"

frontend/app/admin/campaigns/page.tsx:31:// Mock data
frontend/app/admin/campaigns/page.tsx:32:const mockCampaigns = [
frontend/app/admin/replies/page.tsx:46:// Mock data
frontend/app/admin/replies/page.tsx:47:const mockReplies: Reply[] = [
frontend/app/admin/leads/page.tsx:31:// Mock data
frontend/app/admin/leads/page.tsx:32:const mockLeads = [
frontend/app/admin/revenue/page.tsx:28:// Mock data
frontend/app/admin/revenue/page.tsx:29:const mockRevenue = {
frontend/app/admin/revenue/page.tsx:39:const mockTierBreakdown = [
frontend/app/admin/revenue/page.tsx:45:const mockRecentTransactions = [
frontend/app/admin/revenue/page.tsx:52:const mockUpcomingRenewals = [
frontend/app/admin/revenue/page.tsx:58:const mockAtRisk = [
frontend/app/admin/costs/page.tsx:15:// Mock data
frontend/app/admin/costs/page.tsx:16:const mockCosts = {
frontend/app/admin/costs/channels/page.tsx:23:// Mock data
frontend/app/admin/costs/channels/page.tsx:24:const mockChannelCosts = {
frontend/app/admin/system/page.tsx:31:// Mock data
frontend/app/admin/system/page.tsx:32:const mockServices = [
frontend/app/admin/system/page.tsx:40:const mockFlows = [
frontend/app/admin/system/page.tsx:71:const mockErrors = [
frontend/app/admin/system/page.tsx:92:const mockDbStats = {
frontend/app/admin/system/page.tsx:103:const mockRateLimits = [
frontend/app/admin/system/queues/page.tsx:48:// Mock data
frontend/app/admin/system/queues/page.tsx:49:const mockFlows: Flow[] = [
frontend/app/admin/system/queues/page.tsx:97:const mockQueueStats: QueueStats = {
frontend/app/admin/system/rate-limits/page.tsx:43:// Mock data
frontend/app/admin/system/rate-limits/page.tsx:44:const mockRateLimits: RateLimit[] = [
frontend/app/admin/system/errors/page.tsx:42:// Mock data
frontend/app/admin/system/errors/page.tsx:43:const mockErrors: ErrorEntry[] = [
frontend/app/admin/compliance/page.tsx:23:// Mock data
frontend/app/admin/compliance/page.tsx:24:const mockCompliance = {
frontend/app/admin/compliance/bounces/page.tsx:48:// Mock data
frontend/app/admin/compliance/bounces/page.tsx:49:const mockBounces: BounceEntry[] = [
frontend/app/admin/compliance/suppression/page.tsx:42:// Mock data
frontend/app/admin/compliance/suppression/page.tsx:43:const mockSuppressionList = [
frontend/app/admin/clients/[id]/page.tsx:41:const mockClient = {
frontend/app/admin/settings/users/page.tsx:51:// Mock data
frontend/app/admin/settings/users/page.tsx:52:const mockUsers: User[] = [

15 admin .tsx files contain top-level `const mock*` data declarations.
```

### Cross-check — admin pages that DO call backend
```
$ grep -rlE "fetch\(|useQuery|useSWR|/api/" frontend/app/admin/ --include="*.tsx" --include="*.ts"
frontend/app/admin/page.tsx
frontend/app/admin/activity/page.tsx
frontend/app/admin/clients/page.tsx

3 of 20 admin pages call backend APIs.
```

### V8 honest verdict

| Page | Backend wiring | Data source |
|---|---|---|
| admin/ (overview)             | YES | live API |
| admin/activity/                | YES | live API |
| admin/clients/                 | YES | live API |
| admin/clients/[id]/            | NO  | mockClient hardcoded |
| admin/campaigns/               | NO  | mockCampaigns |
| admin/replies/                 | NO  | mockReplies |
| admin/leads/                   | NO  | mockLeads |
| admin/revenue/                 | NO  | 5× mock arrays |
| admin/costs/                   | NO  | mockCosts |
| admin/costs/channels/          | NO  | mockChannelCosts |
| admin/system/                  | NO  | 5× mock arrays |
| admin/system/queues/           | NO  | mockFlows + mockQueueStats |
| admin/system/rate-limits/      | NO  | mockRateLimits |
| admin/system/errors/           | NO  | mockErrors |
| admin/compliance/              | NO  | mockCompliance |
| admin/compliance/bounces/      | NO  | mockBounces |
| admin/compliance/suppression/  | NO  | mockSuppressionList |
| admin/settings/users/          | NO  | mockUsers |
| admin/settings/                | NO  | (no mock — static UI) |
| admin/onboarding-progress/     | NO  | (no mock — static UI) |

**3 of 20 admin pages are wired to real Supabase data via backend. 15 are rendering hardcoded mock arrays. 2 are static UI without data.**

---

## CORRECTIONS TO MY PHASE 2 AUDIT (audit_phase2_aiden.md)

| Phase 2 claim | Reality after V6/V7/V8 |
|---|---|
| "32 frontend routes WORKS" | File-exists for 32. Auth gate works. Signup form rendering — UNVERIFIED (CSR, no browser). End-to-end signup flow — UNVERIFIED. |
| "20 admin routes WORKS" | **3 of 20 actually fetch real data. 15 render mock const arrays.** WORKS verdict was a file-existence claim, not a renders-real-data claim. |
| "10-page onboarding flow WORKS" | 4 of the live onboarding pages call backend endpoints. The 7-step Variant A spec (domain/DNS/mailbox/self-test) is design-stage, NOT in the live UI. |

---

## THE PRINCIPLE

I conflated "file exists with reasonable code" with "feature works end-to-end". That's the same failure mode as the Supabase `subscription_recurring` table containing services nobody pays for — both are "self-reported by our own systems" rather than verified against the running outside world.

For frontend going forward:
- **Deployed status:** Vercel API + curl HTTP probe (this report)
- **Renders real data:** grep `mock*` declarations + count `fetch(`/`useQuery` per page
- **End-to-end:** headless browser (Playwright) + seeded test account — required to close UNVERIFIED items

Any frontend route claim of WORKS in a future audit will require all three.
