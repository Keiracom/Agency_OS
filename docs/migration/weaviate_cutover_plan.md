# Weaviate Cutover Plan — `<source>` → `keiracom-product`

**Phase 1.2.5 bundle artefact 4** (Aiden R6/G9).
Authored 2026-05-24. Executes in Phase 2.0 when the product repo creates the `keiracom-product` collection.

This document is the strategy + rollback companion to `scripts/migration/weaviate_cutover.py`. The script is the executable; this doc is the why, the no-flag-day principle, and the per-step rollback.

---

## Notes — canonical key values (per audit-dispatch checklist, `_orchestrator.md`)

Both keys queried 2026-05-24 ahead of authoring. Pasted verbatim so the dispatcher and reviewers can cross-check claims in the doc + script against the SSOT.

### `ceo:agency_os_keiracom_separation_v1` (updated 2026-05-24T11:04Z)

> Status: **RATIFIED**. 3-repo topology: fleet repo (Dave internal agent team), product repo (Keiracom working name, V1.0 AI workforce code), archive repo (1100 prior PRs + dead BDR code).
>
> Sequencing:
> 1. Phase 1.1 — V1.0 ratification (DONE 2026-05-24)
> 2. Phase 1.2 — retire Agency OS architecture doc + V1.0-aligned doc + content audit
> 3. **Phase 1.2.5 (INSERT) — pre-migration artefact bundle: 3-repo architecture doc + per-repo CLAUDE.md split decision + bd-routing policy + Weaviate cutover plan + discovery log classifier + migrated-manifest seed**
> 4. Phase 1.3 — agent identity refresh for 4 PARTIAL IDENTITY files
> 5. Phase 2.0 — repo creation: carve fleet repo, create fresh product repo, confirm archive state, namespace ceo_memory + Weaviate
> 6. Phase 2.1 — Hindsight verification spike (6 items)
> 7. Phase 2.2 — migrate product code via clean PRs subject to dynamic-exclusion migration manifest
>
> Consolidated gates relevant to this artefact:
> - "Weaviate ingest gate: every payload declares target collection or rejected"
> - "Recall scope gate: product agent recall hard-codes product collection; cross-collection blocked at helper layer"
> - "Phase 1.2.5 architecture doc bundle BEFORE first product-migration PR"
> - **"Weaviate cutover script with per-step verification; no flag-day"** ← this artefact
> - "Backup gate: scripts cover both Weaviate collections"
> - "Negative-path tests on namespace boundaries (positive + negative on ceo_memory + Weaviate)"

### `ceo:memory_abstraction_layer_v1` (updated 2026-05-24T15:12Z)

> Status: **RATIFIED**. Hindsight self-hosted (Vectorize.io MIT) as memory engine, deployed per-tenant VPC.
>
> Phase 2 build gating (Aiden 6 gates): A: Hindsight spike completes favourable BEFORE Phase 2 build starts; B: V1.0-aligned architecture doc lands BEFORE Phase 2 dispatches; C: Whiteboard-flush-through-Ingest is runtime code, not comment; D: Trace primitive empirically reconstructible; E: MCP swappability via dual-backend; F: Migration runner is P0 critical-path.
>
> Eleven agreed positions (relevant subset):
> - "MCP swappability: agents call memory MCP tools, never SQL/Cypher; swap backend = rewrite DAL"
> - "Whiteboard flush through Ingest at every task boundary"
> - "Tenancy: schema-per-tenant + 20-30 tripwire + migration runner pre-launch"
> - "Hindsight self-hosted as engine"

**Read-out:** Weaviate is the current memory store; Hindsight is the post-Phase-2.1 target. This cutover handles the **Weaviate-to-Weaviate** collection split — a smaller scope than Hindsight migration. The Hindsight migration itself is a separate Phase 2.1+ artefact and is out of scope here. This cutover is purely about isolating product-tagged objects into their own Weaviate collection so the product repo can recall scope-bounded.

---

## Strategy

### What the script does

Moves objects whose `context_tag == "product"` from the existing collection (default `Decisions`) into the new `keiracom-product` collection. Each row gets a **deterministic UUID** derived from `(cutover_tag, source_id)` so re-runs upsert in place rather than duplicating.

### What the script does NOT do

- **Does not write Hindsight.** Hindsight migration is the Phase 2.1+ workstream after the spike concludes favourable.
- **Does not delete from source by default.** Step 5 (`purge_old`) is opt-in via `--purge-old`; the source remains the recall fallback during the dual-write window.
- **Does not rewrite agent code.** Step 4 (`repoint`) only edits configuration files listed in a manifest; the agent code paths that consume `collection_name` are unchanged.

### No-flag-day principle

Each of the five steps is independently invocable (`--step snapshot|write|verify|repoint|purge|all`) and reversible:

| Step | Mutation | Rollback |
| --- | --- | --- |
| (1) snapshot | writes a single JSON file | `rm` the file |
| (2) write | upserts to `keiracom-product` | step (5) `purge --target` (or manual `DELETE` per id; UUIDs are deterministic so trivial to enumerate) |
| (3) verify | read-only, no rollback needed | n/a |
| (4) repoint | edits configs listed in manifest; writes `.cutover-backup` per file | `mv <file>.cutover-backup <file>` |
| (5) purge | deletes from source collection (opt-in) | restore from Weaviate backup gate ([backup script ownership](#open-followups)) |

Operators run each step independently, verify, then proceed. The only step gated on a previous step's data is (2) `write` and (5) `purge`, which both consume the snapshot file from (1). Both tolerate a missing snapshot in `--dry-run`.

---

## Operator runbook — Phase 2.0 execution

> Run from the product repo once the `keiracom-product` Weaviate class exists.

```bash
# Step 0 — dry-run the full plan to confirm intent
python3 scripts/migration/weaviate_cutover.py --dry-run --step all

# Step 1 — snapshot product-tagged rows
python3 scripts/migration/weaviate_cutover.py --step snapshot

# Step 2 — write to keiracom-product
python3 scripts/migration/weaviate_cutover.py --step write

# Step 3 — verify (HARD-REQUIRED — exits non-zero on mismatch)
python3 scripts/migration/weaviate_cutover.py --step verify || { echo "verify FAILED, abort"; exit 1; }

# Step 4 — repoint product agent configs (manifest filled in Phase 2.0)
python3 scripts/migration/weaviate_cutover.py --step repoint --repoint-manifest scripts/migration/repoint_manifest.json

# Step 5 — purge from source ONLY after dual-write window settles
python3 scripts/migration/weaviate_cutover.py --step purge --purge-old
```

### Dual-write window

Run steps (1)→(4) and leave the source collection untouched for a settling window (suggested: ≥ 7 days from production launch of the product repo, or until recall scope-boundary regression tests have run clean for a full deploy cycle). Only then run step (5).

During the dual-write window, **every product-tagged WRITE made by the running agents must go to BOTH collections** so the cut is consistent at the moment step (5) fires. This dual-write is **not** the responsibility of `weaviate_cutover.py` — it lives in the indexer layer (the per-source indexers extending `indexer_base.IndexerBase`). Phase 2.0 implementation must add a dual-write toggle to the affected indexers; this script is purely the one-shot migration.

---

## Per-step rollback detail

### (1) snapshot — rollback
Delete `snapshot.json`. No Weaviate state was touched. Re-run later.

### (2) write — rollback
`keiracom-product` got new rows. To roll back without disturbing earlier intentional writes to that class:

```bash
# Re-snapshot what was cut over (snapshot file is idempotent + still present)
# Then enumerate the deterministic target ids and DELETE them.
python3 -c "
import json, sys
sys.path.insert(0, 'scripts/orchestrator')
from indexer_base import deterministic_uuid
payload = json.load(open('/tmp/weaviate_cutover_snapshot.json'))
for row in payload['rows']:
    src = row['_additional']['id']
    print(deterministic_uuid('cutover_to_keiracom_product', src))
" | xargs -I{} curl -s -X DELETE http://127.0.0.1:8090/v1/objects/Keiracom_Product/{}
```

### (3) verify — rollback
Read-only. Nothing to roll back.

### (4) repoint — rollback
For every `<config>.cutover-backup` file the script left, restore:

```bash
for f in $(find . -name '*.cutover-backup'); do
    mv "$f" "${f%.cutover-backup}"
done
```

### (5) purge — rollback
The hardest step to reverse — source rows are gone from Weaviate. Recover via Weaviate backup (S3 snapshot per the "backup gate" in `ceo:agency_os_keiracom_separation_v1` consolidated gates). This is why step (5) is opt-in and the dual-write window is mandatory.

---

## Verification gates

| Gate | Where | Trigger |
| --- | --- | --- |
| Snapshot file atomicity | step (1) uses `tmp.replace(path)` — POSIX atomic | always |
| Deterministic UUID | step (2) derives id from `(UUID_SOURCE_TAG, source_id)` | always |
| Count match | step (3) `aggregate_count(target) >= len(snapshot.rows)` | required, exits 1 on fail |
| Sample-read parity | step (3) re-GETs first `SAMPLE_PARITY_N` target ids | required, exits 1 on fail |
| Config backup | step (4) writes `<file>.cutover-backup` before mutating | always non-dry-run |
| Opt-in destructive | step (5) requires explicit `--purge-old` flag | always |

---

## Open follow-ups (sequenced post-Phase-2.0)

- **Backup script ownership** (`ceo:agency_os_keiracom_separation_v1` gate: "Backup gate: scripts cover both Weaviate collections") — extending the existing Weaviate backup to cover `keiracom-product` is a separate artefact, not Phase 1.2.5.
- **Cross-collection recall block at helper layer** (gate: "Recall scope gate") — enforce in `llama_recall_engine.py` / `bd recall` so product agents cannot cross-fetch from fleet collection. Phase 2.0 implementation.
- **Dual-write toggle in `indexer_base`** — needed during the dual-write window described above. Phase 2.0 implementation.
- **Hindsight migration** — separate Phase 2.1+ workstream after the spike concludes favourable.

---

## Test plan

Unit tests live in `tests/scripts/migration/test_weaviate_cutover.py` and cover:

- Snapshot idempotency (rerun → identical file)
- Snapshot dry-run is read-only
- Write uses deterministic UUID + strips internal `_additional`
- Write dry-run never posts
- Verify count mismatch → False
- Verify aggregate-unreachable → False (not a silent pass)
- Verify happy path → True
- Repoint applies + leaves `.cutover-backup`
- Repoint dry-run leaves filesystem untouched
- Repoint missing manifest → 0 edits, warning, no crash
- Purge opt-in semantics + dry-run never deletes

Integration test against a live Weaviate is intentionally **not** in this artefact — there is no `keiracom-product` class yet, and the source class is production-shared. Integration test belongs in the Phase 2.0 PR that creates the class.

CLI dry-run smoke:

```bash
python3 scripts/migration/weaviate_cutover.py --dry-run --step all --purge-old
```

Run `ruff check` + `ruff format --check` on the script + tests before PR; CI rules in `feedback_ruff_format_check_required`.
