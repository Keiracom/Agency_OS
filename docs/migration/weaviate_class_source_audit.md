# Weaviate 13-Class Source Audit — Cold-Start Migration Step 1

**KEI:** Agency_OS-w5fj (P1). **Author:** aiden. **Reviewers per author-exclusion:** Elliot + Max. **Dispatched by:** Elliot 2026-05-25 post snapshot-phase (Orion-confirmed archive at `/home/elliotbot/clawd/backups/memory_pre_hindsight_migration_20260525/`, 2.1GB, chmod -R a-w, loss-risk zero).

**Gate:** this audit decides whether the cold-start plan needs hand-migration carve-outs for any non-pipeline-fed classes. Output informs step 5 (re-point indexers).

---

## Headline finding

**4 of 13 classes have NO discoverable writer in current codebase** (`grep -rn '"<ClassName>"'` returns zero hits in `scripts/` or `src/`). They exist in Weaviate (with object counts) but the code that populates them is either deleted, archived, in a separate repo we don't see, or was a one-shot human action via Weaviate Console / curl.

The 4: **SessionTranscripts (117171 objects)**, **SessionFacts (10532)**, **ExternalKnowledge (12521)**, **Global_governance_patterns (5)**.

**SessionTranscripts is the highest-stakes** — 117k objects, no writer. If we cannot find/reconstruct the writer, that data is hand-migration only (Category B), and its size makes hand-migration operationally painful.

---

## Classification table (13 classes)

| Class | Objects | Category | Source | Writer found? |
|---|---|---|---|---|
| Decisions | 418 | **A pipeline** | Supabase `public.ceo_memory` | ✓ `scripts/orchestrator/ceo_memory_indexer.py` (`target_class = DECISIONS_CLASS`) |
| AgentMemories | 7669 | **A pipeline** | Supabase `public.agent_memories` (callsign-scoped) | ✓ `scripts/orchestrator/elliot_memories_indexer.py` (`target_class = AGENT_MEMORIES_CLASS`); presumed sibling `agent_memories_indexer.py` for non-elliot callsigns |
| Keis | 488 | **A pipeline** | Linear API (KEI issues) | ✓ `scripts/orchestrator/linear_state_indexer.py` (`target_class = KEIS_CLASS`) |
| Codebase | 207 | **A pipeline** | Git commits (this repo) | ✓ `scripts/orchestrator/git_commits_indexer.py` (`target_class = CODEBASE_CLASS`) |
| StrategicDocuments | 2 | **A pipeline** | Google Drive (`config/drive_index_targets.json`) | ✓ `scripts/orchestrator/drive_strategic_indexer.py` (`STRATEGIC_CLASS = "StrategicDocuments"`); currently failing per dispatch — separate issue |
| Slack_history | 14772 | **A pipeline** | Slack (channels) | ✓ `scripts/orchestrator/slack_history_indexer.py` (file present; Slack is canonical upstream source) |
| ToolCalls | 5289 | **A pipeline** | Supabase `public.tool_call_log` | ✓ `scripts/orchestrator/tool_call_log_indexer.py` (file present) |
| SessionTranscripts | 117171 | **B HAND-MIGRATION** | Claude session JSONL files (per dispatch) | ✗ NO WRITER FOUND in current codebase — see §Risk surface below |
| SessionFacts | 10532 | **C DERIVED** | Derived from SessionTranscripts (per dispatch) | ✗ NO WRITER FOUND; classification holds if dispatch source-claim is accurate |
| Sessions | 48666 | **B HAND-MIGRATION** | Unclear — kei75_sweeps + kei75_sessions_source_id operate on it but neither writes | ✗ NO WRITER FOUND |
| Discoveries | 14176 | **A pipeline (probable)** | `~/.claude/projects/.../discovery_log.jsonl` written by `bd discover` per `discovery_log.py` docstring | ⚠️ JSONL writer found (`scripts/orchestrator/discovery_log.py`); Weaviate indexer that reads JSONL → Discoveries class NOT found in current code — see §Discoveries note |
| Global_governance_patterns | 5 | **B HAND-MIGRATION** | Likely human-curated (5 objects = small + structured set) | ✗ NO WRITER FOUND |
| ExternalKnowledge | 12521 | **B HAND-MIGRATION** | Unknown — zero hits in codebase | ✗ NO WRITER FOUND — orphan class |

