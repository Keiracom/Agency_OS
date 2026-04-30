# Phase 4 Visual Parity Audit

Read-only research. Per-route gap report comparing the React app against `/demo` (`frontend/landing/demo/index.html`, 2,344 lines). Goal: ATLAS B2 visual-parity sweep gets a route-level spec to work from after ATLAS B1's sidebar consolidation lands.

**Reference paths**

- `/demo` source: `/home/elliotbot/clawd/Agency_OS/frontend/landing/demo/index.html`
- React routes: `/home/elliotbot/clawd/Agency_OS/frontend/app/**`
- React components: `/home/elliotbot/clawd/Agency_OS/frontend/components/**`

**Branch**: `aiden/phase4-visual-parity-audit` (off `origin/main`). No code edits — doc-only.

## Design token reference (canonical /demo)

Pulled from `/demo/index.html:20-50`:

| Token | Value | Usage |
|---|---|---|
| `--cream` | (light bg, dark cream) | Page background |
| `--ink` | `#0C0A08` | Primary text |
| `--ink-2` | `#2E2B26` | Secondary text |
| `--ink-3` | `#7A756D` | Tertiary / labels |
| `--amber` | `#D4956A` | Brand accent (italic spans, CTA) |
| `--copper` | `#C46A3E` | ROI emphasis |
| `--green` | `#6B8E5A` | A/B grades, success |
| `--red` | `#B55A4C` | F grade, error |
| `--rule` | `rgba(12,10,8,0.08)` | Borders |
| Topbar height | `52px` | `--topbar-h` |
| Sidebar width | `232px` | `--sidebar-w` |
| Bottomnav | `60px` | mobile only |

Typography:
- Playfair Display (serif) — `.page-h` 30px (24px mobile), `.h-line` 22px
- DM Sans (body) — 14px default
- JetBrains Mono — `.section-label` 10px / 0.14em / uppercase / weight 600

Common patterns:
- `.page-h` (Playfair 30px, italic `<em>` carries amber colour)
- `.page-sub` (13px DM Sans, max-width 820px, mb 22px)
- `.section-label` (mono uppercase, mt 24px / mb 12px)
- `.bf-section h4` (drawer section heading, mono uppercase)

## Table of contents

