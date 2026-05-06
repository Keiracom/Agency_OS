# SKILL: Seek Hiring Acceleration — Capacity-Trigger Discovery

**Purpose:** F2.2 alternative discovery model — surface AU SMBs with hiring spikes (≥5 new postings in 30d) on Seek.com.au. Hiring-spike = capacity buying signal (HR / payroll / comms / management tools / marketing budget). Net-new discovery feed; complements AusTender (revenue trigger) and ASIC (formation trigger) with a *capacity* trigger.
**Status:** ⚠️ Apify token confirmation pending. Skill spec ships ahead of credential clarification.
**Source:** Seek.com.au scraped via Apify actor `websift/seek-job-scraper`. Seek itself does not publish a public job-search API.
**Credentials Required:** `APIFY_API_TOKEN` (existing Apify subscription may already cover this actor — Dave-action to confirm or provision separately).
**Cost gate:** ~$0.50 AUD per 1,000 postings scraped via Apify. Daily cron at ~5K postings/day = ~$2.50 AUD/day = **~$75 AUD/month**.

---

## At-a-Glance (Anthropic tool-doc template — 6-vector hardened)

**What:** Daily Apify run scrapes recent Seek AU job postings. Aggregator groups by `companyName`, filters to companies with ≥5 new postings in 30d window (configurable), runs the **two mandatory blocklists** (recruitment agencies + marketing/creative agencies), then resolves company → domain → ABN match → BU candidate row.

**Why this skill exists:**
- F2.2 research found Seek captures ~70% of AU job market vs LinkedIn ~30%. Hiring-spike detection here is more representative than LinkedIn — and avoids the LinkedIn ToS risk (ASLR + AU contract law).
- ~250K active postings on Seek AU; spike-companies (≥5 new postings/30d) ≈ 5–10% of active employers ≈ **3–5K candidates/month**. Highest volume of any F2.2 model at lowest cost.
- Capacity signal complements revenue (AusTender) and formation (ASIC) — three orthogonal triggers feeding the same pipeline.

**When to use:**
- Daily cron at 02:00 AEST (low Apify queue) scraping the last 24h of postings, then re-aggregating against the rolling 30d window.
- Weekly aggregator-only re-run (no fresh scrape) to recompute spikes when blocklist tuning changes.
- Backfill: pull last 30d of postings on first run to seed the BU; subsequent runs are deltas.

**When NOT to use:**
- NOT for one-off prospect lookups — Apify run cost + scrape latency makes ad-hoc queries wasteful. For "is X hiring?" use a different tool.
- NOT before both blocklists are loaded and verified (recruitment + marketing/creative). See Two Blocklists section. Violation: outbound to a Keiracom-client agency = brand damage.
- NOT during Seek-scrape-block windows — Seek's anti-bot defences occasionally rate-limit Apify; tolerate 30–60 minute gaps.
- NOT before `APIFY_API_TOKEN` is verified live (call `actor.run` health endpoint with a 1-posting input; non-200 = block all calls).

**Caveats:**
- **ToS risk is real but bounded.** Seek's ToS prohibits scraping; Apify routes through residential proxies + UA rotation. AU contract-law enforcement against Apify-style scrapers is rare but non-zero. Use with operator awareness.
- **Company → domain resolution is lossy.** Seek lists `companyName` (free-text) and sometimes a `companyId`. Resolving "Acme Marketing Pty Ltd" → `acme.com.au` is heuristic (search + LinkedIn-company-page lookup + ABN-name match). Expect 60–80% resolution rate; the rest insert as `domain = NULL` for downstream resolution worker.
- **Recruitment-agency contamination.** Hays / Robert Half / Adecco / Talent International / Randstad etc. post on behalf of OTHER companies. Their `companyName` value is the agency, not the underlying employer. Without filtering, half the spike list will be recruitment firms. **Blocklist 1 (mandatory).**
- **Keiracom-client contamination.** AU marketing / creative / advertising agencies are Keiracom's intended customers, not prospects. Outbound to them = client brand damage. **Blocklist 2 (mandatory).**
- **Spike threshold tuning.** Default 5+ postings in 30d. Lower threshold = more candidates but higher noise (consultancies post-as-individuals). Higher threshold = fewer but higher-quality spikes.
- **Posting freshness.** A "spike" can include re-posted listings (failed first hire → repost). Heuristic dedupe on `(companyName, jobTitle, location)` reduces but doesn't eliminate.
- **Seek doesn't publish ABN.** Resolving Seek `companyName` → ABN requires a separate ASIC name-search call OR fuzzy ABN-match against existing BU. Adds a step vs AusTender (ABN inline) and ASIC (ABN inline).

