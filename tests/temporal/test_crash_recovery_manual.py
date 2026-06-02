"""test_crash_recovery_manual.py — manual proof harness for PR #1388 crash-recovery gate.

GATE TEXT (verbatim):
    The chain restarts from the last completed activity after kill -9 on the
    worker process, with no duplicate side-effects.

This file is the operator-runnable harness backing that gate. Distinct from
tests/keiracom_system/temporal/test_v1_chain_crash_recovery.py (the CI gate
runner, env-gated via GATE_CRASH_DISPATCH_CMD) — this one is for hands-on
verification by a human against a live Temporal cluster, with verbose progress
output and Temporal event-history inspection.

USAGE (manual, from repo root):

    # 1. Ensure Temporal server reachable + DB env loaded
    export TEMPORAL_ADDR=45.76.114.137:7233    # or 127.0.0.1:7233 for local
    export MANUAL_TEMPORAL_GATE=1              # opt-in, prevents accidental run
    source /home/elliotbot/.config/agency-os/.env

    # 2. Run as plain script (recommended — verbose progress to stdout)
    python tests/temporal/test_crash_recovery_manual.py

    # 3. OR run via pytest (CI-skipped via @pytest.mark.manual + module guard)
    pytest tests/temporal/test_crash_recovery_manual.py -v -s

EXIT 0 = gate passes. Non-zero = gate fails (reason printed to stderr).

WHAT IT PROVES:
  (a) RESUME — after kill -9 mid-chain, a fresh worker picks up the workflow
      and drives it to completion (5/5 steps in `completed_steps`).
  (b) NO RE-EXECUTION OF COMPLETED ACTIVITIES — the Temporal event history
      shows ActivityTaskScheduled fires exactly once per chain_step (the
      strongest available proof that activity 1 didn't re-run after restart).
  (c) NO DUPLICATE DB SIDE-EFFECTS (opt-in, non-dry-run only) — when run
      with --no-dry-run, queries public.keiracom_spawn_attribution and asserts
      exactly one row per (chain_id, callsign) pair. Default mode is dry_run
      (no Anthropic cost, no DB writes — the activity short-circuits before
      the DB layer), so the DB check is skipped unless explicitly enabled.

WHY DRY_RUN IS THE DEFAULT:
  v1_chain_workflow.py's run_chain_step short-circuits the entire pipeline
  (Anthropic call + insert_attribution) under dry_run, returning a fake atom_id
  after a 5s sleep. That keeps the gate cheap to re-run (no LLM cost) while
  still exercising the Temporal scheduling/recovery layer — which is what the
  gate text is actually about. Side-effect duplication is a separate concern
  covered by the idempotency check on (chain_id, callsign) inside the activity
  and is unit-tested in PR #1388's test_v1_chain_crash_recovery.py.

TIMING NOTES:
  Each dry_run activity sleeps 5s. Sequential leg = aiden_plan → max_challenge
  → nova_build (~15s); parallel leg = orion_spec ‖ atlas_safety (~5s wall).
  Full chain wall-clock ≈ 20-22s under dry_run. We kill at T+8s — after
  aiden_plan completes (~T+5s, accounting for ~2s worker startup) and during
  max_challenge. This is the canonical "kill -9 mid-chain after 1st activity
  completes" scenario from the gate text.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import subprocess
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

WORKER_CMD = [sys.executable, "-m", "src.keiracom_system.temporal.worker"]
DEFAULT_KILL_DELAY_S = 8.0
DEFAULT_COMPLETION_TIMEOUT_S = 180.0
WORKER_STARTUP_GRACE_S = 2.0


def _stderr(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _stdout(msg: str) -> None:
    print(msg, flush=True)


def _gate_enabled() -> bool:
    return bool(os.environ.get("MANUAL_TEMPORAL_GATE", "").strip())


def _temporal_addr() -> str:
    return os.environ.get("TEMPORAL_ADDR", "").strip()


def _spawn_worker() -> subprocess.Popen:
    """Spawn the production worker as a subprocess. Inherits TEMPORAL_ADDR + env."""
    return subprocess.Popen(  # noqa: S603 — WORKER_CMD is fixed, not user input
        WORKER_CMD,
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _kill_worker_hard(proc: subprocess.Popen) -> None:
    """kill -9 the worker. Idempotent on already-dead procs."""
    if proc.poll() is not None:
        return
    with contextlib.suppress(ProcessLookupError):
        os.kill(proc.pid, signal.SIGKILL)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=5)


def _terminate_worker_soft(proc: subprocess.Popen | None) -> None:
    """Clean up a worker subprocess. Used in finally blocks."""
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


async def _await_workflow_result(client, workflow_id: str, timeout_s: float) -> dict:
    """Poll workflow handle until complete or timeout. Returns the workflow result dict."""
    handle = client.get_workflow_handle(workflow_id)
    deadline = time.monotonic() + timeout_s
    last_log = 0.0
    while time.monotonic() < deadline:
        try:
            result = await handle.result(rpc_timeout=5)
            return result  # type: ignore[no-any-return]
        except asyncio.TimeoutError:
            now = time.monotonic()
            if now - last_log > 10:
                _stdout(f"  ... still waiting for {workflow_id} ({int(deadline - now)}s left)")
                last_log = now
            await asyncio.sleep(2)
    raise TimeoutError(f"Workflow {workflow_id} did not complete within {timeout_s}s")


async def _count_activity_schedules(client, workflow_id: str) -> Counter:
    """Inspect Temporal event history; return a Counter of ActivityTaskScheduled per activity_type.

    This is the strongest proof of "resume from last completed activity, not
    re-run": if aiden_plan completed before the kill -9, its scheduled count
    must be exactly 1 in the post-recovery history. >1 = activity re-executed.
    """
    handle = client.get_workflow_handle(workflow_id)
    counts: Counter = Counter()
    async for event in handle.fetch_history_events():
        attrs = getattr(event, "activity_task_scheduled_event_attributes", None)
        if attrs is None:
            continue
        activity_type = getattr(getattr(attrs, "activity_type", None), "name", None)
        if not activity_type:
            continue
        input_payloads = getattr(getattr(attrs, "input", None), "payloads", None) or []
        chain_step = "unknown"
        for payload in input_payloads:
            data = getattr(payload, "data", b"") or b""
            try:
                decoded = data.decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue
            for step in (
                "aiden_plan",
                "max_challenge",
                "nova_build",
                "orion_spec",
                "atlas_safety",
            ):
                if f'"chain_step":"{step}"' in decoded or f"'chain_step': '{step}'" in decoded:
                    chain_step = step
                    break
            if chain_step != "unknown":
                break
        counts[chain_step] += 1
    return counts


def _query_attribution_rows(chain_id: str) -> dict[str, int]:
    """Count keiracom_spawn_attribution rows per callsign for chain_id. Empty dict on DB failure."""
    try:
        from src.keiracom_system.vault.agent_cold_start import _connect
    except Exception as exc:  # noqa: BLE001
        _stderr(f"  WARN: cannot import _connect ({exc}); skipping DB check")
        return {}
    try:
        conn = _connect()
    except Exception as exc:  # noqa: BLE001
        _stderr(f"  WARN: DB connect failed ({exc}); skipping DB check")
        return {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT callsign, COUNT(*) FROM public.keiracom_spawn_attribution "
                "WHERE chain_id = %s GROUP BY callsign",
                (chain_id,),
            )
            rows = cur.fetchall()
        return {callsign: int(count) for callsign, count in rows}
    finally:
        conn.close()


async def _drive_crash_recovery(
    *,
    dry_run: bool,
    kill_delay_s: float,
    completion_timeout_s: float,
) -> dict:
    """Drive the full kill-and-restart cycle. Returns dict of evidence for assertions."""
    from src.keiracom_system.temporal.client import from_env
    from src.keiracom_system.temporal.v1_chain_workflow import (
        V1_CHAIN_TASK_QUEUE,
        ChainWorkflowInput,
        V1ChainWorkflow,
    )

    task_id = f"manual-crash-{uuid.uuid4().hex[:8]}"
    workflow_id = f"v1-chain-{task_id}"
    chain_id = task_id

    worker_a: subprocess.Popen | None = None
    worker_b: subprocess.Popen | None = None
    try:
        _stdout(f"[1/8] spawn worker A — task_id={task_id} dry_run={dry_run}")
        worker_a = _spawn_worker()
        await asyncio.sleep(WORKER_STARTUP_GRACE_S)
        if worker_a.poll() is not None:
            raise RuntimeError(f"worker A died on startup (exit {worker_a.returncode})")

        _stdout(f"[2/8] connect to Temporal at {_temporal_addr()}")
        client = await from_env()

        _stdout(f"[3/8] start workflow id={workflow_id}")
        await client.start_workflow(
            V1ChainWorkflow.run,
            ChainWorkflowInput(task_id=task_id, chain_id=chain_id, dry_run=dry_run),
            id=workflow_id,
            task_queue=V1_CHAIN_TASK_QUEUE,
        )

        _stdout(f"[4/8] sleep {kill_delay_s}s (lets aiden_plan complete + max_challenge start)")
        await asyncio.sleep(kill_delay_s)
        if worker_a.poll() is not None:
            raise RuntimeError("worker A died before scheduled kill — timing assumption broken")

        _stdout(f"[5/8] kill -9 worker A pid={worker_a.pid}")
        _kill_worker_hard(worker_a)
        await asyncio.sleep(1)

        _stdout("[6/8] spawn worker B (recovery worker)")
        worker_b = _spawn_worker()
        await asyncio.sleep(WORKER_STARTUP_GRACE_S)
        if worker_b.poll() is not None:
            raise RuntimeError(f"worker B died on startup (exit {worker_b.returncode})")

        _stdout(f"[7/8] await workflow completion (timeout {completion_timeout_s}s)")
        result = await _await_workflow_result(client, workflow_id, completion_timeout_s)

        _stdout("[8/8] fetch event history + DB attribution rows")
        schedule_counts = await _count_activity_schedules(client, workflow_id)
        attribution_counts = {} if dry_run else _query_attribution_rows(chain_id)

        return {
            "task_id": task_id,
            "chain_id": chain_id,
            "workflow_id": workflow_id,
            "result": result,
            "schedule_counts": dict(schedule_counts),
            "attribution_counts": attribution_counts,
            "dry_run": dry_run,
        }
    finally:
        _terminate_worker_soft(worker_a)
        _terminate_worker_soft(worker_b)


def _assert_gate(evidence: dict) -> list[str]:
    """Apply the gate's three proof clauses to the collected evidence. Returns list of failure strings."""
    failures: list[str] = []
    result = evidence.get("result") or {}
    completed = result.get("completed_steps") or []
    if len(completed) != 5:
        failures.append(f"completed_steps != 5 (got {len(completed)}: {completed})")
    if result.get("task_id") != evidence["task_id"]:
        failures.append(f"task_id mismatch: result={result.get('task_id')} expected={evidence['task_id']}")

    schedule_counts = evidence.get("schedule_counts") or {}
    expected_steps = {"aiden_plan", "max_challenge", "nova_build", "orion_spec", "atlas_safety"}
    for step in expected_steps:
        count = schedule_counts.get(step, 0)
        if count == 0:
            failures.append(f"activity {step} never scheduled (chain incomplete)")
        elif count > 1:
            failures.append(
                f"activity {step} scheduled {count}x — gate violation (resume must NOT re-run completed activities)"
            )

    if not evidence.get("dry_run"):
        attribution_counts = evidence.get("attribution_counts") or {}
        if not attribution_counts:
            failures.append("non-dry-run requested but no attribution rows found (DB write failed or unreachable)")
        else:
            for callsign, count in attribution_counts.items():
                if count != 1:
                    failures.append(
                        f"keiracom_spawn_attribution has {count} rows for callsign={callsign} chain_id={evidence['chain_id']} — expected exactly 1 (no duplicate side-effects)"
                    )
    return failures


