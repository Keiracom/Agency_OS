# DIRECTIVE #303 — Wire Proven Intelligence Endpoints

## Context

Working directory: /home/elliotbot/clawd/Agency_OS

Four DFS endpoints are proven but not wired in the v7 pipeline:
- DFS Competitors Domain ($0.01/domain)
- DFS Backlinks Summary ($0.02/domain)
- DFS SERP Brand Search ($0.002/domain)
- DFS SERP Indexed Pages ($0.002/domain)

**Files in scope ONLY:**
- src/pipeline/paid_enrichment.py
- src/clients/dfs_labs_client.py
- src/pipeline/pipeline_orchestrator.py (ProspectCard dataclass only)
- tests/test_paid_enrichment.py

**DO NOT TOUCH:** intelligence.py, scoring, discovery, outreach.

## Task A — Audit findings (already done for you)

**paid_enrichment.py current state:**
- STEP 1: DFS bulk_domain_metrics (traffic + authority metrics)
- STEP 2: DFS Maps GMB (rating, review count, address)
- STEP 3: Mark completion
- NO calls to competitors_domain, backlinks, brand SERP, or indexed pages

**dfs_labs_client.py current state:**
- `competitors_domain()` method EXISTS at ENDPOINT 3 (line ~349)
- NO `backlinks_summary()` method
- NO `brand_serp()` method
- NO `indexed_pages()` method
- `search_linkedin_people()` exists — shows pattern for SERP calls
- `ads_search_by_domain()` exists — shows pattern for SERP calls

**ProspectCard (pipeline_orchestrator.py line ~69):**
- Has: domain, company_name, location, services, evidence, affordability_band, affordability_score, intent_band, intent_score, is_running_ads, gmb_review_count, gmb_rating, dm_name, dm_title, dm_linkedin_url, dm_confidence, dm_email, dm_email_verified, dm_email_source, dm_email_confidence, email_cost_usd
- MISSING: competitors_top3, competitor_count, referring_domains, domain_rank, backlink_trend, brand_position, brand_gmb_showing, brand_competitors_bidding, indexed_pages

**GLOBAL_SEM_DFS = asyncio.Semaphore(28)** is defined in pipeline_orchestrator.py and used there. In paid_enrichment.py, it is NOT currently imported — you need to import it.

## Task B — Add three new methods to dfs_labs_client.py

Add these methods to DFSLabsClient. Pattern them after the existing `ads_search_by_domain()` method (ENDPOINT 9d, around line 831).

Check the `_post()` method signature and the `_cost_*` pattern. The class tracks costs per-endpoint via `cost_attr` strings. You'll need to add cost tracking attributes.

### 1. backlinks_summary()

```python
async def backlinks_summary(self, target_domain: str) -> dict:
    """
    Get backlink summary for a domain.
    Cost: $0.02 USD per call
    
    Returns:
        {
            "referring_domains": int,  # unique referring domains
            "domain_rank": int,        # DFS domain rank (0-100)
            "backlink_trend": str,     # "growing" | "stable" | "declining"
            "total_backlinks": int,
        }
    """
```

Endpoint: `/v3/backlinks/summary/live`
Payload: `[{"target": target_domain, "include_subdomains": True}]`

**THE BUG FROM #276:** The old parser tried `result.get("items")` but the backlinks/summary endpoint returns data at `tasks[0].result[0]` directly (not under "items"). The correct path is:
```python
result = await self._post(endpoint=..., payload=..., ...)
# result is already tasks[0].result[0] after _post() unwraps it
referring_domains = result.get("referring_domains") or 0
domain_rank = result.get("rank") or 0
total_backlinks = result.get("backlinks") or 0
# trend: compare first_seen dates or use referring_domains_new vs referring_domains_lost
new = result.get("referring_domains_new") or 0
lost = result.get("referring_domains_lost") or 0
if new > lost * 1.1:
    trend = "growing"
elif lost > new * 1.1:
    trend = "declining"
else:
    trend = "stable"
```