**Returns:**
- Spike event: `{company_name, postings_30d, top_roles: [str], last_post_at, locations: [str], company_url: str | None, resolved_domain: str | None, resolved_abn: str | None}`.
- BU mapping target: `display_name`, `domain` (if resolved), `abn` (if resolved); `category_baselines.seek = {postings_30d, top_roles, last_post_at, hire_velocity}` jsonb payload.

---

## Two Blocklists (MANDATORY — MAX directive 2026-05-06)

The Seek discovery flow MUST run two filter passes before any BU INSERT. Either match = drop record + log reason.

### Blocklist 1 — Recruitment Agencies

**Why:** Recruitment agencies post jobs ON BEHALF OF other companies. Their `companyName` is the recruiter, not the employer. A "5+ postings/30d" spike from Hays = Hays' workload, not a real hiring-company signal. Outbound to Hays as a "growing dental practice" prospect is incoherent.

**Detection layers (any single match = drop):**

1. **Company-name keyword regex** (case-insensitive):
   ```
   \b(recruit(ment|ing|er|ers)|talent|staffing|placements?|labour\s+hire|
     human\s+resources?|headhunt(er|ing)|search\s+(firm|partners)|
     consultants?\s+(group|partners)|hr\s+(group|consulting))\b
   ```

2. **Known-recruiter domain blocklist** (seed list, Dave-tunable):
   ```
   hays.com.au, roberthalf.com.au, adecco.com.au, talent-international.com.au,
   randstad.com.au, michaelpage.com.au, hudson.com, peoplebank.com.au,
   chandlermacleod.com, robertwalters.com.au, kelly.com.au, manpowergroup.com.au,
   springprofessional.com.au, designandbuild.com.au, beaumonts.com.au,
   six-degrees.com.au, sustainabletalent.com.au, mars-recruitment.com.au,
   six-people.com, talenza.com.au, davidsonwp.com, jacksonstone.com.au
   ```
   **Maintained in `src/config/seek_blocklists.py` as `RECRUITMENT_DOMAIN_BLOCKLIST`.**

3. **ANZSIC code 7211** (Employment Placement and Recruitment Services) — when ABN is resolved.

4. **`companyName` length heuristic** — recruitment agencies often have generic names ("ABC Talent", "XYZ Search Partners"); when posting volume > 50/30d AND ABN unresolved, flag for human review rather than auto-include. Volume threshold tunable.

### Blocklist 2 — Marketing / Creative / Advertising Agencies (Keiracom clients, not prospects)

**Why:** AU marketing, creative, advertising, branding, design, digital agencies are Keiracom's intended customer segment OR future clients. Outbound prospecting them as if they were SMBs would damage Keiracom's positioning AND mistake them for the wrong ICP. Per pre-revenue reality (zero clients today): we treat every AU marketing agency as a potential customer, not a prospect.

**Detection layers (any single match = drop):**

1. **Company-name keyword regex** (case-insensitive):
   ```
   \b(marketing|advertising|creative|branding|brand\s+(agency|consult)|
     digital\s+(agency|marketing|consult)|content\s+(agency|studio)|
     design\s+(agency|studio)|media\s+(agency|consult|buying)|
     pr\s+(agency|consult)|public\s+relations|growth\s+(agency|consult)|
     performance\s+marketing|seo\s+(agency|consult)|
     adtech|martech|social\s+(media\s+)?agency|video\s+(agency|production)|
     web\s+(agency|design)|ux\s+(agency|consult))\b
   ```

