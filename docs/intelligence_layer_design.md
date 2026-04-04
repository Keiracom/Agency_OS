# Intelligence Layer Design — Task 2.1
## `src/intelligence/website_intelligence.py`

**Author:** architect-0
**For:** build-2 (implementation)
**Date:** 2026-04-04
**Status:** DESIGN ONLY — do not implement without reading this in full

---

## 1. Context & Problem Statement

The current pipeline uses regex and numeric heuristics throughout:

| Location | What | Limitation |
|----------|------|------------|
| `free_enrichment.py` `_detect_ad_tags()` | Ad tag regex (`AW_TAG_RE`, `META_PIXEL_RE`) | Only finds known patterns; misses novel tags |
| `free_enrichment.py` `_extract_cms/tech_stack()` | String match on script `src` attrs | Misses dynamically loaded scripts, custom builds |
| `prospect_scorer.py` `score_intent_free()` | Heuristics on CMS + tracker presence | Cannot understand what the business actually does |
| `stage_4_scoring.py` `_calc_pain_score()` | Rating × review count formula | Cannot read sentiment or identify specific pain themes |
| `pipeline_orchestrator.py` Stage 9 | `services=enrichment.get("services") or []` | `services` is always empty — no source fills it |

The httpx scraper (Task 1.3) now provides raw HTML for every domain. We can feed that HTML to LLMs for real semantic understanding. This design adds an intelligence layer that produces outputs the regex layer cannot.

---

## 2. Output Schema

```python
from dataclasses import dataclass, field

@dataclass
class WebsiteIntelligence:
    # ── Haiku-powered: website comprehension ──────────────────────────
    services: list[str]                 # e.g. ["dental services", "teeth whitening"]
    business_type: str                  # "agency" | "freelancer" | "in-house" | "unknown"
    team_size_signal: str               # "solo" | "small" | "medium" | "large" | "unknown"
    is_actively_marketing: bool         # has active ads/tracking signals = True
    comprehension_confidence: float     # 0.0-1.0 — how readable the HTML was

    # ── Sonnet-powered: intent classification ─────────────────────────
    intent_grade: str                   # "HOT" | "WARM" | "COLD"
    intent_reasoning: str               # 1-sentence plain-English explanation

    # ── Haiku-powered: GMB review intelligence ────────────────────────
    gmb_pain_themes: list[str]          # e.g. ["slow response", "poor quality"]
    gmb_opportunity_score: int          # 0-100 (100 = highest opportunity)

    # ── Meta ──────────────────────────────────────────────────────────
    haiku_cost_aud: float = 0.0         # cumulative Haiku spend for this domain
    sonnet_cost_aud: float = 0.0        # cumulative Sonnet spend for this domain
    fallback_used: bool = False         # True if regex/heuristic fallback triggered
```

---

## 3. Seven Design Decisions

### Decision 1: HTML Truncation Strategy for Haiku

**How many chars, and which chars?**

Raw HTML is 30k–150k characters. Feeding it raw to Haiku is:
1. Expensive (most tokens are script tags and CSS)
2. Ineffective (LLMs are poor at minified JS)

**Decision:** Strip and extract before sending.

**Preprocessing pipeline (in `_extract_visible_text()`):**
1. Remove `<script>...</script>` blocks (regex: `re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)`)
2. Remove `<style>...</style>` blocks
3. Remove `<head>...</head>` block (keep `<title>` contents only)
4. Strip all remaining HTML tags (`re.sub(r'<[^>]+>', ' ', html)`)
5. Collapse whitespace
6. Truncate to **3,000 characters**

**Rationale for 3,000 chars:** The visible text of a homepage (headings, nav, hero copy, services list, CTA, footer) reliably fits in 3,000 chars. This = ~1,000 tokens at 3 chars/token. Adding system prompt (~400 tokens) gives ~1,400 input tokens per call.

Also extract separately and prepend to the text:
- `<title>` tag content
- `<meta name="description">` content
- First `<h1>` content

These are the most signal-dense elements and should not be lost to truncation.

**Format of text sent:**
```
Title: {title_tag}
Description: {meta_description}
H1: {first_h1}

Page text:
{extracted_visible_text_3000_chars}
```

---

### Decision 2: Haiku Prompt — Website Comprehension

