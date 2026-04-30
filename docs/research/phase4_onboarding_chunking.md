# Phase 4 Onboarding Chunking Spec — ATLAS B2.5

Read-only research. Concrete 3-chunk dispatch spec for ATLAS B2.5 (`/onboarding/*` visual parity sweep). All 9 onboarding sub-routes covered exactly once. Each chunk balanced for ~equal effort + grouped by natural design-skin affinity.

**Reference paths**

- React onboarding routes: `/home/elliotbot/clawd/Agency_OS/frontend/app/onboarding/*`
- `/demo` (no onboarding screens; design tokens via `globals.css` post-A1 codemod)

**Branch**: `aiden/phase4-onboarding-chunking` (off `origin/main`). No code edits — doc-only.

## Inventory

| Route | Lines | Demo / Real | Purpose |
|---|---:|---|---|
| `step-1/page.tsx` | 309 | **demo** (simulated) | CRM connect — fake HubSpot/Pipedrive picker |
| `step-2/page.tsx` | 284 | **demo** (simulated) | LinkedIn connect — fake Unipile OAuth |
| `step-3/page.tsx` | 319 | **demo** (simulated) | Confirm services — service-list + add/remove |
| `step-4/page.tsx` | 253 | **demo** (simulated) | Service area picker — radius/region |
| `step-5/page.tsx` | 305 | **demo** (simulated) | Prospect universe build — animated 5-stage progress + redirect to `/dashboard` |
| `agency/page.tsx` | 613 | **real** | Agency profile — website scrape + ICP analysis (longest single file) |
| `crm/page.tsx` | 236 | **real** | CRM OAuth — HubSpot real OAuth flow |
| `linkedin/page.tsx` | 250 | **real** | LinkedIn OAuth — Unipile real OAuth |
| `service-area/page.tsx` | 268 | **real** | Service area + finalize — ends real onboarding, redirects to `/dashboard` |

**Totals:** 2,837 lines across 9 files. Demo routes: 1,470 lines (51.8%). Real OAuth/config routes: 1,367 lines (48.2%).

## Shared imports + design-skin observations

- **All 9 routes** import `useState` + `useRouter` from React + Next.js. No file imports another onboarding route's components — they're 100% independent at the file level.
- **Real-OAuth trio** (`crm`, `linkedin`, `service-area`) share `AlertCircle, ExternalLink, Loader2, ShieldCheck` lucide icons — same error/retry/security-badge UI surface.
- **Demo steps 1-2 + 5** use `Loader2, CheckCircle2` (simulated-loading idiom). Steps 3-4 use domain-specific icons (`Plus, Trash2, ArrowRight` / `MapPin, Zap`).
- **Per-route docstrings** all already declare cream/amber palette + Playfair Display + JetBrains Mono — partial repalette compliance varies by route, sweep should verify each.
- **No internal route-to-route imports** — chunking is constrained only by ATLAS reviewer cognitive load + globals.css conflict avoidance, not by file-coupling.

## Chunking strategy chosen

**Strategy 6 — demo / mixed / real, with paired domain in chunk B:**

- **Chunk A** = early demo screens (step-1, step-2, step-3).
- **Chunk B** = late demo screens + matching real route (step-4 demo + step-5 demo + service-area real). Step-4 (demo service-area) pairs naturally with service-area (real); landing them together keeps the design pattern cross-checked.
- **Chunk C** = remaining real OAuth flows (agency + crm + linkedin). agency is the largest single file (613 lines) and carries the website-scrape + polling-state UI surface; crm + linkedin are similar shorter OAuth flows.

**Rationale:** ~3 files per chunk; ~800–1,100 lines per chunk; demo work front-loaded; real-OAuth work consolidated for cognitive consistency on the error/retry idiom.

**Alternatives considered:**

- **Strategy 1 — Demo vs Real binary split** rejected: chunk A would have 5 files (1,470 lines), chunk B alone with agency (613 lines) — too imbalanced.
- **Strategy 4 — Domain pairing (CRM-demo + CRM-real together)** rejected: pairs demo + real but breaks cognitive flow when ATLAS reviewer wants to think "all simulated screens" or "all real OAuth" at once.
- **O4's original suggestion (1-2 / 3-4 / 5+sub-routes)** would have given chunk C 5 files (step-5 + 4 real routes = 1,672 lines, 60%+ of total) — imbalanced.

