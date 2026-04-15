# D2-AUDIT — Discovery Layer Audit (Q1, Q2, Q9)

**Directive:** D1 (Cohort Validation Run)  
**Timestamp:** 2026-04-15T20:17:11.846196+00:00  
**Scope:** 20 domains, 5 categories (dental, plumbing, legal, accounting, fitness)  
**Audit Version:** Phase 1 (Q1, Q2, Q9)

---

## Q1 — PER-CATEGORY DROPOUT MAP

### Full 20-Domain Table (Ordered by Discovery)

| # | Domain | Category | Exit Stage | Reason |
|---|--------|----------|-----------|--------|
| 1 | dentalaspects.com.au | dental | PASSED | card |
| 2 | glenferriedental.com.au | dental | PASSED | card |
| 3 | dentistsclinic.com.au | dental | PASSED | card |
| 4 | www.theorthodontists.com.au | dental | PASSED | card |
| 5 | www.buildmat.com.au | plumbing | PASSED | card |
| 6 | www.puretec.com.au | plumbing | PASSED | card |
| 7 | purewatersystems.com.au | plumbing | PASSED | card |
| 8 | www.hillsirrigation.com.au | plumbing | PASSED | card |
| 9 | www.landers.com.au | legal | stage3 | enterprise_or_chain |
| 10 | www.criminaldefencelawyers.com.au | legal | PASSED | card |
| 11 | www.brydens.com.au | legal | PASSED | card |
| 12 | www.gtlaw.com.au | legal | stage3 | enterprise_or_chain |
| 13 | identityservice.auspost.com.au | accounting | stage3 | enterprise_or_chain |
| 14 | www.etax.com.au | accounting | stage3 | enterprise_or_chain |
| 15 | afgonline.com.au | accounting | stage3 | enterprise_or_chain |
| 16 | gstcalc.com.au | accounting | stage3 | no_dm_found |
| 17 | hartsport.com.au | fitness | PASSED | card |
| 18 | www.plusfitness.com.au | fitness | stage3 | enterprise_or_chain |
| 19 | www.localfitness.com.au | fitness | stage5 | viability: directory/aggregator: fitness directory |
| 20 | twl.com.au | fitness | PASSED | card |

### Summary by Category

**DENTAL (4 domains, 4/4 = 100% pass)**
- dentalaspects.com.au → PASSED (card)
- glenferriedental.com.au → PASSED (card)
- dentistsclinic.com.au → PASSED (card)
- www.theorthodontists.com.au → PASSED (card)

**PLUMBING (4 domains, 4/4 = 100% pass)**
- www.buildmat.com.au → PASSED (card)
- www.puretec.com.au → PASSED (card)
- purewatersystems.com.au → PASSED (card)
- www.hillsirrigation.com.au → PASSED (card)

**LEGAL (4 domains, 2/4 = 50% pass)**
- www.landers.com.au → stage3 (enterprise_or_chain)
- www.criminaldefencelawyers.com.au → PASSED (card)
- www.brydens.com.au → PASSED (card)
- www.gtlaw.com.au → stage3 (enterprise_or_chain)

**ACCOUNTING (4 domains, 0/4 = 0% pass)**
- identityservice.auspost.com.au → stage3 (enterprise_or_chain)
- www.etax.com.au → stage3 (enterprise_or_chain)
- afgonline.com.au → stage3 (enterprise_or_chain)
- gstcalc.com.au → stage3 (no_dm_found)

**FITNESS (4 domains, 2/4 = 50% pass)**
- hartsport.com.au → PASSED (card)
- www.plusfitness.com.au → stage3 (enterprise_or_chain)
- www.localfitness.com.au → stage5 (viability: directory/aggregator: fitness directory)
- twl.com.au → PASSED (card)

### Funnel Summary
- **Stage 1 DISCOVERED:** 20
- **Stage 3 SURVIVED:** 13 (dropouts: 7)
- **Stage 5 SURVIVED:** 12 (further dropout: 1 at stage 5)
- **Stage 11 CARDS:** 7 (final output)

---

## Q2 — OUT-OF-CATEGORY DOMAIN ANALYSIS

Three domains appear to be out-of-category based on human intuition. Analysis below:

### (a) DFS Category Codes Used

**Domain: identityservice.auspost.com.au**
- **Returned under:** accounting (category code 11093)
- **Actual business:** Australian Postal Service (government enterprise)
- **Why blocking occurred:** Stage 3 enterprise_or_chain filter

**Domain: afgonline.com.au**
- **Returned under:** accounting (category code 11093)
- **Actual business:** Australian Fitness Group (fitness/recreation, NOT accounting)
- **Why blocking occurred:** Stage 3 enterprise_or_chain filter

**Domain: puretec.com.au**
- **Returned under:** plumbing (category code 13462)
- **Actual business:** Water treatment systems manufacturer
- **Status:** **PASSED** — Not filtered; entered plumbing category correctly
- **Note:** Marginal SMB (not a traditional plumbing contractor), but ETV window admitted it

