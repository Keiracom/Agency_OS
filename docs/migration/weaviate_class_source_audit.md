# Weaviate 13-Class Source Audit — Cold-Start Migration Step 1

**KEI:** Agency_OS-w5fj (P1). **Author:** aiden. **Reviewers per author-exclusion:** Elliot + Max. **Dispatched by:** Elliot 2026-05-25 post snapshot-phase (Orion-confirmed archive at `/home/elliotbot/clawd/backups/memory_pre_hindsight_migration_20260525/`, 2.1GB, chmod -R a-w, loss-risk zero).

**Gate:** this audit decides whether the cold-start plan needs hand-migration carve-outs for any non-pipeline-fed classes. Output informs step 5 (re-point indexers).

---

## Headline finding (REVISED 2026-05-25 per Max audit critique)

**Original audit grep methodology missed module-level constant + upsert_object patterns.** After Max applied a broader pattern (`grep -rnE 'class\s*=\s*"<Cls>"|WEAVIATE_CLASS\s*=\s*"<Cls>"|upsert_object\("<Cls>"|_CLASS\s*=\s*"<Cls>"' scripts/`), three classes previously flagged as Category B were empirically reclassified to Category A:

- **SessionTranscripts (117k)** — writer found at `session_transcript_indexer.py:237`. **Cold-start critical-path long-pole evaporates.**
- **SessionFacts (10.5k)** — writer found at `session_transcript_indexer.py:385`. NOT derived (C → A).
- **ExternalKnowledge (12.5k)** — writer found at `external_knowledge_ingester.py` with module constant `WEAVIATE_CLASS = "ExternalKnowledge"`. NOT orphan.

Plus a filename correction: Slack_history writer is `slack_history_ingest.py` (KEI-201 bulk extractor), not `slack_history_indexer.py` as originally cited.

**Revised classification: 10 of 13 classes are Category A pipeline-fed re-ingestible. Only 3 remain Category B hand-migration: Sessions (48k), Discoveries (14k JSONL-source-canonical-but-Weaviate-indexer-absent), Global_governance_patterns (5).**

**Net impact on cold-start plan:** ~140k objects (SessionTranscripts + SessionFacts + ExternalKnowledge) move from hand-migration long-pole to normal pipeline re-ingest. Cold-start simplifies significantly — less risk, less work, less downtime window. See revised §Cold-start recovery plan summary below.

## Methodology correction (audit-discipline lesson)

The original grep used patterns like `grep -rn '"<ClassName>"'` which catches CLASS-NAME-AS-LITERAL-IN-NORMAL-POSITION but misses:

1. **Module-level constants** (`WEAVIATE_CLASS = "Foo"`) where the class name is assigned to a constant once, then referenced via the constant variable. Catching requires extending the pattern to constant-assignment shapes.
2. **upsert_object/insert/post call sites** where the class name is the FIRST positional argument inside a function call. `grep '"Foo"'` finds these in principle, but my grep used `grep -rln '"<cls>"' | head -10` which only listed FILES, not actual matches — combined with grep's tendency to surface other noise hits in app-data/status.json and bd issue bodies that look like "no real writer" by inspection, I dismissed positive signals.
3. **Run-against-stale-local-state** — I ran greps from my pr-1039-fix worktree, behind origin/main. `session_transcript_indexer.py` and `external_knowledge_ingester.py` exist on main but were not in my local checkout. Even with broader grep patterns, this would still have missed the writers. **Audits MUST run against a fresh fetch of origin/main, not local worktree state.**

This is the same methodology miss class as PR #1142's LlamaIndex lazy-import case (function-body imports invisible to module-top grep). Both are "grep miss" failures. The corrective discipline is being captured in a feedback memory entry (`feedback_grep_misses_lazy_dynamic_crosstool.md`) plus the `scripts/common/` audit-tooling consolidation KEI I owe.

**The broader grep pattern Max used (canonical form going forward):**
```
grep -rnE 'class\s*=\s*"<Cls>"|WEAVIATE_CLASS\s*=\s*"<Cls>"|upsert_object\("<Cls>"|_CLASS\s*=\s*"<Cls>"' scripts/ src/
```

Run against `git checkout origin/main` state, not local-worktree state.

---

## Classification table (13 classes)