---

## Per-class detail

### Category A — pipeline-fed re-ingestible (7 classes)

These re-index against Hindsight deterministically. Cold-start plan: re-point the indexer's `target_class` from the Weaviate class name to the Hindsight memory-bank id; let the indexer's existing replay logic backfill from the canonical source.

**Decisions (418).** Source: `public.ceo_memory`. Indexer reads the table, writes one Weaviate object per row. Re-ingest target: replay all rows through the indexer pointed at Hindsight bank. Risk: zero.

**AgentMemories (7669).** Source: `public.agent_memories` table. Indexer is callsign-scoped (one elliot-indexer found; presumed siblings for other callsigns OR a single indexer with `--callsign` arg — needs spot-check pre-cutover). Re-ingest target: per-callsign replay. Risk: low (source table is well-populated + audit-trailed).

**Keis (488).** Source: Linear API. Indexer hits Linear's GraphQL with state filters, writes one object per KEI. Re-ingest target: re-query Linear, replay through indexer. Risk: low (Linear is authoritative; tokens are still valid).

**Codebase (207).** Source: git commits. Indexer pulls commits from the local repo. Re-ingest target: replay all commits OR last N (configurable). Risk: zero (git is the canonical source).

**StrategicDocuments (2).** Source: Google Drive (specific doc list in `config/drive_index_targets.json`). Indexer is currently failing per dispatch — separate fix needed BEFORE re-ingest works. Risk: medium (indexer health is a blocker; if not fixed by cold-start, this class re-ingests with 0 objects).

**Slack_history (14772).** Source: Slack API. Indexer pulls channel history via slack-sdk. Re-ingest target: re-query Slack history (rate-limit aware), replay through indexer. Risk: low if rate-limits respected; if Slack workspace-level retention has expired older messages, some loss is unavoidable. Worth: confirm Slack retention covers the 14772 historical objects.

**ToolCalls (5289).** Source: `public.tool_call_log` table. Indexer reads + writes. Re-ingest target: replay all rows. Risk: zero.

### Category B — one-off / hand-migration required (4 classes)

These are the audit findings that need a recovery plan before cold-start. Most consequential: SessionTranscripts (117k objects).

**SessionTranscripts (117171).** Per dispatch: "session-transcript-indexer; pipeline (claude session jsonl is source)". **Indexer not found in current codebase.** The `scripts/orchestrator/` directory has `auto_session_recovery.py` + `kei75_sessions_source_id.py` mentioning sessions, but neither writes to a Weaviate `SessionTranscripts` class. Recovery options:

  - (a) **Source IS reproducible — find the indexer.** The dispatch claims the source is Claude session JSONL files (`~/.claude/projects/-home-elliotbot-clawd-Agency-OS/...`). If we can locate the historical session-transcript-indexer in archived branches, in `scripts/archive/`, or in deleted-but-recoverable git history, restore it + replay against Hindsight. Recovery effort: 1-2 days investigation + restore.
  - (b) **Source is reproducible but indexer is gone — rewrite the indexer.** ~200-400 LoC: walk Claude session JSONL files (well-defined format), extract transcript records, emit one Hindsight memory per session-turn. Recovery effort: 2-3 days.
  - (c) **Snapshot is the source of truth — hand-migrate from snapshot.** The 2.1GB snapshot at `backups/memory_pre_hindsight_migration_20260525/` likely contains a Weaviate dump including these 117k objects. Migrate object-by-object via a one-shot script (read snapshot → write Hindsight). Recovery effort: ~1 day for the script + replay-time depending on Hindsight ingest throughput.

**Recommended: (c) snapshot-based hand-migration** for cold-start unblock, in parallel with (a)/(b) investigation to restore the indexer for ongoing freshness. Otherwise post-cold-start writes (new session transcripts) don't have a path into Hindsight.

**Sessions (48666).** Same shape as SessionTranscripts. `kei75_sweeps` + `kei75_sessions_source_id` operate on the class (sweeps + dedup) but neither writes. Recovery: same (a)/(b)/(c) options. Snapshot-based hand-migration for cold-start; indexer rewrite for ongoing. Effort: similar to SessionTranscripts but cheaper because it's smaller (48k vs 117k).

