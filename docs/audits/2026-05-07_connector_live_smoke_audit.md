# Connector Live-Smoke Audit — 2026-05-07

**Branch:** `aiden/connector-live-smoke-audit` · **Dispatch:** `connector-live-smoke-audit-2026-05-07` (from Aiden)

## Why this audit exists

PR #587 / #588 shipped an AusTender connector whose unit tests passed against a WAF-blocked URL, because every HTTP call was mocked. **Mocks pass against any URL.** PR #600 fixed the connector and added a `@pytest.mark.live` smoke that hits the real `api.tenders.gov.au` endpoint — catching exactly the class of regression the original mocks-only suite missed.

This audit finds every other connector with the same QA gap so we can prioritise live-smoke tests before live cutover. The recommendation is **one live test per connector** (deselected from default `pytest` via `-m "not live"`, run on the live-cutover gate).

## Method

1. Listed every `*.py` file in `src/integrations/` that imports a network library or vendor SDK (`httpx`, `aiohttp`, `requests`, `anthropic`, `openai`, `supabase`, `redis`, `stripe`, `resend`, plus wrappers over those).
2. Located each connector's primary test file by name match + content reference (`from src.integrations.<stem>`).
3. Checked each test file for `@pytest.mark.live` (or `pytestmark = pytest.mark.live`).
4. Classified risk:
   - **HIGH** — third-party / external API (vendor outage, contract drift, billing, rate-limit, WAF-block all possible)
   - **MEDIUM** — managed infra we own the DSN/key for (Supabase, Redis, our own MCP bridge) — failures are config-shaped, not contract-shaped
   - **LOW** — local-only or wrapper-over-wrapper (no direct network call)

## Findings

**26 network connectors total. 1 has a live smoke (austender). 25 are mock-only.**

| Risk tier | Count | Connectors |
|-----------|-------|------------|
| HIGH (3rd-party) | 22 | 21 missing live + 1 covered (austender) |
| MEDIUM (infra)   | 4  | redis, supabase, smartlead_mcp, camoufox_scraper |
| LOW              | 0  | — |

## Connector × test × live-marker table