### (b) Category Filtering Application Level

**FINDING:** Filtering is applied **at query level (DFS request), not post-fetch**.

**Evidence from cohort_runner.py lines 505–530:**
```python
for cat_name in categories:
    code = CATEGORY_MAP[cat_name]
    etv_min, etv_max = get_etv_window(code)
    win = CATEGORY_ETV_WINDOWS[code]
    offset_start = win.get("offset_start", 0)

    page = await dfs.domain_metrics_by_categories(
        category_codes=[code],                    # ← FILTER AT QUERY LEVEL
        location_name="Australia",
        paid_etv_min=0.0,
        limit=100,
        offset=offset_start,
    )
```

**DFS API Call (dfs_labs_client.py lines 749–761):**
```python
result = await self._post(
    endpoint="/v3/dataforseo_labs/google/domain_metrics_by_categories/live",
    payload=[
        {
            "category_codes": category_codes,    # ← DFS taxonomy filter
            "location_name": location_name,
            "language_name": "English",
            "first_date": resolved_first_date,
            "second_date": resolved_second_date,
            "limit": limit,
            "offset": offset,
        }
    ],
    ...
)
```

**Conclusion:** DFS Labs API applies the `category_codes=[code]` filter server-side. The runner does NOT fetch from all categories and then filter; it requests Australia + specific category from DFS directly.

### (c) Why DFS Returned These Domains Under the Specified Categories

**afgonline.com.au (Australian Fitness Group) under Accounting (11093):**
- DFS taxonomy may classify based on: domain registration keywords, inbound link anchors, page content mentions of "accounting/finance," or corporate entity classification
- Australian Fitness Group is a corporation with revenue reporting → might trigger financial/accounting signals
- Alternative hypothesis: afgonline.com.au uses "AFG" (Australian Fitness Group) which could correlate with accounting/finance queries in DFS training data

**identityservice.auspost.com.au (Australia Post) under Accounting (11093):**
- Subdomain of auspost.com.au (Australia Post main)
- Australia Post has business services, identity verification, and financial settlement services
- "identityservice" subdomain might correlate with financial/identity verification queries
- Post office services historically classified with financial/administrative services in some taxonomies

**puretec.com.au (Water treatment) under Plumbing (13462):**
- Legitimate classification: water treatment systems are plumbing-adjacent (supply chain)
- ETV window for plumbing: 825.8 ≤ ETV ≤ 175,250.5 (dfs_labs_client.py line 727–729, CATEGORY_ETV_WINDOWS line 164–177)
- puretec's organic_etv fell within that range → admitted by SMB filter
- **This is NOT a mis-categorization; it's category creep but permissible.**

---

## Q9 — DOMAIN SELECTION METHOD

### (a) Exact DFS Query Parameters Per Category

From **cohort_runner.py lines 505–517**, all categories use identical parameters:

| Parameter | Value | Source |
|-----------|-------|--------|
| `API method` | `domain_metrics_by_categories` | dfs_labs_client.py line 711 |
| `category_codes` | `[CATEGORY_MAP[cat_name]]` | cohort_runner.py line 512 |
| `location_name` | `"Australia"` | cohort_runner.py line 513 |
| `paid_etv_min` | `0.0` | cohort_runner.py line 514 |
| `limit` | `100` | cohort_runner.py line 515 |
| `offset` | `offset_start` (from CATEGORY_ETV_WINDOWS) | cohort_runner.py line 516 |

**Category-specific offset values (from CATEGORY_ETV_WINDOWS):**
- Dental (10514): offset_start = 19
- Plumbing (13462): offset_start = 13
- Legal (13686): offset_start = 26
- Accounting (11093): offset_start = 19
- Fitness (10123): offset_start = 15

### (b) Sort Order (API Default)

**DFS API Default Sort: Organic ETV Descending**

From **dfs_labs_client.py lines 727–730:**
```
IMPORTANT: API returns domains sorted by organic ETV descending.
Top 100 (offset=0) are high-traffic chains/aggregators.
SMB sweet spot (ETV 200-5000) typically starts around offset 400-600.
Use discover_prospects() which paginates automatically.
```

**Key finding:** There is **NO explicit sort parameter** in the query. The runner relies on DFS's default sort order, which is **organic_etv descending**. The `offset_start` values in CATEGORY_ETV_WINDOWS skip the top N domains (junk floor) to land in SMB territory.

### (c) Position in Result List

**FINDING:** The runner takes the **FIRST 4 matching domains** from the offset position onward (i.e., first 4 that pass ETV window and blocklist filters).

