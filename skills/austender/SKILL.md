# SKILL: AusTender — Government Procurement Discovery

**Purpose:** F2.2 alternative discovery model — surface AU SMB suppliers who just won a government contract (intent + revenue signal), and government agencies actively procuring tech (formal buying intent). Net-new discovery feed; complements existing SERP/ABN/LinkedIn discovery.
**Status:** ✅ Public OCDS API — no credential gate. Ready to integrate.
**Source:** AusTender OCDS-compliant JSON API at `https://api.tenders.gov.au/ocds`.
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
- `date_to: date` — required. Inclusive upper bound. The 14-day cap from the legacy WAF-fronted endpoint **no longer applies** post-PR #600 — `api.tenders.gov.au` paginates with `links.next`, so wide ranges work. Wrapper still rejects future or inverted ranges.
- `value_min_aud: int` — optional. Default 50000 (AUD $50k). Below 1000 = reject (noise). **Filtered client-side** — the live API exposes no `min` query param, so the wrapper drains the cursor then drops below-threshold releases before returning.
- Date format passed in URL path as full **ISO 8601 UTC** (`2026-05-04T00:00:00Z`), not bare `YYYY-MM-DD`. Helper `_to_iso_z(d)` does the conversion.
- `release_types: list[str]` — optional. Default `['award']`. Accept any of `['planning', 'tender', 'award', 'contract', 'implementation']`. F2.2 uses `award` only.

**ABN match flow:**
- Every supplier ABN must pass the existing `src/pipeline/abn_match.py` shared helper (refactor pending — see Integration Points). NO direct INSERT to BU without ABN normalisation.
- If `supplier.country != 'AU'` or ABN missing, drop the record (F2.2 scope is AU SMBs only).

**Never pass:**
- A `date_from` more than 365 days back without bounded log batching — the cursor will work, but you'll drain a lot of pages and downstream pipelines may not be sized for the burst. Use `date_range_chunks(start, end, step_days=7)` to batch for log clarity.
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
| `https://api.tenders.gov.au/ocds/findByDates/contractPublished/{startISO}/{endISO}` | GET | Awarded contracts in [start, end] date window. ISO 8601 UTC (`Z`-suffixed) timestamps in path; cursor pagination via `links.next` (100 releases / page). |
| `https://api.tenders.gov.au/ocds/release/{ocid}` | GET | Single release by OCID (Open Contracting ID). |

