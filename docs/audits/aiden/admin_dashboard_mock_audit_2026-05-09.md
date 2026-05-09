# Admin Dashboard Mock Audit

**Compiled:** 2026-05-09
**Author:** Aiden
**Trigger:** Original 2026-05-08 audit flagged "Admin dashboard: 15 of 20 pages render hardcoded mock arrays — Descoped to Phase 4". This audit verifies the count + classifies each page so the Phase 4 work has a concrete starting list.

---

## Headline finding

**16 of 20 admin pages contain inline `const mock*` arrays** (one more than the original 2026-05-08 estimate). 4 pages render real data via `useAdmin*` hooks and Supabase queries.

Different from the dashboard mock-data debt cleared in PRs #644/#647/#652/#653/#654: admin uses **inline** mock literals inside the page files (not imported from `data/mock-*.ts` or `lib/mock/*.ts`). PR-time grep for the dashboard pattern returned zero hits; the inline pattern is what populates these pages.

---

## Per-page classification

### Real-data (4 pages — no inline mocks)

| Page | LOC | Backing |
|---|---|---|
| `/admin` | 308 | `useAdminStats` + `useSystemHealth` + `useAlerts` + `useGlobalActivity` hooks |
| `/admin/activity` | 283 | hook-based (verified no inline mock) |
| `/admin/clients` | 294 | hook-based (verified no inline mock) |
| `/admin/costs/ai` | 254 | hook-based — likely consumes `sdk_usage_log` |
| `/admin/settings` | 234 | hook-based |

### Mock-driven (16 pages — inline `const mock*`)

| Page | Inline mock arrays | Real Supabase target |
|---|---|---|
| `/admin/campaigns` | `mockCampaigns` | `campaigns` table |
| `/admin/clients/[id]` | `mockClient` | `clients` JOIN `memberships` JOIN `users` |
| `/admin/compliance` | `mockCompliance` | aggregate of `email_events` (bounces/complaints) + DNCR check counts |
| `/admin/compliance/bounces` | `mockBounces`, `mockClientRates` | `email_events` filtered to bounce types |
| `/admin/compliance/suppression` | `mockSuppressionList` | `email_suppression` table (verify exists) |
| `/admin/costs` | `mockCosts` | `sdk_usage_log` + `vendor_usage_log` aggregate |
| `/admin/costs/channels` | `mockChannelCosts` | `vendor_usage_log` GROUP BY vendor |
| `/admin/leads` | `mockLeads` | `leads` table |
| `/admin/replies` | `mockReplies` | `activities` filtered to reply-shaped actions |
| `/admin/revenue` | `mockRevenue`, `mockTierBreakdown`, `mockRecentTransactions` | **Blocked** — Stripe wiring + revenue tracking not built |
| `/admin/settings/users` | `mockUsers` | `users` table |
| `/admin/system` | `mockServices`, `mockFlows`, `mockErrors` | mix: services need infra ping; flows from `prefect_flow_runs`; errors from log aggregation |
| `/admin/system/errors` | `mockErrors` | log aggregation table (verify exists) |
| `/admin/system/queues` | `mockFlows`, `mockQueueStats` | Prefect API + Redis queue depth — likely needs backend wiring not just Supabase |
| `/admin/system/rate-limits` | `mockRateLimits`, `mockClientLimits` | rate-limit tracking table (verify exists) |

### Sub-pages already counted above
- `/admin/system/page.tsx` and 3 of its sub-pages (errors/queues/rate-limits) all mock-driven.
- `/admin/costs/page.tsx` mock; `/admin/costs/ai/page.tsx` real; `/admin/costs/channels/page.tsx` mock.
- `/admin/compliance/page.tsx` mock; both subpages also mock.

---

## Wireability tiering

### Tier A — wire-now (low complexity, Supabase tables exist)
- `/admin/campaigns` → `campaigns` table
- `/admin/clients/[id]` → `clients` JOIN
- `/admin/leads` → `leads` table
- `/admin/replies` → `activities` filtered (reply-shaped actions; same pattern as `/api/replies` from PR #639)
- `/admin/settings/users` → `users` table
- `/admin/costs` → `sdk_usage_log` + `vendor_usage_log` (same shape as PR #656 ops panel cost cards)
- `/admin/costs/channels` → `vendor_usage_log` GROUP BY vendor (same shape as PR #656)

**Tier A total:** 7 pages, mostly straightforward SELECT + GROUP BY queries. ~150-250 LOC each = ~1,500-1,800 LOC of wiring work.

### Tier B — needs schema check (table existence not yet verified)
- `/admin/compliance` (aggregate of `email_events` + DNCR — `email_events` exists per PR #639 audit; DNCR aggregate may need new view)
- `/admin/compliance/bounces` (`email_events` filter)
- `/admin/compliance/suppression` (`email_suppression` table — verify exists)
- `/admin/system/errors` (log aggregation table — verify exists)
- `/admin/system/rate-limits` (rate-limit tracking table — verify exists)

**Tier B total:** 5 pages, ~1,000-1,500 LOC of wiring + 0-3 schema migrations depending on what's missing.

### Tier C — blocked on upstream gaps
- `/admin/revenue` — Stripe wiring not built (audit: `price_id=None`); revenue tracking absent
- `/admin/system` — services need infra ping; flows need Prefect API client; errors need log infra
- `/admin/system/queues` — Prefect API + Redis queue depth (backend integration not just Supabase)

**Tier C total:** 3 pages. **Blocked** — wiring premature until upstream features ship.

---

## Recommendation

**Phase 4 admin descope batch:**

1. **Tier A first** — 7 pages, ~1,500-1,800 LOC of wiring. All Supabase-direct, similar shape to /admin/ops (PR #656). Could split into 2-3 PRs (e.g., A1: campaigns + leads + replies + clients/[id]; A2: costs + costs/channels + settings/users).

2. **Tier B second** — verify schema existence first (`email_suppression`, `system_errors`, `rate_limits` tables) via a one-shot read-only SQL check. If tables exist: same shape as Tier A. If missing: schema migration first, like the `vendor_usage_log` precedent in PR #649.

3. **Tier C deferred** — `/admin/revenue` waits on Stripe; `/admin/system` waits on infra-ping integration; `/admin/system/queues` waits on Prefect API client. None of these block earlier-tier work.

**Alt path: descope all 16** — same pattern as Tier 4 dashboard (PR #647). Pre-revenue, internal admin tooling has no paying-customer impact. Could delete instead of wire. Upside: ~5,000+ LOC removed instantly. Downside: rebuild later when there's a real reason.

**My recommendation: wire Tier A, defer Tier B + C.** The admin tooling supports the team's work — different surface from client-facing dashboard. The 7 Tier A pages each have a clear Supabase target table and provide real operational visibility.

---

## Verification commands (rerun before Phase 4 build)

```bash
# Count inline mock arrays per admin page
$ for p in $(find frontend/app/admin -name page.tsx | sort); do
    count=$(grep -cE "^const (mock|MOCK)" "$p")
    [ "$count" -gt 0 ] && echo "$count  $p"
  done

# Total mock arrays across admin
$ grep -rcE "^const (mock|MOCK)" frontend/app/admin --include=page.tsx | awk -F: '{s+=$NF} END {print s}'
```

Pre-Phase-4 schema verification commands documented inline per page in the table above.
