# Corrections to dashboard data-flow audit (PR #643)

**Compiled:** 2026-05-09 (post-stress-test)
**Pairs with:** `dashboard_data_flow_2026-05-09.md`, `option_a_deletion_manifest_2026-05-09.md`
**Why this exists:** Tier 3 stress test on `components/inbox/` revealed gaps that invalidate parts of the original audit. Per Rule 3 + the `independent verification not echo` memory pin, I'm posting the corrections rather than silently amending the manifest.

---

## What the stress test caught

Sandbox branch `aiden/sandbox-tier3-inbox-stress` (since discarded) deleted the 20 inbox/* components flagged "no external importers" in the manifest. `pnpm tsc --noEmit` failed with 20 errors:

```
app/replies/page.tsx(6,34): error TS2307: Cannot find module '@/components/inbox/ConversationList'
app/replies/page.tsx(7,36): error TS2307: Cannot find module '@/components/inbox/ConversationDetail'
components/inbox/index.ts(5,29): error TS2307: ... './InboxHeader'
components/inbox/detail/index.ts(7,35): error TS2307: ... './ReplyDetailHeader'
[... 16 more]
```

Two systematic gaps in the original audit:

### Gap 1 — Barrel exports re-export deleted symbols

The original per-component grep (`grep -rln "from.*[/\"]$comp[\"']"`) caught **named imports** but missed the barrel pattern:

```ts
// frontend/components/inbox/index.ts
export { InboxHeader } from './InboxHeader';
export { InboxFilters } from './InboxFilters';
…
```

Five barrel files (`components/{inbox,inbox/detail,leads,campaigns,billing}/index.ts`) re-export the components I marked deletable. These barrels themselves have non-zero importers in some cases:

| Barrel | External importers |
|---|---|
| `components/inbox/index.ts` | 0 |
| `components/inbox/detail/index.ts` | **`frontend/app/dashboard/inbox/[id]/page.tsx`** (LIVE under /dashboard/) |
| `components/leads/index.ts` | 0 |
| `components/campaigns/index.ts` | only stranded `/campaigns/page.tsx` |
| `components/billing/index.ts` | only stranded `/billing/page.tsx` |

### Gap 2 — `frontend/lib/mock/` directory was not audited

The original audit grepped `lib/demo-data` + `data/mock-*` but missed `frontend/lib/mock/` (3 files, ~20KB). Importer counts:

| File | Importers | Read |
|---|---|---|
| `lib/mock/inbox-data.ts` | 1 | `frontend/app/dashboard/inbox/[id]/page.tsx` |
| `lib/mock/reports-data.ts` | 11 | All `frontend/components/reports/*` consumed by **`/dashboard/reports`** (LIVE) |
| `lib/mock/settings-data.ts` | 8 | `app/settings/page.tsx`, **`app/dashboard/settings/page.tsx`** (LIVE), 6× `components/settings/*` |

This means the original audit's claim that **"/dashboard/* is fully honest, no mock-data imports"** is wrong. Three `/dashboard/*` surfaces are mock-driven:

- `/dashboard/reports` (audit said WORKS) → consumes `lib/mock/reports-data.ts` via 11 reports components
- `/dashboard/settings` (audit said WORKS) → consumes `lib/mock/settings-data.ts` via 6 settings components
- `/dashboard/inbox/[id]` (audit said PARTIAL) → consumes `lib/mock/inbox-data.ts` + 11 detail components

### Gap 3 — `/dashboard/inbox` redirect drops a query param

`NotificationsPanel.tsx` constructs `href="/dashboard/inbox?replyId=rep-123"` URLs (verbatim). The B2.4 redirect to `/dashboard/activity` strips the `?replyId` param. This is a UX bug, not a deletion-safety issue, but worth flagging.

---

## Corrected picture

### Tier 1 (PR #644) — still safe, ship as-is
The 4 files in PR #644 genuinely have 0 importers. Stress test + this re-audit don't change that conclusion. **PR #644 should still merge.**

### Tier 2 + Tier 3 — more coupled than the manifest implied
- `/replies` page deletion REQUIRES `inbox/ConversationList` + `inbox/ConversationDetail` deletion (page imports them direct). They go together, not independently.
- `inbox/` and `inbox/detail/` barrel files MUST be deleted alongside the components they re-export, OR have their export lines edited.
- `/dashboard/inbox/[id]` + 11 `detail/*` components + `lib/mock/inbox-data.ts` are also stranded (no inbound nav links found via grep) — should be added to deletion scope.

### New Tier 4 — `/dashboard/reports` + `/dashboard/settings` are mock-driven
This is the bigger finding. Two LIVE `/dashboard/*` surfaces are NOT honest. They were marked WORKS in the original audit because they render — but they render fake data. Honest path requires either:
- (i) Wire reports + settings components to real Supabase / FastAPI, OR
- (ii) Delete the `/dashboard/reports` + `/dashboard/settings` surfaces (only viable if we descope reports + settings entirely, which is a Dave/Max business decision)

Until Tier 4 is resolved, claiming "no fake data the client can see post-login" is still wrong even if Tiers 1-3 ship.

---

## What I'm doing about it

1. **PR #644 stays as-is** — Tier 1 verification independent of all the above.
2. **PR #643 manifest is overconfident** — the "single mechanical commit, zero risk" framing was wrong for Tier 3. Adding this correction commit so reviewers see the full picture.
3. **No Tier 3 stress-test PR yet** — would have shipped a broken diff. Discarded sandbox.
4. **Tier 4 (reports + settings honesty) is the bigger ask** — needs Dave/Max scope decision.

---

## Recommendation revision

| Tier | Action | Risk | Status |
|---|---|---|---|
| 1 | Delete 4 orphaned files (PR #644) | Zero | Ready to merge |
| 2+3 | Delete stranded routes + components + barrels in **one coupled commit** (not per-tier) | Low if barrels handled | Manifest needs rebuild |
| 4 | Resolve `/dashboard/reports` + `/dashboard/settings` mock-data load | Medium | Needs scope decision (wire vs descope) |

Tier 2+3 PR's correct shape: ~63-70 file deletions (original 63 + 5 barrel files + 11 detail components + lib/mock/inbox-data) totaling ~7,000-7,500 LOC, single PR, requires `pnpm tsc` green post-delete.
