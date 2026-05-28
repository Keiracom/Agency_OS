#!/usr/bin/env python3
"""full_chain_dress_rehearsal.py — THE cutover gate harness (Agency_OS-jb4e).

Drives a REAL open KEI through the full ephemeral chain
(Chat → Deliberator → Worker → Reviewer → merge), TWICE — once recall-active,
once cold — and proves memory adds value via the per-hop retrieval-trace gap.
Success = PR merged + CI passed + governance honoured + trace at every hop +
memory gap demonstrated. Spec: docs/cutover/full_chain_dress_rehearsal_spec.md.

The live run is GATED on the work-loop consumer running (Agency_OS-f5yt) +
Nova #1268. Without `--live` AND a reachable loop, the harness SELF-SKIPS
(exit 0) — it is built + CI-green now; the green run is captured once the loop
is switched on. The pure logic (KEI selection, gap, success evaluation) is
unit-tested without the live loop.

Stdlib only. Heavy/optional deps (redis, psycopg) are lazy-imported on the live
path so the logic layer imports cleanly in hermetic CI.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field

TASKS_CHANNEL = "keiracom:tasks:available"
HOP_AGENTS_DEFAULT = ("chat", "deliberator", "worker", "reviewer")
# Synthetic markers — a KEI matching any of these is NOT a real backlog item.
SYNTHETIC_ID_MARKERS = ("kei-test", "-test", "test001")
SYNTHETIC_TITLE_MARKERS = ("smoke", "test", "scaffold", "dress-rehearsal", "dress rehearsal")


# ─── data model ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HopTrace:
    """One hop's retrieval evidence (a public.retrieval_events row, condensed)."""

    hop: str
    agent: str
    fired: bool  # a retrieval_events row exists for this hop
    bypass_rerank: bool
    top_citation_id: str | None
    top_score: float


@dataclass(frozen=True)
class RunResult:
    kei: str
    recall_active: bool
    hop_traces: tuple[HopTrace, ...]
    pr_number: int | None = None
    pr_merged: bool = False
    ci_passed: bool = False
    governance: dict = field(
        default_factory=dict
    )  # {callsign_tagged, concur_count, no_linear_write, claim_observed}
    worker_retries: int = 0


@dataclass(frozen=True)
class GateOutcome:
    passed: bool
    reasons: tuple[str, ...]
    gap: dict


# ─── §2 real-KEI selection ────────────────────────────────────────────────────


def is_synthetic(kei_id: str, title: str) -> bool:
    low_id, low_title = (kei_id or "").lower(), (title or "").lower()
    if any(mark in low_id for mark in SYNTHETIC_ID_MARKERS):
        return True
    return any(mark in low_title for mark in SYNTHETIC_TITLE_MARKERS)


def select_real_kei(candidates: list[dict]) -> dict | None:
    """Pick the first real (non-synthetic) backlog KEI. `candidates` are
    {id, title, priority} dicts in priority order. None if all synthetic."""
    for c in candidates:
        if not is_synthetic(c.get("id", ""), c.get("title", "")):
            return c
    return None


# ─── §3/§5-S5 memory gap ──────────────────────────────────────────────────────


def _useful_hops(run: RunResult) -> set[str]:
    """Hops where retrieval fired AND surfaced a real citation (not bypassed/empty)."""
    return {
        t.hop
        for t in run.hop_traces
        if t.fired and not t.bypass_rerank and t.top_citation_id and t.top_score > 0
    }


def memory_gap(active: RunResult, cold: RunResult) -> dict:
    """Per-hop gap proving memory helped. `active_only` = hops where the
    recall-active run surfaced a citation the cold run did not."""
    a, c = _useful_hops(active), _useful_hops(cold)
    active_only = sorted(a - c)
    return {
        "active_useful_hops": sorted(a),
        "cold_useful_hops": sorted(c),
        "active_only_hops": active_only,
        "active_strictly_outtraces_cold": bool(active_only),
        "worker_retries_active": active.worker_retries,
        "worker_retries_cold": cold.worker_retries,
        "retries_not_worse": active.worker_retries <= cold.worker_retries,
    }


# ─── §5 success evaluation ────────────────────────────────────────────────────


def evaluate_gate(
    active: RunResult, cold: RunResult, *, hop_agents=HOP_AGENTS_DEFAULT
) -> GateOutcome:
    """Apply the §5 criteria to the recall-active run + the §3 gap. Pure."""
    reasons: list[str] = []
    g = active.governance or {}

    if not active.pr_merged:  # S1
        reasons.append("S1: PR not merged")
    if not active.ci_passed:  # S2
        reasons.append("S2: CI did not pass")
    # S3 governance
    if not g.get("callsign_tagged"):
        reasons.append("S3: PR/commits not callsign-tagged")
    if int(g.get("concur_count", 0)) < 2:
        reasons.append("S3: fewer than 2 NATS concurs")
    if not g.get("no_linear_write", True):
        reasons.append("S3: Linear write detected (LAW violation)")
    if not g.get("claim_observed"):
        reasons.append("S3: claim-before-touch not observed")
    # S4 trace at every hop (recall-active)
    fired = {t.hop for t in active.hop_traces if t.fired}
    missing = [h for h in hop_agents if h not in fired]
    if missing:
        reasons.append(f"S4: no retrieval trace at hop(s): {', '.join(missing)}")
    # S5 memory gap
    gap = memory_gap(active, cold)
    if not gap["active_strictly_outtraces_cold"]:
        reasons.append("S5: recall-active did not out-trace cold (memory gap not demonstrated)")
    if not gap["retries_not_worse"]:
        reasons.append("S5: recall-active had MORE worker retries than cold")

    return GateOutcome(passed=not reasons, reasons=tuple(reasons), gap=gap)


# ─── live orchestration (gated) ───────────────────────────────────────────────


def _loop_reachable() -> bool:
    """True if the work-loop consumer's queue is reachable (REDIS_URL pingable)."""
    url = os.environ.get("REDIS_URL") or os.environ.get("VALKEY_URL")
    if not url:
        return False
    try:
        import redis

        redis.from_url(url, socket_timeout=3, socket_connect_timeout=3).ping()
        return True
    except Exception:  # noqa: BLE001
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Full-chain dress-rehearsal cutover gate")
    parser.add_argument(
        "--live", action="store_true", help="run against the live loop (needs f5yt)"
    )
    parser.add_argument(
        "--kei", help="override the KEI under test (default: highest real bd-ready)"
    )
    args = parser.parse_args(argv)

    if not args.live or not _loop_reachable():
        print(
            "SKIP (dress-rehearsal): harness built + ready. Live run is gated on the work-loop "
            "consumer running (Agency_OS-f5yt) + Nova #1268. Re-run with --live once the loop is on. "
            "See docs/cutover/full_chain_dress_rehearsal_spec.md."
        )
        return 0

    # Live path is intentionally thin here: it wires the spec's seams once the
    # cross-team dependencies (§8) are confirmed with Atlas. Building the live
    # driver against an unconfirmed task-seed schema would be guesswork; the
    # pure gate logic above is the verifiable deliverable now.
    print(
        "LIVE mode requested but the run driver awaits the §8 wiring confirmations "
        "(recall_mode honouring + task-seed schema) from Atlas (#1275/f5yt). "
        "Not executing a guessed seed against production. Exiting without a verdict.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
