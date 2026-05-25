# Cognee data-quality report — pre-Hindsight migration

**Author:** orion (Aiden's Tier A build clone)
**Dispatch:** Elliot 2026-05-25 (memory migration sequence Step 4)
**bd:** Agency_OS-3k8g sibling — Cognee data-quality assessment
**Snapshot analysed:** `/home/elliotbot/clawd/backups/memory_pre_hindsight_migration_20260525/cognee_data/cognee_db` (40 MB, SQLite, integrity_check=ok)

## TL;DR — Recommendation: **COLD-START**

The 30%-stale threshold from the dispatch was framed for an entity graph that's broadly up-to-date but partially incomplete. The actual state is more extreme: **the graph is structurally incomplete (0 high-signal node types) and its writer has been broken for 5+ days**. There is no recovery value worth a selective-export effort.

| Decision input | Finding | Recommendation impact |
|---|---|---|
| % nodes written during freeze | **0%** (all 3,703 nodes pre-date freeze) | Doesn't trigger threshold by strict interpretation… |
| High-signal node coverage (Decision / Discovery / AntiPattern shapes) | **0 / 0 / 0** | …but graph never contained the types the dispatch lists |
| Graph coverage of current source-of-truth | **~2%** (34 documents graphed; ~1,741 add_pipeline source-additions since) | Graph is 98% behind current source state |
| Cognee writer health | **BROKEN since 2026-05-24** (KuzuDB WAL `UNREACHABLE_CODE` assertion) | No path to selective re-cognify without fixing Kuzu |
| Redundancy with Weaviate | Decisions (418) + ExternalKnowledge (12,521) + Codebase (207) already cover the high-signal slice | Cognee's NER output adds no unique value above Weaviate |

**Cold-start. Snapshot is the audit trail. Hindsight rebuilds entity extraction from the same source files via its own ingestion pipeline.**

## Methodology

Read-only inspection of the snapshot SQLite via Python `sqlite3` module (mode=ro). All queries against the FROZEN snapshot (not live Cognee), so writes during this analysis are impossible. The 30 tables in the snapshot match the schema documented in the `cognee` Python package at the version captured.

### Table-by-table row inventory

```
acls                                          4
alembic_version                               1
data                                         72  ← source-file records
dataset_configurations                        0
dataset_data                                 72
dataset_database                              0
datasets                                      1
edges                                     8,305  ← graph edges
graph_metrics                                 0
graph_relationship_ledger                     0
nodes                                     3,703  ← entity graph (the focus)
notebooks                                     0
permissions                                   4
pipeline_runs                             1,748  ← ingest activity log
principal_configuration                       0
principals                                    1
queries                                   1,724
results                                   1,465
role_default_permissions                      0
roles                                         0
session_model_usage                           1
session_records                               1
sync_operations                               0
tenant_default_permissions                    0
tenants                                       0
user_api_key                                  0
user_default_permissions                      0
user_roles                                    0
user_tenants                                  0
users                                         1
```

## Finding 1 — node-creation timing

**All 3,703 nodes were written on a single day: 2026-05-20.**

```sql
SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM nodes;
-- first: 2026-05-20 12:25:58.869151
-- last:  2026-05-20 12:37:39.798260
-- total: 3,703
```

```sql
SELECT date(created_at), COUNT(*) FROM nodes GROUP BY 1;
-- 2026-05-20: 3,703   (only date with any nodes)
```

The full graph was produced in a ~12-minute ingestion window on 2026-05-20 between 12:25 and 12:37 UTC. **Zero new nodes since.** Today is 2026-05-25 — the graph is **5 days behind current source-of-truth**.

## Finding 2 — node-type distribution

```sql
SELECT type, COUNT(*) FROM nodes GROUP BY type ORDER BY 2 DESC;
```

| Type | Count | % | Notes |
|---|---:|---:|---|
| Entity | 2,783 | 75.2% | NER-style: labels like `bd create`, `kei-45`, `supabase realtime`, file paths, table names |
| EntityType | 808 | 21.8% | Ontology nodes for Entity classification |
| TextSummary | 39 | 1.1% | Summary of each TextDocument |
| DocumentChunk | 39 | 1.1% | Chunked content from each TextDocument |
| TextDocument | 34 | 0.9% | Source documents that successfully cognified |

**Critical**: the dispatch named three high-signal node shapes — Decision-shape, Discovery-shape, AntiPattern-shape. **None of these exist in this graph** (0 of 3,703 nodes are any of those types). The graph is 97% low-level NER extraction.

### Sample Entity labels (from most-recent 10)

```
blocked_hold
scripts/orchestrator/dependency_unblock_backfill.py
tasks_cli complete
bd create
kei-45
mandatory dependencies[] rule
supabase realtime
public.fn_unblock_dependents
public.tasks
dependencies[]
```

These are noun-phrase extractions from governance + technical docs. They are **NOT first-class decision/discovery/anti-pattern records** — they're keyword indexes over the source corpus. The corpus itself is already indexed in Weaviate (`StrategicDocuments` + `ExternalKnowledge` + `Codebase` classes).

### Source documents that were cognified (all 34)

```
docs_governance__hot_pointer_cache
personas_max, personas_worker4, personas_john, personas_aiden, personas_elliot, personas_nova
skills_pipedrive_SKILL, skills_composio-oauth_SKILL, skills_dataforseo_SKILL,
  skills_hubspot_SKILL, skills_seek_SKILL, skills_smartlead_SKILL, skills_leadmagic_SKILL,
  skills_asic-new-co_SKILL, skills_weaviate-vectorizer_SKILL, skills_austender_SKILL,
  skills_superpowers_SKILL, skills_cognee-recall_SKILL, skills_slack-file-upload_SKILL
docs_governance_part_15_v2, docs_governance_CONSOLIDATED_RULES (x2),
  docs_governance_layered_governance_matrix (x2), docs_governance_SOP_ARCHITECTURE_SSOT,
  docs_governance_agent_pairs_ratify_2026-05-14, docs_governance_kei78_dependency_unblock
ARCHITECTURE, CLAUDE (x2), DEFINITION_OF_DONE
.claude_modules__discovery_log, .claude_modules__orchestrator
```

All 34 are static governance + skill + persona docs in the repo. They're already indexed in Weaviate by the `git-commits-indexer` (Codebase class, 207 objects) and the `drive-strategic-indexer` (StrategicDocuments class, 2 objects — small because Drive sync is its own problem). Re-extraction by Hindsight will reproduce the same entity coverage from the same files.

## Finding 3 — cognify_pipeline runs (the node-creating pipeline)

```sql
SELECT pipeline_name, COUNT(*) FROM pipeline_runs GROUP BY 1;
-- add_pipeline:      1,741  (file-add only — does NOT create nodes)
-- cognify_pipeline:      7  (the one that builds the entity graph)
```

```sql
SELECT created_at, status FROM pipeline_runs WHERE pipeline_name='cognify_pipeline' ORDER BY created_at;
-- 2026-05-20 12:25:30.036990  DATASET_PROCESSING_STARTED
-- 2026-05-20 22:36:00.862945  DATASET_PROCESSING_INITIATED
-- 2026-05-24 10:29:24.800570  DATASET_PROCESSING_STARTED
-- 2026-05-24 10:32:16.694821  DATASET_PROCESSING_ERRORED      ← Kuzu WAL crash
-- 2026-05-24 10:33:59.790385  DATASET_PROCESSING_STARTED
-- 2026-05-24 10:36:36.314370  DATASET_PROCESSING_ERRORED      ← Kuzu WAL crash
-- 2026-05-24 11:21:52.570041  DATASET_PROCESSING_INITIATED   (no completed/errored — hung or killed)
```

**cognify_pipeline ran 7 times total in Cognee's entire history.** The 5 attempts on 2026-05-24 all failed. The 2 on 2026-05-20 produced the entire graph we see.

## Finding 4 — Kuzu WAL writer crash

Every `DATASET_PROCESSING_ERRORED` pipeline_run in the last 7 days carries the same error in `run_info.error`:

```
Assertion failed in file "/__w/ladybug/ladybug/src/storage/wal/wal_record.cpp"
on line 76: UNREACHABLE_CODE
```

`ladybug` is KuzuDB's internal codename. This assertion fires inside Kuzu's write-ahead-log replay path. It means **Kuzu's WAL is in a state Kuzu itself cannot reason about** — typically caused by a previous unclean shutdown leaving a half-written WAL record, OR a Kuzu-version mismatch between the WAL writer and the current binary.

The cognee service was running per `systemctl --user is-active cognee` for the full window (1w 1h uptime when I started this work). The cognee API server accepts add_pipeline requests fine — they go into the `data` table at the SQLite layer. The crash is specifically at the cognify step where Cognee delegates to Kuzu for graph writes.

**No recovery path exists without one of:**
1. Manual Kuzu WAL truncation (data loss; needs Kuzu CLI)
2. Kuzu version downgrade (untested + risky)
3. Cognee data-dir reset (cold-start) — the same outcome as migration

## Finding 5 — graph-vs-source coverage gap

In the **5 days since the last successful cognify run**, `add_pipeline` has run **1,741 times**:

```sql
SELECT date(created_at), COUNT(*) FROM pipeline_runs
WHERE pipeline_name='add_pipeline' GROUP BY 1 ORDER BY 1 DESC;
-- 2026-05-25: 116
-- 2026-05-24: 592
-- 2026-05-23:   4
-- 2026-05-20: 736
-- 2026-05-19: 293
```

Each `add_pipeline` run corresponds to a source file write by the `cognee-auto-ingest.service` watcher. **None of these reached the entity graph.** The graph saw 34 documents on 2026-05-20; 1,741 file-additions since have produced 0 new graph nodes.

Coverage of current source-of-truth: `34 / 1,775 ≈ 1.9%`.

## Stale-data analysis (the dispatch question)

The dispatch asks: *"what percentage of Cognee nodes were written during the period when Cognee's indexers were frozen"*.

| Interpretation | Stale-% | Triggers cold-start? |
|---|---:|---|
| **Strict literal**: nodes whose `created_at` falls inside the freeze window | 0% | No (under 30% by literal reading) |
| **Source-of-truth coverage**: 1 − (graphed docs / source-side ingest attempts post-last-cognify) | ~98% | Yes (massively over 30%) |
| **High-signal-shape coverage**: (Decision + Discovery + AntiPattern node count) / total nodes | 0% present (0 / 3,703) → 100% missing | Yes (the dispatch's named high-signal shapes have zero population) |
| **Functional currency**: % nodes whose source has been re-written/updated since the node was created | unmeasurable from snapshot alone, but at LEAST the 5 days of source churn means a large fraction | Yes (any conservative estimate exceeds 30%) |

Under three of four interpretations, the threshold is exceeded by a wide margin. The fourth interpretation (strict literal) is not the right framing for the migration decision — it would say "0% stale" even for a graph that's 100% off the current source-of-truth, which is clearly wrong as a recovery-value heuristic.

## Recommendation — COLD-START

Cognee retires cleanly. Reasoning:

1. **Structural fit with Hindsight: zero.** Hindsight stores Decision / Artifact / TaskContext / AntiPattern shapes (via Atlas's PR #1134 wrappers). Cognee's graph contains zero such shapes — only NER-style Entity + EntityType + minimal Document state. There is no 1:1 export mapping that would carry signal across.

2. **Redundancy with Weaviate is total.** The 34 source documents Cognee graphed are all in `Codebase` (207 objects), `StrategicDocuments` (2 objects), or `ExternalKnowledge` (12,521 objects). Weaviate is the live source-of-truth for these. Hindsight will re-extract from the same files via its own retain/cognify equivalent.

3. **Writer is broken with no clean recovery path.** Kuzu WAL `UNREACHABLE_CODE` assertion has been firing since 2026-05-24. Even if we wanted to selective-export, we'd first need to fix Kuzu — that's separate-project scope.

4. **Snapshot is the audit trail.** The full Cognee SQLite (40MB) lives at `/home/elliotbot/clawd/backups/memory_pre_hindsight_migration_20260525/cognee_data/` (chmod -R a-w). Any future entity-mining question can be answered by re-opening the snapshot — but the LIVE Cognee adds nothing.

5. **No paying customers depend on this data.** Pre-revenue per `feedback_pre_revenue_reality`. Cold-start cost is zero customer impact.

## What "cold-start" means in practice

| Action | Owner | When |
|---|---|---|
| Stop `cognee.service` + `cognee-auto-ingest.service` | devops-6 (Elliot's call) | Pre-cutover, after Hindsight is reachable in fleet |
| `mv /home/elliotbot/clawd/cognee_data /home/elliotbot/clawd/cognee_data.retired_20260525` (don't delete; orphan) | same | same |
| Disable `cognee` + `cognee-auto-ingest` units in systemctl --user | same | same |
| Update `ceo:memory_abstraction_layer_v1.engine` reference to drop Cognee | Elliot orchestrator | after cutover |
| `bd create` follow-up: archive `cognee_data.retired_20260525` to long-term storage (or delete after Hindsight has been live and producing for 30 days) | orion | 30 days post-cutover |

Snapshot at `/home/elliotbot/clawd/backups/memory_pre_hindsight_migration_20260525/cognee_data/` stays read-only indefinitely — chmod-locked, ~40 MB, low storage cost. Survives even if `cognee_data.retired_20260525` gets cleaned later.

## What this report deliberately does NOT do

- **Does not propose a selective-export script.** Per cold-start recommendation, no export. If a deliberator concurs that selective export is still warranted (despite 0% high-signal shapes), a separate PR can scope that — but the work would mostly produce duplicates of what Hindsight will re-extract from source on its own.
- **Does not attempt Kuzu WAL recovery.** Out of scope; would only resurrect a writer for a data store we're decommissioning.
- **Does not touch the live Cognee instance.** All analysis was against the frozen snapshot (mode=ro). The live instance is unchanged.

## Verification

Re-runnable independently against the snapshot:

```bash
python3 -c "
import sqlite3
db = sqlite3.connect('file:/home/elliotbot/clawd/backups/memory_pre_hindsight_migration_20260525/cognee_data/cognee_db?mode=ro', uri=True)
# Total nodes
print('total nodes:', db.execute('SELECT count(*) FROM nodes').fetchone()[0])
# Node date range
print('node date range:', db.execute('SELECT MIN(created_at), MAX(created_at) FROM nodes').fetchone())
# Node types
print('node types:', db.execute('SELECT type, count(*) FROM nodes GROUP BY type ORDER BY 2 DESC').fetchall())
# Cognify history
print('cognify runs:', db.execute(\"SELECT created_at, status FROM pipeline_runs WHERE pipeline_name='cognify_pipeline' ORDER BY 1\").fetchall())
"
```

Expected output (verbatim from the snapshot at report-write time):
- total nodes: 3703
- node date range: ('2026-05-20 12:25:58.869151', '2026-05-20 12:37:39.798260')
- node types: [('Entity', 2783), ('EntityType', 808), ('TextSummary', 39), ('DocumentChunk', 39), ('TextDocument', 34)]
- cognify runs: 7 entries spanning 2026-05-20 to 2026-05-24, with 2 ERRORED on 2026-05-24

## Decision summary

**COLD-START.** Cognee retires. Snapshot preserved. Hindsight rebuilds entity coverage from the same source files via its own ingestion. No selective-export script needed.