| Class | Objects | Category | Source | Writer found? |
|---|---|---|---|---|
| Decisions | 418 | **A pipeline** | Supabase `public.ceo_memory` | ✓ `scripts/orchestrator/ceo_memory_indexer.py` (`target_class = DECISIONS_CLASS`) |
| AgentMemories | 7669 | **A pipeline** | Supabase `public.agent_memories` (callsign-scoped) | ✓ `scripts/orchestrator/elliot_memories_indexer.py` (`target_class = AGENT_MEMORIES_CLASS`); presumed sibling `agent_memories_indexer.py` for non-elliot callsigns |
| Keis | 488 | **A pipeline** | Linear API (KEI issues) | ✓ `scripts/orchestrator/linear_state_indexer.py` (`target_class = KEIS_CLASS`) |
| Codebase | 207 | **A pipeline** | Git commits (this repo) | ✓ `scripts/orchestrator/git_commits_indexer.py` (`target_class = CODEBASE_CLASS`) |
| StrategicDocuments | 2 | **A pipeline** | Google Drive (`config/drive_index_targets.json`) | ✓ `scripts/orchestrator/drive_strategic_indexer.py` (`STRATEGIC_CLASS = "StrategicDocuments"`); currently failing per dispatch — separate issue |
| Slack_history | 14772 | **A pipeline** | Slack (channels via `conversations.history`) | ✓ `scripts/orchestrator/slack_history_ingest.py` (KEI-201 bulk extractor; writes to `Slack_history` class) — **corrected from prior `_indexer.py` filename per Max audit** |
| ToolCalls | 5289 | **A pipeline** | Supabase `public.tool_call_log` | ✓ `scripts/orchestrator/tool_call_log_indexer.py` (file present) |
| SessionTranscripts | 117171 | **A pipeline** | Claude session JSONL files | ✓ `scripts/orchestrator/session_transcript_indexer.py:237 upsert_object("SessionTranscripts", ...)` — **RECLASSIFIED B→A per Max audit; original grep missed module-level constant + upsert_object pattern** |
| SessionFacts | 10532 | **A pipeline** | Same session JSONL files (NOT derived from SessionTranscripts despite earlier claim) | ✓ `scripts/orchestrator/session_transcript_indexer.py:385 upsert_object("SessionFacts", ...)` — **RECLASSIFIED C→A per Max audit; has its OWN writer call, not a derivation pass over SessionTranscripts** |
| Sessions | 48666 | **B HAND-MIGRATION** | Unclear — `kei75_sessions_source_id.py` has `SESSIONS_CLASS = "Sessions"` constant but no upsert call; kei75_sweeps + kei75_sessions_source_id are READ-only | ✗ NO WRITER FOUND under broader grep — B classification holds |
| Discoveries | 14176 | **B HAND-MIGRATION** | `~/.claude/projects/.../discovery_log.jsonl` written by `bd discover` per `discovery_log.py` docstring; JSONL→Weaviate indexer absent | ⚠️ JSONL writer found (`scripts/orchestrator/discovery_log.py`); Weaviate indexer that reads JSONL → Discoveries class NOT found under broader grep — B classification holds |
| Global_governance_patterns | 5 | **B HAND-MIGRATION** | Likely human-curated (5 objects = small + structured set) | ✗ NO WRITER FOUND under broader grep — query target list only |
| ExternalKnowledge | 12521 | **A pipeline** | Per `external_knowledge_ingester.py` (KEI-201 sibling) | ✓ `scripts/orchestrator/external_knowledge_ingester.py:59 WEAVIATE_CLASS = "ExternalKnowledge"` (module-level constant + ingester runtime) — **RECLASSIFIED B→A per Max audit; NOT orphan as previously claimed** |

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

### Category B — hand-migration required (3 classes — REVISED DOWN from original 5)

Post-Max-audit reclassifications: SessionTranscripts + SessionFacts + ExternalKnowledge moved out of B to A. The 3 remaining Category B classes are smaller (~62k objects total vs the original ~177k pre-reclassification):

**Sessions (48666).** `kei75_sessions_source_id.py` has `SESSIONS_CLASS = "Sessions"` constant but no upsert call; kei75_sweeps + kei75_sessions_source_id are READ-only (operating ON the class, not WRITING TO it). Recovery options:

  - (a) **Source IS reproducible — find or restore writer.** If a Sessions writer exists in archived branches OR was deleted post-some-refactor, restore + replay.
  - (b) **Rewrite writer.** ~100-200 LoC: walk Claude session JSONL files OR Slack listener events (depending on what populated the original 48k); emit one Hindsight memory per session boundary. Effort: 1-2 days.
  - (c) **Snapshot-based hand-migration.** Read the 48k objects from the `backups/memory_pre_hindsight_migration_20260525/` snapshot; write to Hindsight. ~half-day script + ~5-10 min ingest at the 50 ingests/sec rate.