2. **Known-agency domain blocklist** (seed list, Dave + ELLIOT tunable):
   - Maintained in `src/config/seek_blocklists.py` as `MARKETING_DOMAIN_BLOCKLIST`.
   - Seed entries: any domain referenced in `business_universe` with `gmb_category ILIKE '%agency%'` OR `gmb_category ILIKE '%marketing%'` OR matched in our agency-discovery research lists (PRs #565, #567).

3. **ANZSIC codes** when ABN is resolved:
   - `6940` Advertising Services
   - `6920` Market Research and Statistical Services
   - `5910` Internet Publishing and Broadcasting
   - `8531` Photographic Services (when combined with creative-keyword match)

4. **GMB-category cross-reference** — if `companyName` resolves to a domain already in BU with `gmb_category` matching agency keywords, treat as confirmed agency = drop.

### Blocklist Override

`--allow-agencies` CLI flag for Dave-only research runs. Logs an `[OVERRIDE]` warning per matched record. Never the default. Never enabled in cron.

### Both blocklists must be present, loaded, and verified before any production scrape lands in BU. Connector PR cannot land without both.

---

## Input Parameter Constraints (Poka-Yoke)

**Daily Apify scrape:**
- `start_urls: list[str]` — required. Seek search URLs covering target locations + categories.
- `max_items_per_category: int` — required. Default 5000. Reject if >50000 (Apify cost cap).
- `country: 'AU'` — hardcoded. Seek operates in AU + NZ; this skill is AU-only.
- `freshness_days: int` — optional. Default 1 (last 24h). Reject if >30 (older postings are stale).

**Aggregator + spike detection:**
- `spike_threshold: int` — default 5 postings/30d. Configurable per-vertical.
- `window_days: int` — default 30. Reject if outside [7, 60].
- `min_postings_in_window: int` — same as `spike_threshold`; renamed alias for downstream clarity.

**Blocklist enforcement:**
- `bypass_blocklists: bool` — default `False`. Setting to `True` requires `--allow-agencies` CLI flag AND human confirmation prompt. Never default-on. Never set in scheduled jobs.

**ABN-resolution:**
- `companyName` must pass through `src/pipeline/abn_match.py` (the shared helper refactor — prerequisite). Failed matches insert as `abn = NULL`, `acn = NULL`, with a flag for the domain-resolution backlog worker.

**Never pass:**
- A non-AU `country` parameter — out of scope.
- A scrape with `bypass_blocklists=True` AND `output_to_bu=True` simultaneously (would write contaminated rows). Wrapper rejects this combination.
- Officer / contact-person fields scraped from Seek listings (rare but present in description text) — privacy + bloat. Drop at parse time.

---

## Input Examples (covers edge cases)

**Daily ingestion of yesterday's postings, dental + trades + allied health:**
```json
{
  "start_urls": [
    "https://www.seek.com.au/dental-jobs",
    "https://www.seek.com.au/construction-jobs",
    "https://www.seek.com.au/healthcare-medical-jobs"
  ],
  "max_items_per_category": 5000,
  "freshness_days": 1,
  "spike_threshold": 5
}
```

**Backfill 30d on first run:**
```json
{
  "start_urls": ["..."],
  "max_items_per_category": 50000,
  "freshness_days": 30,
  "spike_threshold": 5
}
```

**Dave-only research run (override blocklists, NO BU write):**
```bash
python scripts/ingest_seek.py --allow-agencies --no-output --dry-run
# Logs every matched company including filtered ones for blocklist tuning
```

---

## Response Trimming (what to persist, what to drop)

**Apify scrape output — PERSIST per posting (raw):**
- `companyName`, `companyId` (when present)
- `jobTitle`, `postedDate`
- `location` (city + state)
- `jobUrl` (audit only — drop after aggregation)

**Apify scrape output — DROP per posting:**
- Full job description (free-text, can be 10K+ chars per posting)
- Salary range (out of scope; not used for spike calc)
- Application URLs / referral codes
- Logo / image URLs
- Bullet-list `requirements` arrays (parser-dependent, low signal value)

**Aggregated spike event — PERSIST:**
- `company_name` → `display_name`
- `postings_30d` → `category_baselines.seek.postings_30d`
- `top_roles[:5]` → `category_baselines.seek.top_roles` (truncate to 5; rest is noise)
- `last_post_at` → `category_baselines.seek.last_post_at`
- `locations[:3]` → `category_baselines.seek.locations`
- `hire_velocity` (postings_30d / 30) → `category_baselines.seek.hire_velocity` (per-day rate)
- `resolved_domain` → `domain` (only when resolution confidence ≥0.8)
- `resolved_abn` → `abn` (only when name-match confidence ≥0.9)
- `abn_match_method` ('exact' | 'fuzzy' | 'unresolved') → `category_baselines.seek.abn_match_method`

**Aggregated spike event — DROP:**
- Per-job `jobUrl` arrays after aggregation
- Description-text aggregations (privacy + bloat)
- Salary-range distributions (out of scope)

---

## API Endpoints (Apify)

| Endpoint | Method | Purpose |
|---|---|---|
| `https://api.apify.com/v2/acts/websift~seek-job-scraper/runs` | POST | Start a sync run with input JSON. |
| `https://api.apify.com/v2/datasets/{datasetId}/items` | GET | Fetch dataset items after run completes. |
| `https://api.apify.com/v2/actor-runs/{runId}` | GET | Poll run status (RUNNING / SUCCEEDED / FAILED / ABORTED). |
| `https://api.apify.com/v2/key-value-stores/{storeId}/records` | GET | Optional — fetch run logs for debugging. |

**Base URL:** `https://api.apify.com/v2/`
**Auth:** `Authorization: Bearer {APIFY_API_TOKEN}` header.
**Format:** JSON.

---

## Seek → BU field mapping

| Source field | BU column / jsonb path |
|---|---|
| Aggregated `company_name` | `display_name` (INSERT only, never overwrite) |
| Resolved `domain` (confidence ≥0.8) | `domain` |
| Resolved `abn` (confidence ≥0.9) | `abn` (after `abn_match.py` canonicalisation) |
| `postings_30d` | `category_baselines.seek.postings_30d` (jsonb) |
| `top_roles[:5]` | `category_baselines.seek.top_roles` (jsonb) |
| `last_post_at` | `category_baselines.seek.last_post_at` (jsonb) |
| `hire_velocity` | `category_baselines.seek.hire_velocity` (jsonb) |
| Pipeline routing | `discovery_source = 'seek_hiring'`, `signal_source = 'seek_hiring'`, `signal_checked_at = NOW()`, `pipeline_stage = 0` |

**No schema migration in v1.** All fields map to existing BU columns or `category_baselines` jsonb. (ASIC PR #584 already adds `acn` typed column for the rare case Seek resolution surfaces an ACN.)

---

## Error Handling (Category → Action mapping)

| HTTP / Condition | Category | Action |
|---|---|---|
| Apify run SUCCEEDED | success | Fetch dataset → aggregate → blocklist → resolve → BU. |
| Apify run FAILED | transient | Re-run once after 5 minutes. If still failing, defer batch to next-day cron. |
| Apify run ABORTED | config_error | Investigate Apify quota / billing. Alert via Slack. |
| Apify 401 | config_error | API token invalid. Disable cron + alert. |
| Apify 429 | rate_limit | Apify shouldn't 429 our own actor; if seen, exponential backoff. |
| Seek anti-bot 403 (in dataset items) | upstream | Apify retries internally; if persistent, defer to next run. |
| Blocklist 1 match | filter | Drop + log `seek_blocklist=recruitment` reason for the company. Never write to BU. |
| Blocklist 2 match | filter | Drop + log `seek_blocklist=marketing_agency` reason. Never write to BU. |
| Domain resolution confidence <0.8 | partial_success | Insert with `domain = NULL`, queue for domain-resolution backlog worker. |
| ABN resolution confidence <0.9 | partial_success | Insert with `abn = NULL`, queue for ABN-resolution backlog worker. |
| Both resolutions fail | filter | Insert with `display_name + category_baselines.seek` only; flag for human review. |

---

## Rate Limiting

- Apify subscription dictates compute units / month, not per-second rate. ~$0.50 AUD per 1K postings is the dominant cost variable.
- Seek itself enforces anti-bot at the proxy layer; Apify rotates UAs + residential proxies. Tolerate 5–10% scrape-failure rate.
- Daily cron at 02:00 AEST avoids Seek's peak traffic; reduces 403 incidence.

---

## Integration Points

| File | Usage |
|---|---|
| `src/integrations/apify_seek_client.py` | TBD — ~150 lines. `httpx.AsyncClient` calling Apify v2 API, polling run status, fetching datasets. |
| `src/pipeline/seek_discovery.py` | TBD — aggregator + spike detection. Calls `abn_match.py` shared helper, applies both blocklists, writes `category_baselines.seek` jsonb. |
| `src/pipeline/abn_match.py` | TBD — shared helper refactor (prerequisite). Same dependency as AusTender + ASIC skills. |
| `src/config/seek_blocklists.py` | TBD — `RECRUITMENT_NAME_KEYWORDS`, `RECRUITMENT_DOMAIN_BLOCKLIST`, `MARKETING_NAME_KEYWORDS`, `MARKETING_DOMAIN_BLOCKLIST`, `MARKETING_ANZSIC_CODES`. Reviewed monthly. |
| `scripts/ingest_seek.py` | TBD — CLI for daily cron. `--start-urls`, `--spike-threshold`, `--window-days`, `--allow-agencies` (override), `--dry-run` (default), `--live`. |
| `tests/test_seek_blocklists.py` | TBD — comprehensive blocklist tests with positive (Hays, Adecco, generic recruitment names) AND negative (real SMB names that don't match) cases for both blocklists. ≥20 test cases. |

**LAW XII:** direct calls to `src/integrations/apify_seek_client.py` outside skill execution are forbidden. The skill is the canonical interface.
**LAW XIII:** any change to Seek-scrape patterns OR blocklist contents updates this SKILL.md in the same PR.

---

## Governance

- **LAW II:** Apify cost in AUD (~$0.50/1K postings). USD billing converted at 1.55× for accounting.
- **LAW VI:** prefer this skill > MCP > exec. There is currently NO Apify MCP server, so all calls go through `src/integrations/apify_seek_client.py` and are wrapped by this skill.
- **LAW XII / XIII:** see Integration Points above.
- **CEO Directive (2026-05-06, MAX greenlight):** Seek is the THIRD F2.2 discovery integration. **Two-blocklist requirement is non-negotiable** — connector PR cannot land without both blocklists implemented, tested, and human-reviewed.

---

## Pending Verification (DO NOT SKIP BEFORE FIRST PRODUCTION USE)

1. **Apify token confirmation** (Dave action) — does our existing Apify subscription cover the `websift/seek-job-scraper` actor, or do we need a separate `APIFY_API_TOKEN`? Check current Apify console.
2. **Blocklist seed-list review** — both `RECRUITMENT_DOMAIN_BLOCKLIST` and `MARKETING_DOMAIN_BLOCKLIST` need ≥30 seed entries each before first run. Dave + ELLIOT review pre-deployment.
3. **Domain-resolution heuristic accuracy** — sample 100 Seek `companyName` → resolved domain; measure accuracy. Below 60% = rework resolution before production.
4. **ABN-name-match thresholds** — confidence cutoff at 0.9 may be too strict (high `abn = NULL` rate) or too loose (false matches). Tune empirically with 200 samples.
5. **Seek anti-bot rate** — measure 24h scrape failure rate; if >10%, reduce frequency or rotate Apify proxy pool.
6. **Spike-threshold empirical tuning** — start at 5 postings/30d. Log distribution; ratchet if too noisy or too sparse.
7. **Re-posting deduplication** — measure how often the same job is re-posted; adjust dedupe heuristic if double-counting inflates spikes.

---

## Migration / Comparison

| Existing F2.1 (Stage 1 Maps) | F2.2 Seek |
|---|---|
| Maps category keyword search | Seek job-posting volume aggregation |
| ~750 domains/run | ~3–5K spike-companies/month |
| Cost: ~$1.20 USD per run | ~$75 AUD/month at daily cron |
| Time-to-stale: months | 7–30 days (hiring window) |
| Quality: business exists in Maps | Capacity / growth signal — actively scaling |
| Domain coverage: high (Maps requires website) | 60–80% resolved at scrape time, rest queued |
| ABN: matched at Stage 4 | Resolved heuristically + matched via shared helper |
| Blocklists: none | **Two mandatory blocklists** |

**Complementary, not replacement.** Maps gives breadth (any business that exists locally); Seek gives motion (businesses that are growing). Most valuable when intersected with downstream qualification (Stage 4 affordability + Stage 5 intent).

---

## Template Checklist (mirrors leadmagic / smartlead / pipedrive / hubspot / austender / asic-new-co)

- [x] **At-a-Glance block** with What / Why / When / Caveats / Returns
- [x] **Two Blocklists section** (mandatory per MAX directive 2026-05-06)
- [x] **Input Parameter Constraints** with start_urls, freshness, spike threshold, blocklist enforcement, poka-yoke
- [x] **Input Examples** ≥3 cases (daily, backfill, override-research)
- [x] **Response Trimming** PERSIST vs DROP per response type
- [x] **API Endpoints table** (Apify v2)
- [x] **Seek → BU field-mapping table** explicit and complete
- [x] **Error Handling** table HTTP / condition → category → action (including blocklist matches)
- [x] **LAW XII / XIII governance note**
- [x] **Pending Verification** section listing every assumption before production
- [x] **Migration / Comparison** vs F2.1 baseline

---

## Dave Actions

1. **Apify token check** — confirm whether `APIFY_API_TOKEN` env var exists and covers `websift/seek-job-scraper`. If yes, no action; spec ships ready. If no, separate Apify subscription needed (~$49 USD/mo Starter).
2. **Blocklist seed-list contribution** — add any AU agencies you can think of to both blocklists. Pre-deployment review.

These actions are NOT blocking the spec PR. They're prerequisites for the connector PR (post-spec).
