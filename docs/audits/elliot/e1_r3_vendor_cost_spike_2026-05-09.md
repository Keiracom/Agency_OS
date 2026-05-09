# E1 R3 — Vendor cost tracking: architecture spike

**Author:** Elliot
**Date:** 2026-05-09
**Status:** Spike (no code; recommendation for Dave's decision)
**Scope:** Track per-call cost for non-token vendors (DataForSEO, Bright Data, Leadmagic, ContactOut). E1 R1/R2/R2.1 covered token-shaped AI vendors only.

## Current state

Vendor clients **compute cost in-memory** but **never persist it**. Example from `src/integrations/leadmagic.py`:

```python
self.total_cost_aud: float = 0.0
…
cost = self._track_cost(_cost_aud(COST_EMAIL_FINDER_USD)) if found else 0.0
```

`cost_aud` lives on the result object and on a process-local running total. Once the process exits, the number is lost.

`enrichment_diagnostic` (59 rows in prod) has **per-tier success flags** (`t15_success`, `tdm0_success`, `stage2_success`, `t3_success`) and **raw response JSONB**, but **no cost columns**. It's a per-lead/per-run diagnostic snapshot, not a per-call ledger.

Net: every DataForSEO SERP call, Leadmagic email find, ContactOut record, and Bright Data GMB lookup is invisible to cost dashboards.

## Three options

### A. Extend `enrichment_diagnostic` with cost columns
Add `t15_cost_aud`, `tdm0_cost_aud`, `stage2_cost_aud`, `t3_cost_aud` (or a JSONB `costs` column).

| Pro | Con |
|---|---|
| Existing table | 1 row = 1 lead-run = N vendor calls — can't separate per-call within a tier |
| Already keyed by `lead_id` | Vendor names hard-coded into column names; new vendor = migration |
| Same write site as the rest of the diagnostic | Diagnostic table stops being purely diagnostic — semantic muddle |

### B. New `vendor_usage_log` table (parallel to `sdk_usage_log`)
Per-call ledger, mirrors `sdk_usage_log` shape but with vendor-shaped fields.

| Pro | Con |
|---|---|
| Per-call granularity preserved (1 row = 1 API hit) | New table = migration + model + service |
| Vendor-agnostic schema (`vendor`, `endpoint`, `units`, `units_unit`) | Two cost tables to query for "total spend last 24h" |
| Easy dashboard alignment with `sdk_usage_log` | Schema decisions for credits-vs-records-vs-calls need care |
| New vendor = data, not migration | |

Schema sketch:

```
vendor_usage_log
  id              uuid PRIMARY KEY
  client_id       uuid REFERENCES clients(id)            -- sentinel for pipeline
  lead_id         uuid REFERENCES leads(id) NULL
  vendor          text NOT NULL                          -- "dataforseo" | "leadmagic" | "contactout" | "brightdata"
  endpoint        text NOT NULL                          -- "domain_rank_overview" | "find_email" | "phone_lookup" | "gmb_lookup"
  units           integer NOT NULL DEFAULT 1             -- records / credits / api_calls
  units_unit      text NOT NULL                          -- "records" | "credits" | "api_calls"
  cost_aud        numeric(10, 6) NOT NULL DEFAULT 0
  duration_ms     integer NOT NULL DEFAULT 0
  success         boolean NOT NULL DEFAULT true
  error_message   text NULL
  created_at      timestamptz NOT NULL DEFAULT now()
  deleted_at      timestamptz NULL
```

### C. Unify into `sdk_usage_log` with vendor-shaped `agent_type`
Reuse the table; treat `model_used` as `"dfs:domain_rank_overview"` etc. and zero out `input_tokens`/`output_tokens`.

| Pro | Con |
|---|---|
| Single table, single dashboard query | `model_used` column lies (vendor endpoint isn't a model) |
| No new migration | `input_tokens`/`output_tokens` become permanently NULL or 0 — schema lies |
| | Mixes token-shaped and call-shaped accounting under one `cost_aud` — masks rate sensitivity |

## Recommendation: **Option B**

Three reasons:

1. **Per-call granularity is load-bearing.** DFS bills per endpoint and per `live_advanced` vs `live_regular` mode; collapsing N calls into one tier-row in `enrichment_diagnostic` (Option A) loses the dimension we'd want to optimise on.
2. **Schema honesty.** Option C makes `model_used` and the token columns lie; future readers chase a non-existent token-cost relationship. The "currency label must match value" memory pin (`feedback_currency_label_must_match_value.md`) applies — column names must match what they store.
3. **New-vendor cost is data, not migration.** Adding a 5th vendor to Option B is `INSERT INTO vendor_usage_log (vendor, …)` — no DDL. Option A requires a migration for every new vendor.

## What would land in Round 3 build

If Dave approves Option B:

1. Migration: `vendor_usage_log` table + sentinel `client_id` reuse.
2. New writer: `src/services/vendor_usage_service.py:log_vendor_usage()` (mirrors `log_sdk_usage`).
3. Helper `_log_vendor_call_to_usage()` in each integration client (DataForSEO, Bright Data, Leadmagic, ContactOut) — same fail-open pattern as the Anthropic/Gemini helpers.
4. Update existing `total_cost_aud` accumulators to **also** call the helper (don't replace — keep in-memory tally for retry/cost-cap logic that already depends on it).
5. New alert: `scripts/alerts/vendor_budget_alert.py` (mirrors budget_threshold_alert.py shape) summing `vendor_usage_log.cost_aud` against a separate per-vendor cap env. Dashboards aggregate `sdk_usage_log` + `vendor_usage_log` to get total spend.

Estimate: ~250 LOC across 1 migration + 1 service + 4 client edits + 1 alert. Three PRs (migration+service, client wiring, alert) for clean review boundaries.

## Why not now

This spike deliberately stops at the table-shape decision because:
- DataForSEO is currently 402-locked (Stage 1/2 broken — Dave decision pending on top-up vs alternate provider). Building cost-tracking on a vendor we may swap is wasted scaffolding. **Option B's `vendor` column tolerates the swap (just write `serpapi` instead of `dataforseo`)**, so the table shape is forward-compatible — but the client-wiring step (item 3 above) should land *after* the DFS decision so we don't write a wrapper for a deprecated client.
- The Round 3 build is sequenceable behind a single shape decision. That decision is what this spike asks Dave to make.

## Decision requested

Pick one: **A** (extend enrichment_diagnostic) / **B** (new vendor_usage_log, recommended) / **C** (unify into sdk_usage_log).

If B, also greenlight the 3-PR build sequence above. If A or C, I'll re-spike on the chosen path.
