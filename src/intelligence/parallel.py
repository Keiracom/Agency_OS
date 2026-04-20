"""Shared async parallelism utility for Pipeline F v2.1 stage execution.

All batch stage runners use run_parallel() instead of raw asyncio.gather.
Provides semaphore limiting, error isolation, and progress logging.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


async def run_parallel(
    items: list[T],
    func: Callable[[T], Coroutine[Any, Any, R]],
    concurrency: int = 10,
    label: str = "batch",
    on_progress: Callable[[int, int], None] | None = None,
) -> list[R | dict]:
    """Run an async function on a list of items with concurrency limiting.

    Args:
        items: List of inputs to process.
        func: Async function that takes one item and returns a result.
        concurrency: Max concurrent executions (from stage_parallelism.py).
        label: Label for log messages (e.g. "Stage 4 SIGNAL").
        on_progress: Optional callback(completed, total) at 25/50/75/100%.

    Returns:
        List of results in input order. Failed items return {"_error": str, "_item_index": i}.
    """
    total = len(items)
    if total == 0:
        return []

    results: list[R | dict] = [None] * total  # type: ignore[list-item]
    semaphore = asyncio.Semaphore(concurrency)
    completed = 0
    milestones = {int(total * p) for p in (0.25, 0.50, 0.75, 1.0)} - {0}

    async def _run_one(i: int, item: T) -> None:
        nonlocal completed
        async with semaphore:
            try:
                results[i] = await func(item)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] item %d failed: %s", label, i, exc)
                results[i] = {"_error": str(exc), "_item_index": i}
            finally:
                completed += 1
                if completed in milestones:
                    pct = int(completed / total * 100)
                    logger.info("[%s] progress %d/%d (%d%%)", label, completed, total, pct)
                    if on_progress is not None:
                        on_progress(completed, total)

    await asyncio.gather(*(_run_one(i, item) for i, item in enumerate(items)))
    return results
