# Audit 2: Cost Tracking + Env Var Verification

Generated: 2026-04-14. Read-only. No code modified.

---

## Section 2a: Cost Table

All cost constants extracted from `src/orchestration/cohort_runner.py` (fixed constants) and `src/clients/dfs_labs_client.py` (per-endpoint Decimal values).

### DFS Labs Client — Per-Endpoint Costs

Source file: `src/clients/dfs_labs_client.py`

Verbatim grep output for cost constants:
```
35:AUD_RATE = Decimal("1.55")
342:            cost_per_call=Decimal("0.015"),   # domains_by_technology
403:            cost_per_call=Decimal("0.011"),   # competitors_domain
453:            cost_per_call=Decimal("0.010"),   # domain_rank_overview
507:            cost_per_call=Decimal("0.010"),   # domain_technologies
588:            cost_per_call=Decimal("0.011"),   # keywords_for_site
646:            cost_per_call=Decimal("0.106"),   # historical_rank_overview
762:            cost_per_call=Decimal("0.10"),    # domain_metrics_by_categories
820:            cost_per_call=Decimal("0.006"),   # google_ads_advertisers
867:            cost_per_call=Decimal("0.0035"),  # maps_search_gmb
923:            cost_per_call=Decimal("0.002"),   # ads_search_by_domain
987:            cost_per_call=Decimal("0.01"),    # search_linkedin_people
1045:           cost_per_call=Decimal("0.01"),    # domains_by_html_terms
1078:           cost_per_call=Decimal("0.006"),   # google_jobs_advertisers
1134:           cost_per_call=Decimal("0.10") + Decimal(str(len(domains))) * Decimal("0.001"),  # bulk_domain_metrics
1223:           cost_per_call=Decimal("0.002"),   # serp_email_search
1265:           cost_per_call=Decimal("0.02"),    # backlinks_summary
1322:           cost_per_call=Decimal("0.002"),   # brand_serp
1374:           cost_per_call=Decimal("0.002"),   # indexed_pages
```

| Component | Endpoint | Reported Cost (code) | DFS Docs Rate | Source | Match |
|-----------|----------|---------------------|---------------|--------|-------|
| domains_by_technology | /v3/domain_analytics/technologies/domains_by_technology/live | $0.015 | Unverified (live URL required) | dfs_labs_client.py:342 | UNVERIFIED |
| competitors_domain | /v3/dataforseo_labs/google/competitors_domain/live | $0.011 | Unverified | dfs_labs_client.py:403 | UNVERIFIED |
| domain_rank_overview | /v3/dataforseo_labs/google/domain_rank_overview/live | $0.010 | Unverified | dfs_labs_client.py:453 | UNVERIFIED |
| domain_technologies | /v3/domain_analytics/technologies/ | $0.010 | Unverified | dfs_labs_client.py:507 | UNVERIFIED |
| keywords_for_site | /v3/dataforseo_labs/google/keywords_for_site/live | $0.011 | Unverified | dfs_labs_client.py:588 | UNVERIFIED |
| historical_rank_overview | /v3/dataforseo_labs/google/historical_rank_overview/live | $0.106 | Matches docstring comment | dfs_labs_client.py:646 | CONSISTENT (internal) |
| domain_metrics_by_categories | /v3/dataforseo_labs/google/domain_metrics_by_categories/live | $0.10 | Unverified | dfs_labs_client.py:762 | UNVERIFIED |
| google_ads_advertisers | /v3/serp/google/ads/live/advanced | $0.006 | Matches docstring "~$0.006/call" | dfs_labs_client.py:820 | CONSISTENT (internal) |
| maps_search_gmb | SERP Google Maps | $0.0035 | Matches docstring "$0.0035/call" | dfs_labs_client.py:867 | CONSISTENT (internal) |
| ads_search_by_domain | SERP Ads | $0.002 | Matches docstring "$0.002/call" | dfs_labs_client.py:923 | CONSISTENT (internal) |
| search_linkedin_people | SERP LinkedIn | $0.01 | No docstring rate | dfs_labs_client.py:987 | UNVERIFIED |
| domains_by_html_terms | Domain Analytics | $0.01 | No docstring rate | dfs_labs_client.py:1045 | UNVERIFIED |
| google_jobs_advertisers | SERP Google Jobs | $0.006 | Matches docstring "~$0.006/call" | dfs_labs_client.py:1078 | CONSISTENT (internal) |
| bulk_domain_metrics | /v3/dataforseo_labs/google/bulk_traffic_estimation/live | $0.10/task + $0.001/domain | EXPLICIT WARNING in code: "Pricing TBD" | dfs_labs_client.py:1107-1135 | FLAGGED — code itself says unverified |
| serp_email_search | SERP | $0.002 | No docstring rate | dfs_labs_client.py:1223 | UNVERIFIED |
| backlinks_summary | Backlinks | $0.020 | Matches docstring "$0.020/call" | dfs_labs_client.py:1265 | CONSISTENT (internal) |
| brand_serp | SERP | $0.002 | Matches docstring "$0.002/call" | dfs_labs_client.py:1322 | CONSISTENT (internal) |
| indexed_pages | Domain Analytics | $0.002 | Matches docstring "$0.002/call" | dfs_labs_client.py:1374 | CONSISTENT (internal) |

