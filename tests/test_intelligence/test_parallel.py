"""Tests for src/intelligence/parallel.py"""
import asyncio

import pytest

from src.intelligence.parallel import run_parallel


@pytest.mark.asyncio
async def test_basic_parallel():
    async def double(x):
        return x * 2
    results = await run_parallel([1, 2, 3, 4, 5], double, concurrency=2, label="test")
    assert results == [2, 4, 6, 8, 10]


@pytest.mark.asyncio
async def test_error_isolation():
    async def maybe_fail(x):
        if x == 3:
            raise ValueError("boom")
        return x * 2
    results = await run_parallel([1, 2, 3, 4, 5], maybe_fail, concurrency=2, label="test")
    assert results[0] == 2
    assert results[1] == 4
    assert "_error" in results[2]  # item 3 failed
    assert results[3] == 8
    assert results[4] == 10


@pytest.mark.asyncio
async def test_concurrency_limit():
    active = 0
    max_active = 0

    async def track(x):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return x

    await run_parallel(list(range(20)), track, concurrency=5, label="test")
    assert max_active <= 5


@pytest.mark.asyncio
async def test_empty_input():
    async def noop(x):
        return x
    results = await run_parallel([], noop, label="test")
    assert results == []
