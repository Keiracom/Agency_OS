# ceo_memory hygiene sweep — flag-before-delete review pass

**Author:** Aiden (design only — per Dave verbatim ts ~1778665450)
**Implementer:** Elliot (post-compact ratification + execute)
**Parallel item:** alongside KEI-37 / KEI-38 / KEI-39 design docs.

## Empirical baseline (live query 2026-05-13)

```sql
SELECT COUNT(*) FROM public.ceo_memory WHERE updated_at < NOW() - INTERVAL '30 days';
-- → 376
```

Note: SLACKBOT artifact-freshness alert ts ~1778660800 said 334; live count is 376 (drift ≈ 12% over the alert window). Cite the live number on each pass.

### Top-level prefix distribution

| Prefix | Count |
|---|---|
| `ceo:` | 253 |
| (other one-off keys — `tier_structure`, `directive_245`, `business_universe_*`, `bu_redesign_mar25`, ...) | 123 |

### `ceo:` sub-prefix sample (first 15)

`directive.336_1_filed` `canonical_parser_principle` `color_rules` `crm_sync_flow_deleted` `directive_250` `directive_227_complete` `multi_brand_policy_ratified` `directive.326` `contactout_100_sample_au_mobile_pct` `design_system` `directive_289` `unit_economics` `directive.F7` `directive_193` `launch_sequence`

## Categorization model

Five buckets. Every stale key falls into exactly one. Bucket determines retain vs prune.

### Bucket A — Retain (architectural / canonical)

Ratified decisions still load-bearing. NEVER prune. Example keys:
- `ceo:stage7_locked`
- `ceo:strategic_decisions`
- `ceo:launch_sequence`
- `ceo:unit_economics`
- `ceo:design_system`
- `ceo:campaign_architecture`
- `ceo:linkedin_infrastructure`
- `ceo:provider_pricing`
- `ceo:source_index`
- `ceo:prototype_ssot`

Match criteria: key name lacks a directive-number / sprint-timestamp / one-shot incident token; key value is a structured-data blob (not narrative log).

### Bucket B — Retain (audit trail — directive completions)

Compliance-audit material per LAW XV. Keep for ≥ 90 days, then archive (not delete). Example keys:
- `ceo:directive_193`, `ceo:directive_227_complete`, `ceo:directive_245`, `ceo:directive_250`, `ceo:directive_266_status`, `ceo:directive_289`, `ceo:directive_326`, `ceo:directive.336_1_filed`, `ceo:directive.F7`
- `directive_024_pr_merge_queue`

Match criteria: key matches `^ceo:directive[._]\d+` or `^directive_\d+`.

### Bucket C — Retain (recent ratified)

Anything updated in the last 7 days is fresh (not stale per the >30d filter, but verify on each run). Skip.

### Bucket D — Archive (sprint state snapshots — superseded)

Operational state from prior sprints. Snapshot-then-prune candidates. Example keys:
- `ceo:sprint_status` (85d old, superseded by current Track 1 state)
- `ceo:savepoint_2026_03_21` (timestamped — superseded by newer savepoints)
- `ceo:bu_redesign_mar25` (sprint timestamp — superseded)
- `ceo:campaign_ux_mar25`
- `ceo:business_universe_message_intelligence_layer`

Match criteria: key contains a date / sprint timestamp / `savepoint_` / `_mar25` / `_apr25` suffix AND the same-conceptual-key has a newer version.

### Bucket E — Prune (one-shot incident markers / superseded research)

Single-use keys whose content is captured elsewhere (PR descriptions, daily logs, fix-forward commits). Safe to delete. Example keys:
- `ceo:crm_sync_flow_deleted` (deletion already happened — incident closed)
- `ceo:contactout_100_sample_au_mobile_pct` (one-time research datapoint)
- `ceo:voice_psychology_research` (subsumed into newer voice strategy keys)
- `bug_275_2` (legacy bug tracker reference)
- `tier_structure` (superseded by `ceo_memory:tier_registry` table)
- `v7_proven_endpoints`, `v7_dead_endpoints` (superseded by ARCHITECTURE.md §3)
- `discovery_model` (legacy discovery — replaced by Pipeline F v2.1)