**System prompt** (cacheable — constant across all calls):
```
You are a business analyst classifying Australian small businesses for digital marketing agency prospecting.
Analyze the website text provided and return a JSON object with exactly the fields specified.
Be concise. Do not explain your reasoning outside the JSON.
```

**User prompt** (dynamic — domain + extracted text):
```
Domain: {domain}

Website content:
---
{extracted_text}
---

Return ONLY this JSON (no markdown, no explanation):
{
  "services": [],
  "business_type": "unknown",
  "team_size_signal": "unknown",
  "is_actively_marketing": false,
  "comprehension_confidence": 0.0
}

Field definitions:
- services: What the business sells or does. Max 6 items. Use plain English labels (e.g. "dental services", "Google Ads management", "plumbing repairs"). Empty array if unclear.
- business_type: "agency" if they sell marketing/design/digital services to other businesses. "freelancer" if solo consultant or contractor. "in-house" if corporate internal team. "unknown" if none apply.
- team_size_signal: "solo" if only 1 person mentioned. "small" if 2-10 people. "medium" if 10-50. "large" if 50+. "unknown" if no people mentioned.
- is_actively_marketing: true if website mentions running ads, promotions, Google Ads, social media campaigns, or if advertising tags are present.
- comprehension_confidence: 0.0 if page was a bot wall or error page. 0.5 if partial content only. 1.0 if clear, readable homepage.
```

**Model:** `claude-haiku-4-5-20251001`
**max_tokens:** 250
**temperature:** 0.1 (deterministic for structured output)

---

### Decision 3: Sonnet Prompt — Intent Classification

**When called:** After Haiku comprehension AND after Stage 6 paid enrichment (we have GMB + ads data). Only for domains that passed the affordability gate (Stage 4).

**System prompt** (cacheable):
```
You are a senior sales strategist at an Australian digital marketing agency.
Your job is to classify whether a local business prospect is HOT, WARM, or COLD — meaning how urgently they need marketing help and how likely they are to convert.

HOT: Business is clearly trying to do marketing but getting poor results. Strong buying signals: running Google Ads without conversion tracking, poor GMB rating despite many reviews, booking system without analytics, no analytics on a WordPress/Webflow site with an active social presence.

WARM: Business has some digital presence and marketing effort but significant untapped gaps. They're doing something right but leaving money on the table.

COLD: Business is either very sophisticated (doesn't need help) or has almost no digital presence/intent signals. Either not a buyer or not ready.

Return only a JSON object. One sentence for reasoning. Be direct and commercial in your language.
```

**User prompt** (dynamic):
```
Domain: {domain}
Services they offer: {", ".join(services) or "unknown"}
Business type: {business_type}
Team size: {team_size_signal}

Intent signals detected:
{chr(10).join("- " + e for e in evidence_list) or "- No intent signals detected"}

Key facts:
- Has website analytics: {has_analytics}
- Running Google Ads: {has_ads_tag}
- Conversion tracking set up: {has_conversion}
- GMB rating: {gmb_rating or "unknown"} ({gmb_review_count} reviews)
- GMB opportunity score: {gmb_opportunity_score}/100
- Actively marketing: {is_actively_marketing}
- Business actively marketing but lacking conversion tracking: {has_ads_tag and not has_conversion}

Return ONLY this JSON:
{"intent_grade": "HOT", "intent_reasoning": "one sentence"}
```

**Model:** `claude-sonnet-4-20250514`
**max_tokens:** 100
**temperature:** 0.2

---

### Decision 4: Haiku Prompt — GMB Review Intelligence

**When called:** After Stage 6 paid enrichment delivers GMB data. Can run concurrently with Sonnet intent grade.

**Input available:** `gmb_rating`, `gmb_review_count`. Review snippets (`gmb_review_snippets`) may or may not be present depending on data source. Design must handle both cases.

**System prompt** (cacheable):
```
You are analyzing Google My Business signals for Australian small businesses to identify marketing pain points.
Score how urgently this business needs marketing help, based on their GMB presence.
Return only JSON. No explanation outside JSON.
```

