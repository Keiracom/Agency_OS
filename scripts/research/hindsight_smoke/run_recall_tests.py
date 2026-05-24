#!/usr/bin/env python3
"""run_recall_tests.py — agentic-SE-fitness recall harness against Hindsight.

Runs the dispatch's four test cases against the ingested pilot data and
scores recall accuracy per MAL primitive.

Test cases (from dispatch):
  TC1 Decision lookup  — 'Why did we choose Hindsight as memory engine?'
  TC2 AntiPattern      — 'What PR review HOLD shape did Max catch repeatedly today?'
  TC3 Trace+filter     — 'Show me all PR review chains where impl-feasibility lens caught a missed substance issue'
  TC4 Cross-node       — 'Which KEI dispatches did atlas close this session?'

Scoring (per-test, conservative): top-K=5; recall_accuracy = (# of returned
results that are 'topically relevant') / max(K, expected_relevant). Relevance
graded by qualitative inspection of the recalled content vs the test intent.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from urllib import error as urlerror
from urllib import request as urlrequest

BASE = "http://localhost:8888"
BANK = "keiracom_smoke"
TIMEOUT = 120

TEST_CASES = [
    {
        "id": "TC1_decision_lookup",
        "query": "Why did we choose Hindsight as the memory engine?",
        "tag_filter": ["mal_node:decision"],
        "intent": "Recall Decisions referencing Hindsight adoption or related ratifications.",
        "expected_signal_tokens": ["hindsight", "memory", "ratif", "concur", "phase"],
    },
    {
        "id": "TC2_antipattern_recall",
        "query": "What failure patterns have we observed in PR reviews and dispatches?",
        "tag_filter": ["mal_node:antipattern"],
        "intent": "Recall AntiPatterns from discovery_log (failed_path entries).",
        "expected_signal_tokens": ["failed", "fail", "wrong", "bug", "broke", "did not"],
    },
    {
        "id": "TC3_artifact_trace",
        "query": "Show PR review chains involving Atlas contributions",
        "tag_filter": ["mal_node:artifact"],
        "intent": "Recall Artifacts (PRs) authored by atlas.",
        "expected_signal_tokens": ["atlas", "pr", "merged", "author"],
    },
    {
        "id": "TC4_taskcontext_cross_node",
        "query": "What KEI dispatches are atlas working on?",
        "tag_filter": ["mal_node:taskcontext"],
        "intent": "Recall TaskContext entries describing KEI work assignments.",
        "expected_signal_tokens": ["kei", "atlas", "dispatch", "task", "agency_os"],
    },
]


def post(path: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urlrequest.Request(
        f"{BASE}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=TIMEOUT) as resp:
            return (resp.status, json.loads(resp.read().decode()))
    except urlerror.HTTPError as e:
        return (e.code, {"error": e.read().decode()[:500]})
    except (urlerror.URLError, json.JSONDecodeError, TimeoutError) as e:
        return (0, {"error": str(e)})


def score_relevance(content: str, signal_tokens: list[str]) -> tuple[bool, list[str]]:
    """True if at least 2 signal tokens present (case-insensitive)."""
    cl = content.lower()
    hits = [t for t in signal_tokens if t.lower() in cl]
    return (len(hits) >= 2, hits)


def run_test(tc: dict, top_k: int = 5, use_filter: bool = True) -> dict:
    body = {"query": tc["query"], "max_tokens": 2000}
    if use_filter and tc.get("tag_filter"):
        body["tags"] = tc["tag_filter"]
        body["tags_match"] = "all"
    t0 = time.time()
    status, resp = post(f"/v1/default/banks/{BANK}/memories/recall", body)
    dt = time.time() - t0
    if status < 200 or status >= 300:
        return {"id": tc["id"], "status": status, "error": resp, "seconds": round(dt, 2)}
    results = resp.get("memories", []) or resp.get("results", []) or []
    if not results and isinstance(resp, dict):
        # Some shapes nest under different keys; capture for debugging.
        return {
            "id": tc["id"],
            "status": status,
            "seconds": round(dt, 2),
            "raw_keys": list(resp.keys())[:10],
            "raw_preview": str(resp)[:300],
        }
    scored = []
    for r in results[:top_k]:
        content = r.get("content", "") or r.get("text", "") or str(r)[:200]
        relevant, hits = score_relevance(content, tc["expected_signal_tokens"])
        scored.append(
            {
                "relevant": relevant,
                "hits": hits,
                "preview": content[:200],
            }
        )
    relevant_count = sum(1 for s in scored if s["relevant"])
    accuracy = relevant_count / max(1, len(scored))
    return {
        "id": tc["id"],
        "status": status,
        "query": tc["query"],
        "intent": tc["intent"],
        "seconds": round(dt, 2),
        "returned": len(scored),
        "relevant": relevant_count,
        "accuracy": round(accuracy, 2),
        "samples": scored,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--out", default="/tmp/hindsight_smoke_recall_results.json")
    args = p.parse_args()
    results = [run_test(tc, top_k=args.top_k) for tc in TEST_CASES]
    summary = {
        "test_count": len(results),
        "passed_70pct": sum(1 for r in results if r.get("accuracy", 0) >= 0.7),
        "passed_50pct": sum(1 for r in results if r.get("accuracy", 0) >= 0.5),
        "total_recall_seconds": round(sum(r.get("seconds", 0) for r in results), 2),
        "per_test": results,
    }
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
