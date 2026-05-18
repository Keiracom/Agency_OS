# KEI-196 — Weaviate Re-ingest with text2vec-transformers: Plan

**Status:** Script + plan shipped (this PR). Live cutover is operator-gated.
**KEI:** [KEI-196](https://linear.app/keiracom/issue/KEI-196) (M1 follow-up from KEI-192 memory audit).
**Authored by:** Scout · 2026-05-18.

## Problem (from KEI-192 audit)

All 5 retrieval-path collections have `vectorizer=none`:

```
$ curl -s http://127.0.0.1:8090/v1/schema | python3 -c "
import json,sys
for c in json.load(sys.stdin).get('classes', []):
    print(f\"{c['class']}: vectorizer={c['vectorizer']}\")"
Discoveries: vectorizer=none
Codebase: vectorizer=none
Keis: vectorizer=none
AgentMemories: vectorizer=none
Decisions: vectorizer=none
ToolCalls: vectorizer=none
Sessions: vectorizer=none
Staging_discoveries: vectorizer=none
Global_governance_patterns: vectorizer=none
```

Without an embeddings vectorizer, `agent_query` similarity scores return 0.0. The default `min_score=0.50` filter then drops every result, and 12/14 retrieval_events end up with `top_citation_id=NULL`. Memory recall is effectively dead despite the data being indexed.

## Fix: re-ingest 5 collections with text2vec-transformers

Target collections (in cutover order):
1. `AgentMemories` — smallest, lowest blast radius, validate-first
2. `Decisions` — small (ceo_memory rows)
3. `Keis` — Linear KEI state, moderate
4. `Discoveries` — largest, 6560 rows with NULL raw_text (see KEI-197)
5. `Codebase` — git commits, indexed continuously

## Prerequisites (operator verifies BEFORE --execute)

**1. t2v-transformers inference container reachable from Weaviate.** Typical setup:
```bash
docker run -d \
  --name t2v-transformers \
  -p 8081:8080 \
  -e ENABLE_CUDA=0 \
  semitechnologies/transformers-inference:sentence-transformers-all-MiniLM-L6-v2
```

Weaviate's `text2vec-transformers` module must be configured with `TRANSFORMERS_INFERENCE_API=http://t2v-transformers:8080` (or whatever the inference host is). Verify:
```bash
curl -s http://127.0.0.1:8090/v1/meta | jq '.modules."text2vec-transformers"'
```

**2. Backup directory writable.** Default: `/home/elliotbot/clawd/logs/kei196_backup/`. Operator checks `ls -ld` permissions before --execute.

**3. KEI-197 cleanup ran first** (recommended). If KEI-197's 6560 NULL-raw_text orphan cleanup runs BEFORE the re-ingest, the post-restore Discoveries class is ~6560 rows smaller — saves embedding compute + cleaner downstream queries.

## Operator workflow (4 phases, gated)

```
# Phase 1 — backup (read-only, safe, idempotent)
python3 scripts/orchestrator/kei196_reingest_with_vectorizer.py --step backup

# Inspect:
ls -la /home/elliotbot/clawd/logs/kei196_backup/
wc -l /home/elliotbot/clawd/logs/kei196_backup/*.jsonl   # row counts per class

# Phase 2 — recreate schema (DESTRUCTIVE — drops + recreates with new vectorizer)
python3 scripts/orchestrator/kei196_reingest_with_vectorizer.py --step recreate --execute

# Phase 3 — restore (re-POST each backed-up object; vectorizer auto-embeds)
python3 scripts/orchestrator/kei196_reingest_with_vectorizer.py --step restore --execute

# Phase 4 — validate scores
python3 scripts/orchestrator/kei196_reingest_with_vectorizer.py --step validate
```

Or full cutover in one command (still requires --execute):
```bash
python3 scripts/orchestrator/kei196_reingest_with_vectorizer.py --step all --execute
```

`--class <Name>` flag restricts to one class — recommended for the first pass against AgentMemories. Validate scores > 0.0 before proceeding to the larger collections.

## Rollback

If recreate succeeds but restore fails partway:
- The `.jsonl` backups remain. Re-run `--step restore --execute` to retry.
- If the schema config itself is broken, delete the class manually and re-run from `--step recreate`.
- Worst case: redeploy the prior schema definitions (from `infra/weaviate/schema.py`) and re-run an existing indexer (`linear_state_indexer.py`, `elliot_memories_indexer.py`, etc.) to reseed.

## Acceptance per KEI-196

- [x] Script handles all 4 phases (backup, recreate, restore, validate) with per-step --execute gating
- [x] Backup is read-only and idempotent
- [x] Restore handles 422 already-exists as success (idempotent on re-run)
- [x] Validate runs a `nearText` probe + returns the top certainty score
- [x] `--class <Name>` restricts to one collection for cautious cutover
- [ ] **Live re-ingest run** — operator-gated. Requires inference container + Weaviate module config verified first.
- [ ] **agent_query.query() returns scores > 0.0 on representative queries** — post-validate confirmation
- [ ] **Behavioural recall test** — query 'psycopg asyncpg DSN bug' returns Atlas's fix as top result via semantic similarity (not LIKE/regex)

## Out of scope (Elliot/Dave follow-up)

- Live cutover (operator decides timing + verifies prereqs)
- Inference container setup if not already running (ops/Atlas DevOps lane per ratified Tier 2)
- Tuning `text2vec-transformers` model choice (MiniLM-L6-v2 is the sensible default for SaaS retrieval; larger models would improve recall at higher compute cost)
- Score threshold tuning post-cutover (KEI-198 is the M3 follow-up that adjusts min_score from the static 0.5 to a score-distribution-aware default)
- Per-class custom moduleConfig (e.g. `vectorizeClassName` per collection — current default uses one config for all 5)

## Cross-reference

- [[kei197_null_raw_text_evidence]] — KEI-197 cleanup should run BEFORE this re-ingest to avoid embedding 6560 NULL-raw_text rows
- KEI-198 (M3) — min_score tuning follow-up after vectorizer is live
- `infra/weaviate/schema.py` — current schema definitions (used as starting point for the recreate step)
- `infra/weaviate/staging_schema.py` — Staging_discoveries schema (not in M1 scope; left vectorizer=none for now)