**Base URL:** `https://api.tenders.gov.au/ocds`
**Auth:** None.
**Format:** JSON conforming to OCDS 1.1 (https://standard.open-contracting.org/1.1/en/).
**Pagination:** cursor-based. Each page response includes `data["links"]["next"]`; walk until absent (or until `_MAX_PAGES = 200` safety belt fires — ≈20k contracts per window).
**Value filtering:** client-side only. The legacy `min` query param does **not** exist on `api.tenders.gov.au`. Drop below-threshold releases after pagination drains.

> **Deprecated (do not use):** the legacy WAF-fronted public-portal OCDS path on `www.tenders.gov.au` — returned 403 in production. PR #587 / #588 originally pointed there; PR #600 migrated the client to `api.tenders.gov.au`.

---

## OCDS → BU field mapping

| OCDS path | BU column / jsonb path |
|---|---|
| `releases[*].parties[role='supplier'].identifier.id` (scheme=AU-ABN) **OR** `releases[*].parties[role='supplier'].additionalIdentifiers[scheme=AU-ABN].id` | `business_universe.abn` |
| `releases[*].parties[role='supplier'].name` | `business_universe.display_name` (only on INSERT; never overwrite existing) |
| `releases[*].parties[role='supplier'].address.countryName` (`AUSTRALIA` uppercase on live feed; case-insensitive match) | drop record if not AU |
| `releases[*].id` (contract_id / OCID) | `category_baselines.austender.contract_id` (jsonb) |
| `releases[*].contracts[*].value.amount` (string!) **preferred** — fall back to `releases[*].awards[*].value.amount` | `category_baselines.austender.contract_value_aud` (jsonb, AUD only) |
| `releases[*].contracts[*].dateSigned` **preferred** — fall back to `releases[*].awards[*].date`, then `releases[*].date` | `category_baselines.austender.awarded_date` (jsonb) |
| `releases[*].parties[role='procuringEntity'].name` (live feed) **OR** `releases[*].parties[role='buyer'].name` (OCDS spec) | `category_baselines.austender.agency_name` (jsonb) |
| `releases[*].contracts[*].items[*].classification.id` (preferred) **OR** `releases[*].awards[*].items[*].classification.id` | `category_baselines.austender.classification_id` (jsonb) |
| Pipeline routing | `discovery_source = 'austender_supplier'`, `signal_source = 'austender_supplier'`, `signal_checked_at = NOW()`, `pipeline_stage = 0` |

**Live-feed deviations from OCDS spec** (verified against `api.tenders.gov.au` 2026-05-07 — encoded in `src/integrations/austender_client.py` post-PR #600):

- `value.amount` arrives as a JSON **string** (e.g. `"607987.88"`), not a number. Coerce with `float()`.
- Buyer party uses role `procuringEntity` (OCDS extension), not bare `buyer`. Parser accepts both.
- Supplier ABN lives under `additionalIdentifiers[]` (array), not `identifier{}` (object). Parser walks both.
- `countryName` is uppercase `AUSTRALIA`. Match case-insensitively.
- Award value is on `contracts[i]` not `awards[i]`. Parser prefers contracts; falls back to awards for older releases.

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
| `src/integrations/austender_client.py` | ✅ live (PR #587/#588 → PR #600). HTTP client over `api.tenders.gov.au/ocds`. `httpx.AsyncClient`, no auth, ISO 8601 + cursor paging. ~330 lines including `AwardEvent` parser. |
| `src/pipeline/austender_discovery.py` | ✅ live. Bridges `AwardEvent` to BU. Calls `abn_match.py` shared helper, writes `category_baselines.austender` jsonb. |
| `src/pipeline/abn_match.py` | ✅ live. Shared helper consumed by AusTender + cohort runners. |
| `scripts/ingest_austender.py` | ✅ live. CLI wrapper for daily cron. `--date-from`, `--date-to`, `--min-value`, `--dry-run` (default), `--live`. Verified end-to-end on 2026-05-07: `fetched=634 parsed=634 would-write=590 errors=0` for a 7-day window ≥ AUD 50k. |
| `tests/integrations/test_austender_client.py` | ✅ 26 unit tests + 1 `@pytest.mark.live` smoke (deselected by default; opt in with `pytest -m live`). |

**LAW XII:** direct calls to `src/integrations/austender_client.py` outside skill execution are forbidden. The skill is the canonical interface.
**LAW XIII:** any change to AusTender call patterns updates this SKILL.md in the same PR.

---

## Governance

- **LAW II:** all `value.amount` cast to AUD integer. Wrapper rejects non-AUD currencies at validation.
- **LAW VI:** prefer this skill > MCP > exec. There is currently NO AusTender MCP server (it's a public REST API), so all calls go through `src/integrations/austender_client.py` and are wrapped by this skill.
- **LAW XII / XIII:** see Integration Points above.
- **CEO Directive (2026-05-06, MAX greenlight):** AusTender is the FIRST F2.2 discovery integration to build (zero credentials, smallest scope, validates the alternative-discovery → BU plumbing pattern that ASIC + Seek will reuse).

---

## Pending Verification (status post-PR #600)

1. **OCDS schema variation** — *resolved* by PR #600. Live audit on `api.tenders.gov.au` 2026-05-07: ABN lives in `additionalIdentifiers[]` (not spec-bare `identifier`), buyer role is `procuringEntity` (not `buyer`), `countryName` is uppercase `AUSTRALIA`, `value.amount` is a JSON string. Parser handles all four deviations.
2. **Pagination behaviour** — *resolved* by PR #600. `links.next` cursor walked until exhausted; safety belt at `_MAX_PAGES = 200` (≈20k contracts per window).
3. **Awards vs Contracts feed split** — *resolved* by PR #600. The canonical endpoint for our use is `/findByDates/contractPublished/{startISO}/{endISO}` (the `releases.json` / `contracts.json` paths from the legacy WAF endpoint don't exist on `api.tenders.gov.au`). Award value lives on `contracts[i].value`; parser falls back to `awards[i].value` for older releases.
4. **Value threshold empirical tuning** — *partially resolved*. AUD $50k floor returns 634 releases over a 7-day window, of which 590 (93%) clear the AU-supplier filter. Tune empirically post-cutover.
5. **Buyer-of-record vs end user** — still open. Whole-of-government panel contracts (DTA etc.) name the panel as buyer, not the actual customer. Follow-up enrichment step for panel orders is pending.
6. **Backfill scope** — *partially resolved*. 90-day seed is now feasible because cursor paging removes the date-range cap. Capacity-check downstream pipeline before kicking off.

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

---

## History / Related PRs

- **PR #583** — initial skill spec (this file's first version) under the deprecated public-portal OCDS path on `www.tenders.gov.au`.
- **PR #587 / #588** — original connector + discovery slice. Mocks-only test suite passed but the URL was WAF-blocked at egress — production returned 403.
- **PR #600** — connector migrated to `api.tenders.gov.au/ocds`. Full ISO 8601 timestamps in path. Cursor paging via `links.next`. Removed `_MAX_DATE_RANGE_DAYS` cap. Bonus parser fixes (contract-side value, string-amount coerce, `procuringEntity` role, `additionalIdentifiers` ABN, uppercase `AUSTRALIA`). First connector to introduce `@pytest.mark.live` marker. **This SKILL.md update tracks PR #600 per LAW XIII.**
- **Connector live-smoke audit (2026-05-07)** — `docs/audits/2026-05-07_connector_live_smoke_audit.md`. Identifies 25 other connectors with the mocks-only QA gap that #587/#588 had.