### Gemini 2.5 Flash — Token Costs

Source file: `src/intelligence/gemini_client.py` and `src/intelligence/gemini_retry.py`

Verbatim:
```
src/intelligence/gemini_client.py:30:INPUT_COST_PER_TOKEN = 0.00000015
src/intelligence/gemini_client.py:31:OUTPUT_COST_PER_TOKEN = 0.0000006
src/intelligence/gemini_retry.py:23:INPUT_COST = 0.00000015   # per token
src/intelligence/gemini_retry.py:24:OUTPUT_COST = 0.0000006   # per token
```

| Component | Metric | Reported Cost | Google Published Rate | Source | Match |
|-----------|--------|--------------|----------------------|--------|-------|
| Gemini 2.5 Flash | Input tokens | $0.00000015/token ($0.15/M) | $0.15/M input (<=1M context) | gemini_client.py:30 | CONSISTENT (matches Google pricing as of 2026-04) |
| Gemini 2.5 Flash | Output tokens | $0.0000006/token ($0.60/M) | $0.60/M output | gemini_client.py:31 | CONSISTENT |

### Cohort Runner — Fixed Stage Cost Constants

Source file: `src/orchestration/cohort_runner.py`

Verbatim grep output:
```
cohort_runner.py:193-194:  # Fixed cost: 10 DFS endpoints × avg $0.0073 = $0.073/domain
                            domain_data["cost_usd"] += 0.073
cohort_runner.py:236-237:  # Fixed cost: historical_rank_overview = $0.106/domain
                            domain_data["cost_usd"] += 0.106
cohort_runner.py:271-272:  # Fixed cost: 3 SERP calls = $0.006 + scraper $0.004 + ContactOut ~$0.013 = $0.023/domain
                            domain_data["cost_usd"] += 0.023
cohort_runner.py:322-323:  # Fixed cost: ~$0.002 DM + $0.025 company = $0.027/domain
                            domain_data["cost_usd"] += 0.027
cohort_runner.py:460:       estimated_cost_per_domain = 0.25  # USD, from Pipeline F v2.1 economics doc
```

