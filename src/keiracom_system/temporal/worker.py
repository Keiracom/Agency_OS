"""worker.py — production Temporal worker that registers Keiracom workflows.

Phase A6 first-workflow per Dave KEI-DAVE-MIGRATION-PATH.

Replaces worker_scaffold.py for production deployment. worker_scaffold.py
remains as a connection-only sanity check (registers ZERO workflows + ZERO
activities) for debugging Temporal connectivity without polluting workflow
state.

USAGE (production container ENTRYPOINT):
    python -m keiracom_system.temporal.worker

Env:
    TEMPORAL_ADDR        — required (e.g. 45.76.114.137:7233)
    TEMPORAL_NAMESPACE   — default 'default'
    TEMPORAL_TASK_QUEUE  — default 'keiracom-default'
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal

from .audit_activity import emit_audit_event
from .client import DEFAULT_NAMESPACE, DEFAULT_TASK_QUEUE, from_env
from .fleet_supervisor_workflow import FleetSupervisorWorkflow
from .v1_chain_workflow import V1ChainWorkflow, capture_hop_reasoning, run_chain_step

log = logging.getLogger(__name__)


async def run() -> None:
    """Connect + register FleetSupervisorWorkflow + emit_audit_event.

    Run until SIGTERM/SIGINT. Logs heartbeat every 60s.
    """
    try:
        from temporalio.worker import Worker
    except ImportError as exc:
        raise RuntimeError(
            f"temporalio SDK not installed; `pip install temporalio` first ({exc})"
        ) from exc

    client = await from_env()
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE", DEFAULT_TASK_QUEUE)
    namespace = os.environ.get("TEMPORAL_NAMESPACE", DEFAULT_NAMESPACE)
    log.info(
        "worker starting: namespace=%s task_queue=%s addr=%s workflows=[FleetSupervisorWorkflow,V1ChainWorkflow] activities=[emit_audit_event,run_chain_step,capture_hop_reasoning]",
        namespace,
        task_queue,
        os.environ.get("TEMPORAL_ADDR"),
    )

    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[FleetSupervisorWorkflow, V1ChainWorkflow],
        activities=[emit_audit_event, run_chain_step, capture_hop_reasoning],
    )

    stop_event = asyncio.Event()

    def _on_signal(signame: str) -> None:
        log.info("worker: %s received — shutting down", signame)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in ("SIGTERM", "SIGINT"):
        loop.add_signal_handler(getattr(signal, sig), _on_signal, sig)

    async def _heartbeat() -> None:
        while not stop_event.is_set():
            log.info("worker: alive (2 workflows + 2 activities registered)")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=60.0)
            except TimeoutError:
                continue

    async with worker:
        await asyncio.gather(stop_event.wait(), _heartbeat())

    log.info("worker: stopped cleanly")


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run())
