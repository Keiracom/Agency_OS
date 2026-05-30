#!/usr/bin/env python3
"""v1_battery_harness.py — V1 chain dress-rehearsal BATTERY harness.

Drives a curated battery of V1 chain runs (variance / memory recall / crash /
heavy / Max-CLI baseline), collects per-run attribution + chain-status metrics,
and renders a markdown PASS/FAIL table against operator-supplied thresholds.

The pre-flight is an **API-not-Max gate**: refuses to run if `ANTHROPIC_API_KEY`
is empty, if `DISPATCHER_AGENT_COMMAND` does not point at `api_agent_cold_start`
(the Anthropic SDK ephemeral entrypoint — Atlas PR #1350 / Agency_OS-l6i2), or
if the dispatcher is unhealthy. Each assertion fails loud and exits non-zero.

Usage:

    # Pre-flight only (no real chain runs):
    python3 scripts/v1_battery_harness.py --dry-run

    # Full API battery against api_agent_cold_start (requires PR #1350 merged):
    python3 scripts/v1_battery_harness.py --thresholds thresholds.json

    # Subset (just Task A variance + Task B cold/warm):
    python3 scripts/v1_battery_harness.py --tasks A,B

    # Max-CLI side-by-side baseline (operator must first flip
    # DISPATCHER_AGENT_COMMAND back to agent_cold_start AND restart the dispatcher):
    python3 scripts/v1_battery_harness.py --baseline-only

KEI: Agency_OS-jb4e (dress-rehearsal gate) + Agency_OS-avii (crash-recovery).

Stdlib only on the import path so the harness loads cleanly in CI. `psycopg` is
lazy-imported on the live attribution-query path; absent psycopg falls back to
the `/dispatcher/chain_status` endpoint (which already wraps the attribution
query in main.py:1364).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# ─── constants ────────────────────────────────────────────────────────────────

DISPATCHER_URL = os.environ.get("DISPATCHER_URL", "http://127.0.0.1:4001")
FACE_MODULE = "src.keiracom_system.chat.face"
DEFAULT_WORKDIR = os.environ.get("DISPATCHER_AGENT_WORKDIR", "/home/elliotbot/clawd/Agency_OS")
CHAIN_STATE_FILE = Path(os.environ.get("V1_CHAIN_STATE_FILE", "/tmp/v1_chain_state.json"))
API_AGENT_NEEDLE = "api_agent_cold_start"
CLI_AGENT_NEEDLE = "agent_cold_start"  # used by --baseline-only; gate inverts
USD_TO_AUD = 1.55  # CLAUDE.md §LAW II — Australia First

RUN_TIMEOUT_S = int(os.environ.get("V1_BATTERY_RUN_TIMEOUT_S", "600"))
FACE_SPAWN_TIMEOUT_S = 30
POLL_INTERVAL_S = 2.0
HTTP_TIMEOUT_S = 10

DEFAULT_THRESHOLDS = {
    "cost_aud_max": 0.50,
    "latency_ms_max": 300_000,
    "cache_hit_pct_min": 0,
    "spawn_overhead_ms_max": 30_000,
    "ttf_signal_ms_max": 10_000,
}

CHAIN_STEPS = ("aiden_plan", "max_challenge", "nova_build", "orion_spec", "atlas_safety")
ROLE_FOR_STEP = {
    "aiden_plan": "aiden",
    "max_challenge": "max",
    "nova_build": "nova",
    "orion_spec": "orion",
    "atlas_safety": "atlas",
}

# ─── battery task briefs ──────────────────────────────────────────────────────

TASK_A_BRIEF = (
    "Add a one-line docstring to scripts/orchestrator/ops_failure_publish.py "
    "noting it publishes ops_failure envelopes to NATS keiracom.ops.failure."
)

TASK_B_BRIEF = (
    "Add a missing edge-case test for the work-loop consumer reconcile path. "
    "When a tenant has multiple lapsed leases simultaneously, reconcile should reclaim "
    "every one in a single sweep. Write a fakeredis-backed test in "
    "tests/keiracom_system/work_loop/test_consumer.py that admits three tasks, deletes "
    "all three lease keys to simulate three crashed agents, calls reconcile, and asserts "
    "all three slots are reclaimed plus the active counter returns to zero."
)

TASK_C_BRIEF = (
    "Add an end-to-end cost-ceiling assertion to the dress-rehearsal harness. "
    "When the rehearsal completes, fetch per-hop attribution rows for the chain_id from "
    "public.keiracom_spawn_attribution, sum cost_usd, convert to AUD at the 1.55 rate "
    "(CLAUDE.md §LAW II), and compare against an operator-supplied ceiling. Fail the "
    "rehearsal if the AUD total exceeds the ceiling. Write the assertion as a pure "
    "function in scripts/cutover/full_chain_dress_rehearsal.py + tests covering "
    "(a) under-ceiling pass, (b) over-ceiling fail, (c) attribution lookup failure "
    "(fail-open to 'cost unknown' rather than crashing the rehearsal)."
)

# ─── pre-flight (the API-not-Max gate) ────────────────────────────────────────


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_anthropic_api_key() -> CheckResult:
    val = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not val:
        return CheckResult(
            "ANTHROPIC_API_KEY",
            False,
            "unset or empty — the Anthropic SDK agent has no credential",
        )
    return CheckResult("ANTHROPIC_API_KEY", True, f"set ({len(val)} chars, sk-* form expected)")


def check_dispatcher_agent_command(*, baseline: bool = False) -> CheckResult:
    val = os.environ.get("DISPATCHER_AGENT_COMMAND", "")
    if not val:
        return CheckResult(
            "DISPATCHER_AGENT_COMMAND",
            False,
            "unset; dispatcher will use its default (Max CLI path = agent_cold_start). "
            "Set DISPATCHER_AGENT_COMMAND='python3 -m src.keiracom_system.vault."
            + (CLI_AGENT_NEEDLE if baseline else API_AGENT_NEEDLE)
            + "' and restart the dispatcher.",
        )
    if baseline:
        # --baseline-only: must be the CLI path; the API path is wrong here.
        if API_AGENT_NEEDLE in val:
            return CheckResult(
                "DISPATCHER_AGENT_COMMAND",
                False,
                f"value contains {API_AGENT_NEEDLE!r}; --baseline-only requires "
                f"{CLI_AGENT_NEEDLE!r} (Max CLI) so the side-by-side captures the CLI path",
            )
        if CLI_AGENT_NEEDLE not in val:
            return CheckResult(
                "DISPATCHER_AGENT_COMMAND",
                False,
                f"value {val!r} does not point at {CLI_AGENT_NEEDLE!r}",
            )
        return CheckResult(
            "DISPATCHER_AGENT_COMMAND", True, f"points at {CLI_AGENT_NEEDLE} (Max CLI baseline)"
        )
    # API battery (the default): must be api_agent_cold_start
    if API_AGENT_NEEDLE not in val:
        return CheckResult(
            "DISPATCHER_AGENT_COMMAND",
            False,
            f"value {val!r} does not contain {API_AGENT_NEEDLE!r} — the API-not-Max gate "
            "blocks running the rehearsal on the Claude Max CLI path. "
            "Atlas PR #1350 / Agency_OS-l6i2 ships api_agent_cold_start; set "
            "DISPATCHER_AGENT_COMMAND='python3 -m src.keiracom_system.vault."
            + API_AGENT_NEEDLE
            + "' and restart the dispatcher.",
        )
    return CheckResult(
        "DISPATCHER_AGENT_COMMAND", True, f"points at {API_AGENT_NEEDLE} (Anthropic SDK path)"
    )


def check_dispatcher_health() -> CheckResult:
    try:
        with urllib.request.urlopen(
            f"{DISPATCHER_URL}/dispatcher/health", timeout=HTTP_TIMEOUT_S
        ) as resp:
            body = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        return CheckResult(
            "dispatcher /health", False, f"probe failed: {type(exc).__name__}: {exc}"
        )
    status = body.get("status", "?")
    components = body.get("components", {})
    if status == "ok" and all(v in ("ok", "green") for v in components.values()):
        return CheckResult("dispatcher /health", True, "status=ok, all components ok/green")
    return CheckResult(
        "dispatcher /health",
        False,
        f"status={status!r}; components={components!r}",
    )


def pre_flight(*, baseline: bool = False) -> list[CheckResult]:
    return [
        check_anthropic_api_key(),
        check_dispatcher_agent_command(baseline=baseline),
        check_dispatcher_health(),
    ]


def print_preflight(results: list[CheckResult]) -> bool:
    """Print one line per check; return True if every check passed."""
    print("\nPRE-FLIGHT (API-not-Max gate):", file=sys.stderr)
    for r in results:
        glyph = "✅" if r.passed else "❌"
        print(f"  {glyph} {r.name}: {r.detail}", file=sys.stderr)
    ok = all(r.passed for r in results)
    if not ok:
        print(
            "\nPRE-FLIGHT FAILED — fix the failing assertion(s) above and re-run. "
            "The harness deliberately refuses to run a 'rehearsal' on the wrong path.\n",
            file=sys.stderr,
        )
    return ok


# ─── chain state + Face trigger ───────────────────────────────────────────────


def _load_chain_state() -> dict:
    try:
        return json.loads(CHAIN_STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def trigger_face_run(brief: str) -> tuple[str | None, float, str]:
    """Spawn Face as a subprocess with FACE_BRIEF; return (chain_id, started_monotonic, face_log).

    Face publishes the initial task_dispatch envelope to keiracom.dispatch.aiden
    and then exits (the chain continues in the consumers). Identification of the
    new chain_id is by diff against the chain state file.

    Fail-open: any failure returns (None, started, log) so the run is marked FAIL.
    """
    pre_ids = set(_load_chain_state().keys())
    env = {**os.environ, "FACE_BRIEF": brief}
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", FACE_MODULE],
            env=env,
            capture_output=True,
            text=True,
            timeout=FACE_SPAWN_TIMEOUT_S,
            cwd=DEFAULT_WORKDIR,
            check=False,
        )
        log = (proc.stdout + proc.stderr)[-2000:]
    except (subprocess.TimeoutExpired, OSError) as exc:
        return None, started, f"Face subprocess failed: {type(exc).__name__}: {exc}"
    post = _load_chain_state()
    new_ids = [cid for cid in post if cid not in pre_ids]
    chain_id = new_ids[0] if new_ids else None
    return chain_id, started, log


def wait_for_chain_complete(chain_id: str, timeout_s: int) -> dict:
    """Poll the chain state file until current_step=='complete' or timeout.

    Returns the final state entry (or whatever state we observed at timeout).
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        entry = _load_chain_state().get(chain_id, {})
        if entry.get("current_step") == "complete":
            return entry
        time.sleep(POLL_INTERVAL_S)
    return _load_chain_state().get(chain_id, {})


