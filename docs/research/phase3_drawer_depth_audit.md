# Phase 3 Drawer 7-Section Depth Audit

Read-only research. Per-section gap report comparing `/demo`'s prospect briefing drawer (7 content sections, 8th hidden inside section 7's combined block) against React's `ProspectDrawer.tsx` + `LeadDetailModal.tsx` + `ProspectDetailCard.tsx` + `VRGradePopover.tsx`.

Goal: scope-accurate v2 backlog for Phase 3 Item 7 (deferred per A3 lesson — backend not ready).

**Reference paths**

- `/demo` drawer template: `/home/elliotbot/clawd/Agency_OS/frontend/landing/demo/index.html:1298-1369` (`openDrawer` function)
- `/demo` VR_EXPLAIN content: `index.html:1376-1419` (the 90 text blocks: 6 categories × 5 grades × 3 sub-sections)
- React drawer: `frontend/components/dashboard/ProspectDrawer.tsx` (256 lines)
- React inline briefing card: `frontend/components/dashboard/ProspectDetailCard.tsx` (319 lines)
- React legacy modal (Tier 2 deletion candidate): `frontend/components/dashboard/LeadDetailModal.tsx` (1045 lines)
- React VR popover: `frontend/components/dashboard/VRGradePopover.tsx` (~200 lines)

**Branch**: `aiden/phase3-drawer-depth-audit` (off `origin/main`). No code edits — doc-only.

## Table of contents

