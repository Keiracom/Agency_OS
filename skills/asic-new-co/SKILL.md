# SKILL: ASIC New Companies — Daily Registration Discovery

**Purpose:** F2.2 alternative discovery model — ingest the daily ASIC new-company registration extract to surface AU SMBs in their first 90 days post-incorporation (peak operational-tools-buying window). Net-new discovery feed; complements AusTender (revenue trigger) and Seek (capacity trigger) with a *formation* trigger.
**Status:** ⚠️ DSP API key NOT provisioned — gated on Dave-action email to `webservices@asic.gov.au` (1–7 day lead time, free). Skill spec ships ahead of credentials.
**Source:** ASIC Digital Service Provider (DSP) APIs — daily new-company extract endpoint.
**Credentials Required:** `ASIC_API_KEY` (issued per DSP after registration). Free of charge.
**Cost gate:** Free API after registration. Optional `Business API` ($0.10–$0.20 AUD per per-company lookup) for enriched ABR lookups; not v1-required.

---

## At-a-Glance (Anthropic tool-doc template — 6-vector hardened)

**What:** Daily ingestion of ASIC's new-company-registration feed. Emit one BU candidate row per new AU company, filtered to Keiracom-relevant ANZSIC industry codes (software, IT services, etc. — configurable). Each row carries the new entity's ABN, ACN, registration date, entity type, ANZSIC code, and registered-office address. Pipeline downstream then runs Stage 2+ (scrape/enrich/score) as for any other discovered domain.

**Why this skill exists:**
- F2.2 research found ~20K new AU companies/month register at ASIC; tech subset 2–3K/month. Massive untapped feed at zero cost.
- 90 days post-registration = peak operational-tools-buying window (per F2.2 research): payroll, comms, accounting, CRM, marketing — all the tools a new entity must onboard.
- Complements existing T1 ABN match (which CHECKS an ABN once we have it from Maps); ASIC NEW provides FRESH registrants the SERP discovery hasn't seen yet.

**When to use:**
- Daily cron pulling prior-day new registrations (delta feed).
- Monthly ANZSIC-code audit: refresh which industry codes route to which Keiracom verticals.
- Backfill mode: pull last 90 days on first run to seed BU with already-registered companies whose 90-day window is still open.

**When NOT to use:**
- NOT for verifying an existing ABN's status — use ABR (Australian Business Register) lookup, not ASIC. Different data layer.
- NOT for decision-maker discovery — ASIC publishes officer roster (directors, secretaries) but DROP that data per Pending Verification #5 (privacy + size). DM resolution stays with LinkedIn/ContactOut.
- NOT before `ASIC_API_KEY` is verified live (call `/me` health endpoint with the key; non-200 = block all calls).
- NOT for entities outside Keiracom-target ANZSIC codes — filter at ingestion to reduce BU bloat.