---

## Chunk A — Early demo screens

**Routes covered:**
- `frontend/app/onboarding/step-1/page.tsx` (CRM connect demo)
- `frontend/app/onboarding/step-2/page.tsx` (LinkedIn connect demo)
- `frontend/app/onboarding/step-3/page.tsx` (Confirm services demo)

**Line counts:**
- step-1: 309
- step-2: 284
- step-3: 319
- **Total: 912 lines / 3 files**

**Shared components / imports:**
- `useState` + `useRouter` (universal across all 9 routes).
- `Loader2, CheckCircle2` lucide icons (simulated-loading idiom for steps 1-2; step-3 uses different icons).
- Local `DEMO_AGENCY = "Bondi Digital Marketing"` constant — same string across all 5 demo steps. Could extract to a shared module if ATLAS prefers.
- Inline SVG icons for CRM logos in step-1 (HubSpot orange, Pipedrive green, etc.). Per-route.
- Linkedin lucide icon in step-2.

**Design-skin scope:**
- `.page-h` (Playfair 30px, italic-em pattern) — verify each step's headline pattern.
- `.page-sub` (13px DM Sans, max-width 820px) — verify caption uses correct typography.
- Card grid for CRM picker (step-1) — match `/demo`'s `.card` (rounded-10px, padding 14-18px, 1px rule border).
- Per-CRM logo card hover states + selected state — currently uses inline SVG, may need polish.
- Step-2 LinkedIn-connect button — amber primary `.btn-primary` style.
- Step-3 service list with `Plus / Trash2 / ArrowRight` action icons — verify icon sizing + spacing.
- Progress indicator across the 5 demo steps — present? consistent? need to add if missing.

**Estimated complexity:** **M** (30 min – 2 hr).

3 files × ~30 min each = ~1.5 hr realistic. The CRM picker (step-1) is the heaviest within this chunk because of the inline SVG icon cards.

**Dependencies:**
- ATLAS B1 (sidebar consolidation) lands first — assumed in flight.
- Phase 3 UX Item 4 (section-label utility) — consumed by section headings within steps; lands first.
- AppShell already canonical (KEEP per cleanup-map).
- No other Phase 3 dependencies — these are pure visual sweeps.

**Test plan:**
- Visual smoke: load each step at `/onboarding/step-N`, verify cream bg + Playfair page-h + amber accents.
- Interactive: click through CRM picker (step-1), LinkedIn button (step-2), service list add/remove (step-3) — verify state transitions still work.
- Forward-nav: step-1 → step-2 → step-3 routing intact (each has `useRouter().push("/onboarding/step-N+1")` in code).
- Mobile: 320px-wide viewport, no horizontal scroll, cards stack vertically.

---

## Chunk B — Late demo + service-area pairing

**Routes covered:**
- `frontend/app/onboarding/step-4/page.tsx` (Service area demo)
- `frontend/app/onboarding/step-5/page.tsx` (Prospect universe build demo + redirect to `/dashboard`)
- `frontend/app/onboarding/service-area/page.tsx` (Real service-area + finalize)

**Line counts:**
- step-4: 253
- step-5: 305
- service-area: 268
- **Total: 826 lines / 3 files**

**Shared components / imports:**
- step-4 + service-area both render service-area pickers — same UI domain. ATLAS reviewer can copy the pattern once and apply to both.
- service-area uses `AlertCircle, Check, Loader2` (real-OAuth error idiom) — different from step-4's demo `MapPin, Zap`.
- step-5 has `useEffect` for the animated 5-stage progress + auto-redirect — only route in this chunk with a side effect.

**Design-skin scope:**
- step-4: `.page-h` "Set your service area" Playfair pattern; map/region picker UI (uses `MapPin, Zap` icons).
- step-5: animated 5-stage progress visualization — verify uses cream/amber palette, not Bloomberg gray. The redirect target after build (`/dashboard`) should be confirmed against Phase 1 discussion (potentially `agencyxos.ai/demo` instead).
- service-area: real service-area picker with `Check` confirmation + `AlertCircle` error state. Same picker pattern as step-4 but with real form state + API submit.
- All 3 should use the same picker layout component if extracted (recommendation for ATLAS).
- "Save & finish" or "Finalize onboarding" CTA — amber primary button right-aligned.

