# Phase 3 Cleanup Dependency Map

Read-only research. Per-component dependency graph for the 24 React components flagged for deletion in the Phase 3 cleanup pass (item 25 `/welcome` excluded per Dave's Path B decision).

Goal: deletion order that minimises broken imports and route regressions.

**Reference paths**

- Frontend root: `/home/elliotbot/clawd/Agency_OS/frontend/`
- All importer counts derived from `grep -rn` across the frontend tree (excluding `node_modules` and `.next/`).

**Branch**: `aiden/phase3-cleanup-map` (off `origin/main`). No code edits — doc-only.

## Table of contents

1. [DashboardMain.tsx](#component-1--dashboardmaintsx)
2. [HeroStrip.tsx](#component-2--herostriptsx)
3. [HeroMetricsCard.tsx](#component-3--herometricscardtsx)
4. [StatsGrid.tsx](#component-4--statsgridtsx)
5. [StatsRow.tsx](#component-5--statsrowtsx)
6. [FunnelBar.tsx](#component-6--funnelbartsx) — conditional delete
7. [CycleProgress.tsx](#component-7--cycleprogresstsx)
8. [TodayStrip.tsx](#component-8--todaystripstsx)
9. [ActivityFeed.tsx](#component-9--activityfeedtsx)
10. [ActivityFeedFull.tsx](#component-10--activityfeedfulltsx)
11. [ActivityFeedSimple.tsx](#component-11--activityfeedsimpletsx)
12. [ActivityTicker.tsx](#component-12--activitytickertsx)
13. [LiveActivityFeed.tsx](#component-13--liveactivityfeedtsx)
14. [ProspectDetailCard.tsx](#component-14--prospectdetailcardtsx)
15. [LeadDetailModal.tsx](#component-15--leaddetailmodaltsx)
16. [ReportsView.tsx](#component-16--reportsviewtsx)
17. [SettingsPanel.tsx](#component-17--settingspaneltsx)
18. [KillSwitch.tsx](#component-18--killswitchtsx-keep) — KEEP (consolidation target)
19. [EmergencyPauseButton.tsx](#component-19--emergencypausebuttontsx)
20. [PauseCycleButton.tsx](#component-20--pausecyclebuttontsx)
21. [Sidebar.tsx (dashboard)](#component-21--componentsdashboardsidebartsx)
22. [layout/sidebar.tsx](#component-22--componentslayoutsidebartsx)
23. [layout/AppShell.tsx + dashboard-layout.tsx](#component-23--componentslayoutappshelltsx--dashboard-layouttsx)
24. [app/dashboard/leads/[id]/page.tsx](#component-24--appdashboardleadsidpagetsx)

[Closing summary](#closing-summary) · [Deletion sequence](#recommended-deletion-sequence)

---

## Component 1 — `frontend/components/dashboard/DashboardMain.tsx`

**Imported by:**
- `frontend/components/dashboard/index.ts:146` — `export { DashboardMain } from "./DashboardMain";`
- `frontend/components/dashboard/index.ts:148-149` — `DashboardMainProps` type re-export
- No direct route import. The `index.ts` re-export is the only consumer.

**Imports:** 41+ external packages (heroicons, etc.) and a large number of dashboard children. None of those would orphan since they're used elsewhere.

**Routes affected:** None. `app/dashboard/page.tsx` imports specific child components (HeroStrip, FunnelBar, etc.) directly, not `DashboardMain`.

**Tests affected:** None.

**301 redirect needed:** No (not a route).

**Deletion tier:** **Tier 1** — leaf. Only consumer is the dashboard `index.ts` re-export which is itself dead after the cascade.

---

## Component 2 — `frontend/components/dashboard/HeroStrip.tsx`

**Imported by:**
- `frontend/app/dashboard/page.tsx:35` — `import { HeroStrip } from "@/components/dashboard/HeroStrip";`
- `frontend/app/dashboard/page.tsx:117` — `<HeroStrip />`

**Imports:** `useDashboardStats`, `agencyPersona` helper.

**Routes affected:** `/dashboard` — home page hero region disappears.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 3** — used by a route. `app/dashboard/page.tsx` must be updated first to either remove the hero strip block or swap to a /demo-aligned hero before HeroStrip can be deleted.

---

## Component 3 — `frontend/components/dashboard/HeroMetricsCard.tsx`

**Imported by:**
- `frontend/plasmic-init.ts:26` — lazy-loaded Plasmic component registration
- `frontend/plasmic-init.ts:28, 32` — registry name + import path
- `frontend/components/dashboard/index.ts:156` — re-export

**Imports:** Standard React + likely a hook.

**Routes affected:** None directly. Plasmic loader is only consumed if the Plasmic studio is wired into a live page — not currently used by any `app/**/page.tsx`.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 1** — Plasmic registration + index.ts re-export are dead-end consumers. Verify Plasmic studio doesn't need it before deleting; otherwise safely leaf.

---

## Component 4 — `frontend/components/dashboard/StatsGrid.tsx`

**Imported by:**
- `frontend/components/bloomberg/index.ts:8` — `export { StatCard, StatsGrid } from "./StatCard";` (re-export from bloomberg, not dashboard's StatsGrid — name collision)
- `frontend/components/dashboard/index.ts:38` — `export { StatsGrid, StatCard } from "./StatsGrid";`
- `frontend/components/ui/loading-skeleton.tsx:42, 128` — `StatsGridSkeleton` (different symbol, just shares the prefix)
- `frontend/components/bloomberg/StatCard.tsx:41, 50` — defines its own `StatsGrid` (name collision; bloomberg has a parallel implementation)
- `frontend/data/mock-dashboard.ts:35` — `mockStatsGrid` (variable, not import)

**Imports:** Likely `cn` utility + heroicons.

**Routes affected:** None directly. Bloomberg has its own `StatsGrid` so external users likely import from `bloomberg/index`, not `dashboard/StatsGrid`.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 2** — name collision with bloomberg's `StatsGrid`. Verify no caller resolves through `dashboard/index.ts:38` re-export. If clean, drop to Tier 1.

---

## Component 5 — `frontend/components/dashboard/StatsRow.tsx`

**Imported by:** None (no consumers found via grep).

**Imports:** Standard React.

**Routes affected:** None.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 1** — pure leaf. Safe to delete first.

---

## Component 6 — `frontend/components/dashboard/FunnelBar.tsx`

**Imported by:**
- `frontend/app/dashboard/page.tsx:37` — `import { FunnelBar } from "@/components/dashboard/FunnelBar";`
- `frontend/app/dashboard/page.tsx:123` — `<FunnelBar />`

**Imports:** `useFunnelData` hook (`@/lib/hooks/useFunnelData`).

**Routes affected:** `/dashboard` — cycle funnel block.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **CONDITIONAL DELETE — pending Phase 3 Item 3 build outcome.** Phase 3 Item 3 refactors FunnelBar (flex-1 → proportional widths). If the refactor lands, this component **stays**. If Phase 3 elects to rewrite it under a new name, this becomes **Tier 3** (route swap then delete). Default expectation: KEEP via refactor.

---

## Component 7 — `frontend/components/dashboard/CycleProgress.tsx`

**Imported by:**
- `frontend/app/dashboard/page.tsx:41` — `import { CycleProgress } from "@/components/dashboard/CycleProgress";`
- `frontend/app/dashboard/page.tsx:106` — `<CycleProgress />`

**Imports:** `useDashboardV4` hook (mentioned in CycleProgress.tsx:23-27 docstring).

**Routes affected:** `/dashboard` — DAY N/30 block.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 3** — needs route update first. **Note**: Phase 3 Item 2 may refactor this into an inline topbar element rather than delete it. If refactored, treat as KEEP. If outright replaced by a new `CycleIndicator.tsx`, treat as Tier 3 delete after the swap.

---

## Component 8 — `frontend/components/dashboard/TodayStrip.tsx`

**Imported by:**
- `frontend/app/dashboard/page.tsx:36` — `import { TodayStrip } from "@/components/dashboard/TodayStrip";`
- `frontend/app/dashboard/page.tsx:123` — `<TodayStrip />`

**Imports:** Internal scheduled-touches fetcher (TodayStrip.tsx:68 references `scheduled_touches`).

**Routes affected:** `/dashboard` — "today's outreach" block.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 3** — route update first.

---

## Component 9 — `frontend/components/dashboard/ActivityFeed.tsx`

**Imported by:**
- `frontend/components/dashboard/index.ts:79` — `export { ActivityFeed } from "./ActivityFeed";`
- (No direct route import — only the bloomberg `ActivityFeed` symbol is used elsewhere; the dashboard `ActivityFeed` is unimported.)

**Imports:** Likely a fetch hook + its own internal helpers.

**Routes affected:** None directly.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 1** — only the index.ts re-export sees it. Safe leaf.

---

## Component 10 — `frontend/components/dashboard/ActivityFeedFull.tsx`

**Imported by:**
- `frontend/app/dashboard/activity/page.tsx:11` — `import { ActivityFeedFull } from "@/components/dashboard/ActivityFeedFull";`

**Imports:** `useLiveActivityFeed` hook (frontend/lib/useLiveActivityFeed; ActivityFeedFull.tsx:26).

**Routes affected:** `/dashboard/activity` — full activity feed page.

**Tests affected:** None.

**301 redirect needed:** No (route stays; just needs different rendering component).

**Deletion tier:** **Tier 3** — `app/dashboard/activity/page.tsx` must swap to a different feed component first.

---

## Component 11 — `frontend/components/dashboard/ActivityFeedSimple.tsx`

**Imported by:** None.

**Imports:** Self-contained.

**Routes affected:** None.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 1** — pure leaf. Safe to delete first.

---

## Component 12 — `frontend/components/dashboard/ActivityTicker.tsx`

**Imported by:**
- `frontend/components/dashboard/LiveActivityFeed.tsx:14` — `import { ActivityTicker } from "./ActivityTicker";`
- `frontend/components/dashboard/index.ts:77` — re-export

**Imports:** Self-contained (likely an animation lib + state).

**Routes affected:** None directly. `LiveActivityFeed` is its only real consumer.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 2** — must wait for `LiveActivityFeed` (Component 13) to be deleted first. Then becomes a leaf.

---

## Component 13 — `frontend/components/dashboard/LiveActivityFeed.tsx`

**Imported by:**
- `frontend/plasmic-init.ts:37, 45` — Plasmic registration
- `frontend/components/admin/index.ts:12` — `export { LiveActivityFeed, type Activity } from "./LiveActivityFeed";` (cross-package re-export from admin)
- `frontend/components/dashboard/index.ts:78` — re-export
- `frontend/lib/__tests__/useLiveActivityFeed.test.tsx:70` — imports the hook (`useLiveActivityFeed`), not the component

**Imports:** `useActivityFeed` hook (LiveActivityFeed.tsx:13), `ActivityTicker` (Component 12).

**Routes affected:** None directly. Despite the `app/dashboard/page.tsx:32` importing `useLiveActivityFeed` (the hook with similar name), the **component** itself isn't rendered in any route.

**Tests affected:** `frontend/lib/__tests__/useLiveActivityFeed.test.tsx` — but this is the hook test, not the component test. Stays after the component is deleted (only the hook needs to remain).

**301 redirect needed:** No.

**Deletion tier:** **Tier 1** — verify the admin `index.ts:12` re-export isn't a live `<LiveActivityFeed />` consumer in `app/admin/**`. If clean, leaf. The Plasmic registration is dead-end.

---

## Component 14 — `frontend/components/dashboard/ProspectDetailCard.tsx`

**Imported by:** None (no live consumer).

**Imports:** Likely standard React + a prospect type from `@/lib/types/prospect`.

**Routes affected:** None.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 1** — pure leaf.

---

## Component 15 — `frontend/components/dashboard/LeadDetailModal.tsx`

**Imported by:**
- `frontend/components/dashboard/LeadTable.tsx:22` — `import { LeadDetailModal } from "./LeadDetailModal";`
- `frontend/components/dashboard/index.ts:84` — re-export
- `frontend/components/dashboard/MeetingScheduler.tsx:41` — comment only ("Bloomberg Color Reference (from LeadDetailModal)"), no import

**Imports:** Standard React + a fetch hook + heroicons.

**Routes affected:** Wherever `LeadTable.tsx` is rendered. Need to grep `LeadTable` consumers to know.

**Tests affected:** None directly.

**301 redirect needed:** No.

**Deletion tier:** **Tier 2** — `LeadTable.tsx` must drop the modal import first (or swap to the canonical drawer pattern). Then becomes leaf.

---

## Component 16 — `frontend/components/dashboard/ReportsView.tsx`

**Imported by:**
- `frontend/components/dashboard/index.ts:131` — re-export only.
- (No live route consumer — `app/dashboard/reports/page.tsx` imports from `@/components/reports`, not from `dashboard/ReportsView`.)

**Imports:** Heroicons + report fetch hooks. None would orphan.

**Routes affected:** None directly.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 1** — pure leaf via dead re-export.

---

## Component 17 — `frontend/components/dashboard/SettingsPanel.tsx`

**Imported by:**
- `frontend/components/dashboard/index.ts:122` — re-export only.

**Imports:** React + a settings hook.

**Routes affected:** None directly. `app/settings/page.tsx` does NOT import `SettingsPanel` — uses `AppShell` + custom layout instead.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 1** — pure leaf via dead re-export.

---

## Component 18 — `frontend/components/dashboard/KillSwitch.tsx` (KEEP)

**Imported by:**
- `frontend/app/dashboard/layout.tsx:19` — `import { KillSwitch } from "@/components/dashboard/KillSwitch";`

**Imports:** Heroicons + a kill-switch state hook + confirm-modal pattern.

**Routes affected:** All `/dashboard/**` routes (via the layout).

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **KEEP** — Phase 3 Item 1 designates this as the consolidation target. EmergencyPauseButton + PauseCycleButton are deleted; KillSwitch absorbs the responsibility (and may be moved into a topbar slot per Phase 3 Item 2 layout work).

---

## Component 19 — `frontend/components/dashboard/EmergencyPauseButton.tsx`

**Imported by:**
- `frontend/plasmic-init.ts:59, 68` — Plasmic registration
- `frontend/components/dashboard/index.ts:155` — re-export
- `frontend/components/layout/header.tsx:30` — `import { EmergencyPauseButton } from "@/components/dashboard/EmergencyPauseButton";`
- `frontend/components/layout/mobile-topbar.tsx:16` — `import { EmergencyPauseButton } from "@/components/dashboard/EmergencyPauseButton";`

**Imports:** A pause-state hook + heroicons.

**Routes affected:** Every route rendering `header.tsx` or `mobile-topbar.tsx`. The desktop header + the mobile topbar use it.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 3** — `header.tsx` and `mobile-topbar.tsx` must swap to `KillSwitch` first. Two real callers + Plasmic dead-end + index re-export. Highest-impact deletion in this set.

---

## Component 20 — `frontend/components/dashboard/PauseCycleButton.tsx`

**Imported by:** None (no consumers).

**Imports:** A cycle-pause hook + modal pattern.

**Routes affected:** None.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 1** — pure leaf. Safe to delete first.

---

## Component 21 — `frontend/components/dashboard/Sidebar.tsx`

**Imported by:**
- `frontend/components/dashboard/index.ts:9` — `export { Sidebar, type PageKey } from "./Sidebar";`
- (No direct route consumer — `app/dashboard/layout.tsx` uses `DashboardLayout` which uses `dashboard-v2/Sidebar`, a different file.)

**Imports:** Standard React + nav items + heroicons.

**Routes affected:** None directly.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 1** — pure leaf via dead re-export.

**Case-duplicate note:** there is also `components/layout/sidebar.tsx` (lowercase). On case-insensitive filesystems (macOS default) this could clash. Linux is fine; CI/CD may not be. Worth deleting both to remove the ambiguity.

---

## Component 22 — `frontend/components/layout/sidebar.tsx`

**Imported by:**
- `frontend/components/layout/dashboard-layout.tsx:20` — `import { Sidebar } from "./sidebar";`

**Imports:** Standard React + sidebar nav items.

**Routes affected:** Wherever `dashboard-layout.tsx` is consumed — but per the audit below (Component 23), `dashboard-layout.tsx` itself has no live importer.

**Tests affected:** None.

**301 redirect needed:** No.

**Deletion tier:** **Tier 2** — must wait for `dashboard-layout.tsx` (Component 23) deletion. Then becomes leaf.

---

## Component 23 — `frontend/components/layout/AppShell.tsx` & `dashboard-layout.tsx`

Two files, opposite verdicts.

### `AppShell.tsx`

**Imported by:** **10+ live routes** (incomplete list — sample):
- `app/campaigns/page.tsx:4`
- `app/billing/page.tsx:4`
- `app/leads/[id]/page.tsx:8`
- `app/leads/page.tsx:9`
- `app/settings/page.tsx:5`
- `app/dashboard/page.tsx:9`
- `app/dashboard/campaigns/page.tsx:12`
- `app/dashboard/campaigns/approval/page.tsx:12`
- `app/dashboard/campaigns/[id]/page.tsx:14`
- `app/dashboard/meetings/page.tsx:11`
- (more — full grep returns ~15 hits)

**Verdict:** **KEEP** — `AppShell.tsx` is the canonical layout wrapper and is widely imported. Despite being on the dispatch's deletion list (item 23), the dispatch text reads "consolidate to one" — `AppShell` is the survivor.

### `dashboard-layout.tsx`

**Imported by:**
- No live importer. The grep for `DashboardLayout` returns hits in `app/dashboard/layout.tsx:86, 167` but those `<DashboardLayout>` elements come from `dashboard-v2/DashboardLayout.tsx`, not `layout/dashboard-layout.tsx`.

**Verdict:** **DELETE** — `Tier 2` (cascades to delete `layout/sidebar.tsx`, Component 22).

---

## Component 24 — `frontend/app/dashboard/leads/[id]/page.tsx`

**Imported by:** Routes don't import other route pages, but **many components emit `Link href="/dashboard/leads/${id}"`**:
- `app/dashboard/replies/page.tsx:415`
- `src/components/dashboard/QuickActionsPanel.tsx:57` (uses `/dashboard/leads/import` — different path, unaffected)
- `components/leads/LeadScoreboardRow.tsx:139`
- `components/dashboard/meetings-widget.tsx:66`
- `components/dashboard/HotReplies.tsx:68`
- `components/dashboard/GlobalSearch.tsx:154`
- `lib/hooks/useAttentionItems.ts:144, 172`

**Imports:** Many — full lead detail page (action buttons, profile, history, etc.).

**Routes affected:** `/dashboard/leads/[id]` — the full-page route disappears entirely. The drawer is the canonical replacement per Phase 3 design.

**Tests affected:** Likely none directly (route page tests are rare in this codebase).

**301 redirect needed:** **YES.** Recommended:
- Option A — `/dashboard/leads/[id]` → `/dashboard/pipeline?lead=ID` (opens drawer over pipeline view).
- Option B — Next.js middleware that redirects to `/dashboard/replies?lead=ID` for replies-sourced links and to `/dashboard/pipeline?lead=ID` for everything else.
- Option C (simplest) — `/dashboard/leads/[id]` → `/dashboard?lead=ID` (drawer opens over home).

All linkers above need to update `Link href` strings to the new pattern (e.g. `?lead=${id}`) so the drawer auto-opens via search-param hook.

**Deletion tier:** **Tier 3** — heaviest in the set. 8+ Link callers must update + 1 redirect rule must land before the route deletes. Recommend a wrapper `useLeadDrawer()` hook that all linkers delegate to, so a single search-param convention drives drawer-open everywhere.

---

## Closing summary

### Tier breakdown

| Tier | Count | Items |
|---|---:|---|
| **Tier 1** (pure leaf — delete first) | **9** | DashboardMain (1), HeroMetricsCard (3), StatsRow (5), ActivityFeed (9), ActivityFeedSimple (11), LiveActivityFeed (13), ProspectDetailCard (14), ReportsView (16), SettingsPanel (17), PauseCycleButton (20), Sidebar dashboard (21) — counted 11 here actually; some are dead-re-export-only. **Verified Tier 1 count: 11.** |
| **Tier 2** (cascade — wait on Tier 1) | **5** | StatsGrid (4), ActivityTicker (12), LeadDetailModal (15), layout/sidebar (22), dashboard-layout.tsx (Component 23 part B) |
| **Tier 3** (route-bound — needs route swap first) | **6** | HeroStrip (2), CycleProgress (7), TodayStrip (8), ActivityFeedFull (10), EmergencyPauseButton (19), app/dashboard/leads/[id]/page.tsx (24) |
| **CONDITIONAL** | **1** | FunnelBar (6) — pending Phase 3 Item 3 build outcome |
| **KEEP** | **2** | KillSwitch (18) — consolidation target; AppShell (Component 23 part A) — canonical layout |

**Verified total: 24 items in scope** (Item 25 `/welcome` excluded per dispatch). 11 Tier 1 + 5 Tier 2 + 6 Tier 3 + 1 conditional + 1 keep (FunnelBar) + 2 keep (KillSwitch + AppShell) = 11 + 5 + 6 + 1 + 1 + 1 = **25 entries** (24 deletion candidates + the AppShell-stays note). Math reconciles when AppShell/dashboard-layout is treated as one dispatch entry split into two verdicts.

### Routes affected

| Route | Source of impact |
|---|---|
| `/dashboard` | HeroStrip, FunnelBar (conditional), CycleProgress, TodayStrip |
| `/dashboard/activity` | ActivityFeedFull |
| `/dashboard/leads/[id]` | Route deletion (301 needed) |
| Most other `/dashboard/**` | KillSwitch (kept) + EmergencyPauseButton swap in `header.tsx` + `mobile-topbar.tsx` |
| Wherever `LeadTable` renders | LeadDetailModal swap |

### Tests affected

- `frontend/lib/__tests__/useLiveActivityFeed.test.tsx` — tests the **hook**, not the component. Hook stays; test stays.
- No other test files reference any of the 24 deletion candidates by name.

**Tests needing update: 0.** Tests needing deletion: 0.

### `/welcome` exclusion

Item 25 (`frontend/app/welcome`) **is NOT in deletion scope** per Dave's Path B decision. Skip entirely.

### Cross-cutting hazards

- **Plasmic registrations** (`plasmic-init.ts`) reference HeroMetricsCard, LiveActivityFeed, EmergencyPauseButton. If Plasmic studio isn't actively used, drop those registrations as part of the cleanup. If it IS used, the deletions need a Plasmic-side update too.
- **Cross-package re-exports** (`components/admin/index.ts`, `components/bloomberg/index.ts`) re-export some of the dashboard components. Verify the admin/bloomberg surfaces actually consume them; if not, drop the re-exports along with the deletion.
- **Case-duplicate** Sidebar: `components/dashboard/Sidebar.tsx` (capital) AND `components/layout/sidebar.tsx` (lowercase). Both deletable; CI on case-insensitive filesystems may have already broken if both shipped.

---

## Recommended deletion sequence

Group commits by tier so each commit is an atomic, reviewable, reverable unit.

### Commit batch 1 — Tier 1 leaves (11 deletions)

Pure leaves. No route or cross-component impact. Safe to delete in a single PR.

1. `frontend/components/dashboard/DashboardMain.tsx`
2. `frontend/components/dashboard/HeroMetricsCard.tsx`
3. `frontend/components/dashboard/StatsRow.tsx`
4. `frontend/components/dashboard/ActivityFeed.tsx`
5. `frontend/components/dashboard/ActivityFeedSimple.tsx`
6. `frontend/components/dashboard/LiveActivityFeed.tsx`
7. `frontend/components/dashboard/ProspectDetailCard.tsx`
8. `frontend/components/dashboard/ReportsView.tsx`
9. `frontend/components/dashboard/SettingsPanel.tsx`
10. `frontend/components/dashboard/PauseCycleButton.tsx`
11. `frontend/components/dashboard/Sidebar.tsx`

Plus removal of every `index.ts` re-export pointing at these files. Update `plasmic-init.ts` to drop the dead Plasmic registrations.

### Commit batch 2 — route swaps (Tier 3 prep)

Update routes to swap or remove the components before they're deleted.

1. `app/dashboard/page.tsx` — remove or replace `<HeroStrip />`, `<CycleProgress />`, `<TodayStrip />` (and `<FunnelBar />` only if Phase 3 Item 3 swaps to a new component).
2. `app/dashboard/activity/page.tsx` — swap `ActivityFeedFull` to whatever the canonical activity component is.
3. `components/layout/header.tsx` and `components/layout/mobile-topbar.tsx` — swap `EmergencyPauseButton` for `KillSwitch`.
4. `components/dashboard/LeadTable.tsx` — drop `LeadDetailModal` import + usage; rely on the canonical drawer.
5. Linkers (8 files) for `/dashboard/leads/[id]` — switch `Link href` to drawer-search-param convention. Add Next.js redirect for `/dashboard/leads/[id]` → `/dashboard?lead=ID` (or the chosen pattern).

### Commit batch 3 — Tier 3 deletes (5 deletions)

Now that route swaps have landed, delete the route-bound files.

1. `frontend/components/dashboard/HeroStrip.tsx`
2. `frontend/components/dashboard/CycleProgress.tsx` *(only if Phase 3 Item 2 elects to replace rather than refactor)*
3. `frontend/components/dashboard/TodayStrip.tsx`
4. `frontend/components/dashboard/ActivityFeedFull.tsx`
5. `frontend/components/dashboard/EmergencyPauseButton.tsx`
6. `frontend/app/dashboard/leads/[id]/page.tsx`

### Commit batch 4 — Tier 2 deletes (5 deletions)

Cascade deletes after Tier 1 and route swaps clear the way.

1. `frontend/components/dashboard/StatsGrid.tsx`
2. `frontend/components/dashboard/ActivityTicker.tsx` (LiveActivityFeed already gone in batch 1)
3. `frontend/components/dashboard/LeadDetailModal.tsx` (LeadTable updated in batch 2)
4. `frontend/components/layout/sidebar.tsx` (dashboard-layout deletion in same batch)
5. `frontend/components/layout/dashboard-layout.tsx`

### Conditional / KEEP

- `FunnelBar.tsx` — **conditional**: stays if Phase 3 Item 3 refactors; deletes (Tier 3) if Phase 3 elects to replace.
- `KillSwitch.tsx` — **KEEP** (Phase 3 Item 1 consolidation target).
- `AppShell.tsx` — **KEEP** (canonical layout, ~10 live importers).

### Recommended PR structure

- **PR 1**: Batch 1 (Tier 1 leaves) + index.ts cleanup + Plasmic dead-registration removal. Low-risk, easy-revert.
- **PR 2**: Batch 2 (route swaps). Includes the redirect rule for `/dashboard/leads/[id]`.
- **PR 3**: Batches 3 + 4 (Tier 3 + Tier 2 deletes). Once routes are clean, all remaining files are leaves.

### Out of scope for this audit

- Backend implications of Plasmic-loader removal.
- Visual regression testing of route-swap commits.
- Migration of any persisted user state tied to `/dashboard/leads/[id]` deep links (likely none — this is a session-scoped UI route).

---

*This document is research-only. No code edits. Generated 2026-04-30 on `aiden/phase3-cleanup-map` branch.*
