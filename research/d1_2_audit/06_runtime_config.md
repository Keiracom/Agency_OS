# AUDIT 6: RUNTIME CONFIG vs CODE EXPECTATIONS

## 1. Env Vars Expected by Pipeline F v2.1

Code analysis across `src/intelligence/` and `src/orchestration/cohort_runner.py`:

**Expected env vars (9 total):**
- APIFY_API_TOKEN
- BRIGHTDATA_API_KEY
- CONTACTOUT_API_KEY
- DATAFORSEO_LOGIN
- DATAFORSEO_PASSWORD
- GEMINI_API_KEY
- HUNTER_API_KEY
- TELEGRAM_TOKEN
- ZEROBOUNCE_API_KEY

**Where used:**
- `gemini_client.py:38` — GEMINI_API_KEY
- `contact_waterfall.py:137,338` — APIFY_API_TOKEN
- `contact_waterfall.py:235-237` — CONTACTOUT_API_KEY, HUNTER_API_KEY, ZEROBOUNCE_API_KEY
- `enhanced_vr.py:147` — GEMINI_API_KEY
- `cohort_runner.py:77` — TELEGRAM_TOKEN
- `cohort_runner.py:452-456` — DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD, GEMINI_API_KEY, BRIGHTDATA_API_KEY

---

## 2. Env Vars Actually Set

**Status: All 9 required vars present in /home/elliotbot/.config/agency-os/.env**

| Env Var | Status |
|---------|--------|
| APIFY_API_TOKEN | PRESENT |
| BRIGHTDATA_API_KEY | PRESENT |
| CONTACTOUT_API_KEY | PRESENT |
| DATAFORSEO_LOGIN | PRESENT |
| DATAFORSEO_PASSWORD | PRESENT |
| GEMINI_API_KEY | PRESENT |
| HUNTER_API_KEY | PRESENT |
| TELEGRAM_TOKEN | PRESENT |
| ZEROBOUNCE_API_KEY | PRESENT |

**Additional optional vars noted:**
- GEMINI_API_KEY_BACKUP (fallback)
- APIFY_API_TOKEN (verified available)

---

## 3. Prefect Deployments

**Pipeline F v2.1 deployment status:**

No dedicated "Pipeline F v2.1" or "cohort_runner" deployment found in active Prefect list.

**Current deployments (27 active, all work pool: agency-os-pool):**
1. batch_campaign_evolution
2. campaign_activation
3. campaign_evolution
4. cis-learning-engine (manual + weekly variants)
5. credit_reset_check
6. crm-sync-flow
7. daily_enrichment
8. daily_learning_scrape
9. hourly_outreach
10. icp_onboarding_flow
11. icp_reextract_flow
12. intelligence_research
13. monthly_replenishment
14. pattern_backfill
15. persona_buffer_replenishment
16. pool_campaign_assignment
17. pool_daily_allocation
18. pool_population
19. post_onboarding_setup
20. reply_recovery
21. single_client_backfill
22. single_client_pattern_learning
23. trigger_lead_research
24. voice-outreach-flow
25. warmup_monitor
26. weekly_pattern_learning

**Finding:**
- Pipeline F v2.1 `cohort_runner.py` is currently RUN-ONLY via CLI (standalone async script)
- No Prefect Flow wrapper deployed for cohort_runner
- All deployments appear to be v1 legacy flows or orchestration runners

---

## 4. Supabase Table Writes

**Code analysis for Pipeline F writes to Supabase:**

Grep results show NO direct Supabase writes in cohort_runner:
- No `supabase.`, `.insert()`, `.update()`, `.upsert()`, `cursor.execute()`, or `commit()` patterns
- References to `business_universe` and `lead_pool` are **DATA SHAPE ONLY** (funnel classification labels)

**Actual behavior:**
- `funnel_classifier.py:28,48,52` — Computes `lead_pool_eligible` flag in memory
- `cohort_runner.py:385,400` — Filters and counts `lead_pool_eligible` records
- **All output written to local JSON files only** (scripts/output/)

**Output flow:**
```python
_write_outputs(pipeline, out_path)  # Writes JSON to disk
_build_summary(pipeline, wall_s)    # Returns in-memory summary dict
```

**File output examples:**
- `scripts/output/cohort_run_YYYYMMDD_HHMMSS/summary.json`
- `scripts/output/cohort_run_YYYYMMDD_HHMMSS/{domain}.json` (per-domain card)

---

## Summary Table: Expected vs Actual

| Resource | Expected | Actual | Status |
|----------|----------|--------|--------|
| **GEMINI_API_KEY** | Code requires | Present in .env | PASS ✓ |
| **BRIGHTDATA_API_KEY** | Code requires | Present in .env | PASS ✓ |
| **DATAFORSEO_LOGIN** | Code requires | Present in .env | PASS ✓ |
| **DATAFORSEO_PASSWORD** | Code requires | Present in .env | PASS ✓ |
| **APIFY_API_TOKEN** | Code requires | Present in .env | PASS ✓ |
| **CONTACTOUT_API_KEY** | Code requires | Present in .env | PASS ✓ |
| **HUNTER_API_KEY** | Code requires | Present in .env | PASS ✓ |
| **ZEROBOUNCE_API_KEY** | Code requires | Present in .env | PASS ✓ |
| **TELEGRAM_TOKEN** | Code optional (Telegram alerts) | Present in .env | PASS ✓ |
| **Prefect Flow (cohort_runner)** | Could be deployed | Not deployed | INFO: CLI-only |
| **Supabase writes (BU/lead_pool)** | Code pattern check | No writes detected | PASS: Local JSON only |

---

## Notes

1. **Runtime config is complete**: All 9 required env vars are present.
2. **Pipeline F is CLI-based**: No Prefect deployment wrapper. Run via `python -m src.orchestration.cohort_runner`.
3. **Supabase integration**: Pipeline F v2.1 does NOT write to Supabase. Output is local JSON only. Classification state (lead_pool_eligible) is computed in-memory and never persisted.
4. **Cost tracking**: Pipeline computes cost_usd and cost_aud in summary; no database persistence required.

---

**Audit conducted:** 2026-04-14 (HEAD: 6fabf01)
**Codebase version:** Pipeline F v2.1
**Config location:** /home/elliotbot/.config/agency-os/.env
