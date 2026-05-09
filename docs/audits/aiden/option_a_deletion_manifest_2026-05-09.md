# Option A — Deletion Manifest

**Compiled:** 2026-05-09
**Author:** Aiden
**Pairs with:** `dashboard_data_flow_2026-05-09.md` (PR #643)
**Status:** Pre-scope. Awaiting Dave/Max ratification of Option A.

This manifest pre-resolves every "is X safe to delete?" question for Option A, so the actual deletion PR is one mechanical commit with no per-file investigation.

---

## TIER 1 — Already orphaned, delete unconditionally (0 importers)

These are pure dead code with **zero importers anywhere in the repo**. No ratification needed beyond Option A itself.

| File | LOC | Importers |
|---|---|---|
| `frontend/lib/demo-data.ts` | 1,603 | 0 |
| `frontend/data/mock-reports.ts` | 315 | 0 |
| `frontend/data/mock-dashboard.ts` | 209 | 0 |
| `frontend/data/mock-settings.ts` | 150 | 0 |

**Tier 1 subtotal: 2,277 LOC.**

---

## TIER 2 — Stranded routes (delete pages + import-only mock files)

| File | LOC | Why safe |
|---|---|---|
| `frontend/app/leads/page.tsx` | 72 | No nav links to `/leads`; only internal back-link from `/leads/[id]` (also being deleted) |
| `frontend/app/leads/[id]/page.tsx` | 59 | No nav links; `[id]` is the only thing referencing `/leads` |
| `frontend/app/campaigns/page.tsx` | 90 | No nav links to `/campaigns` (top-level) |
| `frontend/app/billing/page.tsx` | 59 | No nav links to `/billing` (top-level) |
| `frontend/app/replies/page.tsx` | 64 | No nav links to `/replies` (top-level) |
| `frontend/data/mock-leads.ts` | 119 | Importers = page above + components-being-deleted-below |
| `frontend/data/mock-lead-detail.ts` | 140 | Importers = page above + components-being-deleted-below |
| `frontend/data/mock-campaigns.ts` | 137 | Importers = page above + components-being-deleted-below |
| `frontend/data/mock-billing.ts` | 180 | Importers = page above + components-being-deleted-below |
| `frontend/data/mock-inbox.ts` | 205 | Importers = page above + components-being-deleted-below |

**Tier 2 subtotal: 1,125 LOC.**

---

## TIER 3 — Stranded-only components (delete with the routes)

These have **zero external importers** outside `frontend/components/{leads,campaigns,billing,inbox}/` and `frontend/app/{leads,campaigns,billing,replies}/`. Verified via per-component grep across `frontend/`.

### `components/billing/` (6 of 7 deletable)
- InvoiceTable, PaymentMethod, PlanComparison, PlanHeroCard, UpgradeCTA, UsageMeters
- **KEEP:** `StripeCheckoutButton.tsx` — imported by `frontend/app/page.tsx` (homepage)

### `components/campaigns/` (12 of 19 deletable)
- BestContentCard, CampaignAllocationManager, CampaignChannels, CampaignMetrics, CampaignSequence, CampaignStatusBadge, CampaignTabs, InsightBox, permission-mode-selector, PrioritySlider, RecommendationsCard, SequenceBuilder, SequenceStep
- **KEEP:** `CampaignCard` (used by plasmic + dashboard-v2/DashboardHome), `CampaignMetricsPanel`, `CampaignPriorityCard`, `CampaignPriorityPanel` (all imported by plasmic-init.ts), `TargetingFilters` (used by `/dashboard/campaigns/new` + `useICPAutoPopulate` hook)

### `components/inbox/` (16 of 17 deletable)
- ChannelBadge, ConversationDetail, ConversationList, detail/{ActivityTimeline, AISuggestions, EmailMessage, LeadDetails, LeadHeader, NotesSection, ReplyComposer, ReplyDetailHeader, ScoreBreakdown, SMSThread}, InboxFilters, InboxHeader, InboxListItem, InboxList, InboxPreview, IntentBadge, SentimentBadge
- **KEEP:** `detail/QuickActions.tsx` — imported by `bloomberg/index.ts` + `dashboard/index.ts`

### `components/leads/` (15 of 18 deletable)
- CommunicationTimeline, LeadActivityTimeline, LeadBulkActions, LeadContactInfo, LeadEnrichmentCard, LeadHeader, LeadQuickActions, LeadRadarChart, LeadScoreboardRow, LeadsFilters, LeadsTable, LeadStatusProgress, LeadTierBadge, LeadTimeline, SiegeWaterfallProgress, SplitFlapCounter, WhyHotBadge
- **KEEP:** `ALSScorecard.tsx` — imported by plasmic-init.ts

**Tier 3 subtotal: ~3,300 LOC across 49 components.**

---

## Summary table

| Tier | LOC | Files | Risk |
|---|---|---|---|
| 1 — already orphaned | 2,277 | 4 | Zero |
| 2 — stranded routes + page-only mocks | 1,125 | 10 | Zero (no nav links) |
| 3 — stranded-only components | ~3,300 | 49 | Zero (no external importers verified) |
| **TOTAL** | **~6,700 LOC** | **63 files** | **Zero — single mechanical commit** |

Components retained: 8 (StripeCheckoutButton, CampaignCard, CampaignMetricsPanel, CampaignPriorityCard, CampaignPriorityPanel, TargetingFilters, ALSScorecard, detail/QuickActions). All have a documented external consumer.

---

## Verification commands (rerun before commit)

```bash
# Tier 1 — confirm zero importers
for f in lib/demo-data data/mock-reports data/mock-dashboard data/mock-settings; do
  count=$(grep -rln "from.*[\"'].*$(basename $f)[\"']" frontend --include="*.ts" --include="*.tsx" \
    | grep -v node_modules | grep -v "^frontend/$f.ts$" | wc -l)
  echo "$f: $count importers"
done

# Tier 3 — confirm no external importer for a sample component
for comp in InvoiceTable BestContentCard ConversationList LeadsTable; do
  echo "=== $comp ==="
  grep -rln "from.*[/\"]$comp[\"']\\|import.*\\b$comp\\b" frontend --include="*.ts" --include="*.tsx" \
    | grep -v node_modules \
    | grep -v "^frontend/app/leads\\|^frontend/app/campaigns\\|^frontend/app/billing\\|^frontend/app/replies" \
    | grep -v "^frontend/components/leads\\|^frontend/components/campaigns\\|^frontend/components/billing\\|^frontend/components/inbox"
done
```

---

## Execution plan when Option A is ratified

1. New branch `aiden/option-a-stranded-cleanup` off latest main.
2. Delete all 63 files via `git rm`.
3. `cd frontend && pnpm tsc --noEmit` — must exit 0. If any kept component has a transitive import to a deleted file, fix in the same commit.
4. `pnpm test` — must pass.
5. Single commit, single PR, single review.

Estimated PR diff: 0 ins / ~6,700 del.