| # | Connector | Risk | Test file(s) | `@pytest.mark.live`? | Recommended action |
|---|-----------|------|--------------|----------------------|--------------------|
| 1 | `abn_client.py` | HIGH | `tests/pipeline/test_abn_match.py`, `tests/test_integrations/test_abn_gst_328_6.py`, `tests/test_pipeline/test_abn_matcher_297.py` | ❌ | Add live smoke — see template § A |
| 2 | `ads_transparency.py` | HIGH | `tests/test_integrations/test_ads_transparency.py`, `tests/test_integrations/test_ads_transparency_real.py` | ❌ | The `_real.py` file *suggests* live testing but lacks the marker. Add `@pytest.mark.live` to existing real tests + register marker. |
| 3 | `anthropic.py` | HIGH | `tests/integrations/test_anthropic_batch.py` (closest), `tests/integrations/test_anthropic_rate_limit.py` | ❌ | Live smoke — see template § B |
| 4 | `anthropic_batch.py` | HIGH | `tests/integrations/test_anthropic_batch.py` | ❌ | Live smoke — see template § B (use `messages.batches.create`) |
| 5 | `austender_client.py` | HIGH | `tests/integrations/test_austender_client.py`, `tests/pipeline/test_austender_discovery.py` | ✅ | Positive control. Keep. |
| 6 | `bright_data_client.py` | HIGH | `tests/integrations/test_bright_data_client.py`, `tests/test_bright_data_gmb_client.py` | ❌ | Live smoke — see template § C |
| 7 | `bright_data_gmb_client.py` | HIGH | `tests/test_bright_data_gmb_client.py` | ❌ | Live smoke — see template § C |
| 8 | `bright_data_linkedin_client.py` | HIGH | `tests/test_integrations/test_brightdata_client.py` | ❌ | Live smoke — see template § C |
| 9 | `camoufox_scraper.py` | MEDIUM | (none found) | ❌ | Add a thin test file + live smoke that hits a known-stable public URL (e.g. `https://example.com`). |
| 10 | `contactout_client.py` | HIGH | (none found) | ❌ | Add test file + live smoke — see template § D |
| 11 | `dataforseo.py` | HIGH | (none found) | ❌ | Add test file + live smoke — see template § E |
| 12 | `dfs_gmaps_client.py` | HIGH | `tests/test_dfs_gmaps_client.py` | ❌ | Live smoke — see template § E |
| 13 | `dfs_labs_client.py` | HIGH | `tests/test_clients/test_dfs_labs_client.py`, `tests/test_dfs_labs_client.py` | ❌ | Live smoke — see template § E |
| 14 | `dfs_serp_client.py` | HIGH | `tests/test_clients/test_dfs_serp_linkedin.py`, `tests/test_dfs_serp_client.py` | ❌ | Live smoke — see template § E |
| 15 | `dncr.py` | HIGH | `tests/integrations/test_dncr_client.py`, `tests/outreach/safety/test_dncr_adapter.py`, `tests/test_dncr_client.py` | ❌ | Live smoke — see template § F |
| 16 | `elevenagents_client.py` | HIGH | (none found) | ❌ | Add test file + live smoke — see template § G |
| 17 | `elevenlabs.py` | HIGH | (none found) | ❌ | Add test file + live smoke — see template § G |
| 18 | `httpx_scraper.py` | MEDIUM | `tests/test_integrations/test_httpx_scraper.py` | ❌ | Live smoke against a known-stable public URL — template § H |
| 19 | `leadmagic.py` | HIGH | `tests/test_leadmagic_client.py`, `tests/test_leadmagic_mock.py` | ❌ | Live smoke — see template § I |
| 20 | `pipedrive_client.py` | HIGH | `tests/integrations/test_pipedrive_client.py` | ❌ | Live smoke — see template § J |
| 21 | `prospeo_client.py` | HIGH | (none found) | ❌ | Add test file + live smoke — see template § K |
| 22 | `redis.py` | MEDIUM | `tests/test_redis_relay.py` | ❌ | Live smoke pinging Redis — template § L |
| 23 | `resend_client.py` | HIGH | `tests/api/test_email_routes.py`, `tests/test_campaign_executor.py` | ❌ | Live smoke uses Resend's `onboarding@resend.dev` sandbox sender — template § M |
| 24 | `smartlead_mcp.py` | MEDIUM | (none found) | ❌ | Live smoke through MCP bridge — template § N |
| 25 | `stripe.py` | HIGH | (none found) | ❌ | Add test file + live smoke against Stripe **test mode** keys — template § O |
| 26 | `supabase.py` | MEDIUM | (none found) | ❌ | Live smoke `SELECT 1` — template § P |
| 27 | `telnyx_client.py` | HIGH | (none found) | ❌ | Add test file + live smoke — template § Q |
| 28 | `unipile.py` | HIGH | (none found) | ❌ | Add test file + live smoke — template § R |
| 29 | `vapi.py` | HIGH | (none found) | ❌ | Add test file + live smoke — template § S |

> **Note:** `__init__.py`, `circuit_breaker.py`, and `anthropic_rate_limit.py` are excluded — pure local logic, no network egress.

## Risk-tier summary

| Tier | Has live | Missing live | % covered |
|------|----------|--------------|-----------|
| HIGH | 1 | 21 | 4.5% |
| MEDIUM | 0 | 4 | 0% |
| LOW | — | — | — |
| **Total** | **1** | **25** | **3.8%** |

Per the dispatch, **writing the live tests is out of scope for this PR.** Each per-connector live test will be its own dispatch. Templates below are recommendations, **not** to be added in this audit PR.

## Recommended live-smoke templates (commented-out, NOT for this PR)

Each template targets the same shape: a single async test, marked `@pytest.mark.live`, that calls one cheap read-only endpoint and asserts ≥1 sensible field. The point is to fail loudly when a URL changes, a contract drifts, or auth breaks — not to validate behaviour (which mocks already cover).

```python
# Template § A — abn_client.py
# @pytest.mark.live
# @pytest.mark.asyncio
# async def test_abn_lookup_live_smoke():
#     from src.integrations.abn_client import lookup_by_abn
#     row = await lookup_by_abn("33051775556")  # known-stable AU-ABN
#     assert row is not None and row.get("entityName")
```

```python
# Template § B — anthropic.py / anthropic_batch.py
# @pytest.mark.live
# @pytest.mark.asyncio
# async def test_anthropic_haiku_smoke():
#     from src.integrations.anthropic import client
#     msg = await client.messages.create(
#         model="claude-haiku-4-5", max_tokens=10,
#         messages=[{"role": "user", "content": "ping"}])
#     assert msg.content and msg.usage.input_tokens > 0
```

```python
# Template § C — bright_data_*.py
# @pytest.mark.live
# @pytest.mark.asyncio
# async def test_brightdata_live_smoke():
#     # Trigger a 1-row dataset; assert returns within timeout + has expected keys.
#     # Use the cheapest dataset (e.g. GMB by URL) on a stable target.
```

