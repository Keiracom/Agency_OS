# FlashRank characterisation baseline — NOT precision@5

**Date:** 2026-05-28
**Author:** ORION (Aiden's build clone)
**main SHA at measurement:** `7675c2355b2018fdc25ff3f0798bb8403b549b4a`
**Dispatch:** Elliot → Aiden → Orion. Option B (ground-truth-free proxy) per Aiden's decision on Orion's GAP report.

> ⚠️ **This is a characterisation of reranker *behaviour and cost*, not a quality metric.**
> It deliberately does **NOT** report precision@5. There is no labelled golden query
> set and no ground-truth relevance judgments, so a precision number measured now
> would be indefensible as a ship signal. The proper labelled eval harness is filed
> separately as the Option-A bd issue. These numbers say *how much FlashRank reorders
> the raw ANN candidates and how long it takes* — they say nothing about whether the
> reordered order is **better**.

## Why Option B (and not precision@5)

Orion's directive-scrutiny pass found three blocking gaps for a precision@5 baseline:

1. **FlashRank was not installed** in this worktree venv — every query would have
   bypassed to raw ANN (`reason="flashrank_not_available"`, `rerankers.py:56-59`),
   producing a raw-ANN number mislabelled as FlashRank. *Resolved for this run* by
   installing `flashrank==0.2.10` into the venv (reversible; no production code touched).
2. **The premise was inverted** — FlashRank is *already* the live reranker
   (`orchestrator.py:7-8` → `rerankers.rerank_top_k`). The Nova cross-encoder sidecar
   Wave 1 (#1229) and Wave 2 (#1232) already merged to main. "Wave 3" *swaps*
   FlashRank → sidecar; it does not introduce reranking.
3. **No ground truth** — no canonical eval query set exists; one agent hand-labelling
   its own queries is subjective and non-reproducible.

Aiden chose Option B: characterise the current FlashRank reorder behaviour as the
pre-swap artifact Wave 3 diffs against.

## Method

- **Harness:** `scripts/retrieval/flashrank_characterization.py` (committed alongside this
  report — re-runnable for the Wave-3 after-picture).
- **Backend:** live Hindsight at `http://localhost:8889`, real `/memories/recall` per
  collection (read-only; no writes).
- **Reranker:** in-process FlashRank, model `ms-marco-MiniLM-L-12-v2`, `flashrank==0.2.10`,
  Python 3.12.3.
- **Params:** `k_initial=20`, `k_returned=5` (orchestrator defaults).
- **Latency budget:** raised to `5000ms` for this run via `AGENCY_OS_RERANK_BUDGET_MS`
  to *force the rerank path* (see Finding 2 — at the production default it would bypass).
- **Per query, measured:** rank churn (raw-ANN top-5 identities surviving into the
  FlashRank top-5, plus mean absolute position shift), raw-ANN scores vs FlashRank
  relevance scores for the top-5, and wall-clock ms around `rerankers.rerank_top_k`.
- **Node identity:** `metadata.chunk_id` (falls back to `external_id`, then text hash).

### Collections queried

Probed all ten fleet banks first. **Eight of ten are empty** (see Finding 1), so the
harness queries only the two populated banks:

- `fleet_global_governance_patterns` — 19 documents
- `fleet_decisions` — 2 documents

Combined pool = 21 candidates per query (recall over a small corpus returns the whole
corpus, so each query reorders the same 21 docs — the ANN *order* differs per query).

### Query set (10, governance/decisions-themed to hit the populated banks)

```
1.  agent governance rules and laws
2.  Step 0 RESTATE requirement before execution
3.  how are pull requests reviewed and merged
4.  callsign discipline and identity enforcement
5.  FlashRank cross-encoder reranker design
6.  Hindsight memory recall reader cutover
7.  dispatcher spawn budget ceiling gate
8.  bounded spawn one task per spawn enforcement
9.  Linear and Beads issue tracker sync
10. three-store completion rule LAW XV
```

## Results

| Query | Pool | Rerank latency (ms) | Displaced from top-k | Mean abs pos shift | Top-1 changed | Max FlashRank score |
|---|---|---|---|---|---|---|
| agent governance rules and laws | 21 | 631.2 | 1/5 | 0.8 | yes | 0.0220 |
| Step 0 RESTATE requirement before execution | 21 | 316.0 | 2/5 | 0 | no | 0.0000 |
| how are pull requests reviewed and merged | 21 | 315.8 | 1/5 | 1.25 | no | 0.0000 |
| callsign discipline and identity enforcement | 21 | 323.8 | 4/5 | 2.5 | yes | 0.0000 |
| FlashRank cross-encoder reranker design | 21 | 345.0 | 2/5 | 0.33 | no | 0.0000 |
| Hindsight memory recall reader cutover | 21 | 349.6 | 3/5 | 2 | yes | 0.0000 |
| dispatcher spawn budget ceiling gate | 21 | 324.6 | 1/5 | 0.5 | no | 0.0039 |
| bounded spawn one task per spawn enforcement | 21 | 327.5 | 0/5 | 1 | no | 0.0002 |
| Linear and Beads issue tracker sync | 21 | 347.1 | 4/5 | 2 | yes | 0.0000 |
| three-store completion rule LAW XV | 21 | 345.8 | 3/5 | 0.5 | no | 0.0000 |

### Summary

| Metric | Value |
|---|---|
| Queries total | 10 |
| Queries reranked (not bypassed, at 5000ms budget) | 10 |
| Queries bypassed | 0 |
| Rerank latency — mean | 362.6 ms |
| Rerank latency — median | 336.2 ms |
| Rerank latency — max | 631.2 ms (cold first call) |
| Mean candidates displaced from top-k | 2.1 / 5 |
| Top-1 result changed by rerank | 4 / 10 |

## Findings (characterisation only)

1. **8 of 10 fleet Hindsight banks are empty.** Only `fleet_global_governance_patterns`
   (19) and `fleet_decisions` (2) hold content; `fleet_keis`, `fleet_discoveries`,
   `fleet_agent_memories`, `fleet_sessions`, `fleet_codebase`,
   `fleet_strategic_documents`, `fleet_tool_calls`, `fleet_session_transcripts` all
   returned 0. Any retrieval-quality comparison (Wave 3 included) is currently exercising
   a near-empty corpus — this is the single most important caveat in this document and
   likely warrants its own indexing follow-up before Wave 3 A/B is trusted.

2. **At the production-default 200ms budget, FlashRank would bypass on every query.**
   Measured rerank latency on the 21-candidate pool was 316–631ms (median 336ms),
   all above `DEFAULT_BUDGET_MS=200`. This run forced the rerank path with a 5000ms
   budget. Implication: in default config the *currently shipped* behaviour is
   effectively raw ANN, not FlashRank. Wave 3's sidecar should be compared against
   that reality, and the budget itself is a tuning knob worth revisiting.

3. **FlashRank meaningfully reorders the ANN candidates.** Mean 2.1 of 5 top results
   displaced; the top-1 result changed in 4 of 10 queries; mean absolute position
   shift up to 2.5. So FlashRank does *not* agree with Hindsight's ANN order — there
   is real reordering signal for Wave 3 to diff against (direction/quality unknown
   without labels).

4. **Absolute FlashRank relevance scores are very low** (max 0.022, most ~0.000).
   Consistent with a small, generic governance-pattern corpus weakly matched by the
   cross-encoder for these queries. Do not read low scores as "bad retrieval" — they
   are characterisation, and the corpus is tiny.

## Reproduce

```bash
AGENCY_OS_RERANK_BUDGET_MS=5000 \
  python -m scripts.retrieval.flashrank_characterization
```

Requires `flashrank` installed and Hindsight reachable at `HINDSIGHT_BASE`
(default `http://localhost:8889`). Output is JSON on stdout.

## Follow-ups

- **Option A (filed as a separate bd issue):** labelled golden query set + precision@K
  eval harness as a reusable artifact for the real FlashRank-vs-sidecar A/B.
- **Indexing:** investigate why 8/10 fleet banks are empty before trusting any
  retrieval-quality comparison at scale.
- **Latency budget:** the 200ms default bypasses FlashRank on a 21-doc pool on this
  hardware — revisit during Wave 3 sidecar wiring.
