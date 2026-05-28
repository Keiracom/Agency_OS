# Embedding Model Upgrade Evaluation — 2026-05-28

**Author:** Scout (research lane) · dispatched by Elliot
**Status:** ▸ RESEARCH — NOT a ship signal. No labelled ground-truth eval was run (none exists; see §2).
**Question asked:** should we upgrade from "BGE-small via TEI" to a larger embedding model (BGE-large / BGE-m3) to improve retrieval quality?

---

## ─── TL;DR (recommendation) ───

▸ **NO / DEFER.** An embedding-model upgrade cannot be justified or even measured today, for four independent reasons — and the dispatch's stated baseline is incorrect:

1. **We are not on BGE-small.** The operational embedder is **`gemini/gemini-embedding-001` (768-dim)**, configured in the canonical agency-os `.env`. BGE-small-en-v1.5 via TEI is the *documented V1 plan* (ARCHITECTURE.md), not what is running. TEI runs the **reranker** (`bge-reranker-base`), not the embedder. (§1)
2. **The proposed metric can't measure embedding quality.** "Compare top-3 reranker scores between models" — the reranker is a cross-encoder that re-scores query↔document *text*, **independent of the embedding model**. The embedding model only changes *which* candidates enter the rerank pool. (§2)
3. **No ground-truth golden set exists** (Orion's FlashRank baseline, `docs/retrieval/flashrank_baseline_2026-05-28.md`, established this). Without relevance labels, "model A retrieves better than B" is indefensible. (§2)
4. **Candidate models can't be A/B'd here.** Comparing embedders requires **re-embedding the whole corpus** under each candidate into parallel banks (Hindsight embeds server-side) — not a research-script operation. (§2)

▸ **Bigger finding than the embedding question:** the operational embedder is already a *top-tier* model (Gemini-001 outranks every BGE variant on public MTEB), and the live retrieval-quality signal is currently **gated by the reranker + corpus, not the embedder** — the primary-task top score is **0.39 today, below the cutover P3 ≥0.5 bar (was 0.97 on 2026-05-28)**. The embedding model is the *least* leveraged variable in the current retrieval stack. (§3)

▸ **What to do instead:** the §6 prerequisite chain (reconcile docs↔config + BYOK-sovereignty decision → investigate the 0.97→0.39 reranker regression → build a labelled golden set → then A/B with the §7 harness).

---

## §1 — Current state (CORRECTED)

| | Documented (ARCHITECTURE.md / `docker-compose.tei.yml`) | **Operational (canonical `.env`, verified live)** |
|---|---|---|
| Embedder | BGE-small-en-v1.5, 384-dim, self-hosted TEI (CPU) | **`gemini/gemini-embedding-001`, 768-dim, Google AI API** |
| Provenance | `eleven_agreed_positions #1`: "BGE-small (fastembed lineage, BYOK-sovereign)" | `EMBEDDING_PROVIDER=gemini` / `EMBEDDING_MODEL=gemini/gemini-embedding-001` / `EMBEDDING_DIMENSIONS=768` |
| Reranker | TEI `bge-reranker-base` cross-encoder | TEI `bge-reranker-base` @ `:8091` (confirmed `/info`) — **this is the only TEI in the live path** |
| Corpus | — | `fleet_decisions` bank: **10,291 facts**, last doc 2026-05-28 (dual-write mirror enabled today) |

**Divergence is itself a finding.** The architecture commits to a *BYOK-sovereign, self-hosted* embedder (per-tenant VPC, no third-party data egress). The running config uses an **API embedder** (Gemini) — query/document text leaves the tenant boundary to Google. That is a data-sovereignty decision that contradicts the ratified architecture and needs explicit reconciliation **before** any "which embedding model" question is even coherent.

Evidence:
```
$ grep -i EMBEDDING ~/.config/agency-os/.env
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini/gemini-embedding-001
EMBEDDING_DIMENSIONS=768
$ curl -s localhost:8091/info → {"model_id":"BAAI/bge-reranker-base", ...}      # TEI = reranker
$ curl -s localhost:8889/v1/default/banks → fleet_decisions {"fact_count":10291}
```

---

## §2 — Why the dispatch's comparison cannot be run (4 blockers)

**B1 — Reranker scores are embedding-independent.** The pipeline is two-stage: Hindsight ANN recall → `bge-reranker-base` cross-encoder rerank (`orchestrator.retrieve_with_outcome`). The reranker scores each query↔document **text** pair; it never sees the embedding vector. Swapping BGE-small→BGE-large changes *which* documents reach the rerank pool (recall@k_initial), **not** the reranker score of a given pair. So "compare top-3 reranker scores between embedding models" measures the wrong thing — it would report near-identical scores whenever the same relevant doc is in both pools.

**B2 — Hindsight exposes no recall score.** Hindsight 0.7.0 `/recall` returns results with **no `score`/`relevance` field** (keys observed: `chunk_id, context, document_id, entities, id, mentioned_at, metadata, occurred_*, source_fact_ids, tags, text, type`). `orchestrator._gather_ann_pool` therefore assigns every ANN candidate `score = 0.0`. **The embedding/ANN layer contributes zero numeric signal to ranking** — all discriminative scoring is the reranker's. (Consequence: with the reranker bypassed, every query returns 0 citations via the KEI-198 all-zero sentinel — see §3.)

**B3 — No ground-truth golden set.** Per `docs/retrieval/flashrank_baseline_2026-05-28.md` (Orion): "no canonical eval query set exists … a precision number measured now would be indefensible as a ship signal." Embedding-quality comparison needs relevance labels (recall@k); none exist. The same blocker that stopped a FlashRank precision baseline stops an embedding precision comparison.

**B4 — Candidates require a corpus re-embed.** Query and document vectors must come from the *same* model. Comparing BGE-large/BGE-m3 means deploying a TEI for each, **re-embedding all 10,291 facts** into parallel Hindsight banks, then querying each — multi-GB model pulls + full re-index, not feasible in a research dispatch (and pointless without B3's labels).

**Note on the source query set:** the dispatch cites "10 canonical test queries from `docs/cutover/empirical_test_spec.md §1`." That spec's §1 defines **2 tasks** (primary multi-tenancy + control), not 10 queries. The "or equivalent" 10-query set is the merged adversarial-probe battery (`tests/retrieval/test_adversarial_probe.py`, PR #1251) — used by the §7 harness.

---

## §3 — Live retrieval health snapshot (real, measured today)

Run through the real path (`agent_query.query`) against live Hindsight, primary task from `empirical_test_spec.md §1.1`:

| Condition | Result |
|---|---|
| **Reranker engaged** (`DISPATCHER_RERANKER_ENABLED=true`, `KEIRACOM_RERANKER_URL=:8091`) | 5 citations; correct doc ranked #1 ("single system with tenant isolation … Dave=1, customers=2+"); **top score 0.39**; `bypass_rerank=False` |
| **Reranker bypassed** (default probe, no flag) | **0 citations**; all scores 0.0 → KEI-198 vectorizer-regression sentinel; `bypass_rerank=True` |

Two findings:
- **Retrieval is *correct* but reranker-dependent.** The right decision surfaces #1 — good. But it only works with the reranker explicitly engaged; the raw-ANN path returns nothing (B2).
- **Quality regression vs the cutover spec.** `empirical_test_spec.md §1.1` recorded the same task's top reranker score at **0.97** on 2026-05-28; today it is **0.39 — below the P3 ≥0.5 cutover bar**. Between those points the corpus grew (~1,900 docs → 10,291 facts via the dual-write mirror). This is a **reranker/corpus-chunking issue, not an embedding-model issue**, and is far more urgent than an embedding upgrade. → flagged to Elliot for a triage dispatch.

```
$ DISPATCHER_RERANKER_ENABLED=true KEIRACOM_RERANKER_URL=http://localhost:8091 \
  python3 -c "agent_query.query('...multi-tenancy...')"
citations: 5 bypass_rerank: False
  score=0.3926 [Decisions] Decision made for single system with tenant isolation, no sandbox...
  score=0.1488 [Decisions] The design system's status is 'RATIFIED_PENDING_EXECUTION'.
```

---

## §4 — Candidate models (PUBLISHED benchmarks only — not local measurement)

⚠️ Values are **approximate published figures** (MTEB leaderboard, model cards) as of knowledge cutoff. **Verify against the live leaderboard before acting**, and note Orion's caveat: *general MTEB retrieval may not reflect this workload* (short governance/decision recall, not web QA).

| Model | Dim | Params / size | License | MTEB retrieval (approx, published) | Sovereignty |
|---|---|---|---|---|---|
| BGE-small-en-v1.5 *(documented baseline)* | 384 | ~33M / 0.13 GB | MIT | ~51.7 | self-hosted ✓ |
| BGE-base-en-v1.5 | 768 | ~110M / 0.44 GB | MIT | ~53.2 | self-hosted ✓ |
| BGE-large-en-v1.5 | 1024 | ~335M / 1.3 GB | MIT | ~54.3 | self-hosted ✓ |
| BGE-m3 (multilingual, dense+sparse+colbert) | 1024 | ~568M / 2.3 GB | MIT | strong multilingual (MIRACL leader) | self-hosted ✓ |
| **gemini-embedding-001 *(operational)*** | 768* | API (no local) | proprietary API | top-tier (~68 avg MMTEB, Google-published) | **API — text egresses tenant boundary** |

\* configurable (768 / 1536 / 3072); the system is set to 768.

**Reading:** on *published* benchmarks the operational model (Gemini-001) **already outranks every self-hosted BGE variant**. So "upgrade from BGE-small to BGE-large/m3" is moot under the corrected premise — it would be a *downgrade* on raw MTEB, traded for sovereignty. The real fork is **API-quality-now vs self-hosted-sovereign**, not small-BGE vs large-BGE.

---

## §5 — Infra cost delta ($AUD, 1 USD = 1.55 AUD)

⚠️ Order-of-magnitude; **verify current Google AI + cloud-GPU pricing** before quoting to Dave.

| Option | Cost model | Indicative $AUD | Notes |
|---|---|---|---|
| **Gemini-001 (current)** | per-token API, ongoing | ~A$0.23 / 1M tokens (≈ US$0.15) | scales with corpus re-index + every query + **per tenant**; recurring; sovereignty cost (data egress) |
| BGE-small self-hosted | fixed CPU (co-located w/ reranker TEI) | ~A$0 marginal | already-budgeted CPU sidecar pattern |
| BGE-large self-hosted | fixed; CPU feasible / GPU for throughput | ~A$300–900/mo GPU instance (if GPU) | 1024-dim = ~2.7× pgvector storage + HNSW memory vs 384-dim |
| BGE-m3 self-hosted | fixed; GPU recommended | ~A$300–900/mo GPU + 2.3 GB model | multilingual + multi-vector; heaviest |

**The cost question that matters** is not "which BGE" — it's **API (variable, per-tenant, egress) vs self-hosted (fixed, sovereign)**. For a per-tenant-VPC BYOK product (ARCHITECTURE §SECTION 5), a fixed self-hosted embedder is the architecturally-coherent choice; the cost is one-time infra, not recurring per-tenant API spend.

---

## §6 — Recommendation + prerequisite decision tree

**Recommendation: DEFER the embedding-model upgrade.** It is unmeasurable and not the bottleneck. Resolve these first, in order:

1. **Reconcile docs ↔ config + decide sovereignty** *(Dave/architecture call).* Is the operational Gemini-001 embedder intentional, or drift from the ratified self-hosted-BGE position? An API embedder egresses tenant text — settle this before optimising *which* model.
2. **Triage the 0.97 → 0.39 reranker-score regression** *(build/diagnosis dispatch).* Corpus grew 5×; chunking/scoring changed. The cutover P3 gate currently fails. This blocks cutover regardless of embedding.
3. **Build a labelled golden set** (recall@k relevance judgments over the adversarial-probe queries + the §1.1/§1.2 spec tasks). This is the *only* defensible way to measure embedding quality — and is prerequisite to FlashRank/reranker eval too (shared with Orion's Option-A bd issue).
4. **THEN, if pursuing self-hosted:** A/B BGE variants via the §7 harness — re-embed into parallel banks, measure **recall@k_initial** (not reranker score) against the golden set.

---

## §7 — The defensible empirical harness (run when §6.3 lands)

Embedding quality = **recall@k_initial against ground truth**, NOT reranker score (§2/B1). Procedure:
1. Golden set: `{query → relevant_doc_ids}` over the 10 adversarial-probe queries (PR #1251) + spec §1.1/§1.2.
2. For each candidate model M: deploy TEI(M), re-embed the corpus into bank `fleet_decisions__M`, point `HINDSIGHT` at it.
3. For each query: pull top-`k_initial` (pre-rerank) from each model's bank; compute **recall@k_initial** = (relevant docs in pool) / (total relevant). This isolates the embedder's contribution.
4. Rerank is held constant (same `bge-reranker-base`) — report end-to-end nDCG@3 secondarily.
5. Compare recall@k_initial across models with the golden set as truth. *That* table is a ship signal; reranker-score tables are not.

---

## §8 — GOV-9 findings & provenance

**Directive scrutiny — 5 gaps:**
1. Premise wrong: baseline is Gemini-001, not BGE-small (§1).
2. `empirical_test_spec.md §1` has 2 tasks, not 10 queries → adversarial-probe set is the equivalent (§2 note).
3. Proposed metric (reranker scores) can't measure embedding quality (§2/B1).
4. No ground-truth golden set → quality comparison indefensible (§2/B3, Orion).
5. Candidate A/B needs a corpus re-embed → not runnable in a research dispatch (§2/B4).

**Surfaced separately to Elliot (out of this doc's scope but found during it):**
- Live primary-task reranker score 0.39 < P3 0.5 cutover bar (§3) — recommend a triage dispatch.
- **PR #1262 collision:** my `run_agent_with_recall.sh` (authored on a stale branch base where the file didn't exist) **clobbers the existing Nova #1257 / Elliot wrapper on current main**. Must rebase/withdraw that file before #1262 merges.

**Provenance:** canonical `.env` (`~/.config/agency-os/.env`); `infra/keiracom_system/embeddings/docker-compose.tei.yml`; `ARCHITECTURE.md` §SECTION 5 + eleven_agreed_positions #1; live Hindsight `:8889` + reranker `:8091`; `docs/cutover/empirical_test_spec.md` §0/§1/§3; `docs/retrieval/flashrank_baseline_2026-05-28.md` (Orion); MTEB leaderboard + model cards (published, verify). All live numbers measured 2026-05-28.