| Component | Stage | Reported Cost | Derivation in Code | Actual Rate Derivation | Match |
|-----------|-------|--------------|-------------------|----------------------|-------|
| Stage 4 DFS signal bundle | stage4 | $0.073/domain fixed | "10 DFS endpoints × avg $0.0073" | dfs_signal_bundle.py docstring lists 10 endpoints totalling: $0.010+$0.011+$0.011+$0.010+$0.0035+$0.020+$0.002+$0.002+$0.002+$0.006 = $0.0775. Fixed constant is $0.073 vs actual $0.0775 | MISMATCH — fixed constant $0.073 is lower than sum of actual endpoint costs $0.0775 |
| Stage 6 historical rank | stage6 | $0.106/domain fixed | matches historical_rank_overview per-call cost | dfs_labs_client.py:646 = Decimal("0.106") | MATCH |
| Stage 8a verify fills | stage8 (8a) | $0.023/domain fixed | "3 SERP $0.006 + scraper $0.004 + ContactOut ~$0.013" | ContactOut published ~$0.013/call per scraping plan. SERP $0.006 for 3 calls = $0.002 each (matches DFS SERP rate). Scraper $0.004 unverified | PARTIALLY VERIFIED — ContactOut rate unverified, scraper $0.004 unverified |
| Stage 9 social | stage9 | $0.027/domain fixed | "~$0.002 DM + $0.025 company" | Bright Data LinkedIn scraping pricing unverified | UNVERIFIED |
| Pre-run estimate | global | $0.25/domain | "from Pipeline F v2.1 economics doc" | Sum of per-stage costs: stage2 (SERP 5×$0.002=$0.010) + stage3 (Gemini variable) + stage4 ($0.073) + stage6 ($0.106) + stage8 ($0.023) + stage9 ($0.027) + stage10 (Gemini variable) = ~$0.24+ before Gemini | PLAUSIBLE but not reconciled to exact |

### CRITICAL: Stage 4 Cost Discrepancy

`dfs_signal_bundle.py` docstring (lines 35-46) lists 10 endpoints:
- domain_rank_overview $0.010
- competitors_domain $0.011
- keywords_for_site $0.011
- domain_technologies $0.010
- maps_search_gmb $0.0035
- backlinks_summary $0.020
- brand_serp $0.002
- indexed_pages $0.002
- ads_search_by_domain $0.002
- google_ads_advertisers $0.006

Sum = $0.0775

`cohort_runner.py:194` charges $0.073 fixed. Delta = -$0.0045/domain undercharge. At 100-domain cohort = -$0.45 undercount per run.

---

## Section 2b: Env Var Table

### Full env var grep output (src/ and scripts/):

```
src/telegram_bot/chat_bot.py:32:  TELEGRAM_BOT_TOKEN, TELEGRAM_TOKEN
src/telegram_bot/chat_bot.py:33:  TELEGRAM_CHAT_ID
src/telegram_bot/chat_bot.py:34:  SUPABASE_URL
src/telegram_bot/chat_bot.py:35:  SUPABASE_SERVICE_KEY
src/intelligence/gemini_client.py:38:  GEMINI_API_KEY
src/intelligence/contact_waterfall.py:137: APIFY_API_TOKEN
src/intelligence/contact_waterfall.py:235: CONTACTOUT_API_KEY
src/intelligence/contact_waterfall.py:236: HUNTER_API_KEY
src/intelligence/contact_waterfall.py:237: ZEROBOUNCE_API_KEY
src/orchestration/cohort_runner.py:77:  TELEGRAM_TOKEN
src/orchestration/cohort_runner.py:452: DATAFORSEO_LOGIN
src/orchestration/cohort_runner.py:453: DATAFORSEO_PASSWORD
src/orchestration/cohort_runner.py:455: GEMINI_API_KEY
src/orchestration/cohort_runner.py:456: BRIGHTDATA_API_KEY
src/orchestration/flows/cis_learning_flow.py:45: CIS_MIN_OUTCOMES_THRESHOLD
src/orchestration/flows/rescore_flow.py:33: DATABASE_URL
src/orchestration/flows/stage_9_10_flow.py:177: DATABASE_URL
src/orchestration/flows/marketing_automation_flow.py:54: HEYGEN_AVATAR_ID
src/orchestration/flows/marketing_automation_flow.py:55: HEYGEN_VOICE_ID
src/engines/voice_agent_telnyx.py:112: VOICE_WEBHOOK_URL
src/engines/voice_agent_telnyx.py:258: TELNYX_API_KEY
src/engines/voice_agent_telnyx.py:259: ELEVENLABS_API_KEY
src/engines/voice_agent_telnyx.py:260: GROQ_API_KEY
src/engines/voice_agent_telnyx.py:339: TELNYX_CONNECTION_ID
src/engines/voice_agent_telnyx.py:578: DEEPGRAM_API_KEY
src/prefect_utils/failure_alert.py:8: TELEGRAM_TOKEN
src/prefect_utils/callback_writer.py:13: SUPABASE_URL, SUPABASE_SERVICE_KEY
src/evo/tg_notify.py:5: TELEGRAM_TOKEN
src/evo/tg_notify.py:6: TELEGRAM_CHAT_ID
src/integrations/heygen.py:138: HEYGEN_API_KEY
src/integrations/calendar_booking.py:39-44: CAL_API_KEY, CAL_WEBHOOK_SECRET, CALENDLY_API_KEY, CALENDLY_WEBHOOK_SECRET, CALENDLY_ORG_URI, CALENDLY_EVENT_TYPE
src/integrations/leadmagic.py:83: LEADMAGIC_MOCK
src/integrations/telnyx_client.py:59: TELNYX_API_KEY
src/pipeline/free_enrichment.py:194: SPIDER_API_KEY
src/pipeline/intelligence.py:77: ANTHROPIC_API_KEY
scripts/update_webhook_urls.py:33-36: POSTMARK_SERVER_TOKEN, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
```

