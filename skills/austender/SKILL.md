# SKILL: AusTender — Government Procurement Discovery

**Purpose:** F2.2 alternative discovery model — surface AU SMB suppliers who just won a government contract (intent + revenue signal), and government agencies actively procuring tech (formal buying intent). Net-new discovery feed; complements existing SERP/ABN/LinkedIn discovery.
**Status:** ✅ Public OCDS API — no credential gate. Ready to integrate.
**Source:** AusTender OCDS-compliant JSON API at `tenders.gov.au`.
**Credentials Required:** NONE. Public open-contracting data per Australian Government policy.
**Cost gate:** Free. Only operational cost is downstream pipeline processing.

---

## At-a-Glance (Anthropic tool-doc template — 6-vector hardened)

**What:** Daily ingestion of AusTender OCDS feed. Two prospect paths from one feed:
- **Path A (suppliers — F2.2 priority):** SMB just awarded a government contract = new revenue + validated execution capability. Match supplier ABN to existing BU rows or insert new ones.
- **Path B (buyers — defer to F2.3):** Federal/state agency posting a tech ATM = formal intent + budget commitment. Government agencies are not Keiracom V0 ICP (we target AU SMBs); useful only when we expand upmarket.

**Why this skill exists:**
- F2.1 baseline (per ELLIOT 2026-05-06 audit): 750 → 260 cards = 34.7% yield, $0.054 USD per card. Critical gap: discovery volume is single-source (Maps + ABN match).
- F2.2 expansion adds AusTender as orthogonal signal (procurement intent + revenue confirmation) — same downstream pipeline, different inflow.
- AusTender published research finding (2026-05-06): ~50–400 AU tech tenders/month, OCDS-compliant API, free, denser signal than US SAM.gov due to AU centralised authority.

**When to use:**
- Daily cron pulling prior-day OCDS releases for `award` events with `value.amount >= AUD $50,000` (small contracts are noise).
- Backfill mode: pull last 90 days of awards on first run to seed the BU with recent winners.
- Re-poll a specific contract by ID when reviewing a prospect's AusTender history during qualification.

**When NOT to use:**
- NOT as a real-time signal (procurement events are batched, not streaming — eventual consistency over minutes-to-hours).
- NOT for verifying a supplier's deliverability — AusTender confirms a contract exists but says nothing about email/phone reachability. Stage 7+ (email waterfall) still applies.
- NOT during the first 90 days of new-vendor-on-AusTender data — buyer panels rotate, signal-to-noise improves with longer windows.
- NOT for international suppliers — AusTender awards may go to non-AU entities; ABN-match step filters those out.

**Caveats:**
- **Schema variation across federal vs state.** Federal AusTender follows OCDS strictly; some state portals (Queensland, Victoria) deviate. Wrapper must tolerate optional fields.
- **Eventual consistency.** Awards may publish 1–14 days after contract signature. Don't assume "new awards today" = "today's signed contracts."
- **Aggregator vs underlying buyer.** Some agencies use central procurement panels (e.g. DTA whole-of-government). Buyer-of-record may not be the actual end user.
- **AU TLD filter not sufficient.** Some AU suppliers operate under .com or .net.au; rely on ABN, not domain TLD.
- **Value threshold tuning.** AUD $50k floor is a starting point; below that, contracts are panel-renewals, IT-helpdesk-tickets, or other low-signal procurement. Tune empirically.

**Returns:**
- Award event: `{contract_id, supplier: {abn, name, country}, buyer: {agency_id, agency_name}, value: {amount_aud, currency}, awarded_date, contract_period_start, contract_period_end, description, classification: {scheme, id}}`.
- BU mapping target: `category_baselines.austender = {contract_id, contract_value_aud, agency, awarded_date, classification_id}` jsonb payload alongside `signal_source = 'austender_supplier'`.

---

## Input Parameter Constraints (Poka-Yoke)

**Daily fetch:**
- `date_from: date` — required. Inclusive lower bound. Reject if > today.
- `date_to: date` — required. Inclusive upper bound. Reject if `date_to - date_from > 14 days` (use multiple calls for longer windows; OCDS endpoints time out on wide ranges).
- `value_min_aud: int` — optional. Default 50000 (AUD $50k). Below 1000 = reject (noise).
- `release_types: list[str]` — optional. Default `['award']`. Accept any of `['planning', 'tender', 'award', 'contract', 'implementation']`. F2.2 uses `award` only.

**ABN match flow:**
- Every supplier ABN must pass the existing `src/pipeline/abn_match.py` shared helper (refactor pending — see Integration Points). NO direct INSERT to BU without ABN normalisation.
- If `supplier.country != 'AU'` or ABN missing, drop the record (F2.2 scope is AU SMBs only).