**User prompt** (dynamic):
```
Domain: {domain}
GMB Rating: {gmb_rating or "not available"}
Review Count: {gmb_review_count or 0}
{f"Review snippets:{chr(10)}" + chr(10).join(f'- "{s}"' for s in review_snippets[:5]) if review_snippets else "Review text: not available"}

Pain theme definitions:
- "slow response": business is slow to respond to customers
- "poor quality": service quality complaints visible
- "inconsistent service": highly variable quality mentioned
- "missing digital presence": very few reviews for what appears to be an established business (e.g. <10 reviews but clearly operational)
- "reputation risk": low rating (under 4.0) with high review count (20+) — urgent intervention needed
- "no reviews": zero reviews — invisible online despite being operational

gmb_opportunity_score rules:
- 0-20: Sophisticated business, good reputation, doesn't need help
- 21-50: Decent but gaps exist
- 51-75: Clear pain signals, likely receptive
- 76-100: Urgent — reputation damage, missing presence, or obvious neglect

Return ONLY this JSON:
{"gmb_pain_themes": [], "gmb_opportunity_score": 0}
```

**Model:** `claude-haiku-4-5-20251001`
**max_tokens:** 150
**temperature:** 0.1

---

### Decision 5: Fallback Strategy

Two separate failure modes require different fallbacks:

**A. API unavailable (network error, `anthropic.APIError`, `IntegrationError`):**
- Log warning with domain
- Return `_fallback_result("api_unavailable")` — all fields at safe defaults
- `fallback_used = True`
- Pipeline continues normally using heuristic scoring

**B. Spend limit hit (`AISpendLimitError`):**
- Log a single WARNING per run (not per domain) to avoid log spam
- Skip ALL remaining LLM calls for this run
- Return `_fallback_result("spend_limit")` for all remaining domains
- `fallback_used = True`

**C. JSON parse failure (LLM returned malformed JSON):**
- Log debug message
- Return partial result with what could be parsed, defaults for the rest
- `comprehension_confidence = 0.0` to signal poor quality

**Fallback defaults:**
```python
WebsiteIntelligence(
    services=[],
    business_type="unknown",
    team_size_signal="unknown",
    is_actively_marketing=False,  # safe default — don't assume
    comprehension_confidence=0.0,
    intent_grade="WARM",          # safe middle default — don't discard
    intent_reasoning="LLM analysis unavailable — fallback scoring applied",
    gmb_pain_themes=[],
    gmb_opportunity_score=50,     # neutral — don't over-penalise
    fallback_used=True,
)
```

**The existing regex detections are NOT discarded on fallback.** They are merged into the enrichment dict as before. The intelligence layer adds fields ON TOP of what regex provides.

---

### Decision 6: Token Budget Estimates Per Domain

All costs in AUD. Prompt caching assumed for system prompts after first call in a batch.

| Call | Input (uncached) | Input (cached) | Output | Cost (first domain) | Cost (subsequent) |
|------|-----------------|----------------|--------|---------------------|-------------------|
| Haiku comprehension | 1,400 tokens | 400 tokens cached | 250 tokens | $0.0029 | $0.0025 |
| Sonnet intent grade | 600 tokens | 300 tokens cached | 100 tokens | $0.0051 | $0.0035 |
| Haiku GMB | 500 tokens | 300 tokens cached | 150 tokens | $0.0019 | $0.0015 |
| **Total per domain** | | | | **$0.0099** | **$0.0075** |

Pricing used: Haiku input $1.24/M AUD, output $6.20/M AUD, cached $0.124/M AUD.
Sonnet input $4.65/M AUD, output $23.25/M AUD, cached $0.465/M AUD.

**At scale:**
- 100 domains/run: ~$0.76 AUD (95 cached + 5 cold)
- 1,000 domains/day: ~$7.55 AUD
- Monthly (30k domains): ~$226 AUD

These costs are well within acceptable bounds. The intelligence layer adds ~$7.55 AUD/day to operating costs.

---

### Decision 7: Keep or Remove Regex?

**Decision: KEEP regex. LLM augments, does not replace.**

Reasons:
1. **Ad tag regex is more reliable than LLM.** `AW_TAG_RE` searches minified JS for exact token patterns. Haiku cannot read minified JS — the preprocessing strips it. Regex stays as the authoritative source for `has_google_ads_tag`, `has_meta_pixel`.
2. **Regex is the fallback.** If API is down, the pipeline must still score correctly. Regex ensures this.
3. **`is_actively_marketing`** in `WebsiteIntelligence` should be set to `True` if EITHER the regex detected ad tags OR the LLM judged the business as actively marketing. This is a union, not a replacement.
4. **CMS and tech stack detection** remain regex-based. The LLM doesn't need to reclassify WordPress — it's reliably detected already.