### Env Var Cross-Reference

Keys present in .env (from `grep -v "^#" /home/elliotbot/.config/agency-os/.env | grep "=" | cut -d= -f1 | sort`):
ABN_LOOKUP_GUID, ANTHROPIC_API_KEY, APIFY_API_TOKEN, APOLLO_API_KEY, BRAVE_API_KEY,
BRIGHTDATA_API_KEY, CLICKSEND_API_KEY, CLICKSEND_USERNAME, CONTACTOUT_API_KEY,
CREDENTIAL_ENCRYPTION_KEY, CSB_API_KEY, DATABASE_URL, DATABASE_URL_MIGRATIONS,
DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
EXPO_TOKEN, GEMINI_API_KEY, GEMINI_API_KEY_BACKUP, GITHUB_TOKEN,
GOOGLE_CEO_BRIEFING_DOC_ID, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
GOOGLE_GMAIL_CLIENT_ID, GOOGLE_GMAIL_CLIENT_SECRET, GOOGLE_INTELLIGENCE_FEED_DOC_ID,
GOOGLE_MANUAL_DOC_ID, GROQ_API_KEY, HEYREACH_API_KEY, HUNTER_API_KEY,
INFRAFORGE_API_DOCS, INFRAFORGE_API_KEY, INFRAFORGE_API_URL, LEADMAGIC_API_KEY,
NAMECHEAP_API_KEY, NAMECHEAP_API_USER, NAMECHEAP_USERNAME,
NEXT_PUBLIC_PLASMIC_PROJECT_API_TOKEN, NEXT_PUBLIC_PLASMIC_PROJECT_ID, OPENAI_API_KEY,
OPENROUTER_API_KEY, PLASMIC_PREVIEW_SECRET, PREFECT_API_URL, PROSPEO_API_KEY,
Railway_Account_Token, Railway_Token, Railway_Workspace_Token, REDIS_URL, RESEND_API_KEY,
SALESFORGE_API_DOCS, SALESFORGE_API_KEY, SALESFORGE_API_URL, SPIDER_API_KEY,
SUPABASE_ACCESS_TOKEN, SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET, SUPABASE_PROJECT_REF,
SUPABASE_SERVICE_KEY, SUPABASE_URL, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, TELNYX_API_KEY,
TEST_DAILY_EMAIL_LIMIT, TEST_EMAIL_RECIPIENT, TEST_MODE, TEST_SMS_RECIPIENT,
TEST_VOICE_RECIPIENT, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER,
UNIPILE_API_KEY, UNIPILE_API_URL, UPSTASH_API_KEY, UPSTASH_EMAIL,
UPSTASH_REDIS_REST_TOKEN, UPSTASH_REDIS_REST_URL, URL, V0_API_KEY, VAPI_API_KEY,
VAPI_PHONE_NUMBER_ID, VERCEL_TOKEN, WARMFORGE_API_DOCS, WARMFORGE_API_KEY,
WARMFORGE_API_URL, WEBSHARE_API_KEY, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET,
ZEROBOUNCE_API_KEY