# ─── crash injection (Agency_OS-avii test case) ───────────────────────────────


def inject_crash(hop_step: str) -> tuple[bool, str]:
    """tmux kill-session for the callsign whose hop matches `hop_step`.

    Mid-chain crash injector — the work-loop reconcile path (5-min lease lapse →
    reconcile() reclaim → retry → dead-letter after 3) should observably either
    RECOVER the chain (next hop fires) or DEAD-LETTER it (visible in the chain
    state pending list / DLQ Valkey list).
    """
    role = ROLE_FOR_STEP.get(hop_step)
    if role is None:
        return False, f"unknown hop_step {hop_step!r}; expected one of {list(ROLE_FOR_STEP)}"
    try:
        proc = subprocess.run(
            ["tmux", "kill-session", "-t", role],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            return True, f"killed tmux session {role!r}"
        return False, f"tmux kill-session rc={proc.returncode}: {proc.stderr.strip()}"
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"tmux kill-session raised: {exc}"


# ─── metrics collection ───────────────────────────────────────────────────────


@dataclass
class RunResult:
    label: str
    kind: str
    brief: str
    chain_id: str | None
    status: str  # one of {"PASS", "FAIL", "CRASHED", "DLQ", "TIMEOUT", "SKIPPED"}
    started_ts: float
    ended_ts: float
    metrics: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def fetch_chain_status(chain_id: str) -> dict:
    """GET /dispatcher/chain_status?chain_id=… — best-effort.

    The endpoint (main.py:1322+) summarises chain state + per-hop cost view by
    wrapping the attribution query (main.py:1364). Returns {} on any failure.
    """
    try:
        with urllib.request.urlopen(
            f"{DISPATCHER_URL}/dispatcher/chain_status?chain_id={chain_id}",
            timeout=HTTP_TIMEOUT_S,
        ) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return {}


def fetch_attribution_rows(chain_id: str, task_id: str | None) -> list[dict]:
    """Direct keiracom_spawn_attribution query for per-hop tokens + cache breakdown.

    The attribution table (migration 20260527_keiracom_spawn_attribution.sql) has
    no chain_id column today (main.py:1331), so we filter by `source_id LIKE
    '%<task_id>%'` when a task_id is available, else by recency window.
    Best-effort — returns [] on missing DSN or psycopg.
    """
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        return []
    try:
        import psycopg  # noqa: PLC0415 — lazy; harness imports clean without psycopg
    except ImportError:
        return []
    clean = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    needle = task_id or chain_id
    try:
        with (
            psycopg.connect(clean, prepare_threshold=None, autocommit=True) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                "SELECT ts, source_id, callsign, model, input_tokens, output_tokens, "
                "cache_read_tokens, cache_write_tokens, cost_usd, completion_status "
                "FROM public.keiracom_spawn_attribution "
                "WHERE source_id LIKE %s "
                "ORDER BY ts ASC",
                (f"%{needle}%",),
            )
            rows = cur.fetchall()
    except Exception:  # noqa: BLE001 — best-effort observability; never blocks the harness
        return []
    cols = [
        "ts",
        "source_id",
        "callsign",
        "model",
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_write_tokens",
        "cost_usd",
        "completion_status",
    ]
    return [dict(zip(cols, r, strict=False)) for r in rows]


def derive_metrics(
    chain_id: str | None,
    entry: dict,
    started_ts: float,
    ended_ts: float,
    chain_status: dict,
    attribution: list[dict],
) -> dict:
    """Compute the cross-source metrics table the dispatch asked for."""
    out: dict = {
        "chain_id": chain_id or "n/a",
        "current_step": entry.get("current_step", "?"),
        "steps_done": ",".join(entry.get("steps_done", [])) or "—",
        "latency_ms": int((ended_ts - started_ts) * 1000),
    }
    # Cost — prefer chain_status (already AUD via the endpoint); fall back to attribution sum.
    cost_aud = chain_status.get("cost_aud")
    if cost_aud is None and attribution:
        cost_aud = sum(float(r.get("cost_usd", 0) or 0) for r in attribution) * USD_TO_AUD
    out["cost_aud"] = round(float(cost_aud), 4) if cost_aud is not None else None
    # Token totals
    if attribution:
        out["input_tokens"] = sum(int(r.get("input_tokens", 0) or 0) for r in attribution)
        out["output_tokens"] = sum(int(r.get("output_tokens", 0) or 0) for r in attribution)
        cache_r = sum(int(r.get("cache_read_tokens", 0) or 0) for r in attribution)
        cache_w = sum(int(r.get("cache_write_tokens", 0) or 0) for r in attribution)
        denom = out["input_tokens"] + cache_r + cache_w
        out["cache_hit_pct"] = round(100 * cache_r / denom, 1) if denom > 0 else 0.0
        out["hops_attributed"] = len(attribution)
    else:
        out.update(
            input_tokens=None,
            output_tokens=None,
            cache_hit_pct=None,
            hops_attributed=0,
        )
    # Spawn overhead — time between trigger and first attribution row, if any.
    first_attr_ts = None
    if attribution:
        try:
            first_attr_ts = attribution[0].get("ts")
        except IndexError:
            first_attr_ts = None
    out["spawn_overhead_ms"] = (
        int(_iso_to_unix(first_attr_ts) * 1000 - started_ts * 1000) if first_attr_ts else None
    )
    # Time-to-first-signal — first observable mutation in chain state.
    out["ttf_signal_ms"] = (
        int((_first_mutation_ts(chain_id) or ended_ts) * 1000 - started_ts * 1000)
        if chain_id
        else None
    )
    return out


def _iso_to_unix(ts: str | None) -> float:
    if not ts:
        return 0.0
    try:
        from datetime import datetime  # noqa: PLC0415

        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _first_mutation_ts(chain_id: str | None) -> float | None:
    """Time the state file first showed steps_done non-empty for this chain_id.
    Heuristic only — uses current file mtime as a proxy (the harness sees this
    after `wait_for_chain_complete` so it's an over-estimate; refine when the
    chain_status endpoint exposes per-hop timestamps)."""
    if not chain_id:
        return None
    try:
        return CHAIN_STATE_FILE.stat().st_mtime
    except OSError:
        return None


# ─── per-run executor ─────────────────────────────────────────────────────────


def execute_run(plan: dict) -> RunResult:
    label = plan["label"]
    kind = plan["kind"]
    brief = plan["brief"]
    print(f"\n▶ running {label} ({kind})…", file=sys.stderr)
    chain_id, started_ts, face_log = trigger_face_run(brief)
    if chain_id is None:
        return RunResult(
            label=label,
            kind=kind,
            brief=brief,
            chain_id=None,
            status="FAIL",
            started_ts=started_ts,
            ended_ts=time.monotonic(),
            notes=[f"Face did not produce a new chain_id; tail: {face_log[-400:]!r}"],
        )
    print(f"  chain_id={chain_id}", file=sys.stderr)
    # Optional crash injection.
    crash_hop = plan.get("crash_hop")
    crash_note = None
    if crash_hop:
        # Allow the chain to step into the target role briefly before killing.
        time.sleep(15)
        ok, msg = inject_crash(crash_hop)
        crash_note = f"crash@{crash_hop}: {'OK' if ok else 'FAILED'} — {msg}"
        print(f"  {crash_note}", file=sys.stderr)
    # Wait for completion (or timeout).
    entry = wait_for_chain_complete(chain_id, RUN_TIMEOUT_S)
    ended_ts = time.monotonic()
    chain_status = fetch_chain_status(chain_id)
    task_id = entry.get("task_id") if entry else None
    attribution = fetch_attribution_rows(chain_id, task_id)
    metrics = derive_metrics(chain_id, entry, started_ts, ended_ts, chain_status, attribution)
    # Status classification.
    if not entry:
        status = "TIMEOUT"
    elif entry.get("current_step") == "complete":
        status = "PASS"  # threshold compare happens at render time
    elif crash_hop:
        # crash-injection run with no complete: surface whether it recovered, DLQ'd, or stalled.
        if chain_status.get("dead_lettered"):
            status = "DLQ"
        else:
            status = "CRASHED"
    else:
        status = "FAIL"
    notes = []
    if crash_note:
        notes.append(crash_note)
    if not attribution:
        notes.append("no attribution rows visible — chain may have skipped DB writes")
    return RunResult(
        label=label,
        kind=kind,
        brief=brief,
        chain_id=chain_id,
        status=status,
        started_ts=started_ts,
        ended_ts=ended_ts,
        metrics=metrics,
        notes=notes,
    )


# ─── battery plan + render ────────────────────────────────────────────────────


def battery_plan(tasks_filter: list[str] | None) -> list[dict]:
    """The dispatch's run matrix. `tasks_filter` is a list of letters A/B/C."""
    plan = [
        {"label": "TaskA-run1", "brief": TASK_A_BRIEF, "kind": "variance#1", "task": "A"},
        {"label": "TaskA-run2", "brief": TASK_A_BRIEF, "kind": "variance#2", "task": "A"},
        {"label": "TaskB-cold", "brief": TASK_B_BRIEF, "kind": "memory-cold", "task": "B"},
        {"label": "TaskB-warm", "brief": TASK_B_BRIEF, "kind": "memory-warm", "task": "B"},
        {
            "label": "TaskB-crash",
            "brief": TASK_B_BRIEF,
            "kind": "crash@max",
            "task": "B",
            "crash_hop": "max_challenge",
        },
        {"label": "TaskC", "brief": TASK_C_BRIEF, "kind": "heavy", "task": "C"},
    ]
    if tasks_filter:
        plan = [p for p in plan if p["task"] in tasks_filter]
    return plan


def baseline_plan() -> list[dict]:
    """The Max-CLI side-by-side baseline run (Task B, identical brief)."""
    return [{"label": "TaskB-CLI-baseline", "brief": TASK_B_BRIEF, "kind": "max-cli", "task": "B"}]


def _verdict(metrics: dict, status: str, thresholds: dict) -> tuple[str, list[str]]:
    """Apply threshold comparisons; return (PASS|FAIL|<status>, reasons[])."""
    reasons: list[str] = []
    if status != "PASS":
        return status, reasons
    cost = metrics.get("cost_aud")
    if cost is not None and cost > thresholds["cost_aud_max"]:
        reasons.append(f"cost A${cost} > A${thresholds['cost_aud_max']}")
    lat = metrics.get("latency_ms")
    if lat is not None and lat > thresholds["latency_ms_max"]:
        reasons.append(f"latency {lat}ms > {thresholds['latency_ms_max']}ms")
    chp = metrics.get("cache_hit_pct")
    if chp is not None and chp < thresholds["cache_hit_pct_min"]:
        reasons.append(f"cache_hit {chp}% < {thresholds['cache_hit_pct_min']}%")
    spo = metrics.get("spawn_overhead_ms")
    if spo is not None and spo > thresholds["spawn_overhead_ms_max"]:
        reasons.append(f"spawn_overhead {spo}ms > {thresholds['spawn_overhead_ms_max']}ms")
    ttf = metrics.get("ttf_signal_ms")
    if ttf is not None and ttf > thresholds["ttf_signal_ms_max"]:
        reasons.append(f"ttf_signal {ttf}ms > {thresholds['ttf_signal_ms_max']}ms")
    return ("PASS" if not reasons else "FAIL"), reasons


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4f}" if abs(v) < 1 else f"{v:.2f}"
    return str(v)


