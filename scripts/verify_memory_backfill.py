#!/usr/bin/env python3
"""verify_memory_backfill.py — Agency_OS-jolj — verify-before-retire gate.

Viktor's spec: before retiring the old memory store (ceo_memory), confirm the
ceo_memory → Hindsight fleet_decisions backfill (Agency_OS-c66k / PR #1321)
was lossless. Two checks:

1. COVERAGE — count atomized ceo_memory sources in the backfill ledger
   (`keiracom_atomizer_jobs` rows with `source_ref LIKE 'ceo_memory:%'` AND
   `status = 'atomizer_done'`) must be at least ``PASS_THRESHOLD`` × the
   atomisable ceo_memory rows the backfill is *expected* to cover. Expected
   set is enumerated by exactly the iterators the backfill itself uses
   (`decision_sources.iter_ceo_memory_{directives,decisions,completions,
   deliberations}`), so the expected count is by-construction what the
   backfill would produce on a fresh prod run.

2. SPOT-CHECK — each of ``SPOT_CHECK_KEYS`` (5 canonical ceo: keys) must have
   a corresponding atomizer_done row in the ledger.

If both checks pass: print ``MEMORY_VERIFY_PASS`` (exit 0). Otherwise print
``MEMORY_VERIFY_FAIL`` + a missing-list (exit 1).

Why the ledger is a valid proxy for the bank: `decisions_backfill.run_direct`
calls the canonical `hindsight_writer.atom_to_hindsight_item` +
`default_hindsight_ingest` seam, then `make_db_ledger.record(...)`. The ingest
and the ledger write happen in the same iteration; a successful `atomizer_done`
row means the matching atom was ingested into Hindsight fleet_decisions via the
shared converter the live exit-cycle writer uses (Orion's d0kh format gate).
The ledger and the bank are by-construction in sync. A bank-side content audit
would need the Hindsight read API which is not trivially exposed for arbitrary
counts (probed at c66k time: GET memories=405, POST search=404); the
ledger-based check is the cheapest correct verification.

Usage:
    python3 scripts/verify_memory_backfill.py
        # Requires DATABASE_URL / SUPABASE_DB_URL env (Supabase prod DSN).
        # Read-only — no writes anywhere.

Output (PASS example):
    COVERAGE: ceo_memory atomisable sources expected=N, ledger atomized=M,
              coverage=PP.PP% (threshold ≥95%) — OK
    SPOT-CHECK: 5/5 keys present in ledger:
      ✓ ceo:v1_chain_architecture
      ✓ ceo:atomization_architecture_v1
      ...
    MEMORY_VERIFY_PASS
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Coverage threshold — Viktor's ratified "≥95% counts as lossless" for the
# verify-before-retire gate. Some sources may legitimately drop (transient
# ingest failure, schema-invalid content guarded by the builder). 95% leaves
# headroom for that without admitting silent loss.
PASS_THRESHOLD = 0.95

# Five canonical ceo: keys that are MUST-have in fleet_decisions after the
# backfill — picked because they're the high-signal architectural decisions
# the V1 chain agents need to recall at spawn.
SPOT_CHECK_KEYS: tuple[str, ...] = (
    "ceo:v1_chain_architecture",
    "ceo:atomization_architecture_v1",
    "ceo:session_2026-05-28_architecture_decisions",
    "ceo:two_store_architecture_v1",
    "ceo:ephemeral_capture_model_v1",
)


def _dsn() -> str:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not raw:
        raise SystemExit(
            "verify_memory_backfill: DATABASE_URL or SUPABASE_DB_URL must be set"
        )
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def _print_missing_summary(missing: list[str], spot_failures: list[str]) -> None:
    print(f"  missing {len(missing)} ceo_memory sources from ledger:")
    for r in missing[:10]:
        print(f"    - {r}")
    if len(missing) > 10:
        print(f"    ... and {len(missing) - 10} more")
    if spot_failures:
        print("  spot-check failures (key → expected source_ref):")
        for k in spot_failures:
            print(f"    - {k} → ceo_memory:{k}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--threshold",
        type=float,
        default=PASS_THRESHOLD,
        help=f"coverage ratio required to pass (default {PASS_THRESHOLD})",
    )
    args = parser.parse_args()

    # Lazy import so the script can be imported (e.g. for tests) without
    # needing psycopg + the atomization package present in every env.
    import psycopg  # noqa: PLC0415

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.keiracom_system.atomization.decision_sources import (  # noqa: PLC0415
        iter_ceo_memory_completions,
        iter_ceo_memory_decisions,
        iter_ceo_memory_deliberations,
        iter_ceo_memory_directives,
    )

    conn = psycopg.connect(_dsn(), autocommit=True, prepare_threshold=None)
    try:
        cur = conn.cursor()

        # (1) Expected set: every ceo_memory row the backfill iterators would
        # produce a source for, right now, on this DB. Same iterators as
        # decisions_backfill — by-construction in sync.
        expected_refs: set[str] = set()
        for iter_fn in (
            iter_ceo_memory_directives,
            iter_ceo_memory_decisions,
            iter_ceo_memory_completions,
            iter_ceo_memory_deliberations,
        ):
            expected_refs.update(s.source_ref for s in iter_fn(cur))
        expected_n = len(expected_refs)

        # (2) Ledger set: every source_ref the backfill has marked done.
        cur.execute(
            "SELECT source_ref FROM public.keiracom_atomizer_jobs "
            "WHERE status = 'atomizer_done' AND source_ref LIKE 'ceo_memory:%%'"
        )
        ledger_refs: set[str] = {row[0] for row in cur.fetchall()}
        covered = ledger_refs & expected_refs
        actual_n = len(covered)
        coverage = (actual_n / expected_n) if expected_n else 0.0
        coverage_ok = coverage >= args.threshold

        # (3) Spot-check
        spot_results = {
            key: (f"ceo_memory:{key}" in ledger_refs) for key in SPOT_CHECK_KEYS
        }
        spot_ok = all(spot_results.values())

        # Report
        print(
            f"COVERAGE: ceo_memory atomisable sources expected={expected_n}, "
            f"ledger atomized={actual_n}, coverage={coverage:.2%} "
            f"(threshold ≥{args.threshold:.0%}) — "
            f"{'OK' if coverage_ok else 'FAIL'}"
        )
        print(
            f"SPOT-CHECK: {sum(spot_results.values())}/{len(SPOT_CHECK_KEYS)} "
            "keys present in ledger:"
        )
        for key, present in spot_results.items():
            print(f"  {'✓' if present else '✗'} {key}")

        if coverage_ok and spot_ok:
            print("\nMEMORY_VERIFY_PASS")
            return 0

        print("\nMEMORY_VERIFY_FAIL")
        missing = sorted(expected_refs - ledger_refs)
        spot_failures = [k for k, ok in spot_results.items() if not ok]
        _print_missing_summary(missing, spot_failures)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
