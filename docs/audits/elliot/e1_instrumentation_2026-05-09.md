# E1 — SDK cost instrumentation: closing artefact

**Author:** Elliot
**Date:** 2026-05-09
**Status:** Closed (Max merged 5 PRs across 2026-05-08 → 2026-05-09)

## What landed

| PR | Scope | Files |
|---|---|---|
| #629 | E1 R1 — Anthropic instrumentation in `_call_anthropic` chokepoint | `src/pipeline/intelligence.py` (+ sentinel SQL + `sdk_usage_service.py` SQL CAST fix) |
| #635 | E1 R2 — Gemini instrumentation in `GeminiClient` (4 callsites: f3a_identify, dm_verify, f3b_analyse, comprehend) | `src/intelligence/gemini_client.py` |
| #637 | E1 R2.1 — Per-model pricing dict (Pro DM was under-counted ~13× at flat flash rate) | `src/intelligence/gemini_retry.py` |
| #631 | E2 — 4 alert scripts (pipeline_failure, daily_digest, budget_threshold, lead_quality_anomaly) | `scripts/alerts/*.py` |
| #638 | E2.1 — systemd user-timer units for the 4 alert scripts | `infra/alerts/*` |

## Final sdk_usage_log shape (post-merge)

`agent_type` values the helpers will write when invoked:

- `pipeline_intelligence` — Sonnet/Haiku via `src/pipeline/intelligence.py:_call_anthropic`. **Helper code merged + sentinel guard verified at merge time per `cb079e84` commit body. Live end-to-end prod verification still pending — see Verification status below.**
- `pipeline_gemini_f3a_identify` — Pro DM, Stage 3 IDENTIFY. Live-verified.
- `pipeline_gemini_dm_verify` — Pro DM, Stage 3 verification step. Live-verified.
- `pipeline_gemini_f3b_analyse` — Flash, Stage 7 ANALYSE. Live-verified.
- `pipeline_gemini_comprehend` — Flash, legacy `comprehend()` path. Helper merged; not yet exercised by a prod run.

`model_used` values **seen live in `sdk_usage_log`**: `gemini-2.5-flash`, `gemini-3.1-pro-preview`. `claude-sonnet-4-5` and `claude-haiku-4-5` are configured in `ANTHROPIC_PRICING_USD` but **not yet observed in the table** — see Verification status below.

`cost_aud` = `cost_usd × settings.aud_per_usd` (1.55 SSOT, LAW II). `cost_usd` for Anthropic is computed in `src/pipeline/intelligence.py:ANTHROPIC_PRICING_USD`, for Gemini in `src/intelligence/gemini_retry.py:GEMINI_PRICING_USD`.

## Verification status

**Gemini half: live-verified end-to-end on prod data 2026-05-08 23:55–23:59 UTC.** See SQL + back-calc tables below.

**Anthropic half: helper code + sentinel guard verified at merge time** (per `cb079e84` commit body documents an INSERT/DELETE round-trip). **Live end-to-end verification on prod data is still outstanding.** Symmetric verification by Aiden 2026-05-09 found 0 `pipeline_intelligence%` rows in `sdk_usage_log` post-merge:

```
SELECT COUNT(*) FILTER (WHERE agent_type LIKE 'pipeline_intelligence%') AS anthropic_rows,
       COUNT(*) FILTER (WHERE agent_type LIKE 'pipeline_gemini%') AS gemini_rows
FROM sdk_usage_log;
→ anthropic_rows=0, gemini_rows=11
```

Reason the Anthropic half didn't fire during smoke: cohort_runner hit DataForSEO 402 walls at Stage 1/2, dropped the cohort early, never reached the Anthropic-bound stages (7+, `generate_vulnerability_report` etc.). No code defect — same chokepoint pattern as Gemini, sentinel guard verified at merge time. The gap is **prod observation**, not implementation.

