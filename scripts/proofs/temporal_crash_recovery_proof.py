"""temporal_crash_recovery_proof.py — Temporal crash-recovery Option B proof.

Worker module — three named activities (step1/step2/step3) each writing a
phase marker to PROOF_LOG, then a workflow that chains them. The driver
script (run_temporal_crash_recovery.sh) kills the worker mid-step-2 and
restarts to prove resumption from step 2; the negative case kills before
step 1 completes to prove no silent skip.

Each activity logs `<step>:<phase>:<pid>` per attempt — counting attempts
per step in PROOF_LOG is the verification primitive.

Anchor: KEI Agency_OS-xjtn temporal_chain proof gate. Dave directive
2026-06-02 Task 2 (Option B). Workflow targets Temporal at TEMPORAL_ADDR
(default 45.76.114.137:7233) on task_queue PROOF_QUEUE (default
atlas-crash-proof-xjtn).
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import Worker

PROOF_LOG = Path(os.environ.get("PROOF_LOG", "/tmp/temporal_crash_proof.log"))
SLEEP_S = float(os.environ.get("PROOF_SLEEP_S", "8"))


def _mark(step: str, phase: str) -> None:
    PROOF_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PROOF_LOG.open("a") as f:
        f.write(f"{step}:{phase}:{os.getpid()}\n")


@activity.defn
async def step1(payload: str) -> str:
    _mark("step1", "start")
    await asyncio.sleep(SLEEP_S)
    _mark("step1", "end")
    return f"{payload}|s1"


@activity.defn
async def step2(payload: str) -> str:
    _mark("step2", "start")
    await asyncio.sleep(SLEEP_S)
    _mark("step2", "end")
    return f"{payload}|s2"


@activity.defn
async def step3(payload: str) -> str:
    _mark("step3", "start")
    await asyncio.sleep(SLEEP_S)
    _mark("step3", "end")
    return f"{payload}|s3"


@workflow.defn
class CrashRecoveryProof:
    @workflow.run
    async def run(self, seed: str) -> str:
        opts = {
            "start_to_close_timeout": timedelta(seconds=120),
            "retry_policy": RetryPolicy(maximum_attempts=5),
        }
        a = await workflow.execute_activity(step1, seed, **opts)
        b = await workflow.execute_activity(step2, a, **opts)
        c = await workflow.execute_activity(step3, b, **opts)
        return c


async def run_worker() -> None:
    addr = os.environ.get("TEMPORAL_ADDR", "45.76.114.137:7233")
    queue = os.environ.get("PROOF_QUEUE", "atlas-crash-proof-xjtn")
    client = await Client.connect(addr)
    worker = Worker(
        client,
        task_queue=queue,
        workflows=[CrashRecoveryProof],
        activities=[step1, step2, step3],
    )
    sys.stderr.write(f"[worker pid={os.getpid()}] running queue={queue}\n")
    sys.stderr.flush()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
