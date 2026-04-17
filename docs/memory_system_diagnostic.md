# Agency OS Memory System — Diagnostic

**Author:** Aiden
**Written:** 2026-04-17 (provenance only)
**Companion:** Scout's literature-review output (memory architectures, cognitive science) is the prescriptive half. This doc is the diagnostic half — what's broken in OUR system, with evidence.

---

## TL;DR

We have a write-only memory graveyard. **356 rows in `public.agent_memories`, zero have ever been retrieved.** The SIGNOFF_QUEUE has 17 items found, scored ≥85, never actioned — same pattern at the governance layer. The problem isn't storage capacity or retrieval capability; both exist. The problem is that **no loop binds storage to use**. Every row written is a token cost with no realised return.

## Evidence

### 1. `agent_memories` is 100% unread

| source_type     | rows | state     | avg access_count | never accessed |
|-----------------|-----:|-----------|-----------------:|---------------:|
| decision        | 207  | confirmed | 0.00             | 207            |
| daily_log       | 43   | confirmed | 0.00             | 43             |
| verified_fact   | 33   | confirmed | 0.00             | 33             |
| test_result     | 28   | confirmed | 0.00             | 28             |
| pattern         | 21   | confirmed | 0.00             | 21             |
| skill           | 10   | confirmed | 0.00             | 10             |
| reasoning       | 10   | confirmed | 0.00             | 10             |
| dave_confirmed  | 4    | confirmed | 0.00             | 4              |

Every row is `state='confirmed'`. The `state` column (designed to support `tentative`/`superseded`/`contradicted`/`archived`) is dead. Nothing ever gets promoted, demoted, or killed. It's all "confirmed" by default on write.

### 2. SIGNOFF_QUEUE has 17 items, all `pending`

13 cold-email items scored 85-95 on business value (za-zu, Patio11, Sriram, CB Insights, ElevateSells teardown, etc.). 4 agent-architecture items scored 85-95 on learning (Anthropic "Building Effective AI Agents" at 95, Anthropic "Effective Context Engineering" at 95, MetaGPT, LangChain).

The Anthropic "Building Effective AI Agents" item is literally labelled: *"This IS the blueprint for Elliot."* Unread. Unimplemented. Sitting at `pending` for months.

### 3. No duplicates — so waste isn't from copies

Duplicate detection on first 200 chars returned 0 groups. The pile is 356 unique items that nobody reads, not 100 items copy-pasted 3.5 times. This matters: it means the system is writing novel signal into a void, not thrashing on repetition.

### 4. Content is short enough to index, long enough to matter

- 11 rows under 100 chars (too short, likely noise)
- 203 rows at 100-500 chars (bulk of signal)
- 91 rows at 500-2000 chars
- 51 rows at 2000-10000 chars (deep context / analyses)

If retrieval worked, the 342 rows ≥100 chars contain material Aiden and Elliot would benefit from re-encountering.

## Failure modes, named

### FM-1 — Write-only storage (no retrieval loop)
No process reads from `agent_memories` during normal session work. The `/recall` command exists but isn't invoked ambient-style; it's only used on direct Dave request. Bots write to memory at session end (if at all) but never query it at session start, during reasoning, or before acting. **Result:** memory is a log, not a working substrate.

### FM-2 — No state transitions (all confirmed, no forgetting)
`state` column supports `tentative`/`confirmed`/`superseded`/`contradicted`/`archived`, but every row is `confirmed`. No decay mechanism. A decision made 60 days ago sits next to one made 60 seconds ago with identical weight. Without forgetting or demotion, signal-to-noise is pure gravity — old true things and old wrong things and recent important things compete equally.

### FM-3 — No salience weighting
`business_score` and `learning_score` exist on the schema (cognitive columns from migration 103) but the distribution shows they're not being set on write — nothing surfaces based on importance. All rows are equivalent in retrieval priority. Biological memory doesn't work this way; high-salience events are over-indexed at encoding.