```python
# Template § D — contactout_client.py
# @pytest.mark.live  # gated by CONTACTOUT_API_KEY env presence
# Hit /v1/people/me or equivalent self-check endpoint; asserts auth not 401.
```

```python
# Template § E — dataforseo.py / dfs_*.py
# @pytest.mark.live
# Use the /v3/appendix/user_data endpoint — returns account info, costs nothing.
# assert resp["status_code"] == 20000
```

```python
# Template § F — dncr.py
# @pytest.mark.live
# Lookup a known-public AU number with the registry; assert decision returned.
```

```python
# Template § G — elevenagents_client.py / elevenlabs.py
# @pytest.mark.live
# GET /v1/voices (cheap list call); assert ≥1 voice in response.
```

```python
# Template § H — httpx_scraper.py
# @pytest.mark.live
# @pytest.mark.asyncio
# async def test_httpx_scraper_live_smoke():
#     from src.integrations.httpx_scraper import fetch
#     html = await fetch("https://example.com")
#     assert "Example Domain" in html
```

```python
# Template § I — leadmagic.py
# @pytest.mark.live
# Verify a known-good email; assert {"status": "valid"} or "deliverable".
```

```python
# Template § J — pipedrive_client.py
# @pytest.mark.live
# GET /v1/users/me; assert auth + own user_id present.
```

```python
# Template § K — prospeo_client.py
# @pytest.mark.live
# /account-information endpoint (free); assert credits remaining is int.
```

```python
# Template § L — redis.py
# @pytest.mark.live
# r = await get_redis(); assert (await r.ping()) is True
```

```python
# Template § M — resend_client.py
# @pytest.mark.live
# Send to onboarding@resend.dev sandbox FROM onboarding@resend.dev; assert
# message_id returned. Cleanup-free (sandbox).
```

```python
# Template § N — smartlead_mcp.py
# @pytest.mark.live
# call(tool="ping"); assert MCP bridge returns 200.
```

```python
# Template § O — stripe.py
# @pytest.mark.live  # requires STRIPE_API_KEY to be a TEST-mode sk_test_...
# stripe.Customer.list(limit=1); assert it doesn't raise.
```

```python
# Template § P — supabase.py
# @pytest.mark.live
# @pytest.mark.asyncio
# async def test_supabase_select_one_live_smoke():
#     async with get_db_session() as session:
#         row = (await session.execute(text("SELECT 1 AS ok"))).scalar()
#     assert row == 1
```

```python
# Template § Q — telnyx_client.py
# @pytest.mark.live
# GET /v2/messaging_profiles?page[size]=1; assert auth not 401.
```

```python
# Template § R — unipile.py
# @pytest.mark.live
# GET /api/v1/accounts; assert returns list (may be empty).
```

```python
# Template § S — vapi.py
# @pytest.mark.live
# GET /assistant?limit=1; assert auth not 401.
```

## Cross-cutting recommendations

1. **Register `live` marker globally.** `pytest.ini` should have:
   ```ini
   markers =
       integration: marks tests as integration tests
       live: hits real external services — opt-in via `pytest -m live`
   addopts = ... -m "not live"
   ```
   (Already done in PR #600.)

2. **Pre-commit hook** should run `pytest -m "not live"` (default) — fast and offline.
   **CI** should run `pytest -m live` separately on a live-cutover gate, with vendor keys present.

3. **Per-connector dispatch order.** Suggested priority (highest blast radius first):
   1. `resend_client` (sends real email — already partially covered by #554's smoke harness)
   2. `anthropic` (every prompt path → Haiku/Sonnet/Opus)
   3. `dataforseo` + `dfs_*` (Stage-1 discovery cost path)
   4. `leadmagic` (paid enrichment — already has lots of mocks)
   5. `bright_data_*` (LinkedIn + GMB scrapers)
   6. `abn_client` (cohort gating)
   7. The rest in alphabetical order.

4. **Process lesson** (encode in CONTRIBUTING / definition-of-done):
   *Connector unit tests must include at least one `@pytest.mark.live` smoke before the connector is considered production-ready. Mocks-only suites are insufficient — they pass against any URL.*

## Related PRs

- PR #587 / #588 — original AusTender connector (WAF-blocked URL, mocks-only)
- PR #600 — AusTender API URL fix + ISO 8601 + cursor paging + introduces `@pytest.mark.live` pattern
- PR #596 — pre-commit hook for ruff (referenced by #600 review feedback)
- This PR — audit only; per-connector live-smoke implementations dispatch separately
