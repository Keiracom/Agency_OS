# Dashboard Data-Flow Audit

**Compiled:** 2026-05-09
**Author:** Aiden
**Trigger:** PR #639 (A2) wired 3 Next.js API routes that no consumer hits — `narrow grep misses structure` repeat. This doc traces frontend data flow consumer-up so the next directive targets actual user-visible mocks.

---

## TL;DR

The mock data the audit flagged (`lib/demo-data.ts` 1,603 lines + `data/mock-*.ts` 12 files, ~3,500 LOC total) primarily backs **5 stranded top-level routes** that no nav links to:

| Stranded route | Mock import | Sidebar / bottom-nav link? |
|---|---|---|
| `/leads` | `mockLeads, mockLeadStats` | None |
| `/leads/[id]` | `mockLeadDetail` | None (only internal back-link from [id] → /leads) |
| `/campaigns` | `mockCampaigns, mockBestContent, mockRecommendations` | None |
| `/billing` | `mock-billing` exports | None |
| `/replies` | `mockConversations` | None |

`/dashboard/*` surfaces (the canonical UIs the nav points at) already query real Supabase or redirect to surfaces that do. They are honest. The mock-data debt sits entirely in the orphaned top-level routes.

---

## Three-layer data-flow map

### Layer 1 — `/dashboard/*` (canonical, nav-reachable)

| Path | Status | Data source |
|---|---|---|
| `/dashboard` | landing tiles | server-rendered |
| `/dashboard/pipeline` | WORKS (212 LOC) | real |
| `/dashboard/activity` | wrapper (37 LOC) | `<ActivityFeed/>` queries `cis_outreach_outcomes` via Supabase browser client |
| `/dashboard/meetings` | WORKS (159 LOC) | real |
| `/dashboard/campaigns` + `/[id]` + `/new` + `/approval` | WORKS | real |
| `/dashboard/archive` | WORKS (513 LOC) | real |
| `/dashboard/settings/*` | WORKS | real |
| `/dashboard/leads` | redirect → `/dashboard/pipeline?view=table` (B2.2 dedupe, 2026-04-30) |
| `/dashboard/inbox` | redirect → `/dashboard/activity` (B2.4 consolidation) |
| `/dashboard/replies` | redirect → `/dashboard/activity` (B2.4 consolidation) |
| `/dashboard/reports` | WORKS (181 LOC) | real |

**No mock-data imports anywhere under `/dashboard/*` page tree.** PR #639's wiring of `/api/activity`, `/api/replies`, `/api/leads/counts` was correct in pattern but orphaned in placement — nothing on the canonical dashboard hits those routes.

### Layer 2 — Top-level stranded routes (orphan, no nav)

| Path | LOC | Mock backing | Components used |
|---|---|---|---|
| `/leads` | 72 | `mock-leads.ts` (119 LOC) | `LeadsTable`, `LeadHeader`, `LeadContactInfo`, `LeadRadarChart`, `LeadTimeline`, `SiegeWaterfallProgress` |
| `/leads/[id]` | 59 | `mock-lead-detail.ts` (140 LOC) | same as above + back-link |
| `/campaigns` | 90 | `mock-campaigns.ts` (137 LOC) | `CampaignCard`, `CampaignChannels`, `CampaignMetrics`, `CampaignSequence`, `CampaignStatusBadge`, `BestContentCard`, `RecommendationsCard`, `SequenceStep` |
| `/billing` | 59 | `mock-billing.ts` (180 LOC) | `InvoiceTable`, `PaymentMethod`, `PlanComparison`, `PlanHeroCard`, `UsageMeters` |
| `/replies` | 64 | `mock-inbox.ts` (205 LOC) | `ConversationDetail`, `ConversationList` |

**Total stranded code:** ~344 LOC routes + ~781 LOC mock files + ~3,300 LOC backing components = **~4,400 LOC orphaned**.

**Reachability check:** `grep -rE "href=[\"']/leads['\"]|/campaigns['\"]|/billing['\"]|/replies['\"]"` across `frontend/` returns ONE hit: an internal back-link inside `/leads/[id]` → `/leads`. No sidebar, bottom-nav, or other in-app navigation points at these. They're URL-only ghosts.

### Layer 3 — Marketing surfaces (legitimate demo content)

`HowItWorksClient.tsx`, `HowItWorksCarousel.tsx`, `HowItWorksTabs.tsx`, `DashboardDemo.tsx`, `Plasmic/Header.tsx` — illustrative marketing demos. Acceptable use of fake names (it's marketing showing what the product DOES, not customer-state claims). Not in scope for honesty cleanup unless framing changes.

---

## Wire-targets table — where the real A2 work lives

If the goal is "no fake data the client can see post-login", the next directive should pick ONE of these:

| Option | Action | Risk | Blast radius |
|---|---|---|---|
| **A — Delete stranded routes** | Remove 5 top-level routes + 12 mock files + dependent components that have no other importers | Zero (nothing links to them) | -4,400 LOC, 1 PR |
| **B — Wire stranded routes to real data** | Replicate Layer 1's pattern (Supabase direct via browser client) for each stranded surface | Medium (5 surfaces × component refactor) | +1,000 LOC, 5 PRs |
| **C — Replace with redirects** | Apply the B2.2/B2.4 dedupe pattern: `/leads` → `/dashboard/pipeline?view=table`, `/campaigns` → `/dashboard/campaigns`, etc. | Low | -4,400 LOC, 1 PR |

**Recommendation: option A.** No nav links to these routes. The dashboard nav is the canonical entry point. Deleting them removes the largest pre-revenue honesty risk in one move and closes the "narrow grep misses" failure mode that drove the PR #639 mistake.

Option C is the next-safest if Dave wants direct-URL fallbacks preserved.

Option B is the heaviest path and only justifies cost if there's a UX reason to have parallel `/leads` + `/dashboard/pipeline` surfaces — which the B2.2 dedupe already declined.

---

## What this audit changes for future directives

1. **Phase 1 A2 wasn't really about the dashboard** — it was about the stranded top-level routes the audit didn't separate from /dashboard/.
2. **PR #639's 3 routes (`/api/activity`, `/api/replies`, `/api/leads/counts`)** sit at a layer no current consumer hits. They're harmless infrastructure; if Layer 2 routes get wired (option B), they may become useful. Until then they're forward-compat scaffolding.
3. **`<ActivityFeed/>` already does data-flow right** — Supabase browser client direct, server-side RLS. The pattern Layer 2 should replicate if option B lands.

---

## Verification commands

```bash
# Stranded top-level routes
$ grep -rE "from.*data/mock-|from.*lib/demo-data" frontend/app/ | wc -l
5  # 5 page.tsx files import mock data

# Components backing those routes
$ grep -rln "from.*data/mock-|from.*lib/demo-data" frontend/components | wc -l
22  # 22 components import mock data

# Reachability — only one back-link
$ grep -rE "href=[\"']/(leads|campaigns|billing|replies)['\"]" frontend/ \
    | grep -v node_modules | grep -v __tests__ | grep -v "data/mock\|demo-data"
frontend/app/leads/[id]/page.tsx:            href="/leads"

# Dashboard nav targets
$ grep -E "href.*/dashboard" frontend/components/layout/{sidebar,bottom-nav}.tsx | wc -l
9  # all in-app nav points at /dashboard/*
```
