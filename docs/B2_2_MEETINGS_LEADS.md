# B2.2 visual parity — meetings rebrand + leads dedupe (2026-04-30)

R7 audit done first.

## Sub-task 1 — `/dashboard/meetings` rebrand to /demo

### Pre-existing state
Both `app/dashboard/meetings/page.tsx` and
`components/dashboard/MeetingsCalendar.tsx` were on the dark
Bloomberg theme (`bg-gray-950` / `bg-gray-900` / `border-gray-800` /
`text-gray-{300,400,500}` / `bg-amber-500/10` etc.). Headlines used
serif but not Playfair Display via the global `font-display` token.

### Action
Both files migrated to the cream/amber tokens introduced by A1, with
specific adoption of /demo's `.cal-grid` + `.cal-event` patterns
(prototype lines 380-410, 2031-2108):

**`MeetingsCalendar.tsx`**
- Day cards: `bg-panel border-rule rounded-[10px]` by default;
  `bg-amber-soft border-amber` for today's column
- Day head: large `font-display font-bold text-[18px]` day number
  (today's column renders the number in `text-copper` and adds an
  absolute-positioned `TODAY` mono pill in the top-right corner per
  prototype's `.cal-day-head.today::after`)
- Meeting cards: `bg-amber-soft` with 3px amber left border (default)
  or `bg-[rgba(107,142,90,0.14)]` with 3px green left border (past
  meetings — matches prototype's `.cal-event.green` rule)
- Time text: `font-mono text-[9.5px] text-copper` (default) /
  `text-green` (past)
- VR grade pill: colour-coded square (A/B green, C amber+on-amber,
  D copper, F red) — same component pattern as the kanban cards
- Hover lift: `hover:shadow-[0_2px_10px_rgba(212,149,106,0.25)]
  hover:-translate-y-px`
- Empty state for today: "No meetings today"; otherwise "No meetings"

**`app/dashboard/meetings/page.tsx`**
- Outer wrapper: removed the dark `bg-gray-950` block; now relies on
  AppShell's cream main + standard padding
- Headline: `font-display font-bold text-[28px] md:text-[36px]`
  Playfair "Your week, / N meetings." with amber italic emphasis on
  the count line (matches prototype's `.page-h em` rule)
- Surface toggle (drawer/briefing): cream `bg-surface` background,
  `bg-ink text-white` active pill — same pattern as the pipeline
  view toggle in PR #469
- Upcoming list: `bg-panel border-rule rounded-[10px]` with
  `divide-rule` rows, `hover:bg-amber-soft` row highlight, VR grade
  chip, Playfair-bold name + ink-3 company body
- Empty state: cream-dashed panel with copy "No meetings booked yet
  — Maya is working on N prospects" (mirrors prototype's
  `.today-empty` line 2087)
- Footer nav: `text-ink-3` mono `Home / Pipeline →` links, copper
  hover

**Briefing-page route** — out of scope. The current route opens a
drawer or `<MeetingBriefing>` component depending on `surface`
toggle; the prototype's `openBriefingPage(pid)` full-page-replace
flow would be a separate dispatch.

## Sub-task 2 — `/dashboard/leads` dedupe per ORION O4

### Pre-existing state
658-line bespoke "Animated Lead Scoreboard" — ALS leaderboard with
animated SplitFlap counters, intent-tier filter chips, lead row
component. Showed the same prospect data already available in
`/dashboard/pipeline?view=table`. Different layout, identical data
source.

### Action
Replaced with a 22-line redirect-only page that bounces to
`/dashboard/pipeline?view=table`. Single mental model for prospects
across the app. Original implementation preserved in git history.

### Referrer audit
10 components link to `/dashboard/leads` or `/dashboard/leads/{id}`:
- `app/dashboard/page.tsx` · `app/dashboard/replies/page.tsx`
- `components/plasmic/Sidebar.tsx` · `components/bloomberg/{QuickActions,Sidebar}.tsx`
- `components/leads/LeadScoreboardRow.tsx` · `components/dashboard/HotReplies.tsx`
- `components/onboarding/OnboardingChecklist.tsx`
- `components/dashboard/{GlobalSearch,meetings-widget}.tsx`

All hit the redirect — bounce to `/dashboard/pipeline?view=table`.
The `[id]` route already redirects to `/dashboard/pipeline?lead={id}`
per P3 cleanup (PR #467).

The post-B1 sidebar (PR #468) does **not** carry a "Leads" entry so
no nav update needed.

## Verification
```
pnpm run build → exit 0
```

## Files
- `frontend/app/dashboard/meetings/page.tsx` — cream/amber rebrand
- `frontend/components/dashboard/MeetingsCalendar.tsx` — cream/amber + today pill + past-meeting green variant + VR colour-coded chip
- `frontend/app/dashboard/leads/page.tsx` — 658 → 22 line redirect stub
- `docs/B2_2_MEETINGS_LEADS.md` — this file