def render_markdown(results: list[RunResult], thresholds: dict) -> str:
    lines: list[str] = []
    lines.append("# V1 Chain Dress-Rehearsal — Battery Results")
    lines.append("")
    lines.append(
        f"Generated by `scripts/v1_battery_harness.py`. Thresholds: "
        f"cost ≤ A${thresholds['cost_aud_max']} · latency ≤ {thresholds['latency_ms_max']}ms · "
        f"cache_hit ≥ {thresholds['cache_hit_pct_min']}% · "
        f"spawn_overhead ≤ {thresholds['spawn_overhead_ms_max']}ms · "
        f"ttf ≤ {thresholds['ttf_signal_ms_max']}ms"
    )
    lines.append("")
    header = (
        "| Run | Status | chain_id | cost A$ | latency ms | in tok | out tok | "
        "cache hit % | spawn ms | ttf ms | hops | Notes |"
    )
    sep = "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    lines.append(header)
    lines.append(sep)
    for r in results:
        verdict, reasons = _verdict(r.metrics, r.status, thresholds)
        glyph = {
            "PASS": "✅ PASS",
            "FAIL": "❌ FAIL",
            "CRASHED": "💥 CRASH",
            "DLQ": "📮 DLQ",
            "TIMEOUT": "⏱ TIMEOUT",
            "SKIPPED": "⏭ SKIP",
        }.get(verdict, verdict)
        m = r.metrics
        notes = "; ".join(reasons + r.notes) or "—"
        lines.append(
            f"| {r.label} ({r.kind}) | {glyph} | `{m.get('chain_id', '—')}` | "
            f"{_fmt(m.get('cost_aud'))} | {_fmt(m.get('latency_ms'))} | "
            f"{_fmt(m.get('input_tokens'))} | {_fmt(m.get('output_tokens'))} | "
            f"{_fmt(m.get('cache_hit_pct'))} | {_fmt(m.get('spawn_overhead_ms'))} | "
            f"{_fmt(m.get('ttf_signal_ms'))} | {_fmt(m.get('hops_attributed'))} | {notes} |"
        )
    # Aggregate verdict
    overall = (
        "PASS"
        if all(_verdict(r.metrics, r.status, thresholds)[0] == "PASS" for r in results)
        else "FAIL"
    )
    lines.append("")
    lines.append(f"**Battery overall: {overall}** ({len(results)} runs)")
    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────


