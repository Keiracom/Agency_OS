# A5 piece 5 — Smoke Recall Validation (2026-05-27)

**bd:** Agency_OS-c23f (this validation), Agency_OS-ygxz (piece 4 open gap)
**Script:** `scripts/migrations/a5_smoke_recall.py`
**Results:** `runtime/a5_smoke_recall_results.json` (transient — re-runs overwrite)
**Frozen evidence:** `docs/migration/evidence/a5_smoke_recall_results_2026-05-27.json` (this PR)
**Run timestamp:** 2026-05-27T09:49:13Z (post-Drive-Manual-expansion + post-piece-1b-merge)

## Verdict

**3/4 PASS (rc=1 strict; 75% surface coverage with materially stronger signal vs 2026-05-26 baseline).** Piece 4 remains the same known operator-prereq gap that was open before — Slack #ceo archive not yet exported + ingested. Tracked in Agency_OS-ygxz.

## Per-piece result

| Piece | Wrapper | Query | Memories | Relevant | Δ vs 2026-05-26 |
|---|---|---|---:|---:|---:|
| piece_1b_ceo_memory | DecisionWrapper | "Dave A5 backfill decision policy memory test" | 47 | **8** | **+700%** (1 → 8) |
| piece_2_weaviate_snapshot | DecisionWrapper | "Phase A3 reader cutover orchestrator Atlas" | 67 | **23** | **+666%** (3 → 23) |
| piece_3_drive_manual | DecisionWrapper | "boundary matrix Section 13 directive ratified" | 60 | **32** | **+166%** (12 → 32) |
| piece_4_slack_ceo | TaskContextWrapper | "Dave A5 piece backfill ceo directive" | 3 | **0** | **0** (unchanged) |

## Signal-recovery interpretation

Relevance threshold is `≥2 signal tokens per memory` (Scout's `run_recall_tests.py` conservative-relevance heuristic). The 3 passing pieces went from squeaking past the gate (1-12 relevant memories) to comfortable margins (8-32). Two compounding causes:

1. **Piece 1b ceo_memory HTTP executor merged** since baseline run — DecisionWrapper recall now hits the canonical ceo_memory store, not just the old smoke seeds.
2. **Piece 3 Drive Manual expanded** 2026-05-27 from docs/MANUAL.md only (23 chunks) to docs/MANUAL.md + Keiracom Manual (15 chunks) + Keiracom Architecture V2 Inventory (27 chunks) + Keiracom V2.0 Deep-Dive Audit (6 chunks). Total 48 new chunks → +638 atomized facts in `fleet_smoke` (703 → 1341 fact_count).

Piece 2 weaviate_snapshot's +666% improvement is a side-effect of piece 1b + piece 3 corpus growth — the DecisionWrapper recall surface expanded, so semantically-adjacent Weaviate-snapshot atoms surface higher in recall.

## Piece 4 gap — operator prereq, already filed

`piece_4_slack_ceo` returned only 3 memories total and 0 relevant against the query "Dave A5 piece backfill ceo directive". The backfill script `scripts/migrations/slack_ceo_backfill_to_hindsight.py` exists; the state file `runtime/a5_piece_4_slack_ceo_state.jsonl` does NOT — backfill never run with `--execute`.

Root cause: piece 4 needs a Slack #ceo archive export as input (JSONL per `slack_ceo_backfill_to_hindsight.py` docstring). That export requires operator-side Slack API access + classifier pass; not a worker-tier task.

**Already tracked:** `Agency_OS-ygxz · [ATLAS] A5 piece 4 — 2-month Slack #ceo archive backfill to Hindsight · P1 IN_PROGRESS`.

No new bd issue filed — gap is already open under its canonical KEI.

## What this validates

Cutover Readiness Gate **STATE_SEPARATION knowledge-state-pgvector** criterion at the recall-surface level:

- 3 of 4 historical-content sources surface relevant memories on canonical anchor queries.
- Cross-source compounding works — atoms from piece 1b + 3 lift piece 2's recall via semantic adjacency.
- The recall harness is itself trustworthy — query 1's 1 relevant baseline grew to 8 only because the ceo_memory + Drive Manual corpora grew; query was unchanged.

What this does NOT validate (preserved as honest gaps):

- Cross-tenant recall isolation (this whole surface runs under single `FLEET_TENANT_ID`).
- piece 4 Slack #ceo archive (gap above).
- Recall quality at scale beyond ≥2-signal-token threshold — relevance heuristic is conservative; precision/recall ROC not measured.
- Incremental sync — these are one-shot backfills; ongoing Drive/Slack edits don't auto-flow until Phase B incremental-sync pipeline ships.

## How to re-run

```bash
python3 scripts/migrations/a5_smoke_recall.py --out runtime/a5_smoke_recall_results.json
# rc=0 if all 4 probes pass; rc=1 if any fail (currently rc=1 on piece_4)
```

Hindsight + tenant extension must be running on `localhost:8889` under `FLEET_TENANT_ID=00000000-0000-0000-0000-000000000001`.

## Anchors

- Path (C) dual-store resolution (Dave 2026-05-25): Atlas Drive Manual + Slack #ceo backfills land in Hindsight under `FLEET_TENANT_ID`.
- Five-store completion rule (RATIFIED-CEO 2026-05-26): nothing is done until the runtime proves it. This validation IS the runtime proof for pieces 1b/2/3.
- Viktor 2026-05-25 gap: A3 dual-write mirror covers FORWARD writes only; A5 backfills historical content. 3/4 historical sources now empirically retrievable.