**ExternalKnowledge (12521).** Zero hits in codebase. Genuine orphan. Recovery requires investigation: was it populated by a deleted script? A human curated batch? A Cognee import (Cognee operates at a different layer but might have populated Weaviate at some point)? Pre-cold-start action:

  - **Investigate origin first** (~2-4 hours): grep deleted branches; check `~/.bash_history` or shell logs for ad-hoc curl commands; ask Dave/Viktor if they recall a one-time import.
  - If origin remains unknown after investigation: **snapshot-based hand-migration is the only safe path** — preserves the 12521 objects without understanding their origin. Risk: post-migration these objects exist in Hindsight but no pipeline keeps them fresh; they become stale-by-default. Acceptable for read-only reference data, problematic if they're meant to be ingested-continuously.

**Global_governance_patterns (5).** Only 5 objects suggests human-curated set. Recovery: easiest of the 4 — copy the 5 objects from snapshot to Hindsight manually + document the canonical content + decide whether they're meant to be re-curated periodically (manual maintenance) or were truly one-time. ~1 hour effort.

### Category C — derived (1 class)

**SessionFacts (10532).** Per dispatch: "derived from SessionTranscripts." Implication: SessionFacts is produced by running an extraction pass over SessionTranscripts content (probably an LLM-graded fact-extraction step). Recovery: re-run the derivation against the post-cold-start Hindsight bank that contains SessionTranscripts. No hand-migration needed because derivation IS the source-of-truth path. **Dependency:** SessionTranscripts must be successfully migrated to Hindsight FIRST (otherwise derivation has no source).

If the derivation logic is itself missing from the codebase (likely, since SessionTranscripts indexer is missing), it needs the same recovery as the missing indexers — find or rewrite.

### Discoveries note

`scripts/orchestrator/discovery_log.py` writes `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/discovery_log.jsonl` via `bd discover` invocations. The JSONL is the canonical source — verified.

What's MISSING is the JSONL → Weaviate Discoveries class indexer. The Weaviate class has 14176 objects but the code path that reads the JSONL and writes to Weaviate isn't in `scripts/orchestrator/`. Options:

- The indexer exists but was missed in my grep (worth spot-checking `scripts/` non-orchestrator dirs OR archived locations)
- The indexer was deleted post-PR-#1196 reingest-with-vectorizer work (the existing kei196 script appears to TRANSFORM existing Discoveries rather than ingest new ones)
- Discoveries were populated by a one-shot KEI-196 bootstrap that's gone

If the indexer truly doesn't exist anymore, Discoveries is **Category B** despite the JSONL source being canonical — because we have no automation to re-index from JSONL to Hindsight on an ongoing basis. Hand-migration from snapshot is the safe path; indexer rewrite is the right durable fix.

---

## Risk surface — what could break the cold-start

**Risk 1 — SessionTranscripts hand-migration is the long-pole (117k objects).**