| Code Key | Env Key | File:Line | In .env | Status |
|----------|---------|-----------|---------|--------|
| TELEGRAM_BOT_TOKEN | TELEGRAM_BOT_TOKEN | chat_bot.py:32 | NO | MISMATCH — code reads TELEGRAM_BOT_TOKEN first, falls back to TELEGRAM_TOKEN. Only TELEGRAM_TOKEN is in .env. Bot will use fallback; no runtime failure, but primary key is missing |
| TELEGRAM_TOKEN | TELEGRAM_TOKEN | cohort_runner.py:77, tg_notify.py:5, failure_alert.py:8 | YES | MATCH |
| TELEGRAM_CHAT_ID | TELEGRAM_CHAT_ID | chat_bot.py:33, tg_notify.py:6 | YES | MATCH |
| SUPABASE_URL | SUPABASE_URL | chat_bot.py:34, callback_writer.py:13 | YES | MATCH |
| SUPABASE_SERVICE_KEY | SUPABASE_SERVICE_KEY | chat_bot.py:35, agent_invoker.py:10 | YES | MATCH |
| GEMINI_API_KEY | GEMINI_API_KEY | gemini_client.py:38, cohort_runner.py:455 | YES | MATCH |
| APIFY_API_TOKEN | APIFY_API_TOKEN | contact_waterfall.py:137,338 | YES | MATCH — NOTE: APIFY is listed as dead reference in CLAUDE.md ("Apify -> Bright Data GMB"). Code still calls Apify in contact_waterfall. GOVERNANCE FLAG |
| CONTACTOUT_API_KEY | CONTACTOUT_API_KEY | contact_waterfall.py:235, contactout_client.py:58 | YES | MATCH |
| HUNTER_API_KEY | HUNTER_API_KEY | contact_waterfall.py:236 | YES | MATCH |
| ZEROBOUNCE_API_KEY | ZEROBOUNCE_API_KEY | contact_waterfall.py:237 | YES | MATCH |
| DATAFORSEO_LOGIN | DATAFORSEO_LOGIN | cohort_runner.py:452 | YES | MATCH |
| DATAFORSEO_PASSWORD | DATAFORSEO_PASSWORD | cohort_runner.py:453 | YES | MATCH |
| BRIGHTDATA_API_KEY | BRIGHTDATA_API_KEY | cohort_runner.py:456, icp_scraper.py:577 | YES | MATCH |
| DATABASE_URL | DATABASE_URL | rescore_flow.py:33 | YES | MATCH |
| HEYGEN_AVATAR_ID | HEYGEN_AVATAR_ID | marketing_automation_flow.py:54 | NO | MISSING — key not in .env. Marketing automation flow will fail at runtime if called |
| HEYGEN_VOICE_ID | HEYGEN_VOICE_ID | marketing_automation_flow.py:55 | NO | MISSING — key not in .env |
| HEYGEN_API_KEY | HEYGEN_API_KEY | heygen.py:138 | NO | MISSING — key not in .env. HeyGen integration will raise IntegrationError on init |
| VOICE_WEBHOOK_URL | VOICE_WEBHOOK_URL | voice_agent_telnyx.py:112 | NO | MISSING — defaults to "https://api.agencyos.com.au". May be intentional default |
| TELNYX_API_KEY | TELNYX_API_KEY | voice_agent_telnyx.py:258 | YES | MATCH |
| ELEVENLABS_API_KEY | ELEVENLABS_API_KEY | voice_agent_telnyx.py:259 | YES | MATCH |
| GROQ_API_KEY | GROQ_API_KEY | voice_agent_telnyx.py:260 | YES | MATCH |
| TELNYX_CONNECTION_ID | TELNYX_CONNECTION_ID | voice_agent_telnyx.py:339 | NO | MISSING — voice calls will use None for connection_id |
| DEEPGRAM_API_KEY | DEEPGRAM_API_KEY | voice_agent_telnyx.py:578 | NO | MISSING — voice transcription will fail |
| POSTMARK_SERVER_TOKEN | POSTMARK_SERVER_TOKEN | update_webhook_urls.py:33 | NO | MISSING — script only, not on active pipeline path |
| CAL_API_KEY | CAL_API_KEY | calendar_booking.py:39 | NO | MISSING — calendar booking disabled |
| CAL_WEBHOOK_SECRET | CAL_WEBHOOK_SECRET | calendar_booking.py:40 | NO | MISSING |
| CALENDLY_API_KEY | CALENDLY_API_KEY | calendar_booking.py:41 | NO | MISSING |
| CALENDLY_WEBHOOK_SECRET | CALENDLY_WEBHOOK_SECRET | calendar_booking.py:42 | NO | MISSING |
| CALENDLY_ORG_URI | CALENDLY_ORG_URI | calendar_booking.py:43 | NO | MISSING — defaults to "" |
| SPIDER_API_KEY | SPIDER_API_KEY | free_enrichment.py:194 | YES | MATCH |
| ANTHROPIC_API_KEY | ANTHROPIC_API_KEY | pipeline/intelligence.py:77 | YES | MATCH |
| LEADMAGIC_API_KEY | LEADMAGIC_API_KEY | settings.py:140 | YES | MATCH |
| CIS_MIN_OUTCOMES_THRESHOLD | CIS_MIN_OUTCOMES_THRESHOLD | cis_learning_flow.py:45 | NO | MISSING — defaults to "20" which is acceptable |
| LEADMAGIC_MOCK | LEADMAGIC_MOCK | leadmagic.py:83 | NO | MISSING — defaults to false (no mock). Acceptable |