1. [/dashboard](#route--dashboard)
2. [/dashboard/pipeline](#route--dashboardpipeline)
3. [/dashboard/leads](#route--dashboardleads)
4. [/dashboard/replies and /dashboard/inbox](#route--dashboardreplies--dashboardinbox)
5. [/dashboard/meetings](#route--dashboardmeetings)
6. [/dashboard/reports](#route--dashboardreports)
7. [/dashboard/settings](#route--dashboardsettings)
8. [/onboarding/*](#route--onboarding)
9. [/welcome](#route--welcome)
10. [/(auth)/login + signup](#route--authlogin--signup)

[Closing summary](#closing-summary)

---

## Route — /dashboard

**/demo target:** `renderHome()` at `index.html:1643-1730`. Layout sequence:

1. `.bdr-hero` — avatar + eyebrow + Playfair `h-line` (`Maya found N replies and booked M meetings this week.`).
2. `.sum-row` — 4-column grid of `.sum-card` (Prospects Contacted / Replies / Meetings / Win Rate). Each card: Playfair 26px value + JBMono 10px label + delta line.
3. `.today-strip-head` — JBMono eyebrow row (`Your meetings today` + meta `N meetings · cycle day 14/30`).
4. `.today-strip` — meeting cards OR `.today-empty` placeholder.
5. `.maya-strip` — collapsible "Maya is working in the background" detail strip.
6. `.section-label` "Cycle funnel" + `.funnel-bar` proportional 5-segment + `.funnel-meta` ratio line.
7. `.section-label` "Needs your attention" + `.attention-card` list.

Spacing rhythm: ~24px between sections (`.section-label margin: 24px 0 12px`). Outer page padding via `.main` container.

**Current React state:** `frontend/app/dashboard/page.tsx:1-455`.

- Uses `<AppShell>` wrapper (line ~95) with explicit ambient radial gradient backgrounds at lines 100-110.
- **Two stacked layouts**:
  1. **PR2 Bloomberg block** (line 113-122): `<CycleProgress />` + `<PerformanceMetrics />` + `<HotReplies />` + `<SystemHealth />` in a 2-col grid. Largely duplicates the `/demo` Maya / cycle / hero affordances.
  2. **v10 /demo-aligned block** (line 125-141): `<HeroStrip />` + `<TodayStrip />` + `<FunnelBar />` + `<AttentionCards />` with `<SectionLabel>` headings.
- **Then** a third block (line 143+): "Hero Section - 2 column grid" with Bloomberg `<HeroMetricCard>` cards. ANOTHER duplicate of meeting-stats hero.

**Visual gap:**

- **Layout structure**: React stacks **3 layout systems on top of each other** (Bloomberg cycle/perf/health, then v10 hero/today/funnel/attention, then a Bloomberg HeroMetricCard grid). `/demo` is a single linear sequence: hero → sum-row → today → maya → funnel → attention. Massive dedupe required.
- **Spacing rhythm**: React uses `mb-6 / mb-8` Tailwind defaults (24px / 32px); `/demo` uses `margin: 24px 0 12px` on `.section-label` directly. Should align.
- **Typography**: HeroStrip already uses font-serif (Playfair); BUT the duplicated Bloomberg `<HeroMetricCard>` cards use Inter or similar — break the typeface contract.
- **Component density**: Bloomberg cards (rounded-xl p-6 / p-8) are heavier than `/demo`'s `.sum-card` (padding 14-18px, rounded-10px). Trim padding.
- **Colour**: `/demo` cream-vs-warm-charcoal binary; React mixes amber-tinted radial gradients (line 100-110) that aren't in `/demo`. Drop the gradients.
- **Mobile**: `/demo` collapses sum-row to 2-col (CSS at line ~720 region, not shown). React already does `grid-cols-2 md:grid-cols-4` per HeroStrip line 88 — close to parity.

**Specific changes ATLAS B2 should make:**

1. `frontend/app/dashboard/page.tsx:113-122` — **DELETE** the PR2 Bloomberg block (CycleProgress + PerformanceMetrics + SystemHealth + HotReplies). The /demo home doesn't have those.
2. `frontend/app/dashboard/page.tsx:143+` — **DELETE** the `<HeroMetricCard>` "Hero Section - 2 column grid" (lines 143 onward). Sum-row inside HeroStrip is the canonical 4-card row.
3. `frontend/app/dashboard/page.tsx:100-110` — drop the radial-gradient inline style; replace with `bg-cream` (already a Tailwind token via globals.css).
4. `frontend/components/dashboard/HeroStrip.tsx:55` — Hero card uses `bg-gray-900 border border-gray-800`; should be `.bdr-hero` style: cream bg + 1px ink border, NOT dark gray.
5. Add `.maya-strip` collapsible — currently absent. Net-new component or inline block in `app/dashboard/page.tsx`.
6. `frontend/app/dashboard/page.tsx` — wrap the sum-row + today + funnel + attention sequence in a single `<section>` with `space-y-6` matching `/demo`'s 24px rhythm (already present in v10 block at line 126).

**Complexity:** **L** (2 hr +). Two stacked layout systems to demolish + Maya strip net-new + HeroStrip palette inversion (dark → cream). Highest-effort route.

---

## Route — /dashboard/pipeline

**/demo target:** `renderPipeline()` at `index.html:1757-1900` (approx).

- `.page-h` "Pipeline, N prospects active." with italic `<em>` count.
- `.page-sub` "Click any card or row to open the briefing drawer..."
- `.filter-chips` row with All / Hot / Replied / Meeting filter chips (each with `.chip-count` badge).
- View toggle: `board` vs `table`.
- `.board` Kanban with 5 cols (Discovered / Outreach / Reply / Meeting / Won-Lost), each col has `.col-head` (label + count + percent) and `.col-body`. Won-Lost col has split (won + lost).

**Current React state:** `frontend/app/dashboard/pipeline/page.tsx:1-212`.

- Uses `<AppShell>` wrapper.
- 3 view modes: `list` / `kanban` / `table`.
- `<PipelineStateTabs>` (Review / Outreach / Complete) — `/demo` doesn't have these state tabs; closest is the funnel filter chips.
- `<PipelineFilters>` chips (All / Top 10 / Top 50 / Struggling / Trying / Dabbling) — different filter taxonomy from `/demo` (intent-based vs status-based).
- `<PipelineKanban>` and `<PipelineTable>` separate components.
- Drawer integration via `setActiveLead`.

**Visual gap:**

- **Layout structure**: React has the page-h header but adds the State tabs (Review / Outreach / Complete) that `/demo` lacks. State tabs may be intentional Phase 1+2 work; flag for product decision.
- **Filter taxonomy**: React uses intent buckets (struggling/trying/dabbling); `/demo` uses status (hot/replied/meeting). **Decision needed**: which is canonical? Recommend keeping React's intent-based since it's more pitch-relevant. But align the visual chip pattern (count badge inside chip) to `/demo`.
- **Spacing**: Three view-toggle buttons inline in header — `/demo` puts these in the same area (board/table toggle). Probably already close.
- **Typography**: page-h likely uses Tailwind text-2xl rather than Playfair 30px italic-em pattern.
- **Card density**: `<PipelineKanban>` columns vs `/demo`'s `.col-body` padding probably differ.

**Specific changes ATLAS B2 should make:**

1. `frontend/app/dashboard/pipeline/page.tsx` (header section) — render `.page-h` Playfair 30px with italic-em prospect count: `<h1 className="font-display text-[30px] ...">Pipeline,<br/><em className="text-amber italic">{prospects.length} prospects active.</em></h1>`.
2. `frontend/components/dashboard/PipelineFilters.tsx` — chip pattern: 1px ink border, mono uppercase label, count in `.chip-count` (mono, smaller, ink-3) inside each chip. Match `/demo` line ~190 region.
3. **Decision flag**: keep `<PipelineStateTabs>` Review/Outreach/Complete OR drop in favour of `/demo`'s simpler funnel filter? Suggest keep, but visually align tab styling.
4. `<PipelineKanban>` column header: `.col-head` is `<div>` with span name + span count + percent — match this layout.
5. Won-Lost column: implement the split (won-section + lost-section) per `/demo:1773-1786`.

**Complexity:** **M** (30 min – 2 hr). Pipeline already mostly aligned; mostly typography + chip patterns + the won-lost column split.

---

## Route — /dashboard/leads

**/demo target:** No direct `/demo` equivalent — `/demo` has Pipeline (kanban + table) but no separate "Leads" route. The `/dashboard/leads` route in React appears to be a list-with-filtering surface that overlaps with Pipeline's table view.

**Current React state:** `frontend/app/dashboard/leads/page.tsx:1-658` (large standalone page). Notes from `app/dashboard/replies/page.tsx:415` show `Link href="/dashboard/leads/${id}"` to a per-lead full-page route — that route is in the cleanup-map deletion list (Item 24, drawer becomes canonical).

**Visual gap:**

- **Layout structure**: standalone list view that may duplicate `<PipelineTable>`. Decision: dedupe with `/dashboard/pipeline?view=table` OR keep distinct surface. Recommend dedupe — fewer surfaces, single mental model.
- **Spacing/typography**: page-h likely Tailwind default not Playfair italic. Same fix as Pipeline.

**Specific changes ATLAS B2 should make:**

1. **Decision flag**: deprecate `/dashboard/leads` in favour of `/dashboard/pipeline?view=table&filter=all`. If retained:
   - Apply same `.page-h` Playfair-italic-em pattern.
   - Same filter chip styling as `/dashboard/pipeline`.
   - Drop the per-lead detail Link target (Item 24 in cleanup map).
2. If retained: pass through `<PipelineTable>` rather than re-implementing rows from scratch.

**Complexity:** **M** if dedupe path; **S** if visual-only fixes match Pipeline route's. Recommend dedupe (deletes the 658-line file).

---

## Route — /dashboard/replies + /dashboard/inbox

**/demo target:** `renderFeed()` at `index.html:1973-2020`.

- `.page-h` "Activity feed, everything Maya is doing."
- `.page-sub` "Reverse-chronological. Tap any reply / meeting / signal card to expand. Tap any business name → briefing drawer."
- `.filter-chips` (probably All / Replies / Meetings / Signals / Cadence per `FEED_FILTERS`).
- Day-grouped event list — `.feed-day` divider (e.g. "Tuesday Apr 23") + `.event-card` rows (chronological). Each event-card: `.event-time` + `.event-ico` + `.event-body` (type label + headline + optional quote + meta) + `.event-side` (VR grade chip + chevron). Expandable on click.

**Current React state:**

- `frontend/app/dashboard/replies/page.tsx:1-444` — 444-line page rendering reply triage.
- `frontend/app/dashboard/inbox/page.tsx:1-32` — 32-line stub. Both routes exist but only `/replies` has substance.

**Visual gap:**

- **Two routes vs one**: `/demo` has a single Activity feed; React splits into `/replies` (heavy) + `/inbox` (stub). Decision needed: consolidate to `/dashboard/feed` or `/dashboard/activity` (which exists at `/dashboard/activity` per route inventory).
- **Day-divider pattern**: `/demo`'s `.feed-day` divider missing in React replies (need to verify).
- **Card pattern**: `.event-card` with chronological time + icon + body + side-grade — needs to match.
- **Filter chips**: same chip pattern issue as Pipeline.

**Specific changes ATLAS B2 should make:**

1. **Decision flag**: consolidate `/dashboard/replies` + `/dashboard/inbox` + `/dashboard/activity` into one canonical "Activity feed" route. `/demo` only has one.
2. `frontend/app/dashboard/replies/page.tsx` — apply `.page-h` "Activity feed, everything Maya is doing." Playfair-italic-em pattern.
3. Add day-divider component for chronological grouping.
4. Each event-card: 3-col grid (time | icon | body | side) per `/demo:1991-2010`.
5. Filter chips with count badges (same component as Pipeline).
6. Drop `/dashboard/inbox/page.tsx` (32-line stub) entirely; redirect to consolidated activity route.

**Complexity:** **M** to **L** depending on whether consolidation is in scope. Visual changes alone are M.

---

## Route — /dashboard/meetings

**/demo target:** Meetings calendar at `index.html:2070-2100` region (renderMeetings logic).

- `.page-h` "Your week, N meetings." Playfair italic.
- `.page-sub` "Click any calendar slot or row to open the full briefing page."
- Calendar grid (week view) + day-meet cards (`.day-meet` blocks).
- `.section-label` "Upcoming this week".
- `.upcoming-row` rows (VR grade chip + name/title + date/time/countdown).

**Current React state:** `frontend/app/dashboard/meetings/page.tsx:1-142`.

- Standalone meetings page; renders calendar.

**Visual gap:**

- **Layout structure**: probably similar (calendar grid + upcoming list). Need page-h Playfair-italic-em alignment.
- **Card padding/typography**: `.day-meet` uses specific font sizing (`.dm-time` mono; `.dm-name` bold serif).
- **Drawer integration**: `/demo` opens full briefing PAGE for meetings (not drawer). React uses drawer (per cleanup-map Item 24 deprecating /leads/[id]). Decision: meeting briefing as drawer or full page?

**Specific changes ATLAS B2 should make:**

1. `frontend/app/dashboard/meetings/page.tsx` — `.page-h` "Your week, {N} meetings." pattern.
2. Calendar slot styling: match `/demo`'s `.day-meet` (mono time + Playfair name + ink-3 dm).
3. `.section-label` "Upcoming this week" with the same uppercase-mono utility.
4. `.upcoming-row` 3-col grid: VR chip | main info | when+countdown — match `/demo:2090-2100`.
5. **Decision flag**: drawer vs full briefing page for meetings — both could co-exist (drawer for quick view, full page for "join meeting" workflow). Recommend drawer-only for parity with the rest of the app.

**Complexity:** **M** (30 min – 2 hr). Page-h + section-label + upcoming-row visual swap.

---

## Route — /dashboard/reports

**/demo target:** `renderProgress()` at `index.html:2209-2257`.

- `.page-h` "Cycle progress, partner-ready report." (italic em).
- `.page-sub` "Cycle 3 · day 14 of 30 · refreshed every 5 minutes. Raw metrics only — no unsourced benchmark comparisons."
- `.kpi-row` — 4 cells (Open Rate / Reply Rate / Meeting Rate / Avg Reply Time) with `.kpi-val` (Playfair 28px), `.kpi-l` (mono 10px), `.kpi-note`.
- `.card` with mono `<h4>` "Funnel" + horizontal funnel rows (`.fr-row` with label + bar + percent).
- `.card` "Your subscription efficiency · AUD" + `.roi-grid` (4 cells: Cost/Meeting · Cost/Reply · Cost/Contact · Pipeline ROI).
- "Export report" CTA (amber primary button).

**Current React state:** `frontend/app/dashboard/reports/page.tsx:1-69` — thin Reports page imports from `@/components/reports` (HeroMetrics, ChannelMatrix, MeetingsChart, ConversionFunnel, ResponseRates, WhatsWorking, LeadSources, TierConversion, VoicePerformance, ROISummary).

**Visual gap:**

- **Layout structure**: React has 11+ report components stacked. `/demo` has 3 sections (KPI row + Funnel card + ROI grid). React surface is ~3x denser. Decision: trim to /demo's 3 sections OR keep React's 11 with /demo styling?
- **ROI grid**: `/demo` is 4-cell 2×2 grid (Cost/Meeting / Cost/Reply / Cost/Contact / Pipeline ROI). React's `<ROISummary>` has different shape (per Phase 3 UX inventory Item 6 finding — single ROI value, not 4-cell grid). **NEW component needed.**
- **KPI row**: `<HeroMetrics>` may render the KPI row but field set might differ (Open / Reply / Meeting rates vs whatever HeroMetrics shows).
- **Page-h**: Playfair-italic-em "Cycle progress, partner-ready report."
- **Density**: `.kpi-cell` is light (Playfair value + mono label + small note). React Bloomberg components likely heavier with more chrome.

**Specific changes ATLAS B2 should make:**

1. `frontend/app/dashboard/reports/page.tsx` — `.page-h` Playfair-italic "Cycle progress, partner-ready report." with `.page-sub` "Cycle N · day M of 30 · refreshed every 5 minutes..."
2. **Decision flag**: prune from 11 report sections to /demo's 3 (KPI row + Funnel card + ROI grid)? Pre-revenue, simplicity wins.
3. **NEW component**: `ROIGrid.tsx` 4-cell 2×2 grid (per Phase 3 UX inventory Item 6 spec). Replace `<ROISummary>`.
4. Funnel card: horizontal `.fr-row` per stage with bar fill + percent label — likely needs new component if `<ConversionFunnel>` doesn't already match.
5. Add "Export report" amber primary button at the bottom — currently absent.
6. Caption above ROI grid: copper-coloured "Based on your $X/month subscription" mono uppercase line.

**Complexity:** **M** to **L** (M if just visual swap of existing components, L if also pruning the 11-component stack to /demo's 3-section layout).

---

## Route — /dashboard/settings

**/demo target:** `renderSettings()` at `index.html:2258-2310`.

- `.page-h` "Settings"
- `.page-sub` "Configure Maya, your BDR agent."
- Two `.section-label` blocks: "Agent" and "Notification mode".
- "Agent" `.card` with `.set-row` rows: BDR name / Agency name / Founder / Quality-check cadence / Needs-review threshold / Agency voice tone — each row is `.set-key` (mono label) + `.set-val` (input/select/textarea).
- "Notification mode" `.card` with 3 radio options (Dashboard-first selected; Alerts-only + Reports-only marked "coming soon").
- `<button class="btn btn-primary">Save changes</button>` right-aligned.

**Current React state:** `frontend/app/dashboard/settings/page.tsx:1-133`.

- 5-tab interface: Profile / Team / Integrations / Notifications / Billing.
- Each tab uses a sub-component (ProfileSection, TeamSection, etc.).
- Tab list: rounded pill bar `bg-bg-panel rounded-xl p-1.5`.
- Active tab: amber-tinted bg.

**Visual gap:**

- **Layout structure**: React has 5 tabs vs `/demo`'s single linear page (with Agent + Notification mode sections). Profile/Team/Integrations/Billing are React-only — pre-revenue settings. Notifications maps to /demo's Notification mode section.
- **/demo's "Agent" section** (BDR name, agency name, founder, quality-check cadence, needs-review threshold, agency voice tone) — **NOT IMPLEMENTED** in React. These are Maya/BDR-config fields.
- **Page-h**: React likely has `<SettingsHeader>` rather than a Playfair `.page-h`. Should align.
- **Density**: React tab pills (px-5 py-2.5) heavier than /demo's row-based linear layout.

**Specific changes ATLAS B2 should make:**

1. `frontend/app/dashboard/settings/page.tsx` — keep tabs but apply `.page-h` "Settings" Playfair pattern.
2. **NEW**: Add an "Agent" tab (or new section) carrying `/demo`'s 6 BDR-config rows (BDR name / agency name / founder / quality-check cadence / needs-review threshold / agency voice tone).
3. Notifications tab: align to `/demo`'s 3-radio layout (Dashboard-first selected + 2 "coming soon" options).
4. Section labels via the section-label utility (Phase 3 Item 4 dependency).
5. "Save changes" button: amber primary right-aligned per `/demo:2298`.
6. Trim tab pill padding to closer match `/demo`'s lighter typography.

**Complexity:** **M** (30 min – 2 hr) — visual + new "Agent" config tab.

---

## Route — /onboarding/*

**/demo target:** **None**. `/demo` has no onboarding flow. The 5-step React onboarding is React-only (existing flow).

**Current React state:** `frontend/app/onboarding/{step-1..5,agency,crm,linkedin,service-area,page.tsx}` — 9 sub-routes.

Key file: `step-1/page.tsx` already declares "DESIGN: Bloomberg cream/amber palette, Playfair Display headings" in its docstring — partially repaletted.

**Visual gap:**

- **No /demo target**: this is purely a "is the existing onboarding consistent with /demo's design tokens?" check.
- **Internal consistency**: 9 sub-routes likely have varying degrees of palette compliance. Some early steps (step-1 docstring) reference cream/amber explicitly; later steps unverified.
- **Component style consistency**: cards / buttons / form fields should match `/demo`'s `.card` / `.btn-primary` / `.set-val` patterns.

**Specific changes ATLAS B2 should make:**

1. Audit each onboarding sub-route for palette compliance (cream bg, amber accent, Playfair headings, JetBrains Mono labels).
2. `frontend/app/onboarding/step-{1..5}/page.tsx` — verify each uses `.page-h` Playfair / `.page-sub` 13px DM Sans.
3. CRM connector cards (step-1) — already has SVG icons + colour coded; ensure card padding + rounded matches `/demo`'s `.card` (rounded-10px, padding 14-18px).
4. Form inputs — apply `/demo`'s `.set-val input` styling (1px rule border, mono input text where appropriate).
5. Progress indicator across the 5 steps — verify present + visually consistent.

**Complexity:** **M** (30 min – 2 hr) per sub-route × 9 sub-routes = **L** combined. Recommend chunking into 3-4 ATLAS B2 dispatches (one per step pair).

---

## Route — /welcome

**/demo target:** **None**. `/welcome` is a React-only post-deposit founding-member celebration page.

**Current React state:** `frontend/app/welcome/page.tsx:1-887`. Per its docstring (lines 4-26): "Cream/ink/amber palette (now inherited from globals.css); Playfair Display headlines, DM Sans body, JetBrains Mono labels — unchanged from the original /welcome render." Updated 2026-04-30 (today) per A7.1.

Key elements: hero h1 (line 707), receipt (line 733), next-h (line 777), founder name (line 838), final CTA (line 851).

**Visual gap:**

- **Already at parity** per the docstring claim. A7.1 retire-and-restore landed today.
- **Verification needed**: spot-check that hero-h1, receipt block, founder-bio block, and CTA all use Playfair / DM Sans / JBMono per the design system.

**Specific changes ATLAS B2 should make:**

1. `frontend/app/welcome/page.tsx` — visual smoke test pass; verify globals.css token resolution (post-A1 codemod).
2. Confirm dark-mode toggle works (per A2 docstring claim).
3. No specific changes expected unless smoke test surfaces a regression.

**Complexity:** **S** (under 30 min). Verification-only.

---

## Route — /(auth)/login + signup

**/demo target:** **None**. Auth surfaces are React-only.

**Current React state:**

- `frontend/app/(auth)/login/page.tsx:1-28` — 28-line server component wrapper for SSG.
- `frontend/app/(auth)/signup/page.tsx:1-182` — full client form. Per docstring: "Signup form — cream/amber /demo palette. Playfair headline, JetBrains Mono labels, DM Sans body. UPDATED: 2026-04-30 — A6 auth refinement."

**Visual gap:**

- **Already repaletted** today per A6 dispatch. Same as /welcome — verification only.
- **Login page**: 28-line server wrapper means the actual UI is in a child client component (likely `frontend/app/(auth)/login/...client.tsx` or imported from `@/components/auth/...`). Need to verify it's also repaletted.

**Specific changes ATLAS B2 should make:**

1. Verify login page's child component matches signup palette (cream bg / Playfair headline / JBMono labels).
2. Form input styling: match `/demo`'s `input` baseline (1px rule border, DM Sans body).
3. Submit button: amber primary (matches `/demo .btn-primary`).
4. Error / toast styling: confirm uses ink/amber tokens not Bloomberg gray.

**Complexity:** **S** (under 30 min). Verification + 1-2 polish edits if login child UI lags.

---

## Closing summary

### Route-count tiers by change item count

| Tier | Routes | Count |
|---|---|---:|
| **< 5 changes** | /welcome (verification), /(auth)/login + signup (verification + 1-2 polish) | **2** |
| **5–15 changes** | /dashboard/pipeline (5 changes), /dashboard/leads (1-2 changes if dedupe; otherwise 4-5), /dashboard/meetings (5 changes), /dashboard/reports (6 changes), /dashboard/settings (6 changes) | **5** |
| **> 15 changes** | /dashboard (6 explicit changes but L complexity due to 3-stack demolition), /dashboard/replies + /inbox (consolidation + 6 changes = combined heavy), /onboarding/* (9 sub-routes × ~5 changes each = 45+ items) | **3** |

### Complexity tally

- **S** (under 30 min): /welcome, /(auth)/login + signup → **2 routes**
- **M** (30 min – 2 hr): /dashboard/pipeline, /dashboard/leads, /dashboard/meetings, /dashboard/settings → **4 routes**
- **M-L** (1-3 hr): /dashboard/reports → **1 route** (M if visual-only, L if structural prune)
- **L** (2 hr +): /dashboard, /dashboard/replies+inbox (consolidation), /onboarding/* (9 sub-routes) → **3 routes** (with onboarding being a multi-dispatch effort)

### Total estimate range

- **Optimistic**: 2×0.4 + 4×1 + 1×1.5 + 3×3 = **~15 hours** (if all happy paths land first try, no scope creep).
- **Realistic**: 2×0.5 + 4×1.5 + 1×2.5 + 3×4 = **~22 hours** (some scope expansion on the L routes, especially /dashboard demolition).
- **Pessimistic**: 2×1 + 4×2 + 1×3 + 3×6 = **~31 hours** (onboarding + dashboard each grow significantly).

Total Phase 4 visual-parity sweep estimate: **15–31 hours of ATLAS effort**, biased toward 20–25 hr realistic.

### Recommended ATLAS B2 dispatch order

Two ordering strategies; recommend **Strategy A** (momentum first):

**Strategy A — momentum / lowest-effort first (recommended):**

1. **/welcome** (S, verification) — 5 min smoke test, immediate green.
2. **/(auth)/login + signup** (S, verification + 1-2 polish) — same.
3. **/dashboard/pipeline** (M) — 5 file-level changes; pipeline is daily-touch, polish here visible to investors.
4. **/dashboard/meetings** (M) — `.page-h` + `.upcoming-row` pattern; ~5 changes.
5. **/dashboard/leads** (M) — recommend dedupe with /pipeline; 1-2 changes if redirected.
6. **/dashboard/settings** (M) — `.page-h` + new "Agent" tab + radios.
7. **/dashboard/reports** (M-L) — biggest semantic change (ROI grid + funnel card); high investor-demo value.
8. **/dashboard/replies + /inbox consolidation** (L) — needs product decision on consolidation first; hold for clarity.
9. **/dashboard** (L) — 3-layout demolition; highest-effort. Lands last so the rest of the app is consistent first.
10. **/onboarding/*** (L, multi-dispatch) — chunk into 3 dispatches (steps 1-2, 3-4, 5+sub-routes). Lands on its own track.

**Strategy B — most-visible first (alternative for early-demo polish):**

1. /dashboard (L) — first impression matters most; demolish the 3-stack.
2. /dashboard/pipeline (M) — second-most-touched route.
3. /dashboard/reports (M-L) — investor-facing metrics.
4. ... then everything else.

**Recommendation:** Strategy A — momentum from quick wins surfaces ATLAS B2 confidence + delivers cumulative visual coverage. Save the demolition (/dashboard) for last when the surrounding routes already look consistent.

### Cross-cutting decisions needed before ATLAS B2 starts

1. **ATLAS B1 sidebar consolidation** must land first — assumed in flight.
2. **Pipeline filter taxonomy**: keep React's intent-based (struggling/trying/dabbling) OR adopt `/demo`'s status-based (hot/replied/meeting)? Recommend keep intent.
3. **/dashboard/leads vs /dashboard/pipeline**: dedupe? Recommend yes — single mental model.
4. **/dashboard/replies + /inbox + /activity**: consolidate to one canonical activity route? Recommend yes.
5. **Reports surface depth**: keep React's 11 components vs prune to /demo's 3 sections? Recommend prune for pre-revenue simplicity.
6. **Section-label utility** (Phase 3 UX inventory Item 4) lands first; consumed by every route's section headings.

### Out of scope for this audit

- Mobile-specific responsive breakpoints (separate audit if needed).
- Dark-mode parity verification (covered indirectly via globals.css token resolution).
- Animation / transition timing (Phase 5 polish, not B2).
- Accessibility / aria-label audit (separate dispatch).

---

*This document is research-only. No code edits. Generated 2026-04-30 on `aiden/phase4-visual-parity-audit` branch.*
