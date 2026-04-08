# DIRECTIVE #306 — Marketing Vulnerability Report

## Working directory
/home/elliotbot/clawd/Agency_OS

## Context

Add `generate_vulnerability_report()` to `intelligence.py`, wire it into both `run()` and `run_parallel()` in `pipeline_orchestrator.py`, add `vulnerability_report` field to `ProspectCard`, and write 8 tests.

## FILES IN SCOPE ONLY
- src/pipeline/intelligence.py
- src/pipeline/pipeline_orchestrator.py (ProspectCard + wiring only)
- tests/ (new test file)

DO NOT touch: discovery, DFS clients, scoring, contact waterfall, outreach stack.

---

## AUDIT RESULTS (already done — read these)

### ProspectCard fields available as input to the report:
- domain, company_name, location_display, location_state
- services (list), evidence (list)
- affordability_band, affordability_score
- intent_band, intent_score
- is_running_ads, gmb_review_count, gmb_rating
- competitors_top3 (list of dicts), competitor_count
- referring_domains, domain_rank, backlink_trend
- brand_position, brand_gmb_showing, brand_competitors_bidding
- indexed_pages

### intelligence.py patterns to follow:
- `_call_anthropic(model, system_blocks, user_content, max_tokens)` — returns (text, in_tok, out_tok)
- `GLOBAL_SEM_SONNET` — imported from pipeline_orchestrator at top of file
- `_MODEL_SONNET = "claude-sonnet-4-5"`
- Cache pattern: `{"type": "text", "text": SYSTEM_STRING, "cache_control": {"type": "ephemeral"}}`
- `_parse_json_response(text, fallback)` — safely parses JSON with fallback
- All functions: `async with GLOBAL_SEM_SONNET:` wrapping the `_call_anthropic` call

### Wiring location in run_parallel() (src/pipeline/pipeline_orchestrator.py):
After `refined = await intel.refine_evidence(...)` and before `# ── STAGE 8: DM identification`:
```python
# ── STAGE 7c: Vulnerability Report (Sonnet) ──────────────────────────
vuln_report = await intel.generate_vulnerability_report(
    domain=domain,
    company_name=company_name,
    enrichment=enrichment,
    intelligence=intent_data,
    competitors_data={"top3": intel_top3, "count": intel_count},
    backlinks_data={"referring_domains": intel_rd, "domain_rank": intel_dr, "trend": intel_bt},
    brand_serp_data={"position": intel_bp, "gmb_showing": intel_bgs, "competitors_bidding": intel_bcb},
    indexed_pages=intel_ip,
)
```
Where `intel_top3` etc come from the `paid` dict intelligence results already collected in Stage 6.

### Wiring location in run() (the serial orchestrator, ~line 540):
After `refined = ...` and before DM identification, add the same call.

---

## TASK B — Add generate_vulnerability_report() to intelligence.py

### System prompt (static, cached):

```
_VULN_SYSTEM = """You are a marketing analyst producing a Marketing Vulnerability Report for an Australian business.

You receive raw data from multiple intelligence sources. Your job is to synthesise it into a structured assessment that a marketing agency can show the business owner to explain their marketing gaps.

Rules:
- Assign grades: A (excellent), B (good), C (average), D (poor), F (critical failure)
- Use "Insufficient Data" grade when data for a section is missing or null
- Every finding must reference specific numbers from the data provided
- Do NOT fabricate numbers or make assumptions beyond the data
- Competitive comparisons only where competitor data is actually present
- Be direct and specific — no vague statements like "could be improved"

Output ONLY valid JSON. No preamble, no explanation."""
```

### Function signature:

```python
async def generate_vulnerability_report(
    domain: str,
    company_name: str,
    enrichment: dict,
    intelligence: dict,
    competitors_data: dict | None = None,
    backlinks_data: dict | None = None,
    brand_serp_data: dict | None = None,
    indexed_pages: int = 0,
) -> dict:
    """
    Stage 7c — Sonnet. Synthesise all available intelligence into a structured
    Marketing Vulnerability Report.

    Cost: ~$0.02–0.03 per domain (Sonnet, cached system prompt, ~2K variable tokens).
    Semaphore: GLOBAL_SEM_SONNET.
    Prompt caching: static system prompt cached, variable data last.

    Returns dict with sections: search_visibility, technical_seo, backlink_profile,
    paid_advertising, reputation, competitive_position. Plus overall_grade,
    priority_action, three_month_roadmap.
    """
```

### Fallback dict (returned on any error):

