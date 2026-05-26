#!/usr/bin/env python3
"""ceo_memory_carving_classifier.py — Phase A5 piece 1a classification rule.

Implements the policy-vs-memory carving rule that determines which
`public.ceo_memory` rows get backfilled into Hindsight (as Dave-tenant
memory) versus which stay in Supabase as canonical policy SSOT.

Path (C) per Elliot dispatch 2026-05-26: dual-store honours BOTH
`ceo:boundary_matrix_v1` (policy → Supabase) AND
`ceo:dave_decisions_2026_05_26` decision_1 (backfill → Hindsight) by
carving on the policy-vs-memory test: would this content read the same
way for ANY tenant? Yes = POLICY (skip backfill). No (tenant-specific
to Dave) = MEMORY (backfill via DecisionWrapper under Dave's fleet
tenant_id).

This module is the RULE only. The HTTP executor that consumes its
classification + POSTs to Hindsight is Phase A5 piece 1b (separate PR
per feedback_split_orthogonal_scope).

bd: Agency_OS-oq3c
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter
from typing import Any

logger = logging.getLogger("ceo_memory_carving_classifier")

POLICY = "POLICY"
MEMORY = "MEMORY"

# Meta-rule key prefixes — these are governance content that would read the
# same way for any tenant per the policy-vs-memory test. STAY in Supabase
# ceo_memory; do NOT backfill to Hindsight.
POLICY_PREFIXES: tuple[str, ...] = (
    "ceo:boundary_matrix",
    "ceo:memory_abstraction",
    "ceo:comm_architecture",
    "ceo:agency_os_keiracom_separation",
    "ceo:rule:",
    "ceo:law",
    "ceo:governance",
    "ceo:cognee_retirement_posture",
    "ceo:cognee_retirement_execution",
    "ceo:atomization_architecture",
    "ceo:keiracom_build_priority",
    "ceo:memory_cutover_unblock",
    "ceo:dave_migration_sequence",
)

# Explicitly tenant-specific key prefixes — Dave-as-tenant memory candidates.
MEMORY_PREFIXES: tuple[str, ...] = (
    "ceo:dave_",
    "ceo:byok_",
    "ceo:session_end_",
)


def classify_row(key: str, value: Any | None = None) -> str:  # noqa: ARG001
    """Return POLICY or MEMORY for one ceo_memory row.

    Conservative default for unknown `ceo:*` keys is POLICY — stays in
    Supabase. Operator can override via a manual carve list downstream
    (piece 1b consumes the classification but doesn't strictly enforce
    it as a final-say).

    `value` is currently unused but retained in the signature so future
    rules can inspect row content (e.g. "any row whose value names a
    tenant_id is MEMORY"). Don't break the callable signature.
    """
    if not key.startswith("ceo:"):
        return MEMORY
    if any(key.startswith(p) for p in POLICY_PREFIXES):
        return POLICY
    if any(key.startswith(p) for p in MEMORY_PREFIXES):
        return MEMORY
    if key.startswith("ceo:directive_") and key.endswith("_complete"):
        return MEMORY
    return POLICY


def classify_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply classify_row to each row + return rows annotated with `_carve`."""
    out = []
    for row in rows:
        key = row.get("key", "")
        value = row.get("value")
        carve = classify_row(key, value)
        out.append({**row, "_carve": carve})
    return out


def report(rows: list[dict[str, Any]], *, sample_size: int = 5) -> dict[str, Any]:
    """Build a classification report for operator review.

    Includes counts by carve + sample keys per carve so the operator can
    eyeball the partition before piece 1b ships any data to Hindsight.
    """
    counter: Counter[str] = Counter()
    samples_by_carve: dict[str, list[str]] = {POLICY: [], MEMORY: []}
    for row in rows:
        carve = row.get("_carve", POLICY)
        counter[carve] += 1
        if len(samples_by_carve.get(carve, [])) < sample_size:
            samples_by_carve.setdefault(carve, []).append(row.get("key", ""))
    return {
        "totals": dict(counter),
        "samples_by_carve": samples_by_carve,
        "memory_count": counter.get(MEMORY, 0),
        "policy_count": counter.get(POLICY, 0),
    }


def load_rows_from_jsonl(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def write_rows_to_jsonl(rows: list[dict[str, Any]], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, default=str) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input",
        required=True,
        help="JSONL path with ceo_memory rows (one row per line, fields: key, value, ...)",
    )
    p.add_argument(
        "--export-classifications",
        help="JSONL output path; writes each row annotated with `_carve` for piece 1b consumption",
    )
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    rows = load_rows_from_jsonl(args.input)
    classified = classify_rows(rows)
    rep = report(classified)
    print(json.dumps(rep, indent=2))
    if args.export_classifications:
        write_rows_to_jsonl(classified, args.export_classifications)
        logger.info("wrote %d classified rows → %s", len(classified), args.export_classifications)
    return 0


if __name__ == "__main__":
    sys.exit(main())
