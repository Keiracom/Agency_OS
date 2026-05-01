# B2.4 — Activity Feed Consolidation + Dashboard Home Linear Rewrite

**Phase:** B2.4 (visual parity sweep)
**Branch:** `elliot/b2-4-feed-home`
**Date:** 2026-05-01

## Scope

Two intertwined consolidations:

1. **Activity consolidation.** `/dashboard/replies`, `/dashboard/inbox`, and
   `/dashboard/activity` were three overlapping surfaces showing the same
   underlying outreach events. Collapsed to one canonical
   `/dashboard/activity` matching /demo `renderFeed` (lines 1973-2017).
2. **Dashboard home rewrite.** `/dashboard/page.tsx` was a 455-line
   four-row stack (PR2 cycle/perf/replies/health · v10 home · ROW1 hero +
   donut · ROW2 stats · ROW3 hot/calling/working · ROW4 activity/week/warm).
   Replaced with /demo `renderHome` (lines 1643-1722) — one linear
   sequence: BDR hero → 4-card sum-row → today's meetings strip → Maya
   strip → cycle funnel → attention.

| Surface | Before | After |
|---------|--------|-------|
| `/dashboard` | 455 lines, 4-row stack, 19.7 kB bundle | 41 lines, linear sequence, 7.68 kB bundle |
| `/dashboard/activity` | 34 lines, dark `<ActivityFeedFull>` (no filter, no day groups) | 32-line route + new `<ActivityFeed>` component (day-grouped, channel-filter chips, expandable cards) |
| `/dashboard/replies` | 444 lines, full reply inbox UI | 12-line `redirect("/dashboard/activity")` |
| `/dashboard/inbox` | 32 lines, mock-driven 3-pane inbox | 13-line `redirect("/dashboard/activity")` |

## Activity Feed — `/dashboard/activity`

New `<ActivityFeed>` component
(`frontend/components/dashboard/ActivityFeed.tsx`, 388 lines) — port of
the prototype's `renderFeed`:

- **Channel filter chips:** All · Email · LinkedIn · Voice · SMS, each
  with live count, copper/amber-soft when active.
- **Day-grouped events:** mono uppercase day header
  (`WEDNESDAY 23 APRIL`) per local date.
- **Expandable cards:** click any row → expands to "What Maya is doing
  next" (replies) or "Touch detail" (sends), with an *Open briefing* CTA
  that fires the `<ProspectDrawer>`.
- **Live indicator:** `LIVE` / `POLLING` / `CONNECTING` badge in the chip
  row.
- **Data source:** `cis_outreach_outcomes` joined with
  `business_universe`, same query shape as the prior
  `<ActivityFeedFull>` (which is now unused — separate cleanup).

The route page wraps it in the standard cream/amber Playfair headline
("Activity feed, *everything Maya is doing.*") and `<AppShell pageTitle="Activity">`.

## Dashboard Home — `/dashboard/page.tsx`

41-line single linear sequence:

```tsx
<HeroStrip />          // BDR hero card + 4-card sum-row
<TodayStrip />         // Today's meetings horizontal scroll + scheduled-touches tally
<MayaStrip />          // Collapsible "Maya is working in the background"
<SectionLabel>Cycle funnel</SectionLabel>
<FunnelBar />
<SectionLabel>Needs your attention</SectionLabel>
<AttentionCards onLeadClick={drawer} />
<ProspectDrawer />
```

The four feeder components were rebranded from the prior
`bg-gray-900/800/700` Bloomberg-dark palette to cream tokens:

- `HeroStrip.tsx` — `bg-panel border-rule text-ink`, Playfair on the
  hero copy, amber italic `<em>` on the reply/meeting counts. Sum cards
  carry the /demo `text-amber em` unit suffix pattern (e.g., `8/10`,
  `3.2%`).
- `TodayStrip.tsx` — meeting cards on `bg-panel`, amber hover border,
  `text-amber` time stamps. Touch-tally row uses `text-ink-2`.
- `AttentionCards.tsx` — emerald/red/amber-soft variants on cream
  background; copper CTA mono.
- `MayaStrip.tsx` — **new component**, port of `.maya-strip`
  (lines 1688-1701). Click to expand collapsed strip → 3-row breakdown
  (drafts in flight · critic loop · enrichment). Uses `useDashboardStats`
  for cycle day; counts read zero placeholder until backend exposes
  Maya queue telemetry.

## Files changed

| File | Lines (before → after) | Change |
|------|------------------------|--------|
| `frontend/app/dashboard/page.tsx`            | 455 → 41   | linear-sequence rewrite |
| `frontend/app/dashboard/activity/page.tsx`   | 34 → 32    | rebrand + use new feed |
| `frontend/app/dashboard/replies/page.tsx`    | 444 → 12   | redirect stub |
| `frontend/app/dashboard/inbox/page.tsx`      | 32 → 13    | redirect stub |
| `frontend/components/dashboard/HeroStrip.tsx`     | 127 → 145  | cream rebrand |
| `frontend/components/dashboard/TodayStrip.tsx`    | 236 → 240  | cream rebrand |
| `frontend/components/dashboard/AttentionCards.tsx`| 112 → 112  | cream rebrand |
| `frontend/components/dashboard/MayaStrip.tsx`     | new — 110  | new component |
| `frontend/components/dashboard/ActivityFeed.tsx`  | new — 388  | new feed component |
| `docs/B2_4_FEED_HOME.md`                        | new        | this audit |

## Verification

- `pnpm run build` — green
  - `/dashboard` 7.68 kB (was 19.7 kB → **−61%**)
  - `/dashboard/activity` 4.44 kB (essentially flat — same data shape)
  - `/dashboard/replies` 164 B (was 13.6 kB → redirect stub)
  - `/dashboard/inbox` 164 B (was 6.58 kB → redirect stub)
- No new dependencies. No API changes. No backend writes.

## Out of scope (intentional)

- Wiring `<MayaStrip>` to a real Maya-queue endpoint — counts render zero
  until backend exposes telemetry.
- Deleting the now-unused `<ActivityFeedFull>` component and the old
  `components/inbox/*` mock components — leaving them parked for a
  follow-up cleanup PR.
- Removing legacy sidebar references in `components/plasmic/Sidebar.tsx`
  + `components/bloomberg/Sidebar.tsx` (those are deprecated rail
  variants superseded by `components/layout/sidebar.tsx` per B1; the
  `/dashboard/replies` redirect handles their links).
- Replacing the `<HotReplies>` and `<GlobalSearch>` deep-links to
  `/dashboard/replies` — they'll redirect cleanly to the new feed.
- Tightening `/api/dashboard/bloomberg` and `/api/activity` static
  warnings (pre-existing, unrelated to B2.4).
