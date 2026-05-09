# Tier 4 — Wire vs Descope analysis

**Compiled:** 2026-05-09
**Author:** Aiden
**Pairs with:** `dashboard_data_flow_corrections_2026-05-09.md` (PR #643)
**Trigger:** Max flagged Tier 4 (`/dashboard/reports` + `/dashboard/settings` + `/dashboard/inbox/[id]` mock-driven) as a scope decision for Dave. This doc pre-resolves the wire-vs-descope tradeoff with concrete Supabase tables + LOC estimates so the decision is fast.

---

## Surface 1 — `/dashboard/reports`

**Current state:** 11 components in `frontend/components/reports/` consume `lib/mock/reports-data.ts` (10,408 bytes). Page renders dashboards with fake metrics.

**Mock data shape (14 exports):** `heroMetrics`, `channelData`, `meetingsData`, `funnelData`, `responseRates`, `whoConverts`, `bestTiming`, `discoveryInsight`, `leadSources`, `tierData`, `voiceStats`, `objectionData`, `roiSummary`, `dateRangeOptions`.

| Component | Mock dependency | Real Supabase target | Wiring complexity |
|---|---|---|---|
| `HeroMetrics` | `heroMetrics` (4 KPI cards) | `activities` + `meetings` aggregations + `cis_agent_metrics` | Low — 4 SELECT COUNTs |
| `ChannelMatrix` | `channelData` (channel × metric grid) | `activities` GROUP BY channel × action | Low — single GROUP BY |
| `ConversionFunnel` | `funnelData` (Sent → Opened → Replied → Met → Booked) | `activities` (sent/opened) + `meetings` | Low — 5 COUNT FILTERs |
| `MeetingsChart` | `meetingsData` (monthly breakdown) | `meetings` GROUP BY DATE_TRUNC('month', scheduled_at) | Low |
| `LeadSources` | `leadSources` (where leads came from) | `business_universe.discovery_source` aggregation | Medium — discovery_source enum mapping |
| `TierConversion` | `tierData` (T1/T2/T3 conversion rates) | `cis_als_tier_conversions` | Low — table exists |
| `ResponseRates` | `responseRates` | `activities` reply-action rate over send-action total | Low |
| `WhatsWorking` | `whoConverts`, `bestTiming`, `discoveryInsight` | `conversion_patterns` table (already exists) | Medium — pattern_history JSONB |
| `VoicePerformance` | `voiceStats`, `objectionData` | No live source — voice_calls = 0, objection extraction unwired | **High — blocked on voice path** |
| `ROISummary` | `roiSummary` | Computed (revenue not tracked yet) | **High — blocked on Stripe wiring** |
| `ReportsHeader` | `dateRangeOptions` | Static array, keep | None |

**Wire LOC estimate:** ~250-350 LOC across 8 wirable components + ~3 SQL views/RPCs. **2 components (Voice, ROI) blocked on upstream gaps** (voice path not built, revenue not tracked).

**Pre-revenue reality:** with 0 customers, revenue = $0, voice_calls = 0, meetings = 0. Even fully wired, the page would render mostly zeros. That's honest, but it's a thin payoff for ~300 LOC of wiring work.

**Descope alternative:** delete `frontend/app/dashboard/reports/page.tsx` + 11 components + `lib/mock/reports-data.ts`. ~1,500 LOC removed. Sidebar entry currently links to it (per `frontend/components/layout/sidebar.tsx`); link must also be removed. Re-add Reports later when there's real data.

---

## Surface 2 — `/dashboard/settings`

**Current state:** `frontend/app/dashboard/settings/page.tsx` + 6 components in `frontend/components/settings/` consume `lib/mock/settings-data.ts` (3,876 bytes). Renders profile, team, integrations, notifications, API keys, billing sections.

**Mock data shape:** `UserProfile`, `TeamMember[]`, `Integration[]`, `NotificationPreference[]`, `ApiKey[]`, `BillingInfo`.

**Important nuance:** `/dashboard/settings/profile` and `/dashboard/settings/notifications` are SEPARATE pages flagged WORKS (real backend wiring per audit) at 440 + 619 LOC. The mock-driven `/dashboard/settings/page.tsx` is the index hub — separate from the working sub-pages. It's primarily a navigation card grid + summary.

| Component | Mock dependency | Real Supabase / FastAPI target | Wiring complexity |
|---|---|---|---|
| `ProfileSection` | `mockUserProfile` | `supabase.auth.getUser()` + `users` table (exists, 22 rows) | Low — auth + 1 SELECT |
| `TeamSection` | `mockTeamMembers` | `memberships` JOIN `users` | Low |
| `IntegrationsSection` + `IntegrationCard` | `mockIntegrations` | `client_integrations` table — **MISSING in prod schema** | Medium + schema migration |
| `NotificationsSection` | `mockNotifications` | `notification_preferences` table — **MISSING in prod schema** | Medium + schema migration |
| `BillingSection` | `mockBillingInfo` | Stripe (price_id=None per audit, blocked) | **High — blocked on Stripe** |

**Wire LOC estimate:** ~250-300 LOC. Both `client_integrations` and `notification_preferences` are confirmed missing from `public` schema (verified 2026-05-09 by Elliot via independent table-existence query) — wiring requires creating both tables first (+50 LOC migration each, +100 total). Billing blocked on Stripe.

**Schema verification (verbatim):**
```
client_integrations            MISSING
notification_preferences       MISSING
users                          EXISTS, rows=22
memberships                    EXISTS
```

**Descope alternative:** index page is just a card grid linking to sub-pages. Could be reduced to 50 LOC of static cards pointing at the WORKS sub-pages (`/dashboard/settings/profile`, `/dashboard/settings/notifications`, `/dashboard/settings/icp`, `/dashboard/settings/linkedin`). No data needed.

---

## Surface 3 — `/dashboard/inbox/[id]`

**Current state:** Page + 11 `components/inbox/detail/*` components consume `lib/mock/inbox-data.ts` (10,408 bytes — biggest mock file in scope). Renders single-reply detail view (David Park demo). The `/dashboard/inbox` parent redirects to `/dashboard/activity`; `/dashboard/inbox/[id]` is reachable only by direct URL or via `NotificationsPanel` constructed link (`?replyId=X` which the parent strips).

**Reachability problem:** `NotificationsPanel.tsx` builds `/dashboard/inbox?replyId=rep-123` → parent redirects to `/dashboard/activity` → `?replyId` is dropped → `/dashboard/inbox/[id]` is never actually navigated to. The page is functionally orphaned by the redirect even though it has nominal traffic.

**Mock data shape:** `mockInboxMessages`, `mockDavidParkThread`, `mockDavidParkSMS`, `mockAISuggestions`, `mockDavidParkActivity`, `mockDavidParkNotes`, `mockDavidParkScoreFactors`, plus `intentLabels` + `sentimentIcon` (display constants — keep).

**Wire path:** `activities` table + `cis_reply_classifications` (intent/sentiment) + `business_universe`/`leads` (sender). Each detail-component pulls one slice.

**Wiring complexity:** **High** — 11 components, 7 mock data shapes, multi-table joins. ~600-800 LOC across the cluster.

**Descope alternative:**
1. Fix the `?replyId` query-param drop in `/dashboard/inbox/page.tsx` redirect (1-line fix) — but `/dashboard/activity` doesn't currently know how to deep-link to a reply detail.
2. OR delete `/dashboard/inbox/[id]` entirely + 11 detail components + `lib/mock/inbox-data.ts`. ~1,600 LOC removed. NotificationsPanel must be updated to point at `/dashboard/activity` (no per-reply detail view exists).

---

## Recommendation matrix

| Surface | Wire LOC | Descope LOC saved | Pre-revenue value of wiring | Recommended path |
|---|---|---|---|---|
| `/dashboard/reports` | ~300 (8 components) + 3 blocked | -1,500 | Low (mostly zeros, voice + revenue blocked) | **Descope** — re-add when there's data |
| `/dashboard/settings` | ~250-300 (4 components, 2 require new schema migrations) + 1 blocked | -800 (reduce to 50-LOC card grid) | Low (sub-pages already work) | **Reduce to card grid** |
| `/dashboard/inbox/[id]` | ~700 (11 components, 7 shapes) | -1,600 | Low (parent redirect makes it orphaned) | **Descope** — fix NotificationsPanel link |

**Total wiring effort:** ~1,200 LOC across 22 components, blocked on 4 upstream gaps (voice path, Stripe, integrations table, notification table existence).

**Total descope:** ~3,900 LOC removed. Sidebar entries simplified. NotificationsPanel updated to drop `/dashboard/inbox/...` references.

**My recommendation: descope all three.** Reasons:
1. Pre-revenue, none of these surfaces add user value over their honest-empty equivalents.
2. Two of three are explicitly blocked on upstream gaps Dave is already prioritising (voice, Stripe).
3. /dashboard/inbox/[id] is functionally orphaned by the existing redirect.
4. Re-adding when there's real data to display is cheaper than maintaining mock-driven surfaces in the meantime.

**If Dave prefers to keep them visible:** pick the Reduce path for `/dashboard/settings` (already 80% working via sub-pages) and descope the other two.

---

## Blockers Dave's decision needs

- Does `/dashboard/reports` ship as a marketing-credibility surface (i.e. clients see it during sales cycle even if zeros) or as a post-revenue dashboard?
- Should `/dashboard/inbox/[id]` exist as a per-reply detail view, or is the activity feed (which has expandable cards per `<ActivityFeed/>`) the canonical reply-detail surface?
- ~~Are `client_integrations` and `notification_preferences` tables already in production schema? If not, settings wiring grows.~~ Resolved: both confirmed missing 2026-05-09 (Elliot verification). Settings wiring requires schema migrations before component wiring is possible — strengthens the descope recommendation.

The recommendation works regardless of remaining open questions — descoping is reversible.