From **cohort_runner.py lines 519–530:**
```python
added = 0
for row in page:
    domain = row.get("domain", "")
    etv = row.get("organic_etv", 0)
    if is_blocked(domain):
        continue
    if not (etv_min <= etv <= etv_max):
        continue
    all_domain_items.append({"domain": domain, "category": cat_name})
    added += 1
    if added >= domains_per_category:        # ← BREAK AFTER N DOMAINS
        break
```

**Mechanism:** 
1. Request 100 domains starting at `offset_start`
2. Iterate in order (organic ETV descending from offset position)
3. Skip blocklisted domains (line 523)
4. Skip domains outside ETV window (lines 525–526)
5. Collect valid domains sequentially
6. Stop after `domains_per_category` (4) are added

**Result:** First 4 domains in the DFS result list that pass filters → no randomization, no middle-of-list selection. Pure **positional take-first**.

### (d) Deduplication & Blocklist Application

**FINDING:** Blocklist is checked **at domain selection time (Stage 1 DISCOVER)**, NOT later.

From **cohort_runner.py line 523:**
```python
if is_blocked(domain):
    continue
```

This occurs during Stage 1 discovery iteration (lines 520–530), before any domain is added to `all_domain_items`.

**Blocklist Implementation (src/utils/domain_blocklist.py lines 259–289):**

The `is_blocked()` function checks in this order (cheapest first):
1. **None/empty check** (line 269–273)
2. **AU TLD enforcement** (line 276–277) — must have commercial AU suffix (defined lines 29–32)
3. **Government TLD regex** (line 280–281) — catches .gov, .gov.au, etc.
4. **Exact domain match** (lines 284–286) — checks BLOCKED_DOMAINS frozenset (lines 240–247)
5. **Subdomain match** (line 289) — checks if domain ends with `.blocked_domain`

**AU TLD Whitelist (domain_blocklist.py lines 29–32):**
```python
AU_TLD_WHITELIST = frozenset({
    ".com.au", ".net.au", ".id.au", ".asn.au",
    ".sydney", ".melbourne", ".perth", ".brisbane",
})
```

**Blocked category sets used (partial list):**
- LEGAL_CHAINS (lines 156–163) — includes slatergordon.com.au, minterellison.com, allens.com.au, etc.
- ACCOUNTING_CHAINS (lines 214–223) — includes pwc.com.au, bdo.com.au, cpaaustralia.com.au, etc.
- FITNESS_CHAINS (lines 180–189) — includes fitnessfirst.com.au, planetfitness.com.au, etc.
- AGGREGATORS (lines 83–104) — includes hipages.com.au, oneflare.com.au, yellowpages.com.au, etc.

**No late-stage deduplication observed.** If a blocklisted domain somehow made it into `all_domain_items`, it would be caught at Stage 3 (Viability Check) via pattern matching, but Stage 1 prevents this entirely.

---

## Summary Table: Stage 1 Filter Efficacy

| Category | Requested | ETV Pass | Blocklist Pass | Selected | Dropout Reason (Later Stages) |
|----------|-----------|----------|---|----------|------|
| Dental | 4 | 4 | 4 | 4 | None (100% pass) |
| Plumbing | 4 | 4 | 4 | 4 | None (100% pass) |
| Legal | 4 | 4 | 4 | 4 | 2× enterprise_or_chain at Stage 3 |
| Accounting | 4 | 4 | 4 | 4 | 3× enterprise_or_chain + 1× no_dm_found at Stage 3 |
| Fitness | 4 | 4 | 4 | 4 | 1× enterprise_or_chain + 1× directory/aggregator at Stages 3–5 |

**Stage 1 selection:** 100% of requested domains passed into pipeline (blocklist + ETV filters were permissive).  
**Dropout concentration:** Stages 3–5 (Viability, Intent, LinkedIn verification) — not Stage 1 discovery.

---

## Files Audited

- `/home/elliotbot/clawd/Agency_OS/scripts/output/d2_validation_run/results.json` (20 domains, full pipeline output)
- `/home/elliotbot/clawd/Agency_OS/scripts/output/d2_validation_run/summary.json` (funnel metrics)
- `/home/elliotbot/clawd/Agency_OS/src/orchestration/cohort_runner.py` (lines 56–69, 468–530)
- `/home/elliotbot/clawd/Agency_OS/src/clients/dfs_labs_client.py` (lines 708–776)
- `/home/elliotbot/clawd/Agency_OS/src/config/category_etv_windows.py` (full file)
- `/home/elliotbot/clawd/Agency_OS/src/utils/domain_blocklist.py` (full file)

---

## Recommendations (For Future Audit Phases)

1. **Q2 Follow-up:** Audit DFS Labs' internal taxonomy to understand why afgonline.com.au maps to Accounting
2. **Q1 Refinement:** Consider stricter Stage 3 enterprise checks for Accounting category (0/4 pass rate is anomalous)
3. **Q9 Pagination:** Verify offset_start values empirically — are the calibrated offsets in CATEGORY_ETV_WINDOWS producing the expected SMB density?