**Estimated complexity:** **M** (30 min – 2 hr).

3 files × ~30 min each + step-5 animation polish + cross-check between step-4 and service-area picker = ~1.5–2 hr realistic.

**Dependencies:**
- Same as Chunk A.
- **Critical decision flag**: step-5 redirect target.
  - Currently: `useRouter().push("/dashboard")` (per route docstring + 305-line page).
  - Possible alternative per Phase 1 discussions: `agencyxos.ai/demo` (off-platform demo URL) so investor previews land outside the auth-gated app.
  - Decision needed before this chunk dispatches — flips a single line in step-5 but has product/marketing implications.

**Test plan:**
- Visual smoke: each route loads with correct palette; step-5 animation runs through all 5 stages.
- step-4 → step-5 routing intact (forward navigation).
- step-5 → `/dashboard` redirect (or `agencyxos.ai/demo` if decision flips).
- service-area form: submits, error shows on `AlertCircle`, success shows `Check`.
- service-area submit → `/dashboard` redirect post-finalize.
- Spot-check that step-4 picker pattern matches service-area picker (visual consistency cross-check).

---

## Chunk C — Real OAuth flows

**Routes covered:**
- `frontend/app/onboarding/agency/page.tsx` (Agency profile + website scrape + ICP analysis — largest single file)
- `frontend/app/onboarding/crm/page.tsx` (HubSpot real OAuth)
- `frontend/app/onboarding/linkedin/page.tsx` (Unipile real OAuth)

**Line counts:**
- agency: 613
- crm: 236
- linkedin: 250
- **Total: 1,099 lines / 3 files**

**Shared components / imports:**
- crm + linkedin share `AlertCircle, ExternalLink, Loader2, ShieldCheck` — same security/error/loading idiom. Both are short OAuth-redirect flows.
- agency uses `useEffect, useCallback, useRef` and additional imports for the website-scrape + polling state — most stateful route in the entire onboarding.
- agency calls 4 different API endpoints (analyze / status / result / confirm per its docstring).

**Design-skin scope:**
- agency: `.page-h` "Tell us about your agency" Playfair pattern. Website URL input + analyze button + animated polling-progress UI + ICP-result confirmation step. **Most surface area** to repalette in this chunk.
- crm: HubSpot OAuth init button (amber primary) + `ShieldCheck` security badge + post-redirect callback handling. Short, ~5 visual elements.
- linkedin: same shape as crm — Unipile OAuth init + security badge + callback. Mirror polish.
- All 3 share error-state styling: `AlertCircle` icon + ink-3 text + retry CTA. Standardize.
- All 3 use `ExternalLink` to indicate "this opens in a new tab to the OAuth provider" — verify icon + tooltip consistency.

**Estimated complexity:** **M-L** (1.5 – 2.5 hr).

agency's 613 lines + polling-state UI account for ~60% of this chunk's effort. crm + linkedin together are ~30 min each due to symmetry. Realistic ~2 hr.

**Dependencies:**
- Same as Chunks A + B.
- **Backend dependency**: agency relies on `/api/v1/onboarding/analyze` + `/status/{id}` + `/result/{id}` + `/confirm` — these endpoints presumably exist (route is live in main); ATLAS B2.5 is visual only, no API change.
- **Cross-chunk dependency**: if Chunks A + B land first, the OAuth-error styling pattern established in their `service-area` route can carry into Chunk C's crm/linkedin error states. Sequential ordering helps.

**Test plan:**
- Visual smoke: each route in isolation. agency loads with cream bg + Playfair page-h + amber CTA.
- agency E2E: enter website URL → analyze button → polling spinner → ICP result confirmation → confirm button → redirect.
- crm: click "Connect HubSpot" → opens `/api/v1/oauth/hubspot/start` in popup or redirect → callback handling → success or `AlertCircle` error path.
- linkedin: same as crm but with Unipile.
- Error states: simulate `AlertCircle` paths (network failure, OAuth denied) — confirm error styling matches Chunks A + B service-area pattern.
- Mobile: agency's URL input + button stack vertically; OAuth buttons full-width.

---

## Closing summary

### Coverage check