**Caveats:**
- **Daily delta vs full snapshot.** Some ASIC endpoints return cumulative snapshots (slow + bloated). Wrapper must distinguish and prefer delta endpoints for cron use.
- **ANZSIC vs Keiracom-vertical mapping.** ANZSIC has ~600 codes; Keiracom only cares about ~20–30. Mapping config must live in `src/config/anzsic_keiracom_codes.py` and be reviewed when verticals change.
- **Non-trading registrations.** Many new ABNs are SMSFs (super funds), shelf companies, or holding entities with no real business activity. Filter on `entity_type` to exclude these from outbound.
- **No website at registration time.** Many new entities don't have a `domain` for several weeks. ASIC ingestion produces BU rows with `domain = NULL`; downstream pipeline must tolerate or queue these for delayed Stage 2.
- **Postal address vs trading address.** ASIC publishes the registered-office address (often an accountant's postal box); not the trading location. Don't use for state/suburb signal — defer to Stage 1 Maps.
- **Data privacy.** ASIC officer-roster data is publicly available but using directors' names for outbound without consent is reputationally risky. STORE only the entity-level fields; DROP officer details.

**Returns:**
- Daily new-co event: `{abn, acn, entity_name, entity_type, entity_type_code, registration_date, anzsic_primary, registered_address: {state, postcode, country}}`.
- BU mapping target: `abn`, `entity_type`, `entity_type_code`, `registration_date` (existing columns); `category_baselines.asic = {anzsic_primary, registered_state, registered_postcode}` jsonb payload.

---

## Input Parameter Constraints (Poka-Yoke)

**Daily new-co fetch:**
- `date: date` — required. Single day (delta feed). Reject if > today; reject if older than 365 days (ASIC enforces retention).
- `anzsic_filter: list[str]` — optional. Default = `KEIRACOM_ANZSIC_CODES` constant (config). Each code is a 4-digit string (e.g. `"7000"` for software). Reject anything that isn't `^\d{4}$`.
- `entity_type_filter: list[str]` — optional. Default exclude `['SMSF', 'AFP', 'CFC', 'TST']` (super funds, partnerships, foreign entities, trusts — all out of V0 scope). Accept `['APTY', 'PROP', 'PUBC', 'LIM']` for active trading companies.

**ABN normalisation flow:**
- ABN must pass `src/pipeline/abn_match.py` (the shared helper refactor — prerequisite). Re-format whitespace, validate checksum, dedupe before INSERT.
- ASIC publishes ABN as 11-digit string; normalise to canonical "XX XXX XXX XXX" format before BU comparison.

**Never pass:**
- A `date` parameter inside a try/catch loop without bounded retries — ASIC enforces per-day idempotency, so re-fetching the same date is safe but wasteful.
- A wildcard `anzsic_filter = []` — produces 20K+ rows/day, most unrelated to Keiracom verticals. Reject empty list at wrapper.
- Officer-roster fields (`directors`, `secretaries`, `members`) into BU. Drop at parse time per privacy-and-bloat rule.
- An `entity_type` not in the documented enum — log + skip; ASIC schema occasionally adds new codes.

---

## Input Examples (covers edge cases)

**Daily ingestion of yesterday's tech registrations:**
```json
{
  "date": "2026-05-05",
  "anzsic_filter": ["6910", "6920", "7000", "7001", "7290"],
  "entity_type_filter": ["APTY", "PROP", "PUBC"]
}
```

**Backfill 90 days on first run:**
```python
for day in date_range(today - 90d, today, step=1):
    fetch_new_companies(date=day, anzsic_filter=KEIRACOM_ANZSIC_CODES)
```

**Single-ABN spot lookup during qualification:**
```python
fetch_company_by_abn("12 345 678 901")  # uses /companies/{abn} endpoint
```

---

## Response Trimming (what to persist, what to drop)

**New-co event — PERSIST:**
- `abn` (canonical "XX XXX XXX XXX" format)
- `acn` (9-digit, when present — companies only, not sole-trader ABNs)
- `entity_name` → `display_name` (BU)
- `entity_type`, `entity_type_code` → existing BU columns
- `registration_date` → existing BU column (note: ASIC field name varies — `registrationDate` vs `incorporationDate`)
- `anzsic_primary` → `category_baselines.asic.anzsic_primary` (jsonb)
- `registered_address.state` → `category_baselines.asic.registered_state` (jsonb; NOT the trading state)
- `registered_address.postcode` → `category_baselines.asic.registered_postcode` (jsonb)

**New-co event — DROP:**
- `directors[]`, `secretaries[]`, `members[]` — privacy + bloat. DM resolution stays with LinkedIn/ContactOut at Stage 6.
- `share_structure`, `class_of_shares` — irrelevant for outbound.
- `previous_names[]` — interesting for fraud detection, out of V0 scope.
- `documents[]` — incorporation paperwork; not data.
- All `historical_changes[]` arrays — only the current snapshot is useful for new-co.

---

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/extract/companies/new?date={YYYY-MM-DD}` | GET | Daily delta of new companies registered on that date. F2.2 cron uses this. |
| `/companies/{abn}` | GET | Single-company spot lookup. Used for qualification, not bulk ingestion. |
| `/me` | GET | Health check — verify API key validity. Onboarding only. |
| `/extensions/anzsic` | GET | Reference: ANZSIC code list. Refresh quarterly. |

**Base URL:** TBD (DSP-specific endpoint provided post-registration; commonly `https://api.asic.gov.au/dsp/v1/`).
**Auth:** `Authorization: Bearer {ASIC_API_KEY}` header.
**Format:** JSON.

---

## ASIC → BU field mapping

| ASIC field | BU column / jsonb path |
|---|---|
| `abn` | `business_universe.abn` (after canonicalisation) |
| `acn` | `business_universe.acn` (NEW COLUMN — see below) |
| `entity_name` | `business_universe.display_name` (INSERT only) |
| `entity_type` | `business_universe.entity_type` (existing) |
| `entity_type_code` | `business_universe.entity_type_code` (existing) |
| `registration_date` | `business_universe.registration_date` (existing) |
| `anzsic_primary` | `category_baselines.asic.anzsic_primary` (jsonb) |
| `registered_address.state` | `category_baselines.asic.registered_state` (jsonb) |
| `registered_address.postcode` | `category_baselines.asic.registered_postcode` (jsonb) |
| Pipeline routing | `discovery_source = 'asic_new_co'`, `signal_source = 'asic_new_co'`, `signal_checked_at = NOW()`, `pipeline_stage = 0` |

**One small migration required:**
```sql
ALTER TABLE public.business_universe ADD COLUMN acn text;
CREATE INDEX idx_bu_acn ON public.business_universe(acn) WHERE acn IS NOT NULL;
```
ACN is a 9-digit identifier separate from ABN (companies have both, but a sole-trader ABN has no ACN). Storing as a typed `text` column rather than nesting in `category_baselines` jsonb because:
1. ACN is structural enough to warrant a typed column.
2. Index on ACN enables fast spot lookup during qualification.
3. No data backfill needed — pre-existing BU rows simply have `acn = NULL`.

Migration ships in the connector PR, not the spec PR.

---

## Error Handling (Category → Action mapping)

| HTTP / Condition | Category | Action |
|---|---|---|
| 200 | success | Parse + ABN-canonicalise + ANZSIC-filter + write to BU. |
| 400 | caller_error | Invalid date / ANZSIC code. Validate inputs at wrapper level before retry. |
| 401 | config_error | API key invalid / revoked. Disable cron + alert via Slack. |
| 403 | permission_error | Key valid but lacking `extract:companies:new` scope. Re-issue via DSP support. |
| 404 | not_found | Endpoint path wrong (DSP base URL drift). Update config. |
| 429 | rate_limit | Exponential backoff 1s → 2s → 4s, max 3 retries. ASIC publishes per-DSP limits post-registration. |
| 500 / 502 / 503 | transient | Retry once after 5s. Then defer to next-day cron (idempotent). |
| ABN missing or malformed | filter | Log + drop. ASIC sometimes publishes pending-registration entries without ABN. |
| ANZSIC not in filter | filter | Drop silently — out of Keiracom-vertical scope. |
| Entity type in deny-list | filter | Drop silently — SMSF, partnership, etc. out of scope. |

---

## Rate Limiting

- ASIC publishes per-DSP limits post-registration (commonly ~60 req/min for delta-extract endpoints).
- Default our client to **5 req/sec** for headroom.
- Daily delta is one call; backfill is 90 calls (paginated by day) — sequential at 1 req/sec is ~90s total. Cheap.

---

## Integration Points

| File | Usage |
|---|---|
| `src/integrations/asic_dsp_client.py` | TBD — ~120 lines. `httpx.AsyncClient` with Bearer auth, ANZSIC parsing, ABN canonicalisation. |
| `src/pipeline/asic_discovery.py` | TBD — bridges client output to BU. Calls `abn_match.py` shared helper, writes `category_baselines.asic` jsonb. Filters by ANZSIC + entity_type. |
| `src/pipeline/abn_match.py` | TBD — shared helper refactor (prerequisite). Same dependency as AusTender + Seek skills. |
| `src/config/anzsic_keiracom_codes.py` | TBD — `KEIRACOM_ANZSIC_CODES` constant. List reviewed when verticals change. |
| `scripts/ingest_asic_new_co.py` | TBD — CLI for daily cron. `--date`, `--anzsic-codes`, `--dry-run` (default), `--live`. |
| `supabase/migrations/{date}_bu_acn_column.sql` | TBD — adds `acn text` column + index. Lands with connector PR, not spec PR. |

**LAW XII:** direct calls to `src/integrations/asic_dsp_client.py` outside skill execution are forbidden. The skill is the canonical interface.
**LAW XIII:** any change to ASIC call patterns updates this SKILL.md in the same PR.

---

## Governance

- **LAW II:** ASIC data is free; no AUD/USD conversion needed.
- **LAW VI:** prefer this skill > MCP > exec. There is currently NO ASIC MCP server, so all calls go through `src/integrations/asic_dsp_client.py` and are wrapped by this skill.
- **LAW XII / XIII:** see Integration Points above.
- **CEO Directive (2026-05-06, MAX greenlight):** ASIC New Companies is the SECOND F2.2 discovery integration to build (depends on Dave-action DSP registration; runs in parallel with Seek; AusTender ships first as zero-credential validator).

---

## Pending Verification (DO NOT SKIP BEFORE FIRST PRODUCTION USE)

1. **DSP registration completes** — Dave emails `webservices@asic.gov.au` requesting Digital Service Provider access. Lead time 1–7 days. Until key arrives, all calls fail with no usable error message.
2. **Endpoint base URL** — provided in DSP onboarding email; confirm against the documented `/dsp/v1/` pattern; some DSPs are issued legacy endpoints.
3. **Daily delta vs cumulative** — confirm `/extract/companies/new?date=X` returns ONLY companies registered on that date (delta). If cumulative, switch to `/extract/companies/new?since=X` semantic.
4. **ANZSIC primary code presence** — sample 50 recent registrations, confirm `anzsic_primary` is populated (occasional registrations skip this on filing).
5. **Officer-roster opt-out** — confirm we can request a feed variant that EXCLUDES directors/secretaries/members at the API level (not just at parse time). Reduces privacy surface area.
6. **Entity-type enum drift** — ASIC occasionally adds new codes (e.g. `EFC` for Foreign Companies post-2024). Wrapper must log-and-skip unknown codes rather than throw.
7. **Rate limit ceiling under load** — empirical test with 90-day backfill (90 sequential calls) before kicking off ingestion in earnest.

---

## Migration / Comparison

| Existing F2.1 (Stage 1 Maps) | F2.2 ASIC New Companies |
|---|---|
| Maps category keyword search | Daily registration delta feed |
| ~750 domains/run | ~20K new co/day total, ~50–150 tech-filtered |
| Cost: ~$1.20 USD per run | Free (DSP API) |
| Time-to-stale: months | 90-day peak buying window |
| Quality: business exists in Maps | Freshly incorporated, pre-website-launch in many cases |
| Domain coverage: high (Maps requires website) | LOW at registration time — many `domain=NULL` until weeks later |
| Pipeline gate: ABN match (Stage 4) | ABN attached pre-insert (no Stage 4 ABN call needed) |

**Key compatibility note:** Many ASIC-sourced rows arrive with `domain = NULL`. Downstream pipeline (Stage 2 scrape onwards) must tolerate or queue these for delayed website discovery. Recommend a separate "domain-resolution backlog" worker that retries weekly until a domain is found OR the 90-day window closes.

---

## Template Checklist (mirrors leadmagic / smartlead / pipedrive / hubspot / austender)

- [x] **At-a-Glance block** with What / Why / When / Caveats / Returns
- [x] **Input Parameter Constraints** with date validation, ANZSIC filter, entity-type filter, ABN canonicalisation, poka-yoke
- [x] **Input Examples** ≥3 cases (daily, backfill, single-ABN lookup)
- [x] **Response Trimming** PERSIST vs DROP per response type (officer-roster privacy drop)
- [x] **API Endpoints table** with method + purpose
- [x] **ASIC → BU field-mapping table** explicit and complete
- [x] **Error Handling** table HTTP → category → action
- [x] **One small migration documented** (`acn text` column + index)
- [x] **LAW XII / XIII governance note**
- [x] **Pending Verification** section listing every assumption before production
- [x] **Migration / Comparison** vs F2.1 baseline

---

## Dave Action

**Email `webservices@asic.gov.au`** requesting Digital Service Provider (DSP) API access. Subject: `DSP API access request — Keiracom Pty Ltd`. Body should reference: requesting access to the new-company-registration extract endpoint for B2B SaaS lead-discovery purposes; happy to provide ABN + use-case statement on request. Lead time 1–7 days. Free.

This action is a hard prerequisite for the connector PR (post-spec). Spec ships now to be ready when the key arrives.
