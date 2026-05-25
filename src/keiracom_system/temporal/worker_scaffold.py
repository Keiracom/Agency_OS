"""worker_scaffold.py — Temporal worker scaffold.

Phase A6 build per bd Agency_OS-(A6).

THIS IS A SCAFFOLD — the worker binds to the default task queue, registers
ZERO workflows and ZERO activities, and sits ready. Real workflow + activity
registration lands AFTER Elliot's temp.contract_doc ratifies (per Cat 5 row 100
LOOSE blocker — see docs/architecture/deep_dives/layer_05_orchestration.md §1
and §6).

Per Phase A6 dispatch acceptance: "Worker container scaffolded (not running
real workflows)." This file is exactly that — proves the worker can connect
and the polling loop runs; does not yet do anything domain-specific.

USAGE (production container ENTRYPOINT):
    python -m keiracom_system.temporal.worker_scaffold

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

from .client import DEFAULT_NAMESPACE, DEFAULT_TASK_QUEUE, from_env

log = logging.getLogger(__name__)


async def run() -> None:
    """Connect + bind a worker to the task queue with no registrations.

    Run until SIGTERM/SIGINT. Logs heartbeat every 60s so a container
    operator can see the process is alive.
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
        "worker_scaffold starting: namespace=%s task_queue=%s addr=%s",
        namespace,
        task_queue,
        os.environ.get("TEMPORAL_ADDR"),
    )

    # Empty workflow + activity sets — scaffold-only per Phase A6 acceptance.
    worker = Worker(client, task_queue=task_queue, workflows=[], activities=[])

    stop_event = asyncio.Event()

    def _on_signal(signame: str) -> None:
        log.info("worker_scaffold: %s received — shutting down", signame)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in ("SIGTERM", "SIGINT"):
        loop.add_signal_handler(getattr(signal, sig), _on_signal, sig)

    async def _heartbeat() -> None:
        while not stop_event.is_set():
            log.info("worker_scaffold: alive (registered 0 workflows, 0 activities)")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=60.0)
            except TimeoutError:
                continue

    async with worker:
        await asyncio.gather(stop_event.wait(), _heartbeat())

    log.info("worker_scaffold: stopped cleanly")


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run())