If Recovery option (c) snapshot-based hand-migration is chosen for SessionTranscripts, Hindsight ingest throughput becomes the cold-start critical path. At a conservative 50 ingests/sec (per PR #1130 measurement on similar payloads), 117k = ~40 minutes. At a worse 5/sec under load = ~6.5 hours. **Plan a single dedicated cold-start window for SessionTranscripts migration; don't interleave with other classes.**

**Risk 2 — ExternalKnowledge origin remains unknown.**

If 2-4 hours of investigation doesn't surface the writer or curator, we proceed with snapshot-based hand-migration and accept that the 12521 objects become stale-by-default in Hindsight (no pipeline keeps them fresh). For a class whose role we don't fully understand, this might be acceptable (treat as reference data); if they were meant to be ingested-continuously, post-cold-start retrieval quality degrades over time. **Mitigation: tag these objects in Hindsight metadata as `provenance: unknown_pre_migration` so post-cold-start operators see them clearly when querying.**

**Risk 3 — Discoveries indexer rewrite races bd discover writes.**

If the JSONL→Weaviate (now JSONL→Hindsight) indexer is rewritten DURING cold-start, there's a window where bd discover writes to JSONL but the new indexer isn't yet running. New discoveries land in JSONL but not in Hindsight. **Mitigation: snapshot the JSONL at cold-start time; replay it through the new indexer when ready; concurrent bd discover writes go into a queue that the indexer drains on first run.**

**Risk 4 — Slack history retention may have expired older objects.**

Slack workspace retention policy could be shorter than the historical 14772-object Slack_history span. Re-querying Slack might return fewer than 14772 objects. **Mitigation: spot-check the oldest object timestamp in Slack_history pre-cutover; if older than current Slack retention, use snapshot as fallback for the orphaned window.**

**Risk 5 — StrategicDocuments indexer is currently failing.**

Per dispatch: "drive-strategic-indexer (currently failing)." Until the indexer is fixed, Category A re-ingest doesn't work for this class. **Mitigation: either fix the indexer pre-cold-start (preferred) OR hand-migrate the 2 existing objects from snapshot + accept stale-by-default until indexer fix lands (acceptable because object count is tiny).**

---

## Cold-start recovery plan summary

| Class | Migration approach | Effort | Blocker on cold-start? |
|---|---|---|---|
| Decisions / AgentMemories / Keis / Codebase / Slack_history / ToolCalls | Re-point indexer's target → Hindsight bank; replay from source | ~1h per indexer × 6 = 6 hours | No |
| StrategicDocuments | Fix indexer first (separate KEI) OR hand-migrate 2 objects from snapshot | ~30 min snapshot path / TBD indexer fix | Soft yes (block on indexer fix preferred) |
| SessionTranscripts | Snapshot-based hand-migration script + ingest run (Recovery option c) | 1 day script + ~40min-6hr ingest | **YES — long-pole** |
| SessionFacts | Derived; re-run derivation after SessionTranscripts in Hindsight | depends on derivation script existence | Sequenced after SessionTranscripts |
| Sessions | Same shape as SessionTranscripts — snapshot-based hand-migration | similar to SessionTranscripts but cheaper (smaller) | Yes |
| Discoveries | Snapshot-based hand-migration + rewrite indexer for ongoing | ~1 day script + ~2-3 days indexer rewrite | Soft yes |
| ExternalKnowledge | Investigate origin (2-4h) → snapshot-based hand-migration if unknown | ~1 day | Yes |
| Global_governance_patterns | Manual copy of 5 objects from snapshot + decide curation policy | ~1 hour | No |

**Critical path on cold-start:** SessionTranscripts hand-migration (longest single window, 1-2 days end-to-end including script + ingest). Other classes parallelisable.

**Recommended cold-start sequence:**
1. Pre-cutover (parallel-safe): fix StrategicDocuments indexer; investigate ExternalKnowledge origin; locate or rewrite SessionTranscripts/Sessions/Discoveries indexers.
2. Cutover day 1: SessionTranscripts hand-migration (long ingest window).
3. Cutover day 2: parallel re-ingest of Category A classes + SessionFacts derivation re-run + Global_governance_patterns copy.
4. Post-cutover validation: query Hindsight, compare object counts per class to pre-migration Weaviate counts, flag any drift >5%.

---

## Out-of-scope for this audit

- **Per-object schema migration** (Weaviate property → Hindsight metadata mapping). Separate doc for step 3 / step 5.
- **Cold-start window scheduling** (when do we do the SessionTranscripts long ingest?). Operational decision.
- **Backup of the snapshot itself** (already done per dispatch — Orion-confirmed chmod -R a-w archive). No action.
- **Post-cold-start hot-write handling** (bd discover writes during cold-start window go where?). Addressed in §Risk 3 mitigation but full design is step 5 territory.

---

## Acceptance criteria

- [x] All 13 classes classified (A/B/C) — see §Classification table.
- [x] Source documented per class (table column + per-class detail).
- [x] Writer-not-found classes flagged with recovery options (4 classes: SessionTranscripts, Sessions, ExternalKnowledge, Global_governance_patterns + Discoveries partial).
- [x] Risk surface enumerated with mitigations (5 risks).
- [x] Cold-start recovery plan summary table.
- [ ] Elliot impl-feasibility concur.
- [ ] Max code-quality concur (audit-doc lens = "are the per-class source claims empirically verified / are the recovery options operationally executable?").

---

_End audit. Per orchestrator-merge-after-NATS-concur + author-exclusion: Aiden authored; eligible reviewers Elliot + Max; 2-of-2 lands admin-merge. Step 5 (re-point indexers) consumes the §Cold-start recovery plan summary as input._