**Recommended: (c) for cold-start unblock + (b) in parallel for ongoing freshness.** Otherwise post-cold-start session boundaries don't get captured.

**Discoveries (14176).** `scripts/orchestrator/discovery_log.py` writes `~/.claude/projects/.../discovery_log.jsonl` via `bd discover` invocations. The JSONL is the canonical source — verified. What's MISSING is the JSONL → Weaviate Discoveries class indexer. The Weaviate class has 14176 objects but the code path that reads the JSONL and writes to Weaviate isn't in the codebase under broader-grep extended methodology. Possibilities:

  - The indexer was deleted post-PR-#1196 reingest-with-vectorizer work (the existing kei196 script appears to TRANSFORM existing Discoveries rather than ingest new ones)
  - Discoveries were populated by a one-shot KEI-196 bootstrap that's gone

**Recovery: snapshot-based hand-migration for cold-start; indexer rewrite (~200 LoC, reads JSONL → emits Hindsight memories) for ongoing.**

**Global_governance_patterns (5).** Only 5 objects suggests human-curated set. Recovery: easiest of the 3 — copy the 5 objects from snapshot to Hindsight manually + document the canonical content + decide whether they're meant to be re-curated periodically (manual maintenance) or were truly one-time. ~1 hour effort.

### Category C — derived (0 classes — REVISED from original 1)

**SessionFacts moved C→A** per Max audit. The original dispatch claim "SessionFacts is derived from SessionTranscripts" was wrong: empirically `session_transcript_indexer.py:385` has its OWN `upsert_object("SessionFacts", ...)` call alongside the SessionTranscripts call at line 237. SessionFacts is its own pipeline product from the SAME source (Claude session JSONL files), not a derivation pass.

No Category C classes remain.

### Discoveries note

Covered in §Category B above. JSONL writer exists; Weaviate indexer absent under broader grep. Hand-migration from snapshot for cold-start; indexer rewrite for ongoing freshness.

---

## Risk surface — what could break the cold-start

**Risk 1 — DOWNGRADED post-Max-audit.** Previously: "SessionTranscripts hand-migration is the long-pole (117k objects)." Reclassified: SessionTranscripts is now Category A pipeline-fed via `session_transcript_indexer.py:237`. Cold-start re-points the indexer's writes to Hindsight; existing replay logic backfills from the Claude session JSONL source. **Risk evaporates** for SessionTranscripts, SessionFacts, and ExternalKnowledge (all three: re-point indexer + replay = same risk-zero shape as Decisions/AgentMemories/Keis). Cold-start critical path is no longer the 117k-object SessionTranscripts ingest window.

**Risk 2 — ExternalKnowledge origin remains unknown — RESOLVED post-Max-audit.**

If 2-4 hours of investigation doesn't surface the writer or curator, we proceed with snapshot-based hand-migration and accept that the 12521 objects become stale-by-default in Hindsight (no pipeline keeps them fresh). For a class whose role we don't fully understand, this might be acceptable (treat as reference data); if they were meant to be ingested-continuously, post-cold-start retrieval quality degrades over time. **Mitigation: tag these objects in Hindsight metadata as `provenance: unknown_pre_migration` so post-cold-start operators see them clearly when querying.**

**Risk 3 — Discoveries indexer rewrite races bd discover writes.**

If the JSONL→Weaviate (now JSONL→Hindsight) indexer is rewritten DURING cold-start, there's a window where bd discover writes to JSONL but the new indexer isn't yet running. New discoveries land in JSONL but not in Hindsight. **Mitigation: snapshot the JSONL at cold-start time; replay it through the new indexer when ready; concurrent bd discover writes go into a queue that the indexer drains on first run.**

**Risk 4 — Slack history retention may have expired older objects.**

Slack workspace retention policy could be shorter than the historical 14772-object Slack_history span. Re-querying Slack might return fewer than 14772 objects. **Mitigation: spot-check the oldest object timestamp in Slack_history pre-cutover; if older than current Slack retention, use snapshot as fallback for the orphaned window.**

**Risk 5 — StrategicDocuments indexer is currently failing.**