### FM-4 — No action-binding at ingest
Findings enter the system as notes, not as action proposals. SIGNOFF_QUEUE items have `Action: absorb` or `Action: research` or `Action: evaluate_tool` — none of these are terminal. There's no `Action: integrated` or `Action: rejected-because-X` state. Dave's frustration is correct: a note with "action: absorb" and no subsequent implementation is indistinguishable from a note with no action verb at all.

### FM-5 — No retrieval feedback → no reinforcement
`access_count` = 0 across all rows means even if we DID retrieve, nothing would reinforce. A well-designed memory system uses retrieval frequency as a signal for consolidation vs decay. Ours can't — no reads means no reinforcement loop closes.

### FM-6 — No connective structure
The `supersedes_id` / `contradicted_by_id` / `promoted_from_id` self-FK columns are empty. Memories are isolated nodes. Nothing says "this decision supersedes that one" or "this contradicts that earlier finding." Each row stands alone, so a retrieval that returns row X doesn't surface the chain of reasoning that led to X or the newer row that invalidated X.

## What the data is telling us

The system failed at **utilisation**, not at **acquisition**. Acquisition is fine (356 rows, 0 dupes, varied source_types, reasonable content lengths). Utilisation is zero. Every engineering effort we've put into memory has been on the storage side — schema, indexing, cognitive columns, embeddings. None on the retrieval-into-action side.

That means fixing it with more schema won't work. The fix is a **runtime behaviour** — something that actually reads memory as part of the session loop, binds retrieval to decisions, and creates a feedback signal that closes the consolidation loop.

## What scout's literature review needs to answer

- **Consolidation + forgetting:** McClelland's complementary learning systems, hippocampal replay, interference theory. How do biological systems decide what to keep vs drop? Can we port the mechanism?
- **Retrieval-augmented reasoning patterns:** Which deployed agent systems (Letta, mem0, Zep, MemGPT) actually close the retrieval-into-reasoning loop, and how? Code patterns worth stealing.
- **Salience encoding:** How is importance weighted at write-time in biological memory (emotional tagging, surprise, novelty)? What's the computational analogue?
- **Reconsolidation:** When memory is retrieved, it becomes labile and can be modified. Deployed agent systems rarely do this — finding one that does and understanding how is high-leverage.
- **Action-binding:** Research on how human intentions-in-memory convert to actions (prospective memory, implementation intentions — Gollwitzer). Can we bake this into the data model so every memory has an associated action trigger?

## Immediate actions (volume/event-triggered, not calendar)

These don't need Dave's go — they're diagnostic follow-through:

1. **Instrument retrieval.** Every call to `retrieve()` / `recall()` / `/recall` must increment `access_count` and update `last_accessed_at`. If it doesn't now, that's a bug, not a design choice. Verify in `src/memory/retrieve.py`; patch if missing.
2. **Ingest gate on state.** New rows default to `tentative`, not `confirmed`. Promotion to `confirmed` requires a retrieval event OR a peer-check signal OR explicit Dave confirmation. Stops the "everything is confirmed by default" pathology.
3. **Action-binding at SIGNOFF ingestion.** Every SIGNOFF row must carry a terminal-action proposal (`integrate`/`reject`/`watch-with-trigger`) at write-time, not as a post-hoc review. If the agent ingesting can't propose a terminal action, the item is below bar — don't write it.
4. **Connective writes.** When a new memory contradicts or supersedes an existing one, the `contradicted_by_id` / `supersedes_id` must be populated. Require this at write-time for `decision` and `verified_fact` source_types at minimum.
5. **Retrieval-in-loop.** Session start: retrieve the top-N relevant memories for current directive (by tag/semantic match). Before every significant action: retrieve the top-K memories that could contradict the plan. This is the loop that was missing.

Items 1-5 are all build-able now. Scout's literature review will likely produce a more principled reshape; these are the stop-the-bleeding moves.

## Follow-up items for Elliot peer-check

- Is my FM-1 diagnosis right that `/recall` exists but is never invoked ambient-style? Or are there paths I'm missing?
- Is item 1 (instrument retrieval) actually a bug vs a design omission? Check `src/memory/retrieve.py` and tell me.
- Do items 3-5 conflict with anything you're already building on the cognitive-assistant listener?