1. [Section 1 — Business meta](#section-1--business-meta)
2. [Section 2 — Vulnerability strip + popovers](#section-2--vulnerability-strip--popovers)
3. [Section 3 — Outreach timeline](#section-3--outreach-timeline)
4. [Section 4 — Recommended angle (opening hook)](#section-4--recommended-angle-opening-hook)
5. [Section 5 — Discovery questions](#section-5--discovery-questions)
6. [Section 6 — Common objections + responses](#section-6--common-objections--responses)
7. [Section 7 — Close options + pricing range + competitors](#section-7--close-options--pricing-range--competitors)

[Closing summary](#closing-summary) · [Backend deps](#backend-dependency-summary) · [Content authoring deps](#content-authoring-dependency-summary) · [Recommended v2 scope order](#recommended-v2-scope-order)

---

## Section 1 — Business meta

**/demo source:** `index.html:1308-1320` (the `<div class="bf-section">` containing 8 `bf-kv` pairs).

**/demo content depth (8 fields):**

| # | Field | Source | Notes |
|---|---|---|---|
| 1 | Domain | `p.domain` | Plain text |
| 2 | GMB category | `p.gmb_category` | Plain text |
| 3 | Employees | `staffRange(p.staff)` | Tooltip `title="Source: LinkedIn company page"`; suffix `(LinkedIn)` |
| 4 | Established | `p.est` (year) | Tooltip `title="Source: ABN registry"`; prefix `ABN registered` |
| 5 | DFS organic ETV | `p.dfs_organic_etv` | Prefix `$`, suffix `/mo` |
| 6 | Domain rank | `p.domain_rank` | Suffix `/100` |
| 7 | Backlinks | `p.backlinks_count` | Plain integer |
| 8 | Status | `p.status` | Plain text |

**React equivalent:** `frontend/components/dashboard/ProspectDrawer.tsx:122-130` — section labelled "Enrichment".

**React content depth (5 fields):**

| # | Field | Source | Notes |
|---|---|---|---|
| 1 | ABN | `prospect.enrichment.abn` | Plain text |
| 2 | Industry | `prospect.enrichment.industry` | Plain text |
| 3 | Staff | `prospect.enrichment.employeeCount` | Stringified count |
| 4 | Website | `prospect.enrichment.website` | Linked anchor |
| 5 | Location | `prospect.enrichment.location` | Plain text |

**Gap analysis:**

- **Missing fields (5 of 8):** GMB category, Established (ABN year), DFS organic ETV, Domain rank, Backlinks count, Status.
- **Missing sub-elements:** No source-of-truth tooltips on Employees / Established (demo has `title=""` attrs). No `(LinkedIn)` / `ABN registered` prefix-suffix decoration.
- **Field-level data dependencies (backend):**
  - `gmb_category` — backend already exposes via `business_universe.gmb_category` (see C5 audit). Hook surface needed: extend `useProspectDetail`.
  - `dfs_organic_etv` — column exists per migration 023; needs hook field.
  - `domain_rank` — column exists; hook field.
  - `backlinks_count` — column exists; hook field.
  - `status` — `business_universe.status` (text) exists per migration 086; hook field.
  - `est` (ABN registration year) — derive from `business_universe.registration_date` per migration 086.
- **Field-level content dependencies (authoring):** None — all fields are derived from existing data.

**Estimated v2 effort:** **M** (30 min – 2 hr). 5 hook-field additions + 8 KV row renders + 2 tooltips. No backend SQL needed (all columns exist); just hook + UI.

---

## Section 2 — Vulnerability strip + popovers

**/demo source:** `index.html:1322-1328` (strip) + `index.html:1376-1419` (VR_EXPLAIN content) + `index.html:1426-1455` (`showVRPopover` function).

**/demo content depth:**

- **Strip:** 6 graded categories, each rendering a clickable A–F letter chip + name label.
  - Categories: `website`, `seo`, `reviews`, `ads`, `social`, `content`.
  - Source: `p.vulnGrades[category]` returning one of `A` / `B` / `C` / `D` / `F` (5 grade levels — note: no E).
  - Click → `showVRPopover(p.id, category, event)` opens 3-section explanation.
- **Header narrative:** `p.vulnerability` (free-form text above the strip) + computed overall grade (`overallVulnGrade(p.vulnGrades)`).
- **VR_EXPLAIN content (90 text blocks):**
  - 6 categories × 5 grades × 3 sub-sections (Data / Strengths / Improvements) = **90 distinct text blocks**, all literal strings in `VR_EXPLAIN` object (`index.html:1376-1419`).
  - Sample: `VR_EXPLAIN.website.A.data` = "SSL active, mobile responsive, PageSpeed 82/100, structured data present."
  - Each grade carries: `data` (objective findings), `strengths`, `improvements` — 3 paragraphs per grade per category.

**React equivalent:** Two surfaces:

1. `frontend/components/dashboard/ProspectDrawer.tsx:87-94` — header carries `<VRGradePopover>` for the **overall** grade only. No 6-category strip.
2. `frontend/components/dashboard/ProspectDetailCard.tsx:131-167` — `GradeStrip` renders 6-category strip (`website / seo / reviews / ads / social / content`) BUT **without click popovers**.

**React VR popover content (`VRGradePopover.tsx:70-152`):**

- 4-axis sub-score taxonomy: **Intent / Affordability / Authority / Timing** — completely different from `/demo`'s 6-category taxonomy.
- Strengths list shown only when grade is `A` (line 126-127).
- Improvements list shown only when grade is `D` or `F` (line 128-129).
- Evidence list (max 3 items) appended if `evidence[]` provided.

**Gap analysis:**

- **Taxonomy mismatch:** React's VR axes (intent/affordability/authority/timing) are NOT the demo axes (website/seo/reviews/ads/social/content). They reflect different scoring philosophies — React's are buyer-readiness signals; demo's are agency-service-line vulnerabilities. **Decision needed**: which taxonomy is canonical going forward? The demo categories map directly to agency service offerings (website, SEO, reviews, ads, social, content) which is more useful for the BDR pitch surface. **Recommend adopting the demo taxonomy** as v2 standard.
- **Missing sub-elements:**
  - No strip in `ProspectDrawer.tsx` (the strip lives in `ProspectDetailCard.tsx`, which is a separate inline card, not the drawer).
  - No per-category clickable popover in either surface (`VRGradePopover` is header-level only).
  - No `Data / Strengths / Improvements` 3-section breakdown per category.
  - No `p.vulnerability` free-form narrative paragraph above the strip.
- **Field-level data dependencies (backend):**
  - `vulnerability` (text narrative) — new column on `business_universe` OR `prospects` table. Likely `vulnerability_summary text`.
  - `vulnGrades` JSONB `{ website, seo, reviews, ads, social, content }` of A-F values — new column. The closest existing field is `business_universe.stage_metrics` JSONB; could nest under `stage_metrics.vr_grades`.
- **Field-level content dependencies (authoring):**
  - **90 text blocks** (6 × 5 × 3) for the VR_EXPLAIN dictionary, OR a generation pipeline that outputs them per prospect.
  - Two paths:
    - **Static path** — adopt `/demo`'s VR_EXPLAIN as canonical strings (90 blocks, hand-curated). Same text shown for every grade-A website regardless of which prospect. Deterministic.
    - **Dynamic path** — Gemini (or similar) generates per-prospect `data / strengths / improvements` text from the prospect's actual signal data. More accurate but spendy.

**Estimated v2 effort:** **L** (2 hr +). Largest gap in the doc.

- Static path: ~3 hr (90 block authoring + popover wiring + strip refactor + drawer swap) — content authoring is the long-pole.
- Dynamic path: ~5–8 hr (LLM prompt design + caching + popover wiring + drawer swap), AUD spend depends on Gemini cost per prospect.

---

## Section 3 — Outreach timeline

**/demo source:** `index.html:1330-1333`.

**/demo content depth:**

- Header line: `Outreach timeline` + event count (e.g. ` 12 events`).
- Body: `renderUnifiedTimeline(p, 'ctd')` — calls a unified renderer with chronological events (replies / meetings / signals / cadence touches).
- Event count fed by `unifiedTimeline(p)` (length).

**React equivalent:** `frontend/components/dashboard/ProspectDrawer.tsx:131-134` — `<Section title="Outreach timeline"><OutreachTimeline events={timeline} isLoading={isLoading} /></Section>`. Hook: `useOutreachTimeline(prospect)`.

**React content depth:**

- `OutreachTimeline` component renders chronological events (icon + label + detail per event).
- No event-count badge in the section header.

**Gap analysis:**

- **Missing sub-elements:**
  - Event count badge after the header text (demo: `${evs.length} events`).
- **Field-level data dependencies (backend):** None — `useOutreachTimeline` already returns the event list; the count is a `length` operation client-side.
- **Field-level content dependencies (authoring):** None.

**Estimated v2 effort:** **S** (under 30 min). One template-string edit on the section header.

**Verdict:** Close to parity. Single-line polish.

---

## Section 4 — Recommended angle (opening hook)

**/demo source:** `index.html:1335-1339`.

**/demo content depth:**

- Header: `Recommended angle`.
- AI badge: `<div class="bf-ai">✨ AI-generated briefing · verify before use</div>` (caveat + sparkle icon).
- Body: `p.openingHook` — single hook paragraph.

**React equivalent:** **NOT IMPLEMENTED.** Neither `ProspectDrawer.tsx` nor `ProspectDetailCard.tsx` carries an opening-hook section. `LeadDetailModal.tsx` has unrelated transcript/email content.

**Gap analysis:**

- **Missing fields:** Entire section.
- **Missing sub-elements:** AI-generated banner + opening hook paragraph.
- **Field-level data dependencies (backend):**
  - `opening_hook text` column on `business_universe` or a sibling `prospect_briefing` table. Likely `text` type, ~200-400 char paragraph.
- **Field-level content dependencies (authoring):**
  - Per-prospect hook generation (LLM-pipeline) OR per-vertical templated hooks (e.g. dental → "I noticed your booking widget hasn't been updated since…").
  - Estimated input cost: 1 prompt + 1 completion per prospect × N prospects. With Gemini Pro ~$0.0001/prospect for short hooks; Sonnet ~$0.001.

**Estimated v2 effort:** **S** (under 30 min) for the UI + backend column. **L** if the generation pipeline is in scope.

---

## Section 5 — Discovery questions

**/demo source:** `index.html:1341-1344`.

**/demo content depth:**

- Header: `Discovery questions`.
- Body: `<ul>` of strings from `p.discoveryQuestions[]` array.
- Sample (from prospect data — see `index.html:893-1061` records): array of 3 questions per prospect, e.g. `["Why did you pause Google Ads — was it the cost or the results?", "Have you seen patient numbers affected?", ...]`.

**React equivalent:** **NOT IMPLEMENTED.**

**Gap analysis:**

- **Missing fields:** Entire section.
- **Missing sub-elements:** None beyond the section.
- **Field-level data dependencies (backend):**
  - `discovery_questions text[]` array column OR JSONB list. ~3-5 strings per prospect.
- **Field-level content dependencies (authoring):**
  - Per-prospect question generation. Same path as Section 4 (templated vs LLM-generated).
  - Static-template path: per-vertical question banks (dental, plumbing, legal, accounting, fitness — 5 verticals × 5 questions = 25 strings). Lowest spend.
  - LLM path: ~3 questions × generation cost per prospect.

**Estimated v2 effort:** **S** (under 30 min) for UI + column. **M** (30 min – 2 hr) if static per-vertical question banks added. **L** if LLM pipeline.

---

## Section 6 — Common objections + responses

**/demo source:** `index.html:1346-1349`.

**/demo content depth:**

- Header: `Common objections`.
- Body: array of `{obj, response}` pairs from `p.objections[]`. Each pair renders as:
  - `<div class="obj-q">${o.obj}</div>` — the objection (italicised in CSS).
  - `<div class="obj-a">${o.response}</div>` — the recommended response.
- Sample: `{obj: "We're already using XYZ", response: "Got it — most clients we win were using XYZ first..."}`. ~3 pairs per prospect.

**React equivalent:** **NOT IMPLEMENTED.**

**Gap analysis:**

- **Missing fields:** Entire section.
- **Missing sub-elements:** Pairs (objection + response).
- **Field-level data dependencies (backend):**
  - `objections jsonb` array of `{obj, response}` objects. Or two parallel text[] arrays.
- **Field-level content dependencies (authoring):**
  - Per-vertical objection bank: most BDR objections recur ("we already have someone", "no budget", "wrong time of year") so 5 verticals × 5 common objections × 1 response each = 25 pairs. Static authoring path is feasible.
  - LLM-generated per-prospect path same as above.

**Estimated v2 effort:** **S** (under 30 min) UI + column. **M** if static vertical bank authored.

---

## Section 7 — Close options + pricing range + competitors

**/demo source:** `index.html:1351-1361` (combined block — close options + pricing + competitors). Dispatch numbers this as one section but the markup uses 2 `bf-section` blocks (lines 1351-1356 close+pricing, 1358-1361 competitors).

**/demo content depth:**

- **Sub-section 7a — Close options + pricing:**
  - Header: `Close options`.
  - `<ul>` of strings from `p.closeOptions[]` array.
  - Caption (mono uppercase): `Your service pricing — from your agency rate card`.
  - Pricing display: `<div>` (Playfair Display 20px bold) showing `p.pricingRange` (e.g. `"$2,500 - $5,000/mo"`).
- **Sub-section 7b — Competitors:**
  - Header: `Also ranking for your keywords`.
  - `<ul>` of strings from `p.competitors[]` array.

**React equivalent:** **NOT IMPLEMENTED.**

**Gap analysis:**

- **Missing fields:** Entire combined section.
- **Missing sub-elements:**
  - Close options list.
  - Pricing range serif display.
  - Competitors list.
  - "Also ranking for your keywords" framing on the competitors header.
- **Field-level data dependencies (backend):**
  - `close_options text[]` (or JSONB).
  - `pricing_range text` — agency rate card; per-tier or per-vertical.
  - `competitors text[]` (domain strings) OR derivable from existing DFS competitors data (see `paid_enrichment.py` STEP 3 intelligence path which already fetches `competitors_top3` per domain — that's the source).
- **Field-level content dependencies (authoring):**
  - `pricing_range` per agency profile — likely a static config (e.g. `agency_service_profile.pricing_tiers`).
  - `close_options[]` per vertical — 3-5 close phrasings per vertical (~25 total).

**Estimated v2 effort:** **M** (30 min – 2 hr). 3 list-render blocks + 2 backend columns + 1 already-existing field (competitors). Pricing display is trivial typography. Largest cost is the close-options content authoring.

---

## Closing summary

### Section parity tally

| Section | /demo depth | React depth | Verdict |
|---|---|---|---|
| 1. Business meta | 8 fields | 5 fields | **PARTIAL** — 3 fields missing + 2 source tooltips |
| 2. Vulnerability + popovers | 6-cat strip + 90 text blocks | 4-axis taxonomy mismatch + no per-cat popover | **MAJOR GAP** — taxonomy disagreement + 90 text blocks unauthored |
| 3. Outreach timeline | events + count badge | events without count badge | **NEAR PARITY** — single template edit |
| 4. Recommended angle | AI badge + hook paragraph | not implemented | **MISSING** |
| 5. Discovery questions | UL list (3-5 per prospect) | not implemented | **MISSING** |
| 6. Common objections | obj/response pairs (~3 per prospect) | not implemented | **MISSING** |
| 7. Close + pricing + competitors | UL + serif pricing + UL | not implemented | **MISSING** |

**Summary:** **0 sections at parity, 2 partial (1 + 3), 5 missing.** Out of 7 dispatch sections, only the timeline section is close to parity.

### Total field count delta

| Surface | /demo | React | Delta |
|---|---:|---:|---:|
| Business meta fields | 8 | 5 | **+3 needed** |
| VR strip categories | 6 (website/seo/reviews/ads/social/content) | 6 (in `ProspectDetailCard`) but **wrong popover taxonomy** in drawer | mismatch |
| VR popover sub-sections per grade | 3 (Data/Strengths/Improvements) | 2 (Strengths only on A; Improvements only on D/F) | **+1-2 always-on** |
| VR_EXPLAIN content blocks | **90** literal strings | 0 | **+90 to author** |
| Discovery questions | 3-5 per prospect | 0 | **N×3-5 needed** |
| Objections | ~3 per prospect | 0 | **N×3 needed** |
| Close options | ~3 per prospect | 0 | **N×3 needed** |
| Pricing range | 1 string per agency | 0 | **+1 per agency** |
| Competitors | 3 per prospect | 0 (but existing DFS pipeline has top-3) | **wire existing** |
| Opening hook | 1 paragraph per prospect | 0 | **+1 per prospect** |

### Backend dependency summary

New backend-exposed fields (column or hook):

1. `business_universe.gmb_category` — exists, needs hook surface.
2. `business_universe.dfs_organic_etv` — exists (migration 023), needs hook surface.
3. `business_universe.domain_rank` — exists, needs hook surface.
4. `business_universe.backlinks_count` — exists (migration 031), needs hook surface.
5. `business_universe.status` — exists (migration 086), needs hook surface.
6. `business_universe.registration_date` — exists, needs hook surface (renders as `est` year).
7. `business_universe.vulnerability_summary text` — **NEW column** (or `stage_metrics.vulnerability` JSONB key).
8. `stage_metrics.vr_grades` JSONB `{website, seo, reviews, ads, social, content: A|B|C|D|F}` — **NEW JSONB key**, no schema migration if `stage_metrics` is the host.
9. `business_universe.opening_hook text` — **NEW column** (~400 char paragraph).
10. `business_universe.discovery_questions text[]` — **NEW column** (~3-5 strings).
11. `business_universe.objections jsonb` — **NEW column** (array of `{obj, response}`).
12. `business_universe.close_options text[]` — **NEW column** (~3-5 strings).
13. `agency_service_profile.pricing_range text` — **NEW column** (per-agency, not per-prospect).
14. `business_universe.competitors_top3` — **EXISTS** per `paid_enrichment.py:296` (`competitors_top3` updated by intelligence pipeline). Just needs hook surface.

**Net new columns needed: 6** (items 7-13 above; item 13 is on `agency_service_profile`, the rest on `business_universe`). All others reuse existing storage.

### Content authoring dependency summary

Static-path content authoring required (assuming we adopt the demo's deterministic-text approach over LLM-per-prospect):

1. **VR_EXPLAIN dictionary**: 6 categories × 5 grades × 3 sub-sections = **90 text blocks** (Data / Strengths / Improvements). The `/demo` already authored these in full (`index.html:1376-1419`); copy-paste is the path of least resistance.
2. **Discovery questions per vertical**: 5 verticals × ~5 questions = **25 text blocks**.
3. **Objection responses per vertical**: 5 verticals × ~5 obj/resp pairs = **50 text blocks** (25 objections + 25 responses).
4. **Close options per vertical**: 5 verticals × ~3 closes = **15 text blocks**.
5. **Pricing range** per agency tier: ~3 strings (Spark / Ignition / Velocity).
6. **Opening hook** — has to be per-prospect (LLM or templated).

**Total static content blocks to author: ~183** (90 VR + 25 questions + 50 obj/resp + 15 closes + 3 pricing). The 90 VR blocks already exist verbatim in `/demo`.

LLM-path alternative for opening hooks + questions + objections would replace 95+ of these with per-prospect generation calls (cost: ~$0.001-$0.003 per prospect with Gemini Pro on short generation).

### Recommended v2 scope order

When v2 dispatch fires, build in this order to minimise rework:

1. **Section 3 — Outreach timeline event-count badge** (S; near parity; 1-line polish; lands instantly).
2. **Section 1 — Business meta** (M; 5 hook fields + 8 KV rows; all backend data exists; no content authoring needed). Highest ROI because all data is already in BU.
3. **Section 2a — VR strip in drawer** (S–M; reuse `GradeStrip` from `ProspectDetailCard.tsx:131-167` inside `ProspectDrawer`). Don't tackle popover content yet.
4. **Sections 4 / 5 / 6 / 7 — Static-template content + UI** (M-each; combined L). Can land as one PR if the per-vertical content banks are authored together.
5. **Section 2b — VR_EXPLAIN popovers** (L; 90 text blocks + popover wiring). Lift the demo strings verbatim; biggest content-authoring lift but no thinking required since `/demo` already wrote them.
6. **Sections 4 / 5 / 6 — LLM personalisation** (deferred to a separate dispatch). Replace static templates with per-prospect generation if/when budget approves.

### Cross-cutting decisions needed before v2 dispatch

1. **VR taxonomy**: adopt `/demo`'s 6-category service-line model (website/seo/reviews/ads/social/content) over React's 4-axis buyer-readiness model (intent/affordability/authority/timing)? **Recommend yes** — service-line model is what the BDR pitches against.
2. **Static vs LLM-generated content**: opening hooks + questions + objections — pick a path before scoping the dispatch.
3. **Storage choice**: new `business_universe` columns (6 net new) vs nesting under `stage_metrics` JSONB? Trade-off is queryability vs schema churn.
4. **`LeadDetailModal.tsx` retirement**: once drawer reaches parity, drop the modal (Tier 2 deletion in cleanup map). Drawer becomes single source of truth for prospect detail.

### Out of scope for this audit

- Visual design tokens (covered in Phase 3 Item 4 inventory).
- Mobile responsiveness of the drawer (different dispatch).
- Drawer animation / accessibility audit.
- Critic scores per channel (Phase 3 Item 5, separate audit).

---

*This document is research-only. No code edits. Generated 2026-04-30 on `aiden/phase3-drawer-depth-audit` branch.*
