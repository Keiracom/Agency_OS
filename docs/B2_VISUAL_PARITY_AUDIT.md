# B2.1 visual parity — R7 audit log (2026-04-30)

Audit performed before any code changes per dispatch.

## Sub-task 1 — `/welcome` smoke test
Verified — no changes needed.

PR #461 (A7.1) restored the full 862-line founding-member welcome
page from origin/main and migrated its local CSS-var redefinitions
of `--cream / --ink / --amber / --rule` to read from `globals.css`,
so the page now uses the same token system as the rest of the app
and inverts under `html.dark`. Demo-cookie short-circuit also
verified. Spot-check of class names (`hero-h1`, `confirm-badge`,
`btn-primary`) confirms the prototype's structure intact.

## Sub-task 2 — `/(auth)/login` + `/(auth)/signup` smoke test
Verified — no changes needed.

PR #460 (A6) repalleted both pages: cream rounded panel, Playfair
"Welcome back" / "Create your account" headlines with amber italic
emphasis, JetBrains Mono uppercase labels, cream-bg mono inputs
with `focus:border-amber focus:ring-amber/40`, ink primary button,
cream Google secondary, copper hover for sub-links. `(auth)/layout
.tsx` carries the AgencyOS brand mark + "Try the demo →" footer.
Auth logic (Supabase `signInWithPassword` / `signUp`) byte-
identical to pre-A6.

## Sub-task 3 — `/dashboard/pipeline` rebrand
Gap found. Two components still on the dark Bloomberg theme:

### `PipelineKanban.tsx`
Was 6 columns (discovered/enriched/contacted/replied/meeting/
converted) with `bg-gray-900 border-gray-800` panels and dark cards.
**Migrated** to the prototype's 5-column structure (PIPE_COLS lines
1735-1745):

| Column | Stage(s) merged | Top accent (`.col-*-head::before`) |
|---|---|---|
| **New** | `discovered` + `enriched` | `var(--ink-3)` |
| **Contacted** | `contacted` | `var(--blue)` |
| **Replied** | `replied` | `var(--amber)` |
| **Meeting** | `meeting` | `var(--green)` |
| **Won** | `converted` | `var(--copper)` |

Cards translated to /demo's `.k-card` pattern:
- `bg-panel border border-rule` cream card
- 3px left border in the column's accent colour
- Playfair font-bold 14px name (Company name when present, falls
  back to lead name)
- DM-name body in `text-ink-2`
- JetBrains Mono `text-[10.5px] text-ink-3` channel · date meta line
- Foot row: VR grade chip + score in `text-copper`, separated from
  body by a dashed `border-rule`
- Hover: `border-amber` + `box-shadow` amber glow per prototype
- Native HTML5 drag/drop preserved; first stage in a merged column
  wins on drop (e.g. `discovered` for the New column)

Column header gets the prototype's `top: 0; left/right: 10px;
height: 3px` accent stripe. Counts shown as `<bg-ink white pill>` +
`<text-ink-3 percentage>`. Empty column copy: "Empty — awaiting
prospects".

### `PipelineTable.tsx`
Was `bg-gray-900` outer panel with `bg-gray-800` headers and
`text-gray-300/400/500` body text. **Migrated** to:
- `bg-panel border-rule rounded-[10px]` outer panel
- `bg-surface border-rule` thead with mono uppercase ink-3 headers
  and `hover:text-amber` sort indicator
- `text-ink` row body with Playfair-bold prospect name, `text-ink-2`
  company/stage, `font-mono text-[11px] text-ink-3` for channel /
  dates
- `bg-amber-soft` hover instead of dark grey
- VR grade chip swapped to the prototype's colour-coded square (A/B
  green, C amber+on-amber, D copper, F red) — same component pattern
  as the Kanban cards
- Each cell gets a `data-label` attr so the mobile-card-table CSS
  utility from PR #458 displays "Prospect ·", "Stage ·" etc. as
  cell prefixes when stacked on `<md`

## Verification
```
pnpm run build → exit 0
```

## Files
- `frontend/components/dashboard/PipelineKanban.tsx` — 6 → 5 columns, /demo `.k-card` pattern
- `frontend/components/dashboard/PipelineTable.tsx` — cream/amber rebrand + data-label cells
- `docs/B2_VISUAL_PARITY_AUDIT.md` — this file

## Out of scope (not changed)
- `app/dashboard/pipeline/page.tsx` — view toggle + filter chips +
  state tabs already on /demo design from PR #443 + PR #466
- `PipelineFilters.tsx` — already uses /demo's `.chip` pill pattern
- `PipelineRow.tsx` (list view) — already on /demo design from PR #443
- Drawer behaviour — `<ProspectDrawer>` opens on card click
  (`onOpen(p.id)` → `setActiveLead(id)` → drawer renders), matching
  the prototype's `openDrawer(pid)` pattern. No change needed
