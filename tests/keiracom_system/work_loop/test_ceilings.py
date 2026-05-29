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


# --- operator-uncap (Agency_OS-w667) -----------------------------------


async def test_fleet_tenant_is_uncapped_without_db_lookup():
    # The fleet slug returns FLEET_OPERATOR_CEILING via early return — fetch is
    # never consulted (a raising fetch would surface if it were called).
    result = await ceilings.get_ceiling(ceilings.DEFAULT_FLEET_TENANT_ID, fetch=_raises())
    assert result == ceilings.FLEET_OPERATOR_CEILING
    assert ceilings.FLEET_OPERATOR_CEILING > 20  # well above the highest tier ceiling


async def test_fleet_slug_is_env_overridable(monkeypatch):
    monkeypatch.setenv("FLEET_TENANT_ID", "fleet-x")
    assert await ceilings.get_ceiling("fleet-x", fetch=_raises()) == ceilings.FLEET_OPERATOR_CEILING
    # a non-fleet tenant still goes through the normal lookup
    assert await ceilings.get_ceiling("some-uuid", fetch=_fetch((6, "pro"))) == 6
