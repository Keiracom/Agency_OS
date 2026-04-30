# P3 cleanup — R7 audit + deletion log (2026-04-30)

## ITEM 8 — BDR hero smoke test
HeroStrip.tsx is at parity with /demo's BDR hero block (Playfair
amber italic emphasis, 4-card sum row with proportional flex,
JetBrains Mono labels). **Verified — no changes.** Any future visual
delta is a v2 follow-up and out of scope here.

## CLEANUP — deletion audit + result

### Deletion verification command
```
grep -rEn "[\"']\\./([A-Za-z_/]+/)?<C>[\"']|[\"']@/components/[^\"']*/<C>[\"']|^\\s*import\\s*\\{[^}]*\\b<C>\\b[^}]*\\}\\s*from" \
  --include='*.tsx' --include='*.ts' app/ components/ lib/ hooks/ \
  | grep -v "components/dashboard/<C>\\." \
  | grep -v "components/.*/index\\.ts" \
  | grep -v "\\.test\\.tsx"
```

If output is empty → only barrel re-exports / zero real importers → safe to delete.

### Deletion result table

| Component | Tier | Real importers | Action |
|---|---|---|---|
| `DashboardMain.tsx` | 1 | 0 (barrel only) | ✅ DELETED |
| `HeroMetricsCard.tsx` | 1 | 0 (barrel + plasmic-init) | ✅ DELETED + plasmic-init reg removed |
| `StatsRow.tsx` | 1 | 0 | ✅ DELETED |
| `ActivityFeed.tsx` | 1 | 0 (barrel only) | ✅ DELETED |
| `ActivityFeedSimple.tsx` | 1 | 0 | ✅ DELETED |
| `LiveActivityFeed.tsx` | 1 | 0 (barrel + plasmic-init) | ✅ DELETED + plasmic-init reg removed |
| `ProspectDetailCard.tsx` | 1 | 0 | ✅ DELETED |
| `ReportsView.tsx` | 1 | 0 (barrel only) | ✅ DELETED |
| `SettingsPanel.tsx` | 1 | 0 (barrel only) | ✅ DELETED |
| `dashboard/Sidebar.tsx` | 1 | 0 (case-duplicate of layout/sidebar.tsx) | ✅ DELETED |
| `StatsGrid.tsx` | 2 | 0 (barrel only) | ✅ DELETED |
| `ActivityTicker.tsx` | 2 | 1 — `LiveActivityFeed.tsx` (also being deleted) | ✅ DELETED in same pass |
| `LeadDetailModal.tsx` | 2 | 1 — `LeadTable.tsx:308` (live use) | ❌ BLOCKED — LeadTable opens this modal on row click. Cannot delete without rewiring LeadTable to use the prospect drawer. Deferred to a follow-up PR |
| `app/dashboard/leads/[id]/page.tsx` | 3 | route-bound | ✅ Replaced with redirect → `/dashboard/pipeline?lead={id}` (571 → 22 lines) |
| `KillSwitch.tsx` | extra | 1 — `app/dashboard/layout.tsx:19` (still imported on main) | ❌ BLOCKED — PR #466 (`elliot/p3-items-2-1`) removes the import as part of the PauseAllButton consolidation. Delete after #466 merges |
| `EmergencyPauseButton.tsx` | extra | 2 — `header.tsx:30`, `mobile-topbar.tsx:16` | ❌ BLOCKED — same as KillSwitch, removed by PR #466. Delete after #466 merges |

### Deleted: 12 components + 1 route bespoke implementation = 13 files
- `components/dashboard/DashboardMain.tsx`
- `components/dashboard/HeroMetricsCard.tsx`
- `components/dashboard/StatsRow.tsx`
- `components/dashboard/ActivityFeed.tsx`
- `components/dashboard/ActivityFeedSimple.tsx`
- `components/dashboard/LiveActivityFeed.tsx`
- `components/dashboard/ProspectDetailCard.tsx`
- `components/dashboard/ReportsView.tsx`
- `components/dashboard/SettingsPanel.tsx`
- `components/dashboard/Sidebar.tsx`
- `components/dashboard/StatsGrid.tsx`
- `components/dashboard/ActivityTicker.tsx`
- `app/dashboard/leads/[id]/page.tsx` (replaced with 22-line redirect, original 571 lines preserved in git)

### Blocked deletions (3) — flagged for follow-up
- `LeadDetailModal.tsx` — pending LeadTable rewiring
- `KillSwitch.tsx` — pending PR #466 merge
- `EmergencyPauseButton.tsx` — pending PR #466 merge

### Barrel cleanup
`components/dashboard/index.ts` had dead re-exports for every Tier 1
file. All 9 references stripped. The remaining `ActivityFeedItem`
type re-export points at `@/hooks/use-activity-feed` (a different
hook, not the deleted component) — left as-is.

### plasmic-init.ts
`HeroMetricsCard` and `LiveActivityFeed` registrations removed —
both pointed at deleted modules and would otherwise break the build.

## Verification
```
pnpm run build  →  exit 0
```
- Zero broken imports
- All routes resolve
- 13 components removed; one route bespoke implementation replaced with a redirect