The intelligence layer **adds** `services`, `business_type`, `team_size_signal`, `intent_grade`, `intent_reasoning`, `gmb_pain_themes`, `gmb_opportunity_score`. None of these exist today.

---

## 4. Module Interface Specification

### File: `src/intelligence/website_intelligence.py`

```python
"""
Contract: src/intelligence/website_intelligence.py
Purpose: LLM-powered website and GMB intelligence — supplements regex pipeline
Layer: 3 - engines (imports: models, integrations only)
Imports: src.integrations.anthropic
Consumers: src.pipeline.pipeline_orchestrator (injected as dependency)
"""
```

### Class: `WebsiteIntelligenceEngine`

```python
class WebsiteIntelligenceEngine:

    HAIKU_MODEL = "claude-haiku-4-5-20251001"
    SONNET_MODEL = "claude-sonnet-4-20250514"
    HTML_TEXT_MAX_CHARS = 3000
    HAIKU_MAX_TOKENS = 250
    SONNET_MAX_TOKENS = 100
    GMB_MAX_TOKENS = 150

    def __init__(self, anthropic_client: AnthropicClient) -> None:
        """Inject AnthropicClient — do not instantiate internally."""

    async def analyze(
        self,
        domain: str,
        html: str,
        intent_signals: dict,           # output of ProspectScorer.score_intent_free()
        gmb_data: dict | None = None,   # output of DFS Maps stage
        ads_data: dict | None = None,   # output of DFS Ads stage
    ) -> WebsiteIntelligence:
        """
        Full three-call analysis pipeline:
        1. Haiku: website comprehension (parallel-safe — call first)
        2. Haiku: GMB analysis (can run parallel with step 1)
        3. Sonnet: intent grade (waits for steps 1+2 — needs their output)

        Steps 1 and 2 run concurrently via asyncio.gather().
        Returns WebsiteIntelligence with fallback_used=True on any API failure.
        """

    async def comprehend_website(
        self,
        domain: str,
        html: str,
    ) -> dict:
        """
        Haiku call: extracts services, business_type, team_size_signal,
        is_actively_marketing, comprehension_confidence.

        Returns dict with those keys. On failure, returns safe defaults.
        Records spend via AnthropicClient._record_spend().
        """

    async def grade_intent(
        self,
        domain: str,
        comprehension: dict,
        intent_signals: dict,
        gmb_result: dict | None = None,
        ads_data: dict | None = None,
    ) -> dict:
        """
        Sonnet call: classifies HOT/WARM/COLD.

        Requires comprehension dict output from comprehend_website().
        intent_signals is the ProspectScorer IntentResult dict (has 'evidence', 'signals').
        Returns {"intent_grade": str, "intent_reasoning": str}.
        """

    async def analyze_gmb(
        self,
        domain: str,
        gmb_data: dict,
    ) -> dict:
        """
        Haiku call: identifies GMB pain themes and opportunity score.

        gmb_data keys used: gmb_rating, gmb_review_count, gmb_review_snippets (optional).
        Returns {"gmb_pain_themes": list[str], "gmb_opportunity_score": int}.
        """

    @staticmethod
    def _extract_visible_text(html: str, max_chars: int = 3000) -> str:
        """
        Strip scripts, styles, head (except title), HTML tags.
        Extract title, meta description, first h1 as prefix.
        Truncate body text to max_chars.
        Returns formatted string ready to inject into prompt.
        """

    @staticmethod
    def _parse_haiku_json(content: str, expected_keys: list[str]) -> dict:
        """
        Parse JSON from Haiku response. Handles markdown code fences.
        Returns dict with only expected_keys; fills missing keys with safe defaults.
        Does NOT raise on malformed JSON — returns empty dict instead.
        """

    @staticmethod
    def _fallback_intelligence(reason: str) -> WebsiteIntelligence:
        """Return safe-default WebsiteIntelligence with fallback_used=True."""
```

### Factory function

```python
def get_website_intelligence_engine() -> WebsiteIntelligenceEngine:
    """Get singleton WebsiteIntelligenceEngine using global AnthropicClient."""
    from src.integrations.anthropic import get_anthropic_client
    return WebsiteIntelligenceEngine(get_anthropic_client())
```

---

## 5. Integration Points in `pipeline_orchestrator.py`

### Constructor change

Add optional `intelligence` parameter:

