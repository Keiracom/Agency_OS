#!/usr/bin/env python3
"""full_chain_dress_rehearsal.py — THE cutover gate harness (Agency_OS-jb4e).

Drives a REAL (low-stakes-first) open KEI through the full ephemeral chain
(Chat → Deliberator → Worker → Reviewer → merge) across 4 runs — cold / recall /
crash / dead_letter — proving memory adds value via the per-hop retrieval-trace
gap and that the loop is resilient. Spec: docs/cutover/full_chain_dress_rehearsal_spec.md.

v2.0 (Dave/Viktor 2026-05-29): the harness is the WITNESS, not the judge — it
streams its log LIVE to #ceo (state transitions, retrieval trace, cost, failures)
and produces P1-P11 evidence; **Dave's pass/fail table is the sign-off**. Cost:
per-loop is a FLOOR; the binding number is the 48-72h soak run-rate vs A$350.

The live run is GATED on the work-loop consumer running (Agency_OS-f5yt), the
dispatcher container-defaults fix (g9xx), and Nova #1268. The Slack-origin leg is
the direct Slack→task creator (Agency_OS-evbn, #1291): a `TASK:` #ceo message →
public.tasks row → kei45 trigger → loop; Run-A Step-1 is verified by
`verify_task_row_created`. Without `--live` AND a reachable loop, the harness
SELF-SKIPS (exit 0) — it is built + CI-green now. The pure logic (KEI selection,
gap, cost/soak, P1-P11 evidence) is unit-tested without the live loop.

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
# Note: bare "test" is NOT a title marker — a real "add tests for X" KEI is a
# valid low-stakes gate subject. Fixtures are caught by id (test001/kei-test) or
# the placeholder title phrases below.
SYNTHETIC_ID_MARKERS = ("kei-test", "-test", "test001")
SYNTHETIC_TITLE_MARKERS = ("smoke", "scaffold", "dress-rehearsal", "dress rehearsal", "bd claim")

# Low-stakes markers — the FIRST rehearsal run must pick a real KEI whose scope is
# safe to auto-merge (docs / trivial). Elliot 2026-05-29.
LOW_STAKES_TITLE_MARKERS = (
    "docs",
    "documentation",
    "doc:",
    "readme",
    "typo",
    "comment",
    "rename",
    "trivial",
    "cleanup",
    "lint",
    "format",
    "spelling",
)
LOW_STAKES_PRIORITIES = ("p3", "p4")

# Synthetic fallback — used ONLY when no low-stakes real KEI is ready.
REHEARSAL_FALLBACK = {"id": "rehearsal-1", "title": "rehearsal task", "synthetic_fallback": True}

# Recall toggle (Atlas grounding 2026-05-29): NOT a per-task flag. The recall arm
# sets DISPATCHER_SPAWN_RECALL_ENABLED=true and restarts the dispatcher; the cold
# arm unsets it and restarts. Restart-between-arms is acceptable.
RECALL_ENABLED_ENV = "DISPATCHER_SPAWN_RECALL_ENABLED"

# Failure taxonomy — what the harness must detect + report at each stage (never a
# silent hang). spawn_rejected covers TODAY's 400 (missing container image/name/
# port; Atlas is shipping the dispatcher container-defaults fix — the real-spawn
# arm runs after that lands).
FAILURE_MODES = (
    "spawn_rejected",  # /dispatcher/spawn non-2xx (400 = container defaults missing)
    "no_trace",  # a hop fired no retrieval_events row
    "no_recall_atom",  # recall arm surfaced 0 relevant atoms
    "pr_not_opened",  # chain produced no PR
    "ci_failed",  # PR CI not green
    "not_merged",  # PR not merged
    "governance_violation",  # callsign / concur / claim / linear
    "no_memory_gap",  # recall arm did not out-trace cold
    "crash_unrecovered",  # crash run did not recover
    "not_dead_lettered",  # dead-letter run did not route the failed task to the DLQ
)

# v2.0 (Dave/Viktor 2026-05-29): the gate is 4 runs, not 2.
RUN_MODES = ("cold", "recall", "crash", "dead_letter")
# Cost: per-loop is a FLOOR; the BINDING number is the 48-72h soak run-rate vs target.
SOAK_TARGET_AUD = 350.0
# WITNESS: the rehearsal streams its log LIVE to #ceo so Dave watches it happen.
# Dave's pass/fail table is the sign-off — the harness is the witness, not the judge.
CEO_WITNESS_CHANNEL = os.environ.get("CEO_WITNESS_CHANNEL", "C0B2PM3TV0B")
SLACK_POST_URL = "https://slack.com/api/chat.postMessage"  # NOSONAR S5332


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
    run_mode: str = "recall"  # one of RUN_MODES
    pr_number: int | None = None
    pr_merged: bool = False
    ci_passed: bool = False
    governance: dict = field(
        default_factory=dict
    )  # {callsign_tagged, concur_count, no_linear_write, claim_observed}
    worker_retries: int = 0
    cost_aud: float = 0.0  # per-loop cost FLOOR for this run
    recovered: bool = True  # crash run: did the chain recover?
    dead_lettered: bool = False  # dead-letter run: was the failed task routed to the DLQ?


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


def is_low_stakes(kei_id: str, title: str, priority: str | None = None) -> bool:  # noqa: ARG001
    """A real KEI whose scope is safe to auto-merge on the first rehearsal run —
    docs/trivial by title, or low priority (P3/P4)."""
    low_title = (title or "").lower()
    if any(mark in low_title for mark in LOW_STAKES_TITLE_MARKERS):
        return True
    return str(priority or "").lower() in LOW_STAKES_PRIORITIES


def select_gate_kei(candidates: list[dict]) -> dict:
    """FIRST-run gate subject (Elliot 2026-05-29): prefer a LOW-STAKES real KEI
    (docs/trivial scope) so the real PR + auto-merge is safe. Fall back to the
    synthetic rehearsal task ONLY if no low-stakes real KEI is ready — never
    auto-merge a high-stakes real PR on the first run."""
    real = [c for c in candidates if not is_synthetic(c.get("id", ""), c.get("title", ""))]
    for c in real:
        if is_low_stakes(c.get("id", ""), c.get("title", ""), c.get("priority")):
            return c
    return dict(REHEARSAL_FALLBACK)


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
    # S5 memory gap + the explicit recall-atom assert
    gap = memory_gap(active, cold)
    atom_ok, atom_n = assert_recall_returned_atom(active)
    gap["recall_atoms_active"] = atom_n
    if not atom_ok:
        reasons.append("S5: recall-active returned 0 relevant atoms (assert recall>=1 failed)")
    if not gap["active_strictly_outtraces_cold"]:
        reasons.append("S5: recall-active did not out-trace cold (memory gap not demonstrated)")
    if not gap["retries_not_worse"]:
        reasons.append("S5: recall-active had MORE worker retries than cold")

    return GateOutcome(passed=not reasons, reasons=tuple(reasons), gap=gap)


# ─── §7 seed + asserts + failure classification (Atlas-grounded) ──────────────


def build_seed_sql() -> str:
    """Parameterised INSERT for one task row — values are bound separately, never
    interpolated (injection-safe). The public.tasks AFTER-INSERT trigger (#1275)
    publishes to keiracom:tasks:available, which the work-loop consumer drains."""
    return "INSERT INTO public.tasks (id, title, status) VALUES (%s, %s, 'available')"


def seed_task(task_id: str, title: str, *, dsn: str | None = None) -> str:
    """Seed the task row that drives one arm. Both arms reuse the same task id
    (reset between). Live-only (needs DATABASE_URL); returns the task id."""
    dsn = dsn or os.environ.get("DATABASE_URL") or os.environ.get("RETRIEVAL_EVENTS_DSN")
    if not dsn:
        raise RuntimeError("no DATABASE_URL/RETRIEVAL_EVENTS_DSN — cannot seed task")
    import psycopg

    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    with (
        psycopg.connect(dsn, prepare_threshold=None, autocommit=True) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(build_seed_sql(), (task_id, title))
    return task_id


def assert_recall_returned_atom(run: RunResult) -> tuple[bool, int]:
    """THE memory assert (Elliot 2026-05-29): the recall-active arm must surface
    >=1 relevant atom — a hop where recall fired, was not bypassed, and returned a
    scored citation. Returns (passed, count)."""
    n = len(_useful_hops(run))
    return (n >= 1, n)


def task_row_present(task_ids: list[str], expected_id: str) -> bool:
    """Pure check: did the expected task id appear among the polled rows?"""
    return expected_id in (task_ids or [])


def verify_task_row_created(
    task_id: str, *, dsn: str | None = None, timeout_s: float = 10.0
) -> bool:
    """Run-A Step-1 (Slack-origin leg, Agency_OS-evbn): after Dave types a `TASK:`
    #ceo message, assert the row landed in public.tasks within `timeout_s` (~10s).
    The direct Slack→task creator does the INSERT; this just witnesses it. Returns
    False on timeout / no DSN (the rehearsal reports it; never raises)."""
    dsn = dsn or os.environ.get("DATABASE_URL") or os.environ.get("RETRIEVAL_EVENTS_DSN")
    if not dsn:
        return False
    import time as _t

    import psycopg

    clean = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    deadline = _t.monotonic() + timeout_s
    while _t.monotonic() < deadline:
        try:
            with (
                psycopg.connect(clean, prepare_threshold=None, autocommit=True) as conn,
                conn.cursor() as cur,
            ):
                cur.execute("SELECT id FROM public.tasks WHERE id = %s", (task_id,))
                if task_row_present([r[0] for r in cur.fetchall()], task_id):
                    return True
        except Exception:  # noqa: BLE001 — witness poll never raises
            pass
        _t.sleep(1.0)
    return False


def classify_spawn_failure(status_code: int, body: str = "") -> str | None:  # noqa: ARG001
    """Map a /dispatcher/spawn response to a FAILURE_MODES entry; None on success.
    A 400 today = missing container image/name/port (Atlas container-defaults fix
    pending) — surfaced as spawn_rejected, never swallowed."""
    return None if 200 <= status_code < 300 else "spawn_rejected"


def classify_failure_path(run: RunResult) -> str | None:
    """Map a crash / dead_letter RunResult to a FAILURE_MODES entry; None on a
    clean failure-path outcome. Symmetric with classify_spawn_failure — it ties
    the §9 crash_unrecovered / not_dead_lettered modes to the observed run so the
    harness reports them (P3/P4) instead of hanging. Non-failure-path run_modes
    (cold / recall) return None."""
    if run.run_mode == "crash":
        return None if run.recovered else "crash_unrecovered"
    if run.run_mode == "dead_letter":
        return None if run.dead_lettered else "not_dead_lettered"
    return None


# ─── v2.0 WITNESS — live #ceo stream (Dave watches; Dave's table signs off) ───


@dataclass(frozen=True)
class WitnessEvent:
    run_mode: str
    kind: str  # state_transition | retrieval_trace | cost | failure | evidence
    detail: str


def format_witness(e: WitnessEvent) -> str:
    """One scannable #ceo line per witness event (real-time rehearsal log)."""
    icon = {
        "state_transition": "▸",
        "retrieval_trace": "🔎",
        "cost": "💲",
        "failure": "🔴",
        "evidence": "📋",
    }.get(e.kind, "·")
    return f"{icon} [rehearsal:{e.run_mode}] {e.kind}: {e.detail}"


def post_witness(
    e: WitnessEvent, *, token: str | None = None, channel: str = CEO_WITNESS_CHANNEL
) -> bool:
    """Fire-and-forget post of one witness line to #ceo. Fail-open — a witness
    outage must never abort the rehearsal (mirrors src/slack_bot/direct_post.py)."""
    import json as _json
    import urllib.request as _req

    token = token or os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        print(f"[witness:no-token] {format_witness(e)}")  # local fallback log
        return False
    body = _json.dumps({"channel": channel, "text": format_witness(e)}).encode("utf-8")
    request = _req.Request(
        SLACK_POST_URL,
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with _req.urlopen(request, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:  # noqa: BLE001 — witness must never abort the rehearsal
        return False


# ─── v2.0 COST — per-loop floor vs 48-72h soak (binding A$350) ────────────────


def soak_run_rate_aud(per_loop_aud: float, loops_per_hour: float, soak_hours: float) -> float:
    """Extrapolate the soak run-rate (binding cost) from the per-loop FLOOR.
    Per-loop is the measured floor; the soak run-rate over 48-72h is what binds."""
    return round(per_loop_aud * loops_per_hour * soak_hours, 2)


def validate_soak(run_rate_aud: float, *, target: float = SOAK_TARGET_AUD) -> tuple[bool, float]:
    """Binding cost gate: the 48-72h soak run-rate must be <= target (A$350)."""
    return (run_rate_aud <= target, target)


# ─── v2.0 EVIDENCE — P1-P11 rows for DAVE'S table (harness witnesses, not judges) ──
# PROPOSED P1-P11 — pending Viktor's authoritative enumeration (flagged to Elliot).
# The harness produces the observed evidence per criterion + streams it to #ceo;
# DAVE marks pass/fail. This is NOT a self-sign-off.


@dataclass(frozen=True)
class CriterionEvidence:
    pid: str  # "P1".."P11"
    label: str
    observed: bool
    evidence: str


def collect_gate_evidence(
    runs: dict[str, RunResult], *, target_aud: float = SOAK_TARGET_AUD
) -> list[CriterionEvidence]:
    """Build the P1-P11 evidence rows from the 4 runs for Dave's pass/fail table.
    `runs` keyed by RUN_MODES. Returns observations, NOT a verdict."""
    recall = runs.get("recall")
    cold = runs.get("cold")
    crash = runs.get("crash")
    dl = runs.get("dead_letter")
    gap = memory_gap(recall, cold) if recall and cold else {"active_strictly_outtraces_cold": False}
    atom_ok, atom_n = assert_recall_returned_atom(recall) if recall else (False, 0)
    g = (recall.governance if recall else {}) or {}
    fired = {t.hop for t in recall.hop_traces if t.fired} if recall else set()
    per_loop = recall.cost_aud if recall else 0.0

    def ev(pid, label, observed, detail):
        return CriterionEvidence(pid=pid, label=label, observed=bool(observed), evidence=detail)

    return [
        ev("P1", "cold run completes", bool(cold), f"cold run present={bool(cold)}"),
        ev("P2", "recall run completes", bool(recall), f"recall run present={bool(recall)}"),
        ev(
            "P3",
            "crash run recovers",
            crash.recovered if crash else False,
            f"recovered={crash.recovered if crash else 'n/a'}",
        ),
        ev(
            "P4",
            "dead-letter run routes to DLQ",
            dl.dead_lettered if dl else False,
            f"dead_lettered={dl.dead_lettered if dl else 'n/a'}",
        ),
        ev(
            "P5",
            "PR merged (recall)",
            recall.pr_merged if recall else False,
            f"pr_merged={recall.pr_merged if recall else 'n/a'}",
        ),
        ev(
            "P6",
            "CI passed (recall)",
            recall.ci_passed if recall else False,
            f"ci_passed={recall.ci_passed if recall else 'n/a'}",
        ),
        ev(
            "P7",
            "governance honoured",
            bool(
                g.get("callsign_tagged")
                and int(g.get("concur_count", 0)) >= 2
                and g.get("no_linear_write", True)
                and g.get("claim_observed")
            ),
            f"gov={g}",
        ),
        ev(
            "P8",
            "trace at every hop (recall)",
            not [h for h in HOP_AGENTS_DEFAULT if h not in fired],
            f"fired_hops={sorted(fired)}",
        ),
        ev("P9", "recall returned >=1 relevant atom", atom_ok, f"relevant_atoms={atom_n}"),
        ev(
            "P10",
            "memory gap (recall out-traces cold)",
            gap["active_strictly_outtraces_cold"],
            f"active_only={gap.get('active_only_hops')}",
        ),
        ev(
            "P11",
            "per-loop cost floor measured",
            per_loop > 0,
            f"per_loop_aud={per_loop} (binding=48-72h soak run-rate vs A${target_aud})",
        ),
    ]


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
