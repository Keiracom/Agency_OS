"""Tests for the per-tenant ceiling lookup (fail-open, cost-safe)."""

from __future__ import annotations

from src.keiracom_system.work_loop import ceilings


def _fetch(row):
    async def _f(_tenant_id: str):
        return row

    return _f


def _raises():
    async def _f(_tenant_id: str):
        raise RuntimeError("db down")

    return _f


async def test_explicit_column_value_wins():
    assert await ceilings.get_ceiling("t", fetch=_fetch((6, "pro"))) == 6


async def test_null_column_falls_back_to_tier_default():
    assert await ceilings.get_ceiling("t", fetch=_fetch((None, "pro"))) == 6
    assert await ceilings.get_ceiling("t", fetch=_fetch((None, "scale"))) == 20
    assert await ceilings.get_ceiling("t", fetch=_fetch((None, "solo"))) == 2


async def test_unknown_tenant_uses_default_ceiling():
    assert await ceilings.get_ceiling("t", fetch=_fetch(None)) == ceilings.DEFAULT_CEILING


async def test_unknown_tier_uses_default_ceiling():
    assert (
        await ceilings.get_ceiling("t", fetch=_fetch((None, "mystery"))) == ceilings.DEFAULT_CEILING
    )


async def test_lookup_failure_is_failopen_to_default():
    assert await ceilings.get_ceiling("t", fetch=_raises()) == ceilings.DEFAULT_CEILING