---

## Summary of Flags

### Cost Flags

1. **Stage 4 fixed constant undercharges by $0.0045/domain.** `cohort_runner.py:194` charges $0.073 but actual sum of 10 DFS endpoints called in `dfs_signal_bundle.py` is $0.0775. At scale this causes cumulative cost undercount. File: `src/orchestration/cohort_runner.py:194`.

2. **bulk_domain_metrics pricing explicitly marked TBD in code.** `dfs_labs_client.py:1107-1111` contains warning "Pricing TBD — directive says $0.02/batch-of-1000; Manual says $0.001/domain." Using $0.001/domain until DFS pricing page verified. File: `src/clients/dfs_labs_client.py:1107`.

3. **All DFS endpoint costs are internal-only verified.** No external DFS pricing page URL was accessible during this audit. All per-call costs are self-referential (docstring matches Decimal constant) but not cross-referenced to dataforseo.com/pricing. Manual verification required.

4. **Stage 8a $0.023 breakdown partially unverified.** The $0.004 scraper cost and ContactOut $0.013 rate are asserted in a comment but no source is cited.

### Env Var Flags

1. **APIFY_API_TOKEN present in .env but Apify is a dead reference per CLAUDE.md.** `src/intelligence/contact_waterfall.py:137,338` still calls Apify. Governance gap: CLAUDE.md Dead References table says "Apify -> Bright Data GMB". Key is set so no runtime failure, but the service should be replaced. LAW XIII may apply.

2. **HEYGEN_API_KEY, HEYGEN_AVATAR_ID, HEYGEN_VOICE_ID all missing from .env.** HeyGen integration (`src/integrations/heygen.py`) will raise on init. Marketing automation flow (`src/orchestration/flows/marketing_automation_flow.py`) will fail on avatar/voice config check. Not on active Pipeline F path.

3. **TELNYX_CONNECTION_ID missing from .env.** `voice_agent_telnyx.py:339` passes None. Voice call setup may fail.

4. **DEEPGRAM_API_KEY missing from .env.** `voice_agent_telnyx.py:578` will send Authorization header with "Token None". Deepgram transcription will fail.

5. **TELEGRAM_BOT_TOKEN missing from .env.** `chat_bot.py:32` reads TELEGRAM_BOT_TOKEN first with OR fallback to TELEGRAM_TOKEN. Runtime uses fallback correctly — no failure, but the primary key name is not aligned.

6. **Calendar booking keys (CAL_*, CALENDLY_*) all missing.** `src/integrations/calendar_booking.py` — all 6 keys absent. Feature is inactive.