All 9 onboarding routes covered exactly once across 3 chunks:

- **Chunk A**: step-1, step-2, step-3
- **Chunk B**: step-4, step-5, service-area
- **Chunk C**: agency, crm, linkedin

**Verified: 9/9 routes covered, 0 double-coverage, 0 misses.**

### Effort distribution

| Chunk | Files | Lines | Complexity | Realistic effort |
|---|---:|---:|---|---:|
| A — Early demo (step-1/2/3) | 3 | 912 | M | **~1.5 hr** |
| B — Late demo + service-area (step-4/5 + service-area) | 3 | 826 | M | **~1.5–2 hr** |
| C — Real OAuth (agency + crm + linkedin) | 3 | 1,099 | M-L | **~2 hr** |
| **Total** | **9** | **2,837** | — | **~5 hr realistic** |

### Total estimate range

- **Optimistic**: 1.0 + 1.0 + 1.5 = **3.5 hr** (all happy paths, no scope creep, ATLAS reviewer fast on the OAuth idiom).
- **Realistic**: 1.5 + 1.75 + 2.0 = **~5.25 hr** (some palette-compliance surprises, step-5 animation polish, agency polling state).
- **Pessimistic**: 2.0 + 2.5 + 3.0 = **~7.5 hr** (each chunk hits a backend / decision flag delaying the dispatch).

### Recommended dispatch order

**Sequential. Strict order. Reasons:**

1. All 3 chunks touch the same shared design-skin (cream bg / Playfair page-h / JetBrains Mono labels / amber CTAs). Concurrent ATLAS dispatches risk merge conflicts on `globals.css` token tweaks if any palette adjustment is needed mid-sweep.
2. Chunk B's service-area picker pattern should be cross-checked against step-4's demo equivalent — best done within a single dispatch (which is why they're chunked together) but the pattern then informs Chunk C's `AlertCircle` error layout.
3. Chunk C's agency is the most complex single file in the entire onboarding flow (613 lines, polling state, 4 API endpoints) — ATLAS reviewer benefits from having seen the simpler routes first to set the design baseline.

**Order: A → B → C.**

Each dispatch is a single PR. ATLAS B2.5 fires three sequential dispatches over ~1-2 working days at the realistic estimate. Pessimistic case stretches to ~3 days.

### Critical decisions before B2.5 fires

1. **step-5 redirect target** — currently `/dashboard`. Phase 1 discussions floated `agencyxos.ai/demo` for investor previews. Decide before Chunk B dispatches; one-line edit in step-5.
2. **DEMO_AGENCY constant** — currently `"Bondi Digital Marketing"` hard-coded in 5 files. Extract to a shared `lib/onboarding/demo-fixtures.ts` module? Recommend yes, but do it as a Chunk-A pre-dispatch atom (or skip if ATLAS reviewer prefers minimal scope).
3. **Picker pattern extraction** — step-4 (demo) and service-area (real) both render service-area pickers. Extract to a shared `<ServiceAreaPicker>` component or duplicate? Recommend **duplicate** for v1 (simpler scope; refactor later if both stay long-term).
4. **OAuth callback route consistency** — crm + linkedin OAuth callbacks land at different routes (per `crm/page.tsx` docstring vs `linkedin/page.tsx`). Verify both use the same callback-handler pattern; ATLAS B2.5 may want to standardize.
5. **Progress indicator across 5 demo steps** — does a step-N-of-5 indicator render consistently across step-1..5? Spot-check before A dispatches; if absent, add as a shared atom in Chunk A pre-work.

### Cross-cutting prerequisites (already flagged in Phase 4 main audit)

- ATLAS B1 sidebar consolidation must land first (assumed in flight).
- Phase 3 Item 4 section-label utility must land first (consumed by all 9 routes).
- `globals.css` cream/amber/Playfair tokens already resolved via A1 codemod (per recent commit history).

### Out of scope for this chunking spec

- Per-step copy review (BDR persona name, agency-name placeholders, button text wording).
- Backend API contract changes (none in scope).
- Onboarding analytics / funnel-step tracking (separate dispatch if needed).
- Mobile-only redesign work (covered by general responsive audit).

---

*This document is research-only. No code edits. Generated 2026-04-30 on `aiden/phase4-onboarding-chunking` branch.*