```python
_VULN_FALLBACK = {
    "overall_grade": "Insufficient Data",
    "sections": {
        "search_visibility": {"grade": "Insufficient Data", "findings": [], "data": {}},
        "technical_seo": {"grade": "Insufficient Data", "findings": [], "data": {}},
        "backlink_profile": {"grade": "Insufficient Data", "findings": [], "data": {}},
        "paid_advertising": {"grade": "Insufficient Data", "findings": [], "data": {}},
        "reputation": {"grade": "Insufficient Data", "findings": [], "data": {}},
        "competitive_position": {"grade": "Insufficient Data", "findings": [], "competitors": []},
    },
    "priority_action": "",
    "three_month_roadmap": [],
}
```

### Implementation:

Build the variable user content as a JSON dict containing:
- company name, domain, intent_band, intent_score
- website data: services, cms, has_analytics, has_ads_tag, has_booking_system, has_conversion_tracking
- ads data: is_running_ads, ad_count, google_ads_active
- gmb data: rating, review_count, gmb_found
- competitors (top3 list with domain, intersections, avg_position if available)
- backlinks: referring_domains, domain_rank, backlink_trend
- brand_serp: brand_position, gmb_showing, competitors_bidding
- indexed_pages

Then prompt Sonnet:
```
f"Business intelligence data:\n{json.dumps(context_dict, indent=2)}\n\nProduce the Marketing Vulnerability Report JSON."
```

Use `max_tokens=1200` (enough for all 6 sections with findings).

Wrap in `async with GLOBAL_SEM_SONNET:`.

### Required output JSON structure (Sonnet must return this shape):

```json
{
  "overall_grade": "D+",
  "sections": {
    "search_visibility": {
      "grade": "D",
      "findings": ["specific finding with number", "..."],
      "data": {"keywords_ranking": 23, "brand_position": 8}
    },
    "technical_seo": {
      "grade": "C",
      "findings": ["..."],
      "data": {"indexed_pages": 94, "cms": "WordPress"}
    },
    "backlink_profile": {
      "grade": "D",
      "findings": ["..."],
      "data": {"domain_rank": 18, "trend": "declining"}
    },
    "paid_advertising": {
      "grade": "F",
      "findings": ["..."],
      "data": {"campaigns": 13, "tracking": false}
    },
    "reputation": {
      "grade": "B-",
      "findings": ["..."],
      "data": {"rating": 4.2, "reviews": 265}
    },
    "competitive_position": {
      "grade": "D",
      "findings": ["..."],
      "competitors": [{"domain": "competitor.com.au", "dr": 34}]
    }
  },
  "priority_action": "one sentence — most impactful first action",
  "three_month_roadmap": [
    "Month 1: ...",
    "Month 2: ...",
    "Month 3: ..."
  ]
}
```

---

## TASK C — Wire into ProspectCard and both orchestrator paths

### Step C1: Add field to ProspectCard dataclass

In the `@dataclass class ProspectCard` block (pipeline_orchestrator.py ~line 235), add after the `indexed_pages` field:

```python
# Vulnerability Report (Directive #306)
vulnerability_report: dict = field(default_factory=dict)
```

### Step C2: Wire in run_parallel() — the main path

In `run_parallel()`, find where `refined = await intel.refine_evidence(...)` is called (around line 1005 in the intel branch). After that line and before the DM identification stage, add:

```python
# ── STAGE 7c: Vulnerability Report ───────────────────────────────────
vuln_report = {}
if intel is not None:
    # Collect intelligence endpoint data from the paid results
    _comp_data = {
        "top3": paid.get("competitors_top3", []) if isinstance(paid, dict) else [],
        "count": paid.get("competitor_count", 0) if isinstance(paid, dict) else 0,
    }
    _bl_data = {
        "referring_domains": paid.get("backlinks_referring_domains", 0) if isinstance(paid, dict) else 0,
        "domain_rank": paid.get("backlinks_domain_rank", 0) if isinstance(paid, dict) else 0,
        "trend": paid.get("backlinks_trend", "unknown") if isinstance(paid, dict) else "unknown",
    }
    _brand_data = {
        "position": paid.get("brand_serp_position") if isinstance(paid, dict) else None,
        "gmb_showing": paid.get("brand_serp_gmb_showing", False) if isinstance(paid, dict) else False,
        "competitors_bidding": paid.get("brand_serp_competitors_bidding", False) if isinstance(paid, dict) else False,
    }
    _indexed = paid.get("indexed_pages_count", 0) if isinstance(paid, dict) else 0
    vuln_report = await intel.generate_vulnerability_report(
        domain=domain,
        company_name=company_name,
        enrichment=enrichment,
        intelligence=intent_data,
        competitors_data=_comp_data,
        backlinks_data=_bl_data,
        brand_serp_data=_brand_data,
        indexed_pages=_indexed,
    )
```

