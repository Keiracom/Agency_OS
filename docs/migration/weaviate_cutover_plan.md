# Hindsight Ingest + Weaviate Retirement Plan

**Phase 1.2.5 bundle artefact 4** (Aiden R6/G9).  
Originally authored 2026-05-24 as a Weaviate-to-Weaviate collection split plan.  
**Updated 2026-05-31** — decision change: Hindsight is the ratified memory engine
(`ceo:memory_abstraction_layer_v1`). Weaviate is being retired after Hindsight banks
are populated. This document now describes: ingest pipeline (Weaviate → Hindsight) +
Weaviate retirement sequence (stop service, free 2GB RAM).

The prior Weaviate-to-Weaviate collection split strategy is superseded and archived at
the bottom of this document for reference only.

---

## Notes — canonical key values (per audit-dispatch checklist)

### `ceo:memory_abstraction_layer_v1`

> Status: **RATIFIED**. Hindsight self-hosted (Vectorize.io MIT) as memory engine.
> `mem.cognee_retired` and `mem.weaviate_coldstart` are v2_locks — not for redeliberation.
> Six MAL primitives: Ingest, Recall, Synthesize, Supersede, Trace, Delete.
> MCP swappability: agents call memory MCP tools, never SQL/Cypher — swap backend = rewrite DAL.
> Embedding model: BGE-small-en-v1.5 (TEI sidecar).

### `ceo:agency_os_keiracom_separation_v1`

> Status: **RATIFIED**. Phase 1.2.5 bundle (this artefact) must be complete BEFORE
> the first product-migration PR. Migration runner scope spans 3 repos + shared Supabase.
> Backup gate: scripts cover all data sources.

**Decision change read-out:** The prior plan cut product-tagged objects into a separate
Weaviate collection (`keiracom-product`). That design assumed Weaviate would remain the
memory engine. Hindsight is now the ratified engine. The correct action is: ingest existing
Weaviate data into Hindsight banks, then retire Weaviate entirely. A Weaviate-to-Weaviate
split is no longer needed.

---

## What Weaviate currently holds (2026-05-31 inventory)

| Collection | Count |
|---|---|
| Discoveries | 14,176 |
| Agent memories | 7,732 |
| Session transcripts | 149,456 |

Hindsight banks are currently **empty**. Retrieval calls Hindsight; indexers write to
Weaviate. These are disconnected — the fix is to ingest all Weaviate data into Hindsight,
then retire Weaviate.

---

## Strategy

### Ingest pipeline: Weaviate → Hindsight

Pull each Weaviate object, transform to a natural-language summary (if not already in NL
form), and POST to Hindsight via the MAL `Ingest` primitive. No flag-day — objects are
ingested incrementally; Weaviate remains the fallback recall source until the ingest is
verified complete.

**Atom format (per Amendment 2 to [PLAN:aiden], 2026-05-31):** Atoms are NL summaries
indexed by embedding — not raw logs, not terse DSL. Session transcripts must be summarised
before ingest (not ingested verbatim). Discoveries and agent memories are already NL-form
and can be ingested directly with light wrapping.

### No-flag-day principle

Each step is independently invocable and reversible. Weaviate is not stopped until the
ingest is proven complete and recall from Hindsight returns real signal on a live chain run.

### Weaviate retirement

After ingest is verified: stop the Weaviate Docker container. This frees ~2GB RAM — a
material improvement given the VPS swap pressure (0 free swap as of 2026-05-31).
Retirement is a one-way door: confirm Hindsight recall is working before pulling the trigger.

---

## Operator runbook

### Execute in Phase 1 of the migration plan (before any other Phase 1 work)

