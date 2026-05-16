# Hybrid Memory Phase Complete — Query Quality Probe
**KEI-73 closing validation, Dave-direct dispatch 2026-05-16**

- Author: ATLAS
- Corpus state: Discoveries 14,202 + Sessions 48,666 = 62,868 total
- Probe: 7-query battery from Aiden's build-phase query-gap set
- Method: nearVector via fastembed BGE-small-en-v1.5 (384-dim) → GraphQL Get top-5

## Per-query verdict matrix

| # | Query | Disc top dist | Sess top dist | Verdict |
|---|---|---|---|---|
| 1 | KEI-70 routing rejection rationale | 0.242 | 0.228 | Sessions saves; Discoveries noisy |
| 2 | Sonar S1172 unused parameter fix | 0.272 | **0.204** | EXCELLENT both |
| 3 | JSONB concurrent append race | 0.261 | 0.285 | WEAK — content not crisp |
| 4 | Dave rejection patterns directive | 0.233 | 0.215 | EXCELLENT both |
| 5 | task verification row KEI-58 | **0.226** | 0.203 | EXCELLENT both |
| 6 | Elliot ratification cross-session | 0.245 | 0.217 | Sessions good; Discoveries dup-chunked |
| 7 | gotcha failure pattern previously seen | 0.310 | 0.281 | WEAK — semantic intent mismatch |

**Overall score-quality verdict:** distances 0.18-0.33 range (BGE-small, lower=better). Sessions consistently scoring lower (0.20-0.25) than Discoveries (0.24-0.32) — Sessions retrieves more semantically similar content because rows carry full session-turn text. Discoveries rows are shorter distilled notes, smaller surface area for ANN.

## Verbatim top-1 citations per query

```
[1/7] "decision rationale rejecting random/percentage routing in KEI-70"
  Discoveries#1: task_verifications:bf5e00fb (KEI-53) — distractor, dist 0.2422
  Sessions#1: session_id 3546b03e KEI-62 elliot — "[KEI-62 Epsilon...]", dist 0.2282 ✓

[2/7] "Sonar S1172 unused parameter fix pattern"
  Discoveries#2: memory:reference_sonarcloud_verify_pattern.md (team) — dist 0.2767 ✓
  Sessions#1: session ad5f3957 elliot — "PR #781 SonarCloud S...", dist 0.2041 ✓

[3/7] "JSONB concurrent append race resolution"
  Discoveries#2: ceo_memory:calibration_funnel — "s1_failed_unnest_jsonb_bug", dist 0.2614 (adjacent)
  Sessions#1: session fbe88814 max — Beads issues.jsonl state, dist 0.2848 (off-topic)

[4/7] "Dave rejection patterns directive"
  Discoveries#1: memory:feedback_r1_summary_draft_workflow.md, dist 0.2325 ✓
  Sessions#3: session 32be5db2 aiden — "[ENFORCER]: Rule 9 -- DIRECTIVE-INITIATIV", dist 0.2222 ✓

[5/7] "task verification row passing KEI-58"
  Discoveries#1: memory:reference_task_verification_trigger.md, dist 0.2255 ✓
  Sessions#1: session c04e29a4 orion KEI-49 — "P0001: BLOCKED: Task KEI-49 has acceptance criteria and cannot be marked done without a verification record", dist 0.2031 ✓

[6/7] "cross-session Elliot ratification yesterday"
  Discoveries#1: ceo_memory:ceo:demo_migration_directive — April content (date-off)
  Sessions#1: session 3caf37a5 elliot ROLE-CONTEXT-PRE-2026-05-11 tag preserved, dist 0.2168 ✓

[7/7] "gotcha failure pattern previously seen"
  Discoveries#1: wave3_ingest KEI-73 — "agents_used: [subagent-task-a...]", dist 0.3100 (off-topic)
  Sessions#1: session 2a8cbfb1 elliot ROLE-CONTEXT-PRE-2026-05-11 tag, dist 0.2809 (weak)
```

## Anomalies (5)

1. **Empty raw_text on agent_memories rows.** Wave 4 (Aiden's) ingested many `agent_memories:UUID` rows where the raw_text is blank — only metadata survives. Most queries returned 2-4 such rows in top-5 with no body content. Citation traceable but excerpt unusable.

2. **`agent="unknown"` on many Wave 4 rows.** Source agent metadata lost during ingest for a subset. Less impactful (queries still work) but breaks per-agent filtering downstream.

3. **Wave 3 chunking duplication.** Queries 6 and 7 returned the **same wave3_ingest content 4-5 times** in Discoveries top-5. Chunker isn't dedup-ing identical chunks across overlapping source ranges. Pollutes top-K when query lands on duplicated topic.

4. **Sessions schema lacks `source_id` property.** Caught during probe — my initial query asked for `source_id` on Sessions and Weaviate silently returned empty. Wave 2's ingest path didn't add source_id to schema. Workaround: per-class field projection. Recommend: backfill source_id to Sessions for citation parity with Discoveries.

5. **Role-flag implementation divergence (intentional but worth noting).** Wave 1 (mine) uses `pre_role_swap: bool` metadata field on Discoveries. Wave 2 (Scout's, run by Elliot) uses inline text prefix `[ROLE-CONTEXT-PRE-2026-05-11: 'CTO'=Elliot, 'COO'=Max]` on Sessions raw_text. Both functional; Sessions approach is more visible to agents at retrieval (prefix is in returned text), Discoveries approach is more filterable (metadata-level where clause possible).

## Strongest performers (use these patterns)

- **Memory-notes (~83 distilled feedback docs)** consistently rank top-3 across Q2/Q4/Q5. High-signal, short, well-tagged. Best per-byte recall in corpus.
- **task_verifications** rank top-5 across Q5. Exact-match dist <0.25. Verbatim test output is searchable.
- **Sessions ROLE-CONTEXT-prefixed rows** preserve historical context inline — agents searching about pre-swap content get the role flag in the result text without needing metadata interpretation.

## Weakest performers (worth fixing)

- **agent_memories rows with empty raw_text** (Wave 4) — re-ingest with text payload backfilled.
- **wave3_ingest duplicate chunks** — apply hash-based dedup at chunker layer.
- **Time-based queries** (e.g. "yesterday") — semantic-only retrieval doesn't model recency. If Dave wants temporal filtering, need `created_at` range filter at query time. Q6 highlights this gap.

## Recommendation

Phase B is **READY FOR PRODUCTION USE for Q2/Q4/Q5-shape queries** (canonical, well-named topics). Q1/Q3/Q6/Q7 reveal gaps that should be addressed before relying on retrieval as the primary memory layer:

1. Fix Wave 4 empty-raw_text rows (re-ingest)
2. Fix Wave 3 chunk dedup
3. Add source_id property to Sessions schema + backfill
4. Add `created_at` range filter helper for temporal queries
5. Consider re-ranker (KEI-49 PR1 left FlashRank as follow-up KEI) — would lift Q1/Q7 from "noisy" to "useful"

After these fixes, expected query-quality state is GOOD across all 7 probe shapes.
