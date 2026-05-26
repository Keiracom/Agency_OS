#!/usr/bin/env python3
"""a5_smoke_recall.py — Phase A5 piece 5 smoke recall validation.

Exercises Hindsight recall under Dave's fleet tenant_id against known
historical anchor items per A5 backfill source. Validates that each of
pieces 1b / 2 / 3 / 4 actually landed retrievable content (not just
silently no-op'd).

Runs AFTER operator has run pieces 1b/2/3/4 with `--execute`. If pieces
have not been operator-executed yet, this harness will surface zero
recalls — that's the correct failure mode (empirical-state probe per the
five-store completion rule).

Probes — one per source (piece). Each probe:
1. Calls the wrapper's `.recall(tenant_id=FLEET_TENANT_ID, query=..., top_k=5)`
2. Scores each returned memory against `expected_signal_tokens`
3. Probe passes if ≥1 returned memory contains ≥2 signal tokens (Scout's
   `run_recall_tests.py` conservative-relevance heuristic)

Final verdict: rc=0 if all 4 probes pass; rc=1 if any fail.

bd: Agency_OS-c23f
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("a5_smoke_recall")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from keiracom_system.fleet.hindsight.smoke_wrappers import (  # noqa: E402
    FLEET_TENANT_ID,
    FleetHindsightClient,
    FleetTenantExtension,
)
from src.keiracom_system.memory.wrappers import (  # noqa: E402
    DecisionWrapper,
    TaskContextWrapper,
)

DEFAULT_TOP_K = 5
RELEVANCE_TOKEN_THRESHOLD = 2  # per-memory: ≥N signal-tokens to count as relevant


@dataclass(frozen=True)
class Probe:
    name: str
    wrapper_name: str
    query: str
    expected_signal_tokens: tuple[str, ...]


# Probes — one per A5 backfill source. Tokens chosen to be present in the
# typical ingested content per piece. Conservative-relevance heuristic
# (≥2 tokens per memory) gives some slack for paraphrase / formatting drift.
DEFAULT_PROBES: tuple[Probe, ...] = (
    Probe(
        name="piece_1b_ceo_memory",
        wrapper_name="decision",
        query="Dave A5 backfill decision policy memory test",
        expected_signal_tokens=("a5", "backfill", "dave", "hindsight", "memory"),
    ),
    Probe(
        name="piece_2_weaviate_snapshot",
        wrapper_name="decision",
        query="Phase A3 reader cutover orchestrator Atlas",
        expected_signal_tokens=("a3", "cutover", "atlas", "phase", "weaviate"),
    ),
    Probe(
        name="piece_3_drive_manual",
        wrapper_name="decision",
        query="boundary matrix Section 13 directive ratified",
        expected_signal_tokens=("boundary", "matrix", "section", "directive", "ratified"),
    ),
    Probe(
        name="piece_4_slack_ceo",
        wrapper_name="taskcontext",
        query="Dave A5 piece backfill ceo directive",
        expected_signal_tokens=("a5", "piece", "backfill", "dave", "ceo"),
    ),
)

WRAPPER_BUILDERS = {
    "decision": lambda c, t: DecisionWrapper(c, t),
    "taskcontext": lambda c, t: TaskContextWrapper(c, t),
}


def score_memory_relevance(
    memory: dict[str, Any], tokens: tuple[str, ...]
) -> tuple[bool, list[str]]:
    """Lowercase substring match; returns (is_relevant, matched_tokens)."""
    content = (memory.get("content") or memory.get("text") or "").lower()
    matched = [t for t in tokens if t.lower() in content]
    return (len(matched) >= RELEVANCE_TOKEN_THRESHOLD, matched)


def execute_probe(
    probe: Probe,
    *,
    wrappers: dict[str, Any],
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, Any]:
    """Run one probe; returns a dict with pass/fail + per-memory details."""
    wrapper = wrappers[probe.wrapper_name]
    try:
        memories = wrapper.recall(tenant_id=FLEET_TENANT_ID, query=probe.query, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        return {
            "name": probe.name,
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
            "memories_returned": 0,
            "relevant_memories": 0,
        }
    if not isinstance(memories, list):
        return {
            "name": probe.name,
            "passed": False,
            "error": f"recall returned non-list: {type(memories).__name__}",
            "memories_returned": 0,
            "relevant_memories": 0,
        }
    per_memory = []
    relevant_count = 0
    for mem in memories:
        is_rel, matched = score_memory_relevance(mem, probe.expected_signal_tokens)
        per_memory.append({"matched_tokens": matched, "relevant": is_rel})
        if is_rel:
            relevant_count += 1
    return {
        "name": probe.name,
        "wrapper": probe.wrapper_name,
        "query": probe.query,
        "passed": relevant_count >= 1,
        "memories_returned": len(memories),
        "relevant_memories": relevant_count,
        "per_memory": per_memory,
    }


def build_wrappers(*, client_factory=None, tenant_factory=None) -> dict[str, Any]:
    client = (client_factory or FleetHindsightClient)()
    tenants = (tenant_factory or FleetTenantExtension)()
    return {name: builder(client, tenants) for name, builder in WRAPPER_BUILDERS.items()}


def run(
    *,
    probes: tuple[Probe, ...] = DEFAULT_PROBES,
    wrappers: dict[str, Any] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> tuple[int, list[dict[str, Any]]]:
    wrapper_map = wrappers if wrappers is not None else build_wrappers()
    results: list[dict[str, Any]] = []
    for probe in probes:
        result = execute_probe(probe, wrappers=wrapper_map, top_k=top_k)
        results.append(result)
        marker = "PASS" if result.get("passed") else "FAIL"
        logger.info(
            "[%s] %s — memories=%d relevant=%d",
            marker,
            result["name"],
            result.get("memories_returned", 0),
            result.get("relevant_memories", 0),
        )
    rc = 0 if all(r.get("passed") for r in results) else 1
    logger.info(
        "a5_smoke_recall summary: passed=%d/%d rc=%d",
        sum(1 for r in results if r.get("passed")),
        len(results),
        rc,
    )
    return rc, results


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("runtime/a5_smoke_recall_results.json"),
        help="path to write structured results JSON",
    )
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    rc, results = run(top_k=args.top_k)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    logger.info("results written → %s", args.out)
    return rc


if __name__ == "__main__":
    sys.exit(main())