Per dispatch: "drive-strategic-indexer (currently failing)." Until the indexer is fixed, Category A re-ingest doesn't work for this class. **Mitigation: either fix the indexer pre-cold-start (preferred) OR hand-migrate the 2 existing objects from snapshot + accept stale-by-default until indexer fix lands (acceptable because object count is tiny).**

---

## Cold-start recovery plan summary (REVISED post-Max-audit)

| Class | Migration approach | Effort | Blocker on cold-start? |
|---|---|---|---|
| Decisions / AgentMemories / Keis / Codebase / Slack_history / ToolCalls / SessionTranscripts / SessionFacts / ExternalKnowledge | Re-point indexer's target → Hindsight bank; replay from source | ~1h per indexer × 9 = 9 hours | No |
| StrategicDocuments | Fix indexer first (separate KEI) OR hand-migrate 2 objects from snapshot | ~30 min snapshot path / TBD indexer fix | Soft yes (block on indexer fix preferred) |
| Sessions | Snapshot-based hand-migration + rewrite writer for ongoing | ~half-day snapshot + ~5-10min ingest / ~1-2 days writer rewrite | Soft yes |
| Discoveries | Snapshot-based hand-migration + rewrite JSONL→Hindsight indexer for ongoing | ~1 day script + ~2-3 days indexer rewrite | Soft yes |
| Global_governance_patterns | Manual copy of 5 objects from snapshot + decide curation policy | ~1 hour | No |

**Critical path on cold-start: simplified dramatically post-reclassification.** No single 117k-object long-pole. The largest hand-migration is Discoveries (~14k objects, ~5min ingest at 50/sec). All other Category B classes are small (Sessions 48k via snapshot is ~16min ingest; Global_governance_patterns 5 is trivial).

**Net effort comparison:**
- Original audit estimated cold-start critical path at ~1-2 days (SessionTranscripts long-pole)
- Revised cold-start critical path: ~2-3 days for the Discoveries indexer REWRITE (if we want ongoing freshness), parallel with single-day Category A re-point pass for 9 classes

**Revised cold-start sequence:**
1. Pre-cutover (parallel-safe): fix StrategicDocuments indexer; rewrite Sessions writer + Discoveries indexer (in parallel — both are <2-day rewrites).
2. Cutover day 1: parallel re-point of 9 Category A indexers (~9 hours wall-clock if sequential, faster if parallelised); snapshot-based hand-migration of Sessions + Discoveries + Global_governance_patterns (each <1hr ingest at 50/sec).
3. Cutover day 2: validation + cleanup. Query Hindsight, compare object counts per class to pre-migration Weaviate counts, flag any drift >5%.
4. Post-cutover: rewritten Sessions writer + Discoveries indexer go live for ongoing freshness.

---

## Out-of-scope for this audit

- **Per-object schema migration** (Weaviate property → Hindsight metadata mapping). Separate doc for step 3 / step 5.
- **Cold-start window scheduling** (when do we do the SessionTranscripts long ingest?). Operational decision.
- **Backup of the snapshot itself** (already done per dispatch — Orion-confirmed chmod -R a-w archive). No action.
- **Post-cold-start hot-write handling** (bd discover writes during cold-start window go where?). Addressed in §Risk 3 mitigation but full design is step 5 territory.

---

## Acceptance criteria

- [x] All 13 classes classified (A/B/C) — see §Classification table (REVISED post-Max-audit: 10 A + 3 B + 0 C).
- [x] Source documented per class (table column + per-class detail).
- [x] Writer-not-found classes flagged with recovery options (3 classes post-revision: Sessions, Global_governance_patterns, Discoveries).
- [x] Risk surface enumerated with mitigations (R1 + R2 downgraded post-reclassification; remaining risks still apply).
- [x] Methodology-correction note added (§Headline finding + §Methodology correction).
- [x] Cold-start sequence revised — Category B drops from 5 to 3 classes; SessionTranscripts long-pole evaporates.
- [x] Cold-start recovery plan summary table.
- [ ] Elliot impl-feasibility concur.
- [ ] Max code-quality concur (audit-doc lens = "are the per-class source claims empirically verified / are the recovery options operationally executable?").

---

_End audit. Per orchestrator-merge-after-NATS-concur + author-exclusion: Aiden authored; eligible reviewers Elliot + Max; 2-of-2 lands admin-merge. Step 5 (re-point indexers) consumes the §Cold-start recovery plan summary as input._