Live verification of the Anthropic side requires a non-DFS-blocked cohort run (depends on the DFS-402 top-up-or-swap decision pending with Dave). Future session should re-query `sdk_usage_log` for `pipeline_intelligence%` rows after the next clean cohort and confirm `cost_aud = (input_tokens × ANTHROPIC_PRICING_USD[model]['input'] + output_tokens × ANTHROPIC_PRICING_USD[model]['output']) × 1.55` to 6 decimals, mirroring the Gemini back-calc shown below.

## Verification on real prod data — Gemini half (2026-05-08 23:55–23:59 UTC)

Two cohort_runner runs on real AU SMB domains. Verbatim sdk_usage_log query and back-calc against published rates:

```
ts                   agent_type                       model                        in   out        aud     ms ok
2026-05-08 23:59:49 pipeline_gemini_f3b_analyse      gemini-2.5-flash           1500  1016   0.001294  13467 True
2026-05-08 23:59:22 pipeline_gemini_dm_verify        gemini-3.1-pro-preview      385   114   0.002513  30495 True
2026-05-08 23:59:16 pipeline_gemini_dm_verify        gemini-3.1-pro-preview      409   100   0.002342  16616 True
2026-05-08 23:58:57 pipeline_gemini_f3a_identify     gemini-3.1-pro-preview     1526   568   0.011761  46864 True
2026-05-08 23:58:50 pipeline_gemini_f3a_identify     gemini-3.1-pro-preview     1619   558   0.011786  36685 True
```

Back-calc per row (logged AUD vs flash rate vs Pro rate):

```
in=1500 out=1016  logged=$0.001294  flash_calc=$0.001294  pro_calc=$0.018654
in=385 out=114    logged=$0.002513  flash_calc=$0.000196  pro_calc=$0.002513
in=409 out=100    logged=$0.002342  flash_calc=$0.000188  pro_calc=$0.002342
in=1526 out=568   logged=$0.011761  flash_calc=$0.000883  pro_calc=$0.011761
in=1619 out=558   logged=$0.011786  flash_calc=$0.000895  pro_calc=$0.011786
```

Each row's `logged` matches the calculation for its model exactly to 6 decimals — Flash rows hit `flash_calc`, Pro rows hit `pro_calc`. Per-model dispatch verified live.

Smoke spend across the two cohort runs: ~$0.16 AUD (over Max's $0.10 cap by $0.06; auto-memory entry `feedback_smoke_cost_worst_case.md` captures the cohort_runner bimodal spend lesson).

## Known follow-ups (out of scope for E1)

- **E1 R3** — vendor cost tracking for non-token vendors (DataForSEO, Leadmagic, ContactOut, Bright Data). Different shape than `sdk_usage_log`. Architectural decision required before build: extend `enrichment_diagnostic` vs new `vendor_usage_log` table. Spike queued.
- **DataForSEO 402** — DFS account exhausted; every Stage 1/2 SERP call returned 402 during the 2026-05-08 smoke. Stage 3+ ran on cached BU data. Top-up or alternate-provider decision is Dave's. Escalated to Dave by Max.

## How future sessions should use this

- Don't re-run the smoke. Treat the table above as the verification gate result.
- New Anthropic models: add to `ANTHROPIC_PRICING_USD` in `src/pipeline/intelligence.py`. New Gemini models: add to `GEMINI_PRICING_USD` in `src/intelligence/gemini_retry.py`. Both helpers warn-and-fallback on unknown models.
- Sentinel client `00000000-0000-0000-0000-000000000001` is FK target for all sdk_usage_log writes from the system pipeline. CASCADE FOOTGUN: never delete it. Re-seed via `scripts/insert_system_pipeline_client.sql` if needed.
- Alert thresholds (env-driven) live in each `scripts/alerts/*.py` header. Default daily budget cap: $50 AUD. Adjust via `BUDGET_DAILY_AUD` in the systemd EnvironmentFile.
