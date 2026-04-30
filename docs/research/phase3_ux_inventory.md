# Phase 3 UX Inventory — /demo-Aligned Dashboard Migration

Read-only research. Per-item inventory of the 8 Phase 3 UX items: what already exists in the React app vs what is net-new vs what needs design alignment with the canonical `/demo` source.

**Reference paths**

- `/demo` source: `/home/elliotbot/clawd/Agency_OS/frontend/landing/demo/index.html` (2,344 lines)
- React components: `/home/elliotbot/clawd/Agency_OS/frontend/components/dashboard/*` (70 files)
- React routes: `/home/elliotbot/clawd/Agency_OS/frontend/app/dashboard/*`

**Branch**: `aiden/phase3-ux-inventory` (off `origin/main`). No code edits — doc-only.

## Table of contents

1. [Pause-all kill button consolidation](#item-1--pause-all-kill-button-consolidation)
2. [Maya 'DAY N/30' cycle indicator in topbar](#item-2--maya-day-n30-cycle-indicator-in-topbar)
3. [Proportional cycle funnel bar](#item-3--proportional-cycle-funnel-bar)
4. [Section labels — uppercase mono utility](#item-4--section-labels-uppercase-mono-utility)
5. [Critic scores per channel on prospect cards + drawer](#item-5--critic-scores-per-channel-on-prospect-cards--drawer)
6. [ROI grid on Progress page](#item-6--roi-grid-on-progress-page)
7. [Drawer 7-section depth + content fill](#item-7--drawer-7-section-depth--content-fill)
8. [BDR hero personalisation](#item-8--bdr-hero-personalisation)

[Closing summary](#closing-summary) · [Recommended dispatch order](#recommended-dispatch-order)

---

## Item 1 — Pause-all kill button consolidation

**Current React state:**
- `frontend/components/dashboard/KillSwitch.tsx:1-174` — global pause/resume toggle. Already fixed-position (line 93: `fixed top-3 right-3 z-40`). Confirmation modal + banner-when-active (line 116). The strongest candidate to keep.
- `frontend/components/dashboard/EmergencyPauseButton.tsx:1-191` — alternate emergency pause UI. Overlapping responsibility with KillSwitch.
- `frontend/components/dashboard/PauseCycleButton.tsx:1-301` — customer-facing pause-cycle button with modal confirmation. Similar pattern to KillSwitch but cycle-scoped not global.

**/demo reference:** `frontend/landing/demo/index.html:89-90` (`.kill-btn` style), `:782, :792` (topbar usage `<button class="kill-btn">⏸ Pause all</button>`). Single button, always-visible inside the dark topbar bar (`#topbar`), JetBrainsMono 10px uppercase, hover turns red.

**Diff specification:**
- Pick one canonical pause-all component (recommend keeping `KillSwitch.tsx` as the seed since it already has the modal + state + banner). Remove `EmergencyPauseButton.tsx` outright (delete or mark deprecated — orchestrator currently uses both).
- Move from `fixed top-3 right-3` overlay to inline-in-topbar slot in `DashboardNav.tsx` (currently sidebar-only — does not yet render a topbar). Topbar may need to be added; see Item 2.
- Apply demo styling: `border: 1px solid rgba(255,255,255,0.2)`, `font-family: 'JetBrains Mono'`, `text-transform: uppercase`, hover → `bg: var(--red)`.
- Keep `PauseCycleButton.tsx` only if cycle-scoped (vs global) pause is a deliberate distinct affordance — needs CEO clarification.

**Complexity:** **M** (30 min – 2 hr). Topbar slot integration is the biggest unknown; depends on topbar existing in Phase 1+2 work.

**Dependencies:** Phase 1+2 must produce a topbar-region container in the dashboard layout. If still sidebar-only, KillSwitch can keep its current `fixed` position.

**Test plan:**
- Visual: topbar shows the kill button with demo-correct typography and hover behavior.
- Functional: clicking opens confirmation; confirming POSTs to webhook; banner appears; resume toggles back.
- Regression: confirm orchestrator pause state still drives the global `kill_switch` flag; old `EmergencyPauseButton` import removed cleanly (no broken imports).

---

## Item 2 — Maya 'DAY N/30' cycle indicator in topbar

**Current React state:**
- `frontend/components/dashboard/CycleProgress.tsx:1-125` — exists as a **CARD** (block-level component with progress bar). Per its docstring (line 6): `"MAYA · DAY 14/30 cycle indicator combined into one card"`. Line 13: `CYCLE_LENGTH_DAYS = 30`.
- TODO at line 27: `replace with metrics.cycle_day once backend exposes it`. Currently uses calendar day-of-month modulo 30 as a stand-in. Hook is `useDashboardV4`.

**/demo reference:** `frontend/landing/demo/index.html:82` (`.tb-cycle` class — JetBrainsMono 11px, dot prefix), `:782` (topbar usage `<span class="tb-cycle"><span class="tb-dot"></span>MAYA · DAY 14/30</span>`). Inline element rendered inside `#topbar`, NOT a card.

**Diff specification:**
- Refactor `CycleProgress.tsx` to expose two render modes: `card` (existing, used on home dashboard) and `inline` (new, for topbar). Or extract a new sibling `CycleIndicator.tsx` for the inline form so the card stays intact.
- Inline form: `<span class="font-mono text-[11px] text-white/60 flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>{persona} · DAY {N}/30</span>`
- Wire to a real `cycle_day` source — `lib/hooks/useDashboardStats.ts` or extend `useDashboardV4`. The TODO(api) blocker still applies.

**Complexity:** **S** (under 30 min) for the inline component itself. **M** if the topbar slot requires layout work (see Item 1).

**Dependencies:**
- Topbar layout (shared with Item 1).
- Real `cycle_day` field on `meetings_metrics_v4` (Phase 1+2 backend if not yet shipped).

**Test plan:**
- Visual: dot + uppercase mono text matching demo dimensions (11px, 0.06em letter-spacing) inside topbar.
- Data: indicator advances 1 each calendar day; rolls back to DAY 1/30 on cycle close. Add a unit test for the day-arithmetic if not present.

---

## Item 3 — Proportional cycle funnel bar

**Current React state:**
- `frontend/components/dashboard/FunnelBar.tsx:1-86`. 5 segments per `useFunnelData` hook (`discovered → contacted → replied → meeting → won`). **Each segment uses `flex-1` (equal width)** — line 58 `<div className="flex-1 ..." />` on the empty state and the data-state mirror.
- Hook contract is shaped for this — exposes `stages[].count` + `total` so proportional rendering is straightforward.

**/demo reference:** `frontend/landing/demo/index.html:208-218` (`.funnel-bar` + `.funnel-seg` CSS), `:1703-1710` (usage block — `Cycle funnel` section label, then `.funnel-bar` rendered with `flex:N` proportional widths derived from `cohort.totalDiscovered / cohort.totalContacted / etc`). Each segment shows `<div class="fs-n">{N}</div>` (count) + `<div class="fs-l">{LABEL}</div>` (caption).

**Diff specification:**
- Replace `flex-1` with explicit `flex: {count}` per segment so width is proportional to stage count.
- Edge case: handle `count === 0` — demo treats it as a min-width segment (still shows label). Recommend `flex: ${Math.max(count, 1)}` to avoid disappearing segments.
- Match label sizing: caption is `9px` tracking `0.1em` (currently demo line 212); React already approximates this (line 47: `text-[9px] tracking-[0.1em]`).
- Color tokens: stage palette per demo doesn't change — gray → amber → emerald progression matches what FunnelBar already uses.

**Complexity:** **S** (under 30 min). One-line change to the `flex` style + zero-count guard.

**Dependencies:** None — `useFunnelData` already returns counts.

**Test plan:**
- Visual: at `discovered=247, contacted=89, replied=31, meeting=8, won=3`, segments should narrow rightward. Verify against demo screenshot at `:1703`.
- Edge: `won=0` segment still visible with label (uses `Math.max(count, 1)` for flex weight).
- Hook regression: `useFunnelData` still drives the data — no change to fetch contract.

---

## Item 4 — Section labels — uppercase mono utility

**Current React state:**
- No shared utility class for section labels. Each component re-implements its own `font-mono text-[10px] tracking-widest uppercase text-gray-500` block (e.g. `HeroStrip.tsx:54`, `ProspectDrawer.tsx:166-170` Section helper).
- `ProspectDrawer.tsx:165-173` defines an inline `Section` helper component that already approximates the demo style.

**/demo reference:** `frontend/landing/demo/index.html:128` — `.section-label { font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-3); font-weight: 600; margin: 24px 0 12px; }`. Used at `:1703` (`Cycle funnel`), `:1713` (`Needs your attention`), `:2085` (`Upcoming this week`).

**Diff specification:**
- Add a Tailwind `@apply` utility in `frontend/styles/globals.css` (or wherever the cookbook lives): `.section-label { @apply font-mono text-[10px] tracking-[0.14em] uppercase text-gray-500 font-semibold mt-6 mb-3; }`.
- Or, if the codebase prefers component-level: extract `Section` helper from `ProspectDrawer.tsx:165-173` to a shared `components/dashboard/_atoms/SectionLabel.tsx` with the demo-matching styles.
- Migrate inline label call-sites to the utility (search for `font-mono text-[10px]` patterns).

**Complexity:** **S** (under 30 min) for the utility itself. **M** (30 min – 2 hr) if migrating all existing call-sites is included.

**Dependencies:** None.

**Test plan:**
- Visual: section labels match demo across home, progress, drawer surfaces.
- Snapshot test or Playwright: capture one page, verify label dimensions vs demo CSS.

---

## Item 5 — Critic scores per channel on prospect cards + drawer

**Current React state:**
- `frontend/components/dashboard/ProspectDetailCard.tsx:1-319` — renders prospect briefing card (vulnerability text, A-F grade). **No critic-score block** — `grep critic` returns 0 hits.
- `frontend/components/dashboard/ProspectDrawer.tsx:1-256` — renders Contact, Enrichment, Outreach timeline, Quick actions sections. **No critic-score block.**

**/demo reference:** `frontend/landing/demo/index.html:893-1061` — every prospect record carries `critic:{ email:N, linkedin:N, voice:N, sms:N }` numeric scores (0-100). Sample: `:893` `critic:{ email:82, linkedin:71, voice:88, sms:64 }`.

The /demo does NOT render an explicit critic-grid block in the visible drawer template (lines 1307-1361) — the data is in the dataset but the card UI does not surface it. Phase 3 spec is to ADD a per-channel critic visualization.

**Diff specification:**
- Extend the prospect type (likely `lib/types/prospect.ts` or wherever) to include `critic: { email: number; linkedin: number; voice: number; sms: number }`.
- Render a 4-cell grid in both `ProspectDetailCard` and `ProspectDrawer` showing each channel's score with a colour gradient (>80 green, 60-80 amber, <60 red — match demo `var(--green) / var(--amber) / var(--red)` tokens).
- Net-new SQL/API piece if backend doesn't yet expose critic scores per prospect — Phase 1+2 backend dependency.
- Drawer placement: insert a `Section title="Message critic scores"` block between the Outreach timeline and Quick actions sections.

**Complexity:** **M** (30 min – 2 hr) for UI + type extension. **L** (2hr+) if backend wiring is also in scope.

**Dependencies:** Backend exposes critic-score data per prospect (likely `lib/hooks/useProspectDetail.ts` field). If absent, this item depends on a separate backend dispatch.

**Test plan:**
- Visual: 4-cell grid matches demo colour tokens at score thresholds.
- Functional: card + drawer both render the same scores; colour changes with score crossings.
- Empty state: prospect with no critic data renders "—" rather than 0.

---

## Item 6 — ROI grid on Progress page

**Current React state:**
- `frontend/app/dashboard/reports/page.tsx:1-30` — Reports page imports `ROISummary` from `@/components/reports`. Existing component but layout differs from spec.
- `frontend/components/dashboard/ReportsView.tsx:79-82, :467-470` — `roiSummary` data shape: `{ totalSpend, meetings, roi: 8.2 }`. Single ROI number, not a 4-cell grid.
- No `Progress` page exists at `/dashboard/progress` — closest is `reports`. Spec may mean the existing Reports page or a new dedicated route.

**/demo reference:** `frontend/landing/demo/index.html:428-432` (`.roi-grid` + `.roi-cell` CSS), `:2242-2246` (markup):
- Cell 1: `$312` Cost/Meeting (`$2,500 ÷ 8 meetings`)
- Cell 2: `$81` Cost/Reply (`$2,500 ÷ 31 replies`)
- Cell 3: `$10` Cost/Contact (`$2,500 ÷ 247 contacts`)
- Cell 4: `3.0×` Pipeline ROI (`3 closed × $2,500 deal ÷ subscription`)

Layout: `grid-template-columns: repeat(2, 1fr)` (2×2 grid). Each cell: Playfair Display 26px copper value + JetBrainsMono 10px uppercase label + smaller mono breakdown.

**Diff specification:**
- New component `components/dashboard/ROIGrid.tsx` rendering 4 cells with the demo data shape: `{ value, label, breakdown }`.
- Wire to a hook (likely extension of `useDashboardStats` or new `useROIMetrics`) that computes the four ratios from existing aggregates.
- Place it on `/dashboard/reports/page.tsx` (existing Progress/Reports surface) — replace or supplement the existing `ROISummary` component.

**Complexity:** **M** (30 min – 2 hr). 4-cell grid + ratio compute hook. Backend likely already has the source values (spend, meetings, replies, contacts).

**Dependencies:** Backend `monthly_spend` value — check `useDashboardStats.ts` or `meetings_metrics_v4`. If missing, depends on a backend exposure dispatch.

**Test plan:**
- Visual: 2×2 grid with copper values matching demo. Verify on resize behaves as `grid-template-columns: repeat(2, 1fr)`.
- Calculation: `cost_per_meeting = total_spend / meetings_count`, etc. Snapshot one realistic data point.
- Empty state: when `meetings = 0`, show `—` instead of `Infinity` or `NaN`.

---

## Item 7 — Drawer 7-section depth + content fill

**Current React state:**
- `frontend/components/dashboard/ProspectDrawer.tsx:1-256` — has **4 sections**: Contact (`:114`), Enrichment (`:122`), Outreach timeline (`:131`), Quick actions (`:135`). Plus a header VR-grade chip via `VRGradePopover` at `:90`.
- Section helper at `:165-173` already matches demo `.section-label` style.

**/demo reference:** `frontend/landing/demo/index.html:1307-1361` — drawer body template renders **8 sections** (the dispatch says 7 — close enough; one of these is the AI-angle subsection inside Recommended angle):
1. **Business meta** (`:1308-1318`) — 8 KV pairs: Domain, GMB category, Employees, Established, DFS organic ETV, Domain rank, Backlinks, Status.
2. **Vulnerability — overall grade** (`:1320-1325`) — VR text + 6 graded categories (website, seo, reviews, ads, social, content) with click-popovers (`showVRPopover` at `:563+`).
3. **Outreach timeline** (`:1328-1330`) — `unifiedTimeline()` events.
4. **Recommended angle** (`:1333-1336`) — AI-generated header + opening hook.
5. **Discovery questions** (`:1339-1340`) — `<ul>` of questions.
6. **Common objections** (`:1343-1344`) — Q+response pairs.
7. **Close options + pricing** (`:1347-1352`) — `<ul>` of closes + serif pricing range.
8. **Competitors** (`:1356-1357`) — `<ul>` of competitor domains.

VR popover styling at `:563-580` — sticky overlay with grade + explanation + 4 colour tokens (A/B green, C amber, D copper, F red).

**Diff specification:**
- Add 4 missing sections to `ProspectDrawer.tsx`: Business meta (KV grid), Vulnerability (text + 6-grade strip with popovers), Recommended angle (AI banner + hook), Discovery questions, Common objections, Close+pricing, Competitors. (4 new — Contact + Enrichment + Timeline + Quick actions = 4 existing, total 8.)
- VR popover: extract pattern from `frontend/landing/demo/index.html:563-580` and `:1325` (`onclick="showVRPopover(...)"`). Use existing `VRGradePopover` if it covers this; else build a per-grade-letter popover.
- Type extension: `Prospect.briefing = { businessMeta, vrGrades, openingHook, discoveryQuestions, objections, closeOptions, pricingRange, competitors }`. Likely backend dispatch.
- Section label utility (Item 4) consumed by every new section.

**Complexity:** **L** (2hr+). Largest single item. 4 new sections × ~15-30 min each + popover wiring + type/hook extension + tests.

**Dependencies:**
- Item 4 (section-label utility, ideally landed first).
- Backend exposes briefing fields per prospect — either extend `useProspectDetail` or new hook.
- If briefing data is hand-curated (not yet in DB), this depends on a content-pipeline dispatch.

**Test plan:**
- Visual: drawer matches demo screenshot section-by-section.
- Functional: VR grade popover opens on click, closes on outside click / escape, shows grade + explanation.
- Empty state: each section has graceful "—" or section-hidden behavior when data is missing.
- Accessibility: drawer + popover keyboard-navigable; aria-labels match.

---

## Item 8 — BDR hero personalisation

**Current React state:**
- `frontend/components/dashboard/HeroStrip.tsx:42-86` — **already implemented matching the demo.** Line 46: `headline = ${personaName} found %%REPLIES%% replies and booked %%MEETINGS%% meetings this week.`. Lines 76-86 render with persona avatar + serif headline + amber-emphasized counts.
- Data hook `lib/hooks/useDashboardStats.ts:24-25, :83-118` provides `repliesThisWeek` and `meetingsThisWeek` from real backend tables.

**/demo reference:** `frontend/landing/demo/index.html:164-165` (`.bdr-hero .h-line` CSS — Playfair Display 22px), `:1674` (markup `<div class="h-line">Maya found <em>31 replies</em> and booked <em>8 meetings</em> this week.</div>`).

**Diff specification:**
- **None substantive.** React HeroStrip is already at parity with demo — same headline pattern, same dynamic counts, same amber emphasis on the numerics, same persona name parameterization.
- Optional polish: confirm font-family is `Playfair Display` (the React component uses `font-serif`, which should resolve to Playfair if the font stack is configured). Spot-check fonts in production.

**Complexity:** **S** (under 30 min) — verification + optional font check.

**Dependencies:** None.

**Test plan:**
- Visual: side-by-side HeroStrip vs demo `:1674` — should be visually identical.
- Data: `repliesThisWeek` + `meetingsThisWeek` populated from `useDashboardStats`; confirm via fixture/snapshot.
- Persona: `personaName="Maya"` default works; passing `personaName="Aria"` swaps headline correctly.

---

## Closing summary

### Complexity tally

| Complexity | Count | Items |
|---|---:|---|
| **S** (under 30 min) | 4 | Item 2 (inline-only), Item 3, Item 4 (utility-only), Item 8 |
| **M** (30 min – 2 hr) | 3 | Item 1, Item 5, Item 6 |
| **L** (2 hr +) | 1 | Item 7 |

Where two ranges apply (e.g. Item 4 utility-only S vs full migration M), the smaller is counted; expansion noted in the per-item entry.

### Total estimate range

- **Optimistic** (all S land first try, M+L don't slip): 4×0.4hr + 3×1.0hr + 1×3.0hr = **~6.6 hours**.
- **Realistic** (some scope creep, backend wiring, polish): 4×0.5hr + 3×1.5hr + 1×4.0hr = **~10.5 hours**.
- **Pessimistic** (Item 7 grows, Items 5 + 6 hit backend-data gaps): **~14 hours**.

Total Phase 3 build estimate: **6–14 hours of ORION/build-bot effort**, biased toward the lower-middle of that range if Phase 1+2 prerequisites (topbar layout, critic-score backend, briefing-fields backend, cycle_day API) are landed before Phase 3 starts.

### Recommended dispatch order

Order optimised for: (1) prerequisite chains, (2) early visible polish wins, (3) backend dependencies last.

1. **Item 4** — section-label utility (S, no dependencies). Lands first; consumed by every other item that has a "uppercase mono caption" affordance.
2. **Item 3** — proportional FunnelBar (S, no deps). Visible polish win on home dashboard, two-line code change.
3. **Item 2** — DAY N/30 topbar inline (S; depends on topbar slot from Phase 1+2). Pair this with Item 1 in the same dispatch to avoid two topbar-touching commits.
4. **Item 1** — Pause-all kill consolidation (M; same topbar dependency). Removes EmergencyPauseButton + PauseCycleButton overlap. Ship with Item 2.
5. **Item 8** — BDR hero personalisation verification (S, already at parity). Smoke test + optional font check; mostly a sign-off task.
6. **Item 6** — ROI grid (M; needs `monthly_spend` aggregate). Add new component + hook, place on Reports page.
7. **Item 5** — Critic scores per channel (M; needs `prospect.critic` backend field). Defer until backend confirms exposure.
8. **Item 7** — Drawer 7-section depth (L; needs briefing fields backend). Most complex; lands last so backend has time to fill `discoveryQuestions / openingHook / objections / closeOptions / competitors / vrGrades` fields.

### Cross-cutting dependencies

- **Topbar layout** (Items 1 + 2) — Phase 1+2 needs to introduce a `<header>` slot in `app/dashboard/layout.tsx` if not already present. Currently the dashboard uses sidebar nav (`DashboardNav.tsx`) only.
- **Critic-score backend** (Item 5) — `prospect.critic` JSON object on the prospect detail API.
- **Briefing-content backend** (Item 7) — DB columns or generated content for: `business_meta` (8 fields), `vr_grades` (6 graded categories + explanations), `opening_hook`, `discovery_questions[]`, `objections[]`, `close_options[]`, `pricing_range`, `competitors[]`.
- **Cycle-day API** (Item 2) — `meetings_metrics_v4.cycle_day` field. Currently mocked via calendar-date modulo per `CycleProgress.tsx` TODO at `:27`.

### Out of scope for this audit

- Backend SQL / API design for the 4 missing data sources above.
- Performance benchmarking of new components.
- A/B test plan for hero copy variants.
- Dark-mode / light-mode parity verification.

---

*This document is research-only. No code edits made. Generated 2026-04-30 on `aiden/phase3-ux-inventory` branch.*