async def main(*, dry_run: bool = True, kill_delay_s: float = DEFAULT_KILL_DELAY_S) -> int:
    """Script entry point. Returns 0 on gate pass, non-zero on failure."""
    if not _gate_enabled():
        _stderr(
            "MANUAL_TEMPORAL_GATE not set — this harness is opt-in. "
            "Re-run with `export MANUAL_TEMPORAL_GATE=1` after confirming a live Temporal server is reachable."
        )
        return 2
    if not _temporal_addr():
        _stderr("TEMPORAL_ADDR not set — e.g. `export TEMPORAL_ADDR=127.0.0.1:7233`")
        return 2

    _stdout(f"=== Temporal crash-recovery proof gate (PR #1388 / KEI-248) ===")
    _stdout(f"    TEMPORAL_ADDR={_temporal_addr()}  dry_run={dry_run}  kill_delay={kill_delay_s}s")

    try:
        evidence = await _drive_crash_recovery(
            dry_run=dry_run,
            kill_delay_s=kill_delay_s,
            completion_timeout_s=DEFAULT_COMPLETION_TIMEOUT_S,
        )
    except Exception as exc:  # noqa: BLE001
        _stderr(f"FATAL: {type(exc).__name__}: {exc}")
        return 1

    _stdout("--- evidence ---")
    _stdout(f"  result.completed_steps = {evidence['result'].get('completed_steps')}")
    _stdout(f"  schedule_counts        = {evidence['schedule_counts']}")
    _stdout(f"  attribution_counts     = {evidence['attribution_counts']}")

    failures = _assert_gate(evidence)
    if failures:
        _stderr("GATE FAIL:")
        for f in failures:
            _stderr(f"  - {f}")
        return 1
    _stdout("GATE PASS — chain resumed from last completed activity with no re-execution.")
    return 0