Match criteria: content references vendors/endpoints in ARCHITECTURE.md §3 (Deprecated Vendors); key name contains `bug_` / `v7_` / `_research`.

## Flag-before-delete review pass

Dave's directive: "flag anything that should be retained before deleting. Do not delete without a review pass first."

### Step 1: Bucket assignment (mechanical)

Run a single SQL query that categorises every stale key by the match criteria above:

```sql
WITH stale AS (
  SELECT key, updated_at, jsonb_typeof(value) AS value_type, char_length(value::text) AS value_size
  FROM public.ceo_memory
  WHERE updated_at < NOW() - INTERVAL '30 days'
)
SELECT
  CASE
    WHEN key ~ '^ceo:directive[._]' OR key ~ '^directive_\d+' THEN 'B-audit'
    WHEN key ~ '_(mar|apr|may|jun|jul|aug|sep|oct|nov|dec)25' OR key ~ 'savepoint_' OR key = 'ceo:sprint_status' THEN 'D-archive'
    WHEN key ~ '^(bug_|v7_|_research$)' OR key IN ('tier_structure', 'discovery_model', 'ceo:crm_sync_flow_deleted') THEN 'E-prune'
    WHEN value_type = 'object' AND value_size > 200 THEN 'A-retain'
    ELSE 'unclassified'
  END AS bucket,
  COUNT(*) AS cnt
FROM stale
GROUP BY 1
ORDER BY 1;
```

Output classifies all 376 keys into one of five buckets + an `unclassified` residual.

### Step 2: Manual review (Elliot, ≤ 30 min budget)

For each `unclassified` key, manual decision: A / B / D / E. Append to the buckets above. Refine the regex match-criteria as patterns emerge.

For each `E-prune` key, sanity-check by reading the value (especially when size > 1000 chars). If anything looks load-bearing, demote to A or B.

### Step 3: Archive-before-delete (D + E)

For D and E buckets, dump to a single JSONL archive at `docs/archive/ceo_memory_pruned_2026_05_13.jsonl`:

```sql
COPY (
  SELECT row_to_json(t)
  FROM (
    SELECT key, value, created_at, updated_at
    FROM public.ceo_memory
    WHERE key IN (<bucket D + E keys>)
  ) t
) TO STDOUT;
```

Commit the archive to git. THEN run the delete in a single transaction:

```sql
BEGIN;
DELETE FROM public.ceo_memory WHERE key IN (<bucket D + E keys>);
SELECT COUNT(*) FROM public.ceo_memory WHERE updated_at < NOW() - INTERVAL '30 days';
COMMIT;
```

Expected post-delete count: ~150-200 (Bucket A + B retained).

### Step 4: Quarterly re-sweep

Add a calendar reminder (or cron) for quarterly hygiene sweep — keeps stale-key drift bounded.

## Acceptance criteria

- Bucket categorisation query output committed to docs/wave2/ceo_memory_bucket_report.md.
- Elliot's manual-review pass complete (all `unclassified` resolved).
- Archive JSONL committed BEFORE delete.
- Post-delete count documented.
- New SLACKBOT artifact-freshness alert returns to under 100 stale entries within 24h of the sweep.

## Failure modes + mitigations

- **Mis-classification → load-bearing key pruned**: archive JSONL is the rollback. Re-insert via `INSERT ... SELECT FROM jsonb_populate_recordset(...)`. Recovery time ≤ 5 min.
- **Bucket A/B incorrectly classified as D/E**: caught at step 2 (manual review) before step 3 deletes. If somehow misses both: archive JSONL rescue.
- **New writes during the sweep**: COPY → DELETE in one transaction prevents partial-state. If a write races against the DELETE, last-write-wins on the row — net effect: that key is retained (DELETE finds nothing to delete by the time it runs). Safe outcome.

## Sequencing

This sweep runs in parallel with KEI-37/38/39 ratification. Elliot owns. Aiden's role:
1. This design doc (DONE).
2. Bucket assignment SQL ready (in step 1).
3. Available for spot-checks on Elliot's manual-review pass if invoked.

Estimated total wall-clock: 45 min (bucket query 5 min + manual review 30 min + archive/delete 5 min + verify 5 min).