def _load_thresholds(path: Path | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if path is None:
        # env var fallback (one knob per threshold).
        for k in thresholds:
            env_key = f"V1_BATTERY_{k.upper()}"
            if env_key in os.environ:
                with _suppress(ValueError):
                    thresholds[k] = float(os.environ[env_key])
        return thresholds
    try:
        loaded = json.loads(path.read_text())
        for k, v in loaded.items():
            if k in thresholds:
                thresholds[k] = float(v)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(
            f"warning: failed to load thresholds from {path}: {exc}; using defaults",
            file=sys.stderr,
        )
    return thresholds


from contextlib import suppress as _suppress  # noqa: E402 — kept near use site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="V1 chain dress-rehearsal BATTERY harness (Agency_OS-jb4e + avii)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run pre-flight only; print pass/fail and exit (no chain runs).",
    )
    parser.add_argument(
        "--thresholds",
        type=Path,
        help="JSON file with PASS/FAIL thresholds (cost_aud_max etc.). Default: built-in.",
    )
    parser.add_argument(
        "--tasks",
        type=str,
        default="",
        help="comma-separated subset of task families to run: A,B,C. Default: all.",
    )
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="run ONLY the Task B Max-CLI baseline (operator must flip "
        "DISPATCHER_AGENT_COMMAND back to agent_cold_start and restart the dispatcher first).",
    )
    args = parser.parse_args(argv)

    pre = pre_flight(baseline=args.baseline_only)
    if not print_preflight(pre):
        return 2  # API-not-Max gate failed

    if args.dry_run:
        print("Dry-run pre-flight passed — battery would proceed.", file=sys.stderr)
        return 0

    thresholds = _load_thresholds(args.thresholds)
    print(f"thresholds = {thresholds}", file=sys.stderr)

    if args.baseline_only:
        plan = baseline_plan()
    else:
        tasks_filter = [t.strip().upper() for t in args.tasks.split(",") if t.strip()] or None
        plan = battery_plan(tasks_filter)
        if not plan:
            print(f"no runs selected (tasks={args.tasks!r}); nothing to do", file=sys.stderr)
            return 0

    results = [execute_run(p) for p in plan]
    print(render_markdown(results, thresholds))
    rc = 0 if all(_verdict(r.metrics, r.status, thresholds)[0] == "PASS" for r in results) else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