# ---------------------------------------------------------------------------
# Pytest wrapper — CI skips via the module-level guard below; @pytest.mark.manual
# is for human-readable intent + so an operator can run `pytest -m manual` locally.
# ---------------------------------------------------------------------------

if not _gate_enabled():
    pytest.skip(
        "MANUAL_TEMPORAL_GATE not set — manual proof harness opt-in only "
        "(needs live Temporal server; CI runs the gate via "
        "tests/keiracom_system/temporal/test_v1_chain_crash_recovery.py)",
        allow_module_level=True,
    )

pytest.importorskip("temporalio", reason="temporalio SDK required for manual crash-recovery harness")


@pytest.mark.manual
@pytest.mark.asyncio
async def test_crash_recovery_manual_proof_gate():
    """Manual proof gate runner for PR #1388. See module docstring for setup."""
    exit_code = await main(dry_run=True)
    assert exit_code == 0, f"manual proof gate failed (exit {exit_code}) — see stderr above"


if __name__ == "__main__":
    parser_dry_run = "--no-dry-run" not in sys.argv
    parser_kill_delay = DEFAULT_KILL_DELAY_S
    for i, arg in enumerate(sys.argv):
        if arg == "--kill-delay" and i + 1 < len(sys.argv):
            parser_kill_delay = float(sys.argv[i + 1])
    sys.exit(asyncio.run(main(dry_run=parser_dry_run, kill_delay_s=parser_kill_delay)))