### Step C3: Add vulnerability_report to ProspectCard construction in run_parallel()

At the `card = ProspectCard(...)` call in run_parallel(), add:
```python
vulnerability_report=vuln_report,
```

### Step C4: Wire in run() — the serial path (around line 540 in the intel block)

Find the `refined = await intel.refine_evidence(...)` call in the serial `run()` method (the non-parallel path). Apply the same pattern: collect paid data, call `generate_vulnerability_report`, pass to ProspectCard.

The serial `run()` path is at the top of the `run()` method. Look for the `# Stage 7b` or `# intelligence layer` comment block and add the vulnerability report call after `refine_evidence`.

---

## TASK D — Tests

Create `tests/test_intelligence_vuln_report.py`:

Write these 8 tests:

**test_1_full_data_returns_all_sections**: mock `_call_anthropic` to return a JSON string with all 6 sections. Call `generate_vulnerability_report(...)` with full mock data. Assert `result["sections"]` has all 6 keys: search_visibility, technical_seo, backlink_profile, paid_advertising, reputation, competitive_position.

**test_2_missing_competitors_gives_insufficient**: mock `_call_anthropic` to return JSON where competitive_position grade is "Insufficient Data". Assert it passes through correctly (not treated as error).

**test_3_missing_ads_gives_appropriate_grade**: pass `enrichment={"google_ads_active": False}` with no ads data. The function should NOT crash. Assert result has "paid_advertising" section with some grade.

**test_4_result_json_has_required_keys**: assert result contains "overall_grade", "sections", "priority_action", "three_month_roadmap".

**test_5_vulnerability_report_on_prospect_card**: instantiate `ProspectCard(domain="x.com.au", company_name="X", location="Sydney")` and assert `hasattr(card, "vulnerability_report")` and `isinstance(card.vulnerability_report, dict)`.

**test_6_sonnet_semaphore_acquired**: mock `_call_anthropic`, patch `GLOBAL_SEM_SONNET`. Call `generate_vulnerability_report`. Verify the semaphore was acquired (use `asyncio.Semaphore` and check it was awaited via mock).

**test_7_prompt_caching_block_present**: inspect the `_VULN_SYSTEM_BLOCK` constant. Assert it has `"cache_control"` key with `{"type": "ephemeral"}`.

**test_8_api_error_returns_fallback**: mock `_call_anthropic` to raise `Exception("API error")`. Assert `generate_vulnerability_report` returns the fallback dict without raising, and `result["overall_grade"] == "Insufficient Data"`.

---

## TASK E — Run tests

```bash
cd /home/elliotbot/clawd/Agency_OS
python3 -m pytest tests/test_intelligence_vuln_report.py -v 2>&1 | tail -20
python3 -m pytest tests/ -q --ignore=tests/test_email_verifier.py --ignore=tests/enrichment/test_email_verifier.py 2>&1 | tail -5
```

Baseline: >= 1315 passed, 0 failed.

---

## TASK F — PR

```bash
git checkout -b feat/306-vulnerability-report
git add src/pipeline/intelligence.py src/pipeline/pipeline_orchestrator.py tests/test_intelligence_vuln_report.py
git commit -m "feat(pipeline): #306 — Marketing Vulnerability Report (Sonnet synthesis stage)"
git push origin feat/306-vulnerability-report
gh pr create --title "feat(pipeline): #306 — Marketing Vulnerability Report" --body "Adds generate_vulnerability_report() to intelligence.py as Stage 7c between intent classification and evidence refinement.\n\nSonnet reads all available intelligence (ads, GMB, competitors, backlinks, brand SERP, indexed pages, website comprehension) and produces a structured 6-section Marketing Vulnerability Report with grades, findings, and a 3-month roadmap.\n\nCost: ~\$0.02-0.03/domain. Prompt caching on static system prompt.\n\nWired in both run() and run_parallel().\nvulnerability_report dict field added to ProspectCard.\n8 new tests." --base main
```

---

## REQUIRED OUTPUT (LAW XIV)

1. PR URL
2. `grep -n "async def generate_vulnerability_report" src/pipeline/intelligence.py`
3. `grep -n "vulnerability_report" src/pipeline/pipeline_orchestrator.py`
4. Paste the full `_VULN_SYSTEM` string exactly as written in the code
5. One example mock output showing all 6 sections with grades (from test_1 data)
6. Full pytest output (last 5 lines)

## COMPLETION

When done, run:
openclaw system event --text "Done: #306 — Marketing Vulnerability Report wired. Sonnet Stage 7c. PR open." --mode now