**Never pass:**
- A `date_from` more than 365 days back without paginating — AusTender returns large result sets that risk timeouts.
- Raw description / narrative as a search filter — OCDS narrative is unstructured and inconsistent across agencies.
- A contract_id from a different OCDS feed (e.g. NZ GETS) — federation is conceptual, not implemented; cross-feed IDs collide.

---

## Input Examples (covers edge cases)

**Daily ingestion of yesterday's awards over $50k:**
```json
{
  "date_from": "2026-05-05",
  "date_to": "2026-05-05",
  "value_min_aud": 50000,
  "release_types": ["award"]
}
```

**Backfill 90 days on first run (paginated by week):**
```python
for week_start in date_range(today - 90d, today, step=7):
    fetch_releases(date_from=week_start, date_to=week_start + 6d, value_min_aud=50000)
```

**Single-contract lookup during qualification:**
```python
fetch_release_by_id("CN3987654-A2")  # contract notice ID from a BU row
```

---

## Response Trimming (what to persist, what to drop)

**Award event — PERSIST:**
- `contract_id` (OCDS `releases[*].id`)
- `supplier.abn` (OCDS `releases[*].parties[role='supplier'].identifier.id` — only when `scheme = 'AU-ABN'`)
- `supplier.name` (OCDS `parties[role='supplier'].name`)
- `value.amount` cast to AUD integer (LAW II — reject other currencies)
- `awarded_date` (OCDS `releases[*].date` for award events)
- `buyer.agency_name` (OCDS `parties[role='buyer'].name`)
- `classification.id` (UNSPSC code or AusTender category code — used for vertical filtering)
- `contract_period.startDate`, `contract_period.endDate` (relevance window)

**Award event — DROP:**
- Full narrative description (`title`, `description`) — useful for human review but bloats `category_baselines` jsonb. Persist only first 200 chars.
- Non-supplier `parties` (procurement officers, panel members) — no signal value.
- Bidder list (other vendors who bid and lost) — interesting later for competitive intelligence, out of F2.2 scope.
- Document attachments / annex URLs — reference, not data.
- All `extensions.*` blocks — non-canonical OCDS extensions vary by agency.

---

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `https://www.tenders.gov.au/Atm/Search/Ocds/releases.json` | GET | Daily releases by date range. Query: `?date={YYYY-MM-DD}&type=award` |
| `https://www.tenders.gov.au/Atm/Search/Ocds/contracts.json` | GET | Historical contracts. Query: `?from={YYYY-MM-DD}&to={YYYY-MM-DD}&min={amount}` |
| `https://www.tenders.gov.au/Atm/Search/Ocds/release/{ocid}` | GET | Single release by OCID (Open Contracting ID). |

