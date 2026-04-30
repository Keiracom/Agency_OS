# B2.3 — Settings + Reports Visual Parity

**Phase:** B2.3 (final visual parity sweep)
**Branch:** `elliot/b2-3-settings-reports`
**Date:** 2026-04-30

## Scope

Rebrand the two remaining dashboard sub-routes that still rendered with the
prior Bloomberg-dark Tailwind palette to the cream/amber tokens shipped in
PRs #441–#470.

| Route | Before | After |
|-------|--------|-------|
| `/dashboard/settings` | 133 lines, raw `rgb(212,149,106,…)` literals, no Agent tab | 373 lines, cream/amber tokens, Agent tab default |
| `/dashboard/reports` | 69 lines, 11-section "Analytics Terminal" dark layout | 181 lines, /demo's 3-section `renderProgress` (KPI · Funnel · ROI) |

Both screens now use `<AppShell pageTitle="…">` and `<SectionLabel>` from
PR #462, matching the established Phase 2 pattern.

## Settings — Agent tab

`renderSettings` in `dashboard-master-agency-desk.html` (lines 2258–2305)
defines five tab pills, with the **Agent** tab carrying the founder-facing
configuration. The pre-existing settings page only listed two tabs (API Keys
+ Danger Zone) and shipped no Agent surface at all.

This PR adds:

- `<AgentSection>` containing /demo's `.set-row` grid:
  - BDR name (text)
  - Agency name (text)
  - Founder (text)
  - Quality-check cadence (select: every send / hourly / daily)
  - Needs-review threshold (select: 60% / 70% / 80%)
  - Agency voice / tone (textarea)
- Notification mode radio group (`.notif-row` parity):
  - **Dashboard-first** (selected, `bg-amber-soft border-amber`)
  - Alerts-only (disabled, "coming soon" badge)
  - Reports-only (disabled, "coming soon" badge)
- Tab pills migrated from raw `rgba(212,149,106,0.15)` → `bg-amber-soft text-copper`

The existing `<ApiKeysSection>` and `<DangerZone>` sections are preserved
behind the new tab switcher, both rebranded to the cream/amber tokens.

## Reports — 3-section rewrite

`renderProgress` (lines 2209–2255) is the canonical cycle-progress layout.
The pre-existing reports page rendered an 11-section "Analytics Terminal"
that did not appear anywhere in the prototype.

| Section | Pattern | Spec |
|---------|---------|------|
| 1. KPI row | 4 `.kpi-cell` | Open Rate · Reply Rate · Meeting Rate · Avg Reply Time, Playfair `text-[28px]` value with `text-amber em` unit suffix |
| 2. Funnel card | proportional bars | Discovered → Contacted → Replied → Meetings → Won, `bg-amber` fill, % label tabular-nums |
| 3. ROI grid | 4 `.kpi-cell` on `.bg-surface` | Cost/Meeting · Cost/Reply · Cost/Contact · Pipeline ROI, "Based on your active subscription · cycle to date" copper note |

Each cell carries a `your data only` mono note so the UI is honest about the
absence of unsourced industry-benchmark comparisons. Values are rendered as
`—` placeholders until the metrics endpoint exposes a cycle-telemetry shape;
this matches the anti-vanity-metric convention from the prototype.

The page also retains the page-bottom "Export report" button as a stub that
alerts on click, ready to wire to a future PDF endpoint.

## Files changed

| File | Lines | Change |
|------|-------|--------|
| `frontend/app/dashboard/reports/page.tsx` | 69 → 181 | full rewrite |
| `frontend/app/dashboard/settings/page.tsx` | 133 → 373 | full rewrite — Agent tab added, palette migrated |
| `docs/B2_3_SETTINGS_REPORTS.md` | new | this audit |

## Verification

- `pnpm run build` — green, both routes compile
  - `/dashboard/reports` 1.75 kB
  - `/dashboard/settings` 3.57 kB
- No new dependencies, no API changes, placeholder values for sections
  that lack backend data.

## Out of scope (intentional)

- Wiring `Export report` to a real PDF endpoint — backend stub pending.
- Persisting Agent-tab field changes — UI parity only; mutations land in
  a follow-up once `/api/settings/agent` exists.
- Real cycle telemetry — placeholder `—` until cycle-progress endpoint
  ships.