```bash
# Step 0 — dry-run the full ingest plan
python3 scripts/migration/hindsight_ingest.py --dry-run --source all

# Step 1 — ingest discoveries (14k, fast)
python3 scripts/migration/hindsight_ingest.py --source discoveries
python3 scripts/migration/hindsight_ingest.py --verify --source discoveries

# Step 2 — ingest agent memories (7k, fast)
python3 scripts/migration/hindsight_ingest.py --source agent_memories
python3 scripts/migration/hindsight_ingest.py --verify --source agent_memories

# Step 3 — ingest session transcripts (149k, SLOW — schedule overnight)
# Transcripts require summarisation before ingest. Run with --summarise flag.
# Estimated runtime: 2-4 hours depending on summarisation model latency.
# Do NOT run while 6+ Claude sessions are active (RAM constraint).
python3 scripts/migration/hindsight_ingest.py --source session_transcripts --summarise
python3 scripts/migration/hindsight_ingest.py --verify --source session_transcripts

# Step 4 — verify recall returns real signal (HARD GATE)
python3 scripts/migration/hindsight_ingest.py --verify --recall-probe "recent KEI architecture decision"
# Must return ≥1 result with relevance_score > 0.0

# Step 5 — enable recall in chain
# Set DISPATCHER_SPAWN_RECALL_ENABLED=true in environment.
# Run a chain and confirm recall hit appears in attribution log.

# Step 6 — retire Weaviate (ONLY after Step 4 + Step 5 pass)
systemctl --user stop weaviate
systemctl --user disable weaviate
# Confirm: docker ps shows no Weaviate container
# Confirm: htop shows ~2GB RAM freed
```

### Rollback

| Step | Rollback action |
|---|---|
| Steps 1-3 (ingest) | Hindsight `Delete` primitive per ingested object. Weaviate still running — recall falls back automatically. |
| Step 4 (recall probe) | Read-only. No rollback needed. |
| Step 5 (enable flag) | Set `DISPATCHER_SPAWN_RECALL_ENABLED=false`. Chain runs blind again (pre-migration state). |
| Step 6 (Weaviate retired) | `systemctl --user start weaviate`. Weaviate resumes. Hindsight recall continues — both sources available. |

Step 6 is the hardest to reverse (Weaviate data may have drifted if new indexer writes
continued to Weaviate after retirement). This is why Step 6 requires both the recall probe
AND a live chain confirm before execution.

---

## Gate specifications (Phase 1 build items)

These are gate specifications — the underlying script (`scripts/migration/hindsight_ingest.py`)
is a Phase 1 build item (see Open follow-ups). Gates become executable once the script ships.

| Gate | Specified mechanism | Expected exit |
|---|---|---|
| Ingest count match | `hindsight_ingest.py --verify --source X`: Hindsight row count ≥ Weaviate count for source X | 0 pass / 1 fail |
| Recall signal | `--recall-probe`: semantic query returns ≥1 result with relevance_score > 0.0 | 0 pass / 1 fail |
| Live chain recall hit | Chain attribution log shows recall_fired=true after DISPATCHER_SPAWN_RECALL_ENABLED=true | 0 pass / 1 fail |
| Weaviate retired | Weaviate container not running AND Hindsight recall still returns results | 0 pass / 1 fail |

All four gate specifications must be implemented and green before Phase 1 migration work starts.

---

## Resource impact

Ingest runtime:
- Discoveries (14k): ~10-20 min
- Agent memories (7k): ~5-10 min
- Session transcripts (149k with summarisation): 2-4 hours — schedule overnight

RAM during ingest: the ingest script + summarisation model adds ~300-500MB peak. Confirm
≥1GB available before starting Step 3. Do not run Step 3 while 6+ Claude sessions active.

Post-retirement gain: ~2GB RAM freed. VPS swap pressure drops materially.

---

## Open follow-ups (not in this artefact)

- `scripts/migration/hindsight_ingest.py` implementation — this doc describes the
  interface; the script itself is the Phase 1 build item.
- Dual-write gate (new Weaviate writes also go to Hindsight during ingest window) — needed
  to prevent data drift between Steps 1-3 and Step 6. Phase 1 implementation.
- Summarisation model selection for session_transcripts — Haiku is the cost-appropriate
  choice for 149k summaries. Confirm with Elliot before running Step 3.

---

## Superseded plan (archived — Weaviate-to-Weaviate collection split)

The prior version of this document described a Weaviate collection split: moving
product-tagged objects from the `Decisions` collection into a new `keiracom-product`
collection using `scripts/migration/weaviate_cutover.py`. That strategy is superseded
because Weaviate is being retired entirely. The script is kept in the repo as a reference
for Hindsight `Delete` rollback patterns; do not run it as part of the Phase 1.2.5 bundle.