```python
def __init__(
    self,
    discovery,
    free_enrichment,
    scorer=None,
    dm_identification=None,
    gmb_client=None,
    ads_client=None,
    prospect_scorer=None,
    intelligence=None,           # NEW: WebsiteIntelligenceEngine | None
):
    ...
    self._intel = intelligence
```

When `intelligence=None`, the pipeline behaves exactly as today — zero behaviour change.

### New Stage 4.5: Intelligence Analysis

Insert between Stage 4 (affordability gate) and Stage 5 (intent free gate):

```python
# ── STAGE 4.5: LLM website intelligence (optional) ────────────────
if self._intel is not None and afford_passed:
    sem_intel = asyncio.Semaphore(10)  # 10 concurrent Haiku calls
    intel_coros = []
    for domain, enrichment, afford in afford_passed:
        spider_html = enrichment.get("_raw_html", "")  # see note below
        intent_free_result = self._scorer.score_intent_free(enrichment)
        intel_coros.append(
            self._stage_intelligence(
                sem_intel, domain, spider_html, intent_free_result, enrichment
            )
        )
    intel_results = list(await asyncio.gather(*intel_coros, return_exceptions=False))
    # Merge intelligence into enrichment dicts
    for i, (domain, enrichment, afford) in enumerate(afford_passed):
        intel = intel_results[i]
        if intel:
            enrichment["services"] = intel.services
            enrichment["business_type"] = intel.business_type
            enrichment["team_size_signal"] = intel.team_size_signal
            enrichment["intent_grade"] = intel.intent_grade
            enrichment["intent_reasoning"] = intel.intent_reasoning
            enrichment["gmb_pain_themes"] = intel.gmb_pain_themes
            enrichment["gmb_opportunity_score"] = intel.gmb_opportunity_score
            enrichment["_intel_fallback"] = intel.fallback_used
    logger.info("stage4_5_complete intel_analyzed=%d", len(intel_results))
```

**Note on `_raw_html`:** The `enrich_from_spider` method must be updated to also store raw HTML in the enrichment dict under `_raw_html`. The `_parse_html_content` method has already parsed it — we just need to also pass through the raw HTML. The `_raw_html` key is underscore-prefixed to signal it is internal/not persisted to DB.

### Stage 7 augmentation: Intent full score boost

After computing `intent_full`, check `intent_grade` from intelligence:

```python
intent_full = self._scorer.score_intent_full(enrichment, ads_data, gmb_data)

# Boost or override with LLM intelligence if available
if enrichment.get("intent_grade") == "HOT" and not enrichment.get("_intel_fallback"):
    if intent_full.band not in ("STRUGGLING", "TRYING"):
        # LLM sees HOT but regex sees lower — log and apply LLM
        logger.info(
            "stage7_intel_boost domain=%s llm=HOT regex=%s",
            domain, intent_full.band,
        )
        intent_full = IntentResult(
            raw_score=max(intent_full.raw_score, 8),
            band="STRUGGLING",
            signals=intent_full.signals,
            evidence=intent_full.evidence + [enrichment.get("intent_reasoning", "")],
            passed_free_gate=True,
        )
```

### New helper method

```python
async def _stage_intelligence(
    self,
    sem: asyncio.Semaphore,
    domain: str,
    html: str,
    intent_free: Any,
    enrichment: dict,
) -> WebsiteIntelligence | None:
    """STAGE 4.5: LLM website intelligence for one domain."""
    async with sem:
        try:
            gmb_data = enrichment.get("gmb_data")  # may not exist yet at stage 4.5
            signals = {
                "evidence": getattr(intent_free, "evidence", []),
                "signals": getattr(intent_free, "signals", {}),
                "has_analytics": any(
                    "analytics" in t for t in enrichment.get("website_tracking_codes", [])
                ),
                "has_ads_tag": enrichment.get("has_google_ads_tag", False),
                "has_conversion": enrichment.get("has_conversion_tag", False),
            }
            return await self._intel.analyze(domain, html, signals, gmb_data)
        except Exception:
            logger.debug("stage_intelligence_failed domain=%s", domain)
            return None
```

---

## 6. `stage_4_scoring.py` Integration (Secondary Path)

The `Stage4Scorer` processes `business_universe` rows in batch — it does NOT have Spider HTML (those rows may have been scraped weeks ago). Its integration is limited to the GMB analysis only.

**Change to `_calc_pain_score`:**

