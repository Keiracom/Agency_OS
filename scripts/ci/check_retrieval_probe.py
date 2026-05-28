#!/usr/bin/env python3
"""check_retrieval_probe.py — Wave 6 continuous adversarial retrieval gate.

Runs the adversarial probe battery (defined once in
`tests/retrieval/test_adversarial_probe.py`) against a LIVE Hindsight and
reports a precision score. Per GOV-12 ("Gates As Code, Not Comments") this is
the runtime executable conditional; the blocking/non-blocking decision is a
single env-var toggle, not a comment.

GATE POLICY:
  * No live Hindsight (`HINDSIGHT_URL` unset)  -> SKIP, exit 0. This is the
    hermetic-CI default (GitHub runners have no memory layer); the probe is
    meaningful only where a live instance is reachable.
  * Live + precision >= threshold              -> PASS, exit 0.
  * Live + precision <  threshold:
      - RETRIEVAL_PROBE_BLOCKING unset/false   -> WARN, exit 0 (initial state).
      - RETRIEVAL_PROBE_BLOCKING truthy         -> FAIL, exit 1 (at cutover).
  * Setup/import error:
      - non-blocking -> WARN, exit 0 (never break CI before cutover).
      - blocking     -> FAIL, exit 1.

Env-var reconciliation: the orchestrator reads `HINDSIGHT_BASE`; this gate's
opt-in signal is `HINDSIGHT_URL` per the Wave 6 dispatch. When set, the URL is
pushed onto `orchestrator.HINDSIGHT_BASE` so recall hits the operator's
instance and the two names cannot drift.

USAGE:
    python3 scripts/ci/check_retrieval_probe.py
    python3 scripts/ci/check_retrieval_probe.py --report
    RETRIEVAL_PROBE_BLOCKING=1 python3 scripts/ci/check_retrieval_probe.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HINDSIGHT_URL_ENV = "HINDSIGHT_URL"
BLOCKING_ENV = "RETRIEVAL_PROBE_BLOCKING"
_TRUTHY = {"1", "true", "yes", "on"}


def _blocking() -> bool:
    return os.environ.get(BLOCKING_ENV, "").strip().lower() in _TRUTHY


def _exit(code: int, *, blocking: bool) -> int:
    """In non-blocking mode a would-be failure (code 1) downgrades to 0 (warn)."""
    if code != 0 and not blocking:
        return 0
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wave 6 adversarial retrieval probe gate")
    parser.add_argument("--report", action="store_true", help="print per-probe PASS/FAIL lines")
    args = parser.parse_args(argv)
    blocking = _blocking()

    base = os.environ.get(HINDSIGHT_URL_ENV)
    if not base:
        print(
            f"SKIP (retrieval-probe): {HINDSIGHT_URL_ENV} unset — no live Hindsight to probe. "
            "Gate is inert in hermetic CI; set HINDSIGHT_URL to run against a live instance."
        )
        return 0

    # Heavy imports happen only on the live path so the skip case stays cheap.
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from src.retrieval import orchestrator
        from tests.retrieval.test_adversarial_probe import (
            PRECISION_THRESHOLD,
            evaluate_all,
            precision,
            real_query,
        )

        orchestrator.HINDSIGHT_BASE = base
        results = evaluate_all(real_query)
    except Exception as exc:  # noqa: BLE001 — setup failure policy depends on blocking mode
        verdict = "FAIL" if blocking else "WARN"
        print(f"{verdict} (retrieval-probe): probe setup error: {exc!r}", file=sys.stderr)
        return _exit(1, blocking=blocking)

    score = precision(results)
    passed = sum(1 for r in results if r.passed)
    if args.report:
        for r in results:
            mark = "PASS" if r.passed else "FAIL"
            detail = "" if r.passed else f" — {'; '.join(r.reasons)} [top={r.top_source_id!r}]"
            print(f"  {mark} [{r.category}] {r.name}{detail}")

    summary = (
        f"precision {score:.0%} ({passed}/{len(results)} probes) "
        f"vs threshold {PRECISION_THRESHOLD:.0%}"
    )
    if score >= PRECISION_THRESHOLD:
        print(f"OK (retrieval-probe): {summary}")
        return 0

    verdict = "FAIL" if blocking else "WARN"
    mode = "blocking" if blocking else "non-blocking (warn-only until cutover)"
    print(f"{verdict} (retrieval-probe): {summary} — {mode}", file=sys.stderr)
    return _exit(1, blocking=blocking)


if __name__ == "__main__":
    sys.exit(main())
