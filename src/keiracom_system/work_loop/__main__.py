"""Run the work-loop consumer as a service (Agency_OS-nkc0).

    python -m src.keiracom_system.work_loop

Subscribes to Valkey `keiracom:tasks:available` and drives the tier-gated
spawn loop (admit → POST /dispatcher/spawn → overflow at ceiling). Slot release
on agent exit + crash-recovery reconcile run in the dispatcher process
(src/dispatcher/main.py lifespan), not here — this entrypoint is just the
subscribe→process loop.
"""

from __future__ import annotations

import asyncio
import logging

from src.keiracom_system.work_loop.consumer import WorkLoopConsumer


def main() -> None:  # pragma: no cover — process entrypoint
    logging.basicConfig(level=logging.INFO)
    asyncio.run(WorkLoopConsumer().run())


if __name__ == "__main__":  # pragma: no cover
    main()