**Base URL:** `https://www.tenders.gov.au/Atm/Search/Ocds/`
**Auth:** None.
**Format:** JSON conforming to OCDS 1.1 (https://standard.open-contracting.org/1.1/en/).

---

## OCDS → BU field mapping

| OCDS path | BU column / jsonb path |
|---|---|
| `releases[*].parties[role='supplier'].identifier.id` (scheme=AU-ABN) | `business_universe.abn` |
| `releases[*].parties[role='supplier'].name` | `business_universe.display_name` (only on INSERT; never overwrite existing) |
| `releases[*].id` (contract_id / OCID) | `category_baselines.austender.contract_id` (jsonb) |
| `releases[*].awards[*].value.amount` | `category_baselines.austender.contract_value_aud` (jsonb) |
| `releases[*].date` (award type) | `category_baselines.austender.awarded_date` (jsonb) |
| `releases[*].parties[role='buyer'].name` | `category_baselines.austender.agency_name` (jsonb) |
| `releases[*].awards[*].items[*].classification.id` | `category_baselines.austender.classification_id` (jsonb) |
| Pipeline routing | `discovery_source = 'austender_supplier'`, `signal_source = 'austender_supplier'`, `signal_checked_at = NOW()`, `pipeline_stage = 0` |

**No schema migration in v1.** Existing BU columns cover everything via `category_baselines` jsonb. AusTender ships the same day specs land.

---

## Error Handling (Category → Action mapping)

| HTTP / Condition | Category | Action |
|---|---|---|
| 200 | success | Parse + ABN-match + write to BU. |
| 400 | caller_error | Invalid date format / range too wide. Validate inputs at wrapper level before retry. |
| 404 | not_found | Specific OCID not present (deleted or pre-OCDS era). Skip silently. |
| 429 | rate_limit | Exponential backoff 1s → 2s → 4s, max 3 retries. AusTender doesn't publish a ceiling — be polite (1 req/sec default). |
| 500 / 502 / 503 | transient | Retry once after 5s. If still failing, defer batch to next-day cron. |
| Timeout | transient | Halve the date range, retry. Wide ranges are the most common timeout cause. |
| ABN missing or non-AU | filter | Drop record silently — out of F2.2 scope. |
| Value < threshold | filter | Drop record silently — noise. |
| Currency != AUD | filter | Drop record silently — non-AU contract anomaly. |

---

## Rate Limiting

- AusTender does NOT publish a per-key rate limit (no key required).
- Empirical guidance: 1 request/second is courteous and unlikely to trigger 429.
- For backfill (90-day initial seed), paginate by week and run sequentially (~13 calls × 1s = 13 seconds total — very cheap).

---

## Integration Points

| File | Usage |
|---|---|
| `src/integrations/austender_client.py` | TBD — main HTTP client. ~80 lines. Uses `httpx.AsyncClient`, no auth, OCDS schema parsing. |
| `src/pipeline/austender_discovery.py` | TBD — bridges client output to BU. Calls `abn_match.py` shared helper, writes `category_baselines.austender` jsonb. |
| `src/pipeline/abn_match.py` | TBD — refactor of existing ABN match logic from `cohort_runner` into shared helper. **Refactor PR is a prerequisite for AusTender + Seek skills.** |
| `scripts/ingest_austender.py` | TBD — CLI wrapper for daily cron. `--date-from`, `--date-to`, `--min-value`, `--dry-run` (default), `--live`. |

**LAW XII:** direct calls to `src/integrations/austender_client.py` outside skill execution are forbidden. The skill is the canonical interface.
**LAW XIII:** any change to AusTender call patterns updates this SKILL.md in the same PR.

---

## Governance

- **LAW II:** all `value.amount` cast to AUD integer. Wrapper rejects non-AUD currencies at validation.
- **LAW VI:** prefer this skill > MCP > exec. There is currently NO AusTender MCP server (it's a public REST API), so all calls go through `src/integrations/austender_client.py` and are wrapped by this skill.
- **LAW XII / XIII:** see Integration Points above.
- **CEO Directive (2026-05-06, MAX greenlight):** AusTender is the FIRST F2.2 discovery integration to build (zero credentials, smallest scope, validates the alternative-discovery → BU plumbing pattern that ASIC + Seek will reuse).

---

## Pending Verification (DO NOT SKIP BEFORE FIRST PRODUCTION USE)

1. **OCDS schema variation** — confirm fields `parties[role='supplier'].identifier.id` are present + `scheme = 'AU-ABN'` on a sample of 50 recent awards. Some agencies use legacy CN-format IDs without ABN inline.
2. **Pagination behaviour** — confirm date-range query returns paginated results when N > 1000; test pagination cursor format (`next_url` vs `offset` parameter).
3. **Awards vs Contracts feed split** — `releases.json` and `contracts.json` overlap in coverage. Determine which is canonical for "award event" purposes (provisional answer: `releases.json` filtered by `tag = 'award'`).
4. **Value threshold empirical tuning** — start at AUD $50k, log discarded volume, ratchet down if signal density too low.
5. **Buyer-of-record vs end user** — for whole-of-government panel contracts, the named buyer (e.g. DTA) may not be the actual customer. May need a follow-up enrichment step for panel orders.
6. **Backfill scope** — initial 90-day seed: estimate 600–1500 supplier-side prospects depending on value threshold. Capacity-check downstream pipeline before kicking off.

---

## Migration / Comparison

| Existing F2.1 (Stage 1 Maps) | F2.2 AusTender |
|---|---|
| Maps category keyword search | Procurement event match |
| ~750 domains/run | ~50–400 supplier prospects/month |
| Cost: ~$1.20 USD per run + Stage 2 scrape | Free per fetch + downstream scrape |
| Time-to-stale: months (business existence) | Days–weeks (recent contract = recent signal) |
| Quality signal: business exists in Maps | Quality signal: gov-validated AU SMB with new revenue |
| Pipeline gate: ABN match (Stage 4) | Pipeline gate: ABN attached pre-insert |

**Complementary, not replacement.** Maps gives breadth; AusTender gives intent + revenue qualification.

---

## Template Checklist (mirrors leadmagic / smartlead / pipedrive / hubspot)

- [x] **At-a-Glance block** with What / Why / When to use / When NOT / Caveats / Returns
- [x] **Input Parameter Constraints** with date-range limits, value threshold, AU enforcement, poka-yoke
- [x] **Input Examples** ≥3 cases (daily, backfill, single-contract lookup)
- [x] **Response Trimming** PERSIST vs DROP per response type
- [x] **API Endpoints table** with method + purpose
- [x] **OCDS → BU field mapping table** explicit and complete
- [x] **Error Handling** table HTTP → category → action
- [x] **LAW XII / XIII governance note** — skill is canonical interface
- [x] **Pending Verification** section listing every assumption before production
- [x] **Migration / Comparison** vs F2.1 baseline
