#!/usr/bin/env python3
"""validate_hybrid_recall.py — empirical proof that Hindsight recall is hybrid.

Agency_OS-stz8 (CUTOVER-GATING — hybrid vector+BM25 atom retrieval). The stz8
premise was "replace pure-vector similarity with hybrid". Empirical finding
(Atlas 2026-05-28): Hindsight recall is ALREADY a multi-way hybrid (upstream
vectorize-io/hindsight #708) — there is no per-request alpha knob in any version
and no Weaviate path (backend is embedded Postgres + VectorChord). So the gate
is satisfiable by VALIDATION, not by a RecallRequest schema change or a fork.

This harness proves the two legs of hybrid independently:

  LEXICAL LEG (BM25): ingest atoms carrying rare, semantically-empty exact tokens
  (error code, function name, decision ID) alongside distractor atoms with no
  such token, then recall BY the exact token. A random token like
  "ENOENT_PG0_4471X" has ~zero embedding signal — a pure-vector index could not
  reliably surface it. If it surfaces (ideally rank 1), BM25/lexical is active.

  SEMANTIC LEG (vector): recall with a paraphrase that shares NO exact token with
  the target atom. If the right atom surfaces, the vector leg is active.

Both legs passing on the SAME bank with the SAME recall endpoint == hybrid.

Run: python3 scripts/research/hindsight_smoke/validate_hybrid_recall.py
Targets the fleet instance (port 8889), bank "hybrid_validation". Re-runnable:
re-ingesting the same atoms is idempotent for the rank-1 assertion.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import post  # noqa: E402

FLEET_BASE = "http://localhost:8889"
BANK = "hybrid_validation"

# Each target atom embeds ONE rare exact token in otherwise-generic prose.
# The token is the kind of atomised terminology the cutover gate cares about:
# error codes, function names, decision IDs — content pure-vector tends to miss.
TARGETS = [
    {
        "id": "err-code",
        "token": "ENOENT_PG0_4471X",
        "kind": "error code",
        "content": "During the fleet deploy the consolidation worker raised error "
        "ENOENT_PG0_4471X after the volume mount failed at startup.",
        # Paraphrase shares NO exact token with the atom — exercises the vector leg.
        "semantic_query": "what failure happened when the database storage mount "
        "broke during rollout?",
    },
    {
        "id": "fn-name",
        "token": "release_already_reviewed_claims_zq7",
        "kind": "function name",
        "content": "The fleet supervisor sweeper release_already_reviewed_claims_zq7 "
        "frees claims that were reviewed but never closed.",
        "semantic_query": "which background routine unlocks tasks that were checked but left open?",
    },
    {
        "id": "decision-id",
        "token": "DEC-STZ8-7QJ6",
        "kind": "decision id",
        "content": "Decision DEC-STZ8-7QJ6 ratified that hybrid recall is validated "
        "empirically rather than by adding a request parameter.",
        "semantic_query": "what was decided about proving blended search instead of "
        "a new query field?",
    },
]

# Distractors: same domain prose, NONE of the rare tokens. If an exact-token query
# returns a distractor above its target, lexical ranking is weak.
DISTRACTORS = [
    "The deploy pipeline restarted the container after a routine image pull.",
    "A scheduled job archived old review threads at the end of the week.",
    "The team agreed to document the runbook before the next migration window.",
    "Monitoring reported nominal memory usage across the fleet host overnight.",
]


def _ingest(content: str, ext_id: str, tags: list[str]) -> bool:
    # One retry: the FIRST write to a cold bank can 500/timeout while the bank
    # is being created. Retrying absorbs that race so a flake never reads as a
    # recall failure.
    item = {"content": content, "tags": tags, "metadata": {"external_id": ext_id}}
    for _attempt in range(2):
        status, _ = post(
            f"/v1/default/banks/{BANK}/memories",
            {"items": [item], "async": False},
            base=FLEET_BASE,
        )
        if 200 <= status < 300:
            return True
        time.sleep(1)
    return False


def _recall(query: str, top_k: int = 5) -> list[dict]:
    status, resp = post(
        f"/v1/default/banks/{BANK}/memories/recall",
        {"query": query, "max_tokens": 1500},
        base=FLEET_BASE,
    )
    if status < 200 or status >= 300 or not isinstance(resp, dict):
        return []
    return (resp.get("results") or resp.get("memories") or [])[:top_k]


def _warm_bank() -> None:
    """Absorb the cold-bank first-write race with a throwaway write."""
    _ingest("bank warm-up atom — ignore.", "warmup", ["hybrid_val", "warmup"])
    time.sleep(1)


def _rank_of(token: str, results: list[dict]) -> int:
    """1-based rank of the first result containing token; 0 if absent."""
    for i, r in enumerate(results, start=1):
        text = (r.get("text") or r.get("content") or "").upper()
        if token.upper() in text:
            return i
    return 0


def main() -> int:
    print(f"=== stz8 hybrid-recall validation against {FLEET_BASE} (bank={BANK}) ===\n")

    _warm_bank()
    ing = {t["id"]: _ingest(t["content"], t["id"], ["hybrid_val", "target"]) for t in TARGETS}
    for i, d in enumerate(DISTRACTORS):
        _ingest(d, f"distractor-{i}", ["hybrid_val", "distractor"])
    print(f"[ingest] targets: {ing}")
    if not all(ing.values()):
        print("[ingest] ABORT — a target atom failed to ingest; cannot validate recall.")
        return 2
    print()

    # Small settle window; the probe showed no lag, retry guards consolidation jitter.
    time.sleep(2)

    lexical_pass = 0
    semantic_pass = 0

    print("--- LEXICAL LEG (BM25): recall by rare exact token ---")
    for t in TARGETS:
        results = _recall(t["token"])
        rank = _rank_of(t["token"], results)
        ok = rank == 1
        lexical_pass += ok
        verdict = "PASS rank=1" if ok else (f"PARTIAL rank={rank}" if rank else "FAIL absent")
        print(f"  [{t['kind']:<13}] query='{t['token']}' -> {verdict} (n={len(results)})")

    print("\n--- SEMANTIC LEG (vector): recall by paraphrase, no shared token ---")
    for t in TARGETS:
        results = _recall(t["semantic_query"])
        rank = _rank_of(t["token"], results)
        ok = rank > 0
        semantic_pass += ok
        verdict = f"PASS rank={rank}" if ok else "FAIL absent"
        print(
            f"  [{t['kind']:<13}] '{t['semantic_query'][:48]}...' -> {verdict} (n={len(results)})"
        )

    print("\n=== VERDICT ===")
    print(f"  lexical (BM25) leg:   {lexical_pass}/{len(TARGETS)} exact tokens surfaced at rank 1")
    print(
        f"  semantic (vector) leg: {semantic_pass}/{len(TARGETS)} paraphrases surfaced the target"
    )
    hybrid = lexical_pass == len(TARGETS) and semantic_pass >= 1
    print(f"  HYBRID CONFIRMED: {hybrid}")
    print(
        "  Interpretation: rare semantically-empty tokens surfacing at rank 1 can ONLY "
        "come from a lexical/BM25 index; paraphrase recall can only come from a vector "
        "index. Both on one endpoint == hybrid recall is live on the deployed instance."
    )
    return 0 if hybrid else 1


if __name__ == "__main__":
    sys.exit(main())
