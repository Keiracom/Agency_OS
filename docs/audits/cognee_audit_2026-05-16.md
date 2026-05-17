# Cognee Audit — 2026-05-16

**Author:** scout
**Date:** 2026-05-16
**Mandate:** Dave-direct [READ-ONLY] — before Weaviate declared primary memory layer, audit Cognee's role in the three-layer architecture (Cognee session memory ↔ Weaviate collective ↔ LlamaIndex retrieval orchestration). Reframed per Dave correction: Cognee is NOT a deprecation candidate.
**Status:** AUDIT-ONLY. No data touched. Reports what EXISTS, not what should be built.

## Plain English

Dave: Cognee SQLite (`/home/elliotbot/clawd/cognee_data/cognee_db`, **215 MB**) contains **genuine session memory** — 55,290 nodes + 166,766 edges + 20,904 pipeline runs + 3,753 ingested data rows. **Not stale orphan data.** The graph IS the thing.

But the service has been **idle for 3 days**. **Last write: 2026-05-13 21:26:43 UTC.** cognee.service has been "active" the whole time, but zero writes since. **The writers stopped — readers were never wired.**

Concrete answers to your 5 questions:

| # | Question | Finding |
|---|----------|---------|
| 1 | Is Cognee writing + who? | NO writes since 2026-05-13 21:27 UTC (3 days idle); historical writers were `scripts/cognee_ingest.py` (Max KEI-7 / Streams 2-4) and KEI-44 (Orion, all transient scopes FAILED) |
| 2 | Session memory hydration on task start? | **NOT WIRED.** Zero `cognee_recall` references in `~/.config/agency-os/hooks/*.sh` or inbox-watchers. The KEI-7 wiring documented in `skills/cognee-recall/SKILL.md` is **doc-only — not implemented in active scripts** |
| 3 | Cognee↔Weaviate integration? | **NONE.** Only co-mentioned in test fixtures + dep-pin research docs. No production code crosses the two stores |
| 4 | Both layers on task start? | **NEITHER consistently.** KEI-51 (PR #888, my work) reads `discovery_log.jsonl` only. Cognee hydration absent. Weaviate has 14,202 docs across 6 collections but no hook calls it on task start either |
| 5 | SQLite large from genuine accumulation? | **GENUINE** — 55,290 nodes / 166,766 edges / 20,904 pipeline_runs is non-trivial accumulated work. Not stale orphan. **Idle ≠ dead.** But last write 3 days ago means session memory has frozen |

## Verbatim evidence

### Q1 — Active writes / consumers

**systemd:**
```
cognee.service - Agency OS — Cognee API server (knowledge graph + memory layer)
   Loaded: loaded (/home/elliotbot/.config/systemd/user/cognee.service; enabled)
   Active: active (running) since Thu 2026-05-14 07:51:32 UTC; 2 days ago
   Main PID: 1014956 (uvicorn) — 127.0.0.1:8000
```

**Live HTTP probe:**
```
$ curl http://127.0.0.1:8000/health
{"status":"ready","health":"healthy","version":"1.0.9"}
```

**Open file handles on cognee_db:** none (empty `lsof` result).

**Last writes:**
```
pipeline_runs.last(created_at):       2026-05-13 21:27:21.400086
data.last(created_at):                2026-05-13 21:26:43.279493
session_model_usage.last(updated_at): 2026-05-13 08:36:05.454016
```

**Failed transient scopes (recent attempts):**
```
cognee-exec-304929.scope  failed  /tmp/orion-kei44-allocator.py
cognee-exec-306102.scope  failed  /tmp/orion-kei44-allocator.py
cognee-exec-309639.scope  failed  /tmp/orion-kei44-allocator.py
cognee-exec-311800.scope  failed  /tmp/tmp.qu6kQAEHyR.py
```

All 4 recent invocation attempts were Orion KEI-44 (memory-cap acceptance) — **all failed**.

### Q2 — Hydration on task start

```
$ grep -rE 'cognee' ~/.config/agency-os/hooks/*.sh
(no matches)
$ grep -E 'cognee' /home/elliotbot/clawd/scripts/{atlas,orion,scout}_inbox_watcher.sh
(no matches)
```

The KEI-7 dispatch enrichment described in `skills/cognee-recall/SKILL.md` (lines 22-30):
> *"Per KEI-7 wiring: when an inbox-watcher reads a new dispatch file for a clone callsign, the CONTENT is piped through `scripts/cognee_recall.py` before the `tmux send-keys` injection."*

…is **documented but not present** in any active hook or watcher script on this worktree.

### Q3 — Integration Cognee ↔ Weaviate

```
$ grep -rE 'cognee.*weaviate|weaviate.*cognee' --include='*.py' --include='*.md' .
tests/memory/test_environment_hash.py:    def test_key_software_has_cognee_and_weaviate(...)
docs/runbooks/resource-monitor.md: ... cgroup caps for Weaviate + Cognee ...
docs/wave2/kei58_staleness_governance_research.md: ... cognee, weaviate-client ...
```

**Zero production-code references.** Only test fixtures + dependency-pinning research docs. The two stores operate **fully independently**.

### Q4 — Per-task receipt

`bd claim` context injection (KEI-51, PR #888 — Scout this session):

```python
# scripts/orchestrator/claim_context_injector.py — reads ~/.claude/.../memory/discovery_log.jsonl
# extra_sources kwarg = post-KEI-49 Weaviate retrieval extension point (stub-only today)
```

Reads: `discovery_log.jsonl` ONLY. No Cognee. No Weaviate (extension point exists; not wired).

Other session-start hooks (`pre_compact_alert.py`, `inbox_check_hook.sh`, `session_resumption_watchdog.sh`, `recorder_hook.sh`): all read HEARTBEAT/identity/inbox files. **None call Cognee.** **None call Weaviate.**

So on task start, an agent currently receives:
- ✅ Capsule (anti-amnesia) state
- ✅ Recent inbox messages
- ✅ HEARTBEAT marker
- ✅ ceo_memory (if queried)
- ❌ Cognee session memory (not wired)
- ❌ Weaviate collective memory (not wired; KEI-51 extension-point stub only)

### Q5 — SQLite contents

**30 tables.** Headline counts:

```
TABLE                          ROWS
---------------------          ------
data                           3,753
dataset_data                   3,753
datasets                       1
edges                          166,766
nodes                          55,290
pipeline_runs                  20,904
session_records                (unknown — no time-col PRAGMA could anchor recency)
users / tenants / acls / etc.  small
graph_metrics                  0
graph_relationship_ledger      0
notebooks                      0
```

**Top node labels (entity types):**
```
agent:max                  2,520
source:agent_memories      962
concept                    579
status                     567
date                       559
callsign:elliot            550
source:ceo_memory          500
source:turn_logs           497
exit:success               497
person                     453
```

**Interpretation:** Cognee was actively ingesting `agent_memories` + `ceo_memory` + `turn_logs` with full entity extraction (concept/person/status/date). The graph has real semantic structure — this is the per-session memory layer Dave described. **It worked. It stopped.**

### Stack config (from `~/.config/agency-os/.env`)

```
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-2.5-flash
LLM_TEMPERATURE=0.0
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini/gemini-embedding-001
EMBEDDING_DIMENSIONS=768
```

Cognee per `src/cognee/client.py` docstring uses:
- LLM: Gemini 2.5 Flash
- Embedding: Gemini text-embedding (note: env says `gemini-embedding-001`; client docstring says `text-embedding-004` — drift to verify)
- Vector DB: pgvector on Supabase ($SUPABASE_DB_URL)
- Relational: sqlalchemy on $SUPABASE_DB_URL
- Graph DB: **Kuzu at `/home/elliotbot/clawd/cognee_graph/` — BUT THIS DIRECTORY IS EMPTY**

⚠ **Graph-DB directory is empty.** The 166,766 edges and 55,290 nodes are stored INSIDE the SQLite `cognee_db` file, not in Kuzu. Either the configuration shifted away from Kuzu or Kuzu was never populated.

### Weaviate counterpart (for comparison only)

```
$ curl localhost:8090 ... collections.list_all
['Codebase', 'Decisions', 'Discoveries', 'Keis', 'Sessions', 'ToolCalls']
Discoveries.total_count = 14,202
```

**Six Weaviate collections.** Discoveries is the largest. No `agent:max` / `callsign:elliot` style node tags — Weaviate ingestion (Atlas/Max Phase C waves) used a different schema.

## What EXISTS (per Dave's "report what exists, not what should be built")

1. **Cognee session memory layer EXISTS** in 215 MB SQLite (cognee_db) with 55,290 nodes + 166,766 edges + 20,904 pipeline runs + 3,753 ingested data rows.
2. **Cognee API EXISTS + responds** on 127.0.0.1:8000 (`/health` returns `ready/healthy/1.0.9`). API requires auth; no `COGNEE_AUTH` / `COGNEE_KEY` in `~/.config/agency-os/.env`.
3. **Cognee writers existed** — `scripts/cognee_ingest.py` (Max KEI-7 Streams 2-4) + KEI-44 Orion allocator. **All recent invocations failed.**
4. **Cognee readers existed** — `scripts/cognee_recall.py` + `skills/cognee-recall/SKILL.md`. **Wiring into hooks/watchers does NOT exist on this worktree.**
5. **Cognee+Weaviate integration code does NOT exist** — only test fixtures + dep pins.
6. **Three-layer composition (Cognee + Weaviate + LlamaIndex) is doc-only.** Each layer is reachable in isolation; no code stitches them together for task-start hydration.

## Open observations (for Elliot consolidation, not recommendations)

- **Why writers stopped on 2026-05-13:** correlates with KEI-44 allocator failures + KEI-23 Lance writer concurrency crashes (per `docs/wave2/kei23_stream2_crash_diagnosis.md`). The pipeline may have been disabled after those crashes pending a fix.
- **`cognee_graph/` empty:** suggests Kuzu graph backend was never written OR migration moved storage into the SQLite. Worth confirming with Max (Cognee-stack owner).
- **No auth on this worktree:** if hydration is to be re-wired via the HTTP API rather than direct SDK, the agent processes need COGNEE_AUTH credentials in their env. SDK path (via `src/cognee/client.py`) bypasses HTTP auth.
- **Conflict with `subprocess_memory_cap` rule (ceo:rule, KEI-43):** "Any long-running subprocess (Cognee, data ingestion, batch jobs) must have a memory cap set." `scripts/orchestrator/cognee_capped.sh` exists — verify cognee.service is wrapped by this. Service file shows `Memory: 5.7M (high: 2.6G max: 3.0G)` so cap appears applied.
- **Per `~/.claude/projects/.../memory/feedback_clear_not_equal_reset.md`:** process uptime ≠ activity. Cognee process uptime (2 days) is misleading; actual activity is 0 writes / 3 days.

## What's NOT in scope for this audit

- Re-enabling Cognee writers (recommendation deferred).
- Wiring task-start hydration (recommendation deferred).
- Cognee+Weaviate stitching design (recommendation deferred).
- Schema reconciliation (Cognee node labels vs Weaviate Discoveries schema).
- Per Dave's reframe + read-only mandate: **no action proposed.**

---

*Read-only audit. Reports what exists. Awaiting Elliot consolidation + Dave plan.*