The function signature stays the same. The `Stage4Scorer._score_dimensions()` method gains a new optional call:

```python
# If GMB intelligence is available in the business row, use it
gmb_opp = business.get("gmb_opportunity_score")  # int | None — new DB column
if gmb_opp is not None:
    pain_score = max(pain_score, gmb_opp)  # use whichever is higher
```

This requires:
1. A new `gmb_opportunity_score` column on `business_universe` (migration needed)
2. A Prefect flow that runs `WebsiteIntelligenceEngine.analyze_gmb()` for rows that have GMB data but no `gmb_opportunity_score`

**This is a future task.** The primary integration path is `PipelineOrchestrator`.

---

## 7. Directory Structure

```
src/
└── intelligence/
    ├── __init__.py
    └── website_intelligence.py     ← build-2 creates this
```

No other files needed. The `__init__.py` exports `WebsiteIntelligenceEngine`, `WebsiteIntelligence`, `get_website_intelligence_engine`.

---

## 8. Testing Requirements for build-2

build-2 must create `tests/intelligence/test_website_intelligence.py` covering:

1. `test_extract_visible_text_strips_scripts` — script tags removed from output
2. `test_extract_visible_text_truncates_to_3000` — output never exceeds max_chars
3. `test_parse_haiku_json_handles_markdown_fences` — strips ` ```json ` wrapper
4. `test_parse_haiku_json_returns_defaults_on_bad_json` — no exception on malformed
5. `test_analyze_returns_fallback_on_api_error` — mock API to raise `APIError`
6. `test_analyze_returns_fallback_on_spend_limit` — mock `AISpendLimitError`
7. `test_comprehend_website_parses_services` — mock Haiku response, check field parsing
8. `test_grade_intent_returns_hot_warm_cold` — verify valid enum values only
9. `test_analyze_gmb_handles_missing_review_snippets` — optional field absent

All tests use mocked `AnthropicClient` — no real API calls in tests.

---

## 9. Implementation Notes for build-2

1. **Import only from `src.integrations`** — do not import from `src.engines` or `src.pipeline`. Layer 3 rule.

2. **Pass `AnthropicClient` in constructor** — do not call `get_anthropic_client()` inside the class. Testability.

3. **Use `asyncio.gather()` for steps 1+2** — Haiku comprehension and Haiku GMB are independent; run concurrently.

4. **JSON parsing must be bulletproof** — LLMs occasionally return extra prose. `_parse_haiku_json` must handle: no JSON found, JSON in code fence, valid JSON with missing keys, JSON with extra keys. Never raise.

5. **`_raw_html` storage** — coordinate with `free_enrichment.py` to ensure `enrich_from_spider()` includes `_raw_html` in its return dict. The raw HTML from `_scrape_website()` must be passed through.

6. **Prompt caching** — pass `enable_caching=True` to `AnthropicClient.complete()`. Both Haiku calls and the Sonnet call have cacheable system prompts. Cached reads cost 90% less.

7. **Semaphore limit of 10** for intelligence stage — Anthropic's default rate limit is ~50 RPM for Haiku, ~10 RPM for Sonnet. The stage runs Haiku first (10 concurrent), then Sonnet serially per batch is fine given Sonnet is only called after affordability + intent gates thin the pool significantly.

8. **Do not add `services` to `business_universe` DB schema yet** — the `services` field stays in-memory in `ProspectCard` for now. If needed, a future migration can persist it.

---

## 10. Summary of Decisions

| # | Decision | Chosen |
|---|----------|--------|
| 1 | HTML truncation | Strip scripts/styles/head, extract visible text, 3,000 char limit with title/desc/h1 prefix |
| 2 | Haiku website prompt | JSON-only output, 0.1 temp, 250 max tokens, full field definitions in prompt |
| 3 | Sonnet intent prompt | HOT/WARM/COLD with explicit criteria, 0.2 temp, 100 max tokens |
| 4 | Haiku GMB prompt | Pain theme enum + 0-100 score, handles missing review text gracefully |
| 5 | Fallback | `fallback_used=True` dataclass field; API errors return safe defaults; pipeline never breaks |
| 6 | Token budget | ~$0.0075 AUD/domain (cached); ~$7.55 AUD/day at 1,000 domains |
| 7 | Regex strategy | KEEP all regex; LLM adds new fields only; `is_actively_marketing` is OR of regex+LLM |
