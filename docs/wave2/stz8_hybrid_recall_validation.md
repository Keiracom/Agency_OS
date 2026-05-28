# Agency_OS-stz8 — Hybrid Recall Validation (Path 1)

**Agent:** atlas
**Dispatched by:** elliot (PATH 1 AUTHORISED, 2026-05-28) after Aiden ARCH-CLEAR
**KEI:** Agency_OS-stz8 — CUTOVER-GATING — Hybrid search (vector + BM25 + metadata filter) in Hindsight recall (Tier 1 #1)
**Mandate:** LAW XIV raw-output, verbatim evidence.

---

## Outcome

**The cutover gate is met by the deployed Hindsight service as-is. No `RecallRequest` change, no fork, no upstream PR.**

Hindsight recall on the fleet instance (v0.6.2) is empirically confirmed to be **hybrid** — both a lexical/BM25 leg and a semantic/vector leg are live on the same recall endpoint. The stz8 premise ("replace pure-vector similarity with hybrid") was based on a misread: Hindsight recall was never pure-vector. It is a built-in multi-way hybrid (upstream `vectorize-io/hindsight` #708, "How We Built a 4-Way Hybrid Search System That Actually Runs in Parallel").

## Why the original Option-A scope was infeasible (and abandoned)

The dispatch initially scoped a `hybrid_alpha` field on `RecallRequest`, confined to `keiracom_system/fleet/hindsight/`, wired to "Weaviate's hybrid query". All three premises are false:

1. **Code location.** `RecallRequest` is defined upstream in `vectorize-io/hindsight` → `hindsight-api-slim/hindsight_api/api/http.py`, baked into the `ghcr.io/vectorize-io/hindsight` image. `keiracom_system/fleet/hindsight/` holds only deploy glue (docker-compose, provisioning, smoke wrappers). A change confined there — or to our MAL wrappers — cannot add a request field the vendor API rejects.
2. **`hybrid_alpha` does not exist.** Upstream code search for `hybrid_alpha` returns 0 results across all versions. The field name was invented.
3. **No Weaviate.** The deployed API spec has zero `weaviate`/`vectorchord`/`bm25`/`hybrid` references; Hindsight's backend is embedded Postgres + VectorChord. Weaviate is the *legacy* store being migrated away from in Phase A3. The alpha convention quoted (0.0=BM25 / 1.0=vector) is Weaviate's, not Hindsight's.

A genuine per-request alpha knob would require forking Hindsight (Option B) + a custom image — out of scope for a P0 cutover gate, and unnecessary given recall is already hybrid.

## Evidence — deployed service surface

```
GET http://localhost:8889/version
{"api_version":"0.6.2","features":{"observations":true,"mcp":true,"worker":true,"bank_config_api":true,"file_upload_api":true}}

RecallRequest params (/openapi.json):
  query, types, budget, max_tokens, trace, query_timestamp, include, tags, tags_match, tag_groups
Spec scan: hybrid=False, bm25=False, weaviate=False, vectorchord=False
```

Latest upstream tag is **v0.7.0** (we run v0.6.2; image is `:latest` + `pull_policy: always`).

## Evidence — empirical hybrid proof

Harness: `scripts/research/hindsight_smoke/validate_hybrid_recall.py`. Method: ingest
target atoms each carrying ONE rare, semantically-empty exact token (error code,
function name, decision ID) plus distractor atoms with no such token, then recall.

- **Lexical/BM25 leg:** query = the rare exact token. A token like `ENOENT_PG0_4471X`
  carries ~zero embedding signal — a pure-vector index cannot reliably surface it.
  Surfacing it (rank 1) proves a lexical/BM25 index is active.
- **Semantic/vector leg:** query = a paraphrase sharing NO exact token with the
  target. Surfacing the target proves a vector index is active.

Both legs on the same bank + same endpoint == hybrid.

```
=== stz8 hybrid-recall validation against http://localhost:8889 (bank=hybrid_validation) ===

[ingest] targets: {'err-code': True, 'fn-name': True, 'decision-id': True}

--- LEXICAL LEG (BM25): recall by rare exact token ---
  [error code   ] query='ENOENT_PG0_4471X' -> PASS rank=1 (n=5)
  [function name] query='release_already_reviewed_claims_zq7' -> PASS rank=1 (n=5)
  [decision id  ] query='DEC-STZ8-7QJ6' -> PASS rank=1 (n=5)

--- SEMANTIC LEG (vector): recall by paraphrase, no shared token ---
  [error code   ] 'what failure happened when the database storage ...' -> PASS rank=1 (n=5)
  [function name] 'which background routine unlocks tasks that were...' -> PASS rank=2 (n=5)
  [decision id  ] 'what was decided about proving blended search in...' -> PASS rank=1 (n=5)

=== VERDICT ===
  lexical (BM25) leg:   3/3 exact tokens surfaced at rank 1
  semantic (vector) leg: 3/3 paraphrases surfaced the target
  HYBRID CONFIRMED: True
```

Also confirmed: the rare tokens survive Hindsight's LLM consolidation verbatim
(consolidated fact text retained `ENOENT_PG0_4471X` exactly), and `async:False`
ingest is synchronous with no measurable recall lag.

## Follow-ups (not blocking stz8 closure)

- **Version pin.** The compose file uses `image: ...:latest` + `pull_policy: always`, so a restart silently adopts v0.7.0. For reproducibility, pinning to an explicit tag is worth a separate infra decision (own KEI). Not changed here so this validation's evidence stays tied to the version it was run against (v0.6.2).
- **Metadata pre-filter leg.** stz8's title also mentions a structured metadata pre-filter. `RecallRequest` already supports `tags` + `tags_match` (+ `tag_groups`); the existing `run_recall_tests.py` exercises tag filtering. Hybrid + tag pre-filter together cover the gate's three named components.
- **Cold-bank first-write race.** The first write to a freshly-created bank can 500/timeout; the harness absorbs this with a warm-up write + one ingest retry. Worth noting for any production ingest path against a new bank.