Check how `_post()` works — look at the return value. It may return `tasks[0].result[0]` already (look for `_unwrap` or similar), or it may return the raw response. Adapt accordingly.

### 2. brand_serp()

```python
async def brand_serp(
    self,
    business_name: str,
    location_code: int = 2036,
    language_code: str = "en",
) -> dict:
    """
    Check brand search presence for a business name.
    Cost: $0.002 USD per call
    
    Returns:
        {
            "brand_position": int | None,   # position in organic results (None = not found)
            "gmb_showing": bool,            # Knowledge Panel / GMB showing
            "competitors_bidding": bool,    # are competitors running ads on this brand name
        }
    """
```

Endpoint: `/v3/serp/google/organic/live/advanced`
Payload: 
```python
[{
    "keyword": business_name,
    "location_code": location_code,
    "language_code": language_code,
    "depth": 10,
    "se_domain": "google.com.au",
}]
```

Parse items:
- `brand_position`: find item where `item.get("type") == "organic"` and the domain appears in url — take `rank_absolute`
- `gmb_showing`: any item where `item.get("type") in ("local_pack", "knowledge_graph", "maps_pack")`
- `competitors_bidding`: check if `paid_results` or any `type == "paid"` items exist

### 3. indexed_pages()

```python
async def indexed_pages(
    self,
    domain: str,
    location_code: int = 2036,
    language_code: str = "en",
) -> int:
    """
    Get approximate indexed page count via site: SERP query.
    Cost: $0.002 USD per call
    
    Returns:
        int: estimated indexed pages (0 if not found)
    """
```

Endpoint: `/v3/serp/google/organic/live/advanced`
Payload:
```python
[{
    "keyword": f"site:{domain}",
    "location_code": location_code,
    "language_code": language_code,
    "depth": 1,
    "se_domain": "google.com.au",
}]
```

Parse: `tasks[0].result[0].get("se_results_count") or 0`

**Important:** Look at how the existing `_post()` method unwraps the DFS response before returning. The `search_linkedin_people()` method (ENDPOINT 9b, ~line 893) uses a SERP endpoint — use the same pattern.

## Task C — Add four endpoint calls to paid_enrichment.py

After STEP 2 (GMB), add STEP 3: Intelligence Endpoints (before the completion marking step, which becomes STEP 4).

```python
# STEP 3 — Intelligence Endpoints (competitors, backlinks, brand, indexed pages)
# Runs in parallel per domain using GLOBAL_SEM_DFS.
# Only for domains that passed the intent gate (all passing_rows here).
```

**Import at top of file:**
```python
from src.pipeline.pipeline_orchestrator import GLOBAL_SEM_DFS
```

For each domain, run all four calls in `asyncio.gather` with `return_exceptions=True`. Each call must be wrapped in `async with GLOBAL_SEM_DFS:`.

Helper to call within gather — use a wrapper coroutine pattern:
```python
async def _sem_call(coro):
    async with GLOBAL_SEM_DFS:
        return await coro
```

Store results in a new dict per domain, then write to BU in a single UPDATE:
```sql
UPDATE business_universe SET
    competitors_top3 = $2,
    competitor_count = $3,
    backlinks_referring_domains = $4,
    backlinks_domain_rank = $5,
    backlinks_trend = $6,
    brand_serp_position = $7,
    brand_serp_gmb_showing = $8,
    brand_serp_competitors_bidding = $9,
    indexed_pages_count = $10,
    intelligence_enriched_at = NOW()
WHERE id = $1
```

**If columns don't exist in BU:** use `ON CONFLICT DO NOTHING` or wrap in try/except and log the column error — do NOT fail the pipeline if the BU columns aren't migrated yet. The data should still flow through to the enrichment dict.

For `business_name` lookup for brand SERP: use `extract_business_name(domain)` from `src/utils/domain_parser.py` (already imported in paid_enrichment.py) as fallback. Check if there's a `display_name` or `gmb_name` in the row first.

