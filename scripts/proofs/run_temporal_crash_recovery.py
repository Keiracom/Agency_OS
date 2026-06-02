"""run_temporal_crash_recovery.py — driver for the temporal crash-recovery proof.

Two cases:

  POSITIVE (resume-from-step-2):
    - clean PROOF_LOG
    - start workflow ID 'pos-<uuid>'
    - start worker
    - wait until step2:start appears in PROOF_LOG (step1 already :end)
    - SIGKILL worker
    - restart worker
    - wait for workflow completion
    - assert: step1 ran 1x, step2 ran >= 2x (initial + retry), step3 ran 1x

  NEGATIVE (kill before step1 completes — verify no silent skip):
    - clean PROOF_LOG
    - start workflow ID 'neg-<uuid>'
    - start worker
    - wait until step1:start appears (NO step1:end yet)
    - SIGKILL worker IMMEDIATELY
    - restart worker
    - wait for workflow completion
    - assert: step1 ran >= 2x (re-executed, NOT silently skipped),
              step2 ran 1x, step3 ran 1x

Output: each case prints "POSITIVE PASS" / "NEGATIVE PASS" + the raw
PROOF_LOG content. Non-zero exit if any assert fails.

Anchor: KEI Agency_OS-xjtn Task 2. Dave directive 2026-06-02.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

PROOF_LOG = Path("/tmp/temporal_crash_proof.log")
WORKER_CMD = [
    sys.executable,
    "-m",
    "scripts.proofs.temporal_crash_recovery_proof",
]
TASK_QUEUE = "atlas-crash-proof-xjtn"
TEMPORAL_ADDR = os.environ.get("TEMPORAL_ADDR", "45.76.114.137:7233")
WORKFLOW_TIMEOUT_S = 300


def _reset_log() -> None:
    if PROOF_LOG.exists():
        PROOF_LOG.unlink()


def _read_marks() -> list[tuple[str, str, str]]:
    if not PROOF_LOG.exists():
        return []
    out = []
    for line in PROOF_LOG.read_text().splitlines():
        parts = line.split(":")
        if len(parts) == 3:
            out.append((parts[0], parts[1], parts[2]))
    return out


def _step_counts(phase_filter: str = "end") -> dict[str, int]:
    """Count how many times each step reached `phase_filter` (default 'end')."""
    c: Counter[str] = Counter()
    for step, phase, _pid in _read_marks():
        if phase == phase_filter:
            c[step] += 1
    return dict(c)


def _step_start_counts() -> dict[str, int]:
    """How many times each step STARTED (attempt counter)."""
    c: Counter[str] = Counter()
    for step, phase, _pid in _read_marks():
        if phase == "start":
            c[step] += 1
    return dict(c)


def _start_worker() -> subprocess.Popen:
    return subprocess.Popen(
        WORKER_CMD,
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, "TEMPORAL_ADDR": TEMPORAL_ADDR, "PROOF_QUEUE": TASK_QUEUE},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _wait_for_mark(step: str, phase: str, timeout_s: float = 60) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for s, p, _pid in _read_marks():
            if s == step and p == phase:
                return True
        time.sleep(0.5)
    return False


async def _start_workflow(workflow_id: str, seed: str) -> str:
    from temporalio.client import Client

    from scripts.proofs.temporal_crash_recovery_proof import CrashRecoveryProof

    client = await Client.connect(TEMPORAL_ADDR)
    handle = await client.start_workflow(
        CrashRecoveryProof.run,
        seed,
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    return await asyncio.wait_for(handle.result(), timeout=WORKFLOW_TIMEOUT_S)


def _run_case(case_name: str, kill_after_mark: tuple[str, str]) -> dict:
    """Returns a result dict with raw evidence."""
    print(f"\n=== CASE: {case_name} ===")
    _reset_log()
    wf_id = f"{case_name}-{uuid.uuid4().hex[:8]}"
    worker = _start_worker()
    print(f"[driver] started worker pid={worker.pid} workflow_id={wf_id}")

    # Give worker a beat to register with Temporal.
    time.sleep(2)

    # Start workflow in background thread (sync wait blocks if we run it here).
    import threading

    result_box: dict = {}

    def _runner():
        try:
            r = asyncio.run(_start_workflow(wf_id, "seed"))
            result_box["result"] = r
        except Exception as exc:
            result_box["error"] = repr(exc)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()

    # Wait for the kill-trigger mark.
    target_step, target_phase = kill_after_mark
    print(f"[driver] waiting for mark {target_step}:{target_phase} ...")
    if not _wait_for_mark(target_step, target_phase, timeout_s=60):
        worker.terminate()
        raise RuntimeError(f"timeout waiting for {target_step}:{target_phase}")

    # SIGKILL the worker.
    print(f"[driver] SIGKILL worker pid={worker.pid}")
    os.kill(worker.pid, signal.SIGKILL)
    worker.wait()
    print("[driver] worker reaped")

    # Read intermediate state.
    intermediate_marks = _read_marks()
    print(f"[driver] marks at kill: {intermediate_marks}")

    # Restart worker.
    worker2 = _start_worker()
    print(f"[driver] restarted worker pid={worker2.pid}")

    # Wait for workflow result.
    t.join(timeout=WORKFLOW_TIMEOUT_S)
    if t.is_alive():
        worker2.terminate()
        raise RuntimeError("workflow did not complete after worker restart")

    # Cleanup worker2.
    worker2.terminate()
    try:
        worker2.wait(timeout=5)
    except subprocess.TimeoutExpired:
        worker2.kill()

    final_marks = _read_marks()
    final_starts = _step_start_counts()
    final_ends = _step_counts("end")

    print(f"[driver] final marks: {final_marks}")
    print(f"[driver] step starts (attempts): {final_starts}")
    print(f"[driver] step ends (completions): {final_ends}")
    print(f"[driver] workflow result: {result_box}")

    return {
        "case": case_name,
        "workflow_id": wf_id,
        "intermediate_marks": intermediate_marks,
        "final_marks": final_marks,
        "starts": final_starts,
        "ends": final_ends,
        "result": result_box,
    }


def main() -> int:
    print(f"Temporal addr: {TEMPORAL_ADDR}, queue: {TASK_QUEUE}")
    print(f"PROOF_LOG path: {PROOF_LOG}")

    failures: list[str] = []

    # POSITIVE — kill mid-step-2 (after step2:start, before step2:end).
    pos = _run_case("pos", kill_after_mark=("step2", "start"))
    # Assertions:
    if pos["ends"].get("step1") != 1:
        failures.append(f"POSITIVE: step1 ended {pos['ends'].get('step1')} times, expected 1")
    if pos["starts"].get("step2", 0) < 2:
        failures.append(
            f"POSITIVE: step2 started {pos['starts'].get('step2', 0)} times, "
            "expected >= 2 (initial + retry-after-crash)"
        )
    if pos["ends"].get("step2") != 1:
        failures.append(
            f"POSITIVE: step2 ended {pos['ends'].get('step2')} times, expected 1 (final completion)"
        )
    if pos["ends"].get("step3") != 1:
        failures.append(f"POSITIVE: step3 ended {pos['ends'].get('step3')} times, expected 1")
    if "result" not in pos["result"] or pos["result"]["result"] != "seed|s1|s2|s3":
        failures.append(
            f"POSITIVE: workflow result was {pos['result']!r}, expected 'seed|s1|s2|s3'"
        )

    # NEGATIVE — kill mid-step-1 (BEFORE any activity completes).
    neg = _run_case("neg", kill_after_mark=("step1", "start"))
    if neg["starts"].get("step1", 0) < 2:
        failures.append(
            f"NEGATIVE: step1 started {neg['starts'].get('step1', 0)} times, "
            "expected >= 2 (re-executed after crash — proves no silent skip)"
        )
    if neg["ends"].get("step1") != 1:
        failures.append(
            f"NEGATIVE: step1 ended {neg['ends'].get('step1')} times, expected 1 (final completion)"
        )
    if neg["ends"].get("step2") != 1:
        failures.append(f"NEGATIVE: step2 ended {neg['ends'].get('step2')} times, expected 1")
    if neg["ends"].get("step3") != 1:
        failures.append(f"NEGATIVE: step3 ended {neg['ends'].get('step3')} times, expected 1")

    print("\n=== PROOF VERDICT ===")
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "POSITIVE PASS: kill mid-step-2 → step1 not re-executed (1x), step2 re-executed (>=2 attempts, 1 completion), step3 ran once."
    )
    print(
        "NEGATIVE PASS: kill mid-step-1 (no checkpoint) → step1 re-executed (>=2 attempts, 1 completion), no silent skip."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