The enrichment result for each domain should be returned/stored in a dict:
```python
intel_results[domain] = {
    "competitors_top3": [...],
    "competitor_count": int,
    "referring_domains": int,
    "domain_rank": int,
    "backlink_trend": str,
    "brand_position": int | None,
    "brand_gmb_showing": bool,
    "brand_competitors_bidding": bool,
    "indexed_pages": int,
}
```

Return `intel_results` in the `stats` dict as `"intelligence_enriched": len(intel_results)`.

## Task D — Update ProspectCard

In `src/pipeline/pipeline_orchestrator.py`, add to the `ProspectCard` dataclass:

```python
# Intelligence endpoints (Directive #303)
competitors_top3: list = field(default_factory=list)
competitor_count: int = 0
referring_domains: int = 0
domain_rank: int = 0
backlink_trend: str = "unknown"
brand_position: Optional[int] = None
brand_gmb_showing: bool = False
brand_competitors_bidding: bool = False
indexed_pages: int = 0
```

## Task E — Tests

In `tests/test_paid_enrichment.py`, add tests after the existing ones:

1. **test_competitors_enrichment**: mock `competitors_domain()` returning 3 items → verify `intel_results[domain]["competitor_count"] == 3` and `competitors_top3` has 3 entries

2. **test_backlinks_parser_fix**: mock backlinks response with `{"referring_domains": 142, "rank": 23, "backlinks": 580, "referring_domains_new": 10, "referring_domains_lost": 3}` → verify `referring_domains == 142`, `domain_rank == 23`, `backlink_trend == "growing"`

3. **test_brand_serp_uses_business_name**: mock `brand_serp()` and verify it is called with the business name (not the domain string itself)

4. **test_indexed_pages**: mock `indexed_pages()` returning 47 → verify `intel_results[domain]["indexed_pages"] == 47`

5. **test_prospect_card_has_intelligence_fields**: instantiate `ProspectCard(domain="x.com.au", company_name="X", location="Sydney")` and assert `hasattr(card, "competitors_top3")` etc.

Also write a test `test_intelligence_calls_use_sem_dfs` — mock the semaphore and verify all four calls acquire it.

## Task F — Run tests

```bash
cd /home/elliotbot/clawd/Agency_OS
python -m pytest tests/test_paid_enrichment.py -v 2>&1 | tail -30
python -m pytest tests/ -x -q 2>&1 | tail -10
```

Baseline: >= 1289 passed, 0 failed

## Task G — Required output

After all changes:

1. `grep -n "competitors_domain\|backlinks_summary\|brand_serp\|indexed_pages" src/pipeline/paid_enrichment.py`
2. `grep -n "competitors_top3\|domain_rank\|brand_position\|indexed_pages" src/pipeline/pipeline_orchestrator.py`
3. Verbatim diff showing the backlinks parser fix (old vs new JSON path)
4. pytest output with final count

Then create PR:
```bash
git checkout -b feat/303-intelligence-endpoints
git add src/pipeline/paid_enrichment.py src/clients/dfs_labs_client.py src/pipeline/pipeline_orchestrator.py tests/test_paid_enrichment.py
git commit -m "feat(pipeline): #303 — wire Competitors, Backlinks, Brand SERP, Indexed Pages endpoints"
git push origin feat/303-intelligence-endpoints
gh pr create --title "feat(pipeline): #303 — wire four proven intelligence endpoints" --body "Wires DFS Competitors Domain, Backlinks Summary, Brand SERP, and Indexed Pages into paid_enrichment.py. Adds three new client methods to dfs_labs_client.py. Fixes backlinks parser bug from #276. Adds 6 tests. ProspectCard updated with 9 new fields." --base main
```

## Completion

When done, run:
openclaw system event --text "Done: #303 — four intelligence endpoints wired, PR open, tests passing" --mode now
