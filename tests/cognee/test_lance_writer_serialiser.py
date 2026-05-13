"""Tests for KEI-23 Cognee Lance writer-serialiser monkeypatch.

Crash anchor: 2026-05-13T01:54:53 lance error "Too many concurrent writers"
in lance-4.0.0/src/dataset/write/retry.rs:48. Diagnostic + recommendation:
docs/wave2/kei23_stream2_crash_diagnosis.md + PR #825.

Fix shape: module-level asyncio.Semaphore(1) wrapping
LanceDBAdapter.index_data_points (the funnel point all batch writes flow
through, delegating to create_data_points -> collection.merge_insert).
"""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def fake_lance_adapter(monkeypatch):
    """Inject a fake cognee.infrastructure.databases.vector.lancedb.LanceDBAdapter
    so the writer-serialiser installer can find + patch it."""
    # Build the package chain so `from cognee.infrastructure.databases.vector.lancedb.LanceDBAdapter import LanceDBAdapter`
    # resolves to our test double.
    fake_cognee = ModuleType("cognee")
    fake_infra = ModuleType("cognee.infrastructure")
    fake_db = ModuleType("cognee.infrastructure.databases")
    fake_vec = ModuleType("cognee.infrastructure.databases.vector")
    fake_lance_pkg = ModuleType("cognee.infrastructure.databases.vector.lancedb")
    fake_lance_mod = ModuleType("cognee.infrastructure.databases.vector.lancedb.LanceDBAdapter")

    class FakeLanceDBAdapter:
        async def index_data_points(self, index_name, index_property_name, data_points):
            return ("orig", index_name, index_property_name, len(data_points))

    fake_lance_mod.LanceDBAdapter = FakeLanceDBAdapter
    fake_cognee.add = AsyncMock(return_value="add-result")
    fake_cognee.cognify = AsyncMock(return_value="cognify-result")
    fake_cognee.memify = AsyncMock(return_value="memify-result")
    fake_cognee.search = AsyncMock(return_value=[])

    monkeypatch.setitem(sys.modules, "cognee", fake_cognee)
    monkeypatch.setitem(sys.modules, "cognee.infrastructure", fake_infra)
    monkeypatch.setitem(sys.modules, "cognee.infrastructure.databases", fake_db)
    monkeypatch.setitem(sys.modules, "cognee.infrastructure.databases.vector", fake_vec)
    monkeypatch.setitem(
        sys.modules, "cognee.infrastructure.databases.vector.lancedb", fake_lance_pkg
    )
    monkeypatch.setitem(
        sys.modules, "cognee.infrastructure.databases.vector.lancedb.LanceDBAdapter", fake_lance_mod
    )

    # Stub the users.methods import path too (touched by other tests).
    users_methods = ModuleType("cognee.modules.users.methods")
    users_methods.get_user_by_email = AsyncMock(return_value=None)
    users_methods.create_user = AsyncMock()
    monkeypatch.setitem(sys.modules, "cognee.modules.users.methods", users_methods)

    sys.modules.pop("src.cognee.client", None)
    sys.modules.pop("src.cognee", None)
    return SimpleNamespace(adapter_class=FakeLanceDBAdapter, mod=fake_lance_mod)


def test_installer_skips_when_provider_not_lancedb(fake_lance_adapter, monkeypatch):
    monkeypatch.setenv("VECTOR_DB_PROVIDER", "pgvector")
    from src.cognee import client  # noqa: F401 — import triggers installer

    method = fake_lance_adapter.adapter_class.index_data_points
    assert getattr(method, "__kei23_serialised__", False) is False


def test_installer_patches_when_provider_is_lancedb(fake_lance_adapter, monkeypatch):
    monkeypatch.setenv("VECTOR_DB_PROVIDER", "lancedb")
    from src.cognee import client  # noqa: F401

    method = fake_lance_adapter.adapter_class.index_data_points
    assert getattr(method, "__kei23_serialised__", False) is True


def test_installer_is_idempotent(fake_lance_adapter, monkeypatch):
    """Repeated invocations must not stack wrappers."""
    monkeypatch.setenv("VECTOR_DB_PROVIDER", "lancedb")
    from src.cognee import client

    first_wrapper = fake_lance_adapter.adapter_class.index_data_points
    client._install_lance_writer_serialiser()
    second_wrapper = fake_lance_adapter.adapter_class.index_data_points
    assert first_wrapper is second_wrapper


def test_concurrent_writes_are_serialised(fake_lance_adapter, monkeypatch):
    """N concurrent invocations: max in-flight count must be 1 (semaphore=1)."""
    monkeypatch.setenv("VECTOR_DB_PROVIDER", "lancedb")
    # Replace the underlying index_data_points with one that tracks concurrency.
    in_flight = 0
    max_in_flight = 0
    completed = 0

    async def tracked(self, index_name, index_property_name, data_points):
        nonlocal in_flight, max_in_flight, completed
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        # Yield to let other tasks run — if no semaphore, they'd all enter here.
        await asyncio.sleep(0.01)
        in_flight -= 1
        completed += 1
        return None

    fake_lance_adapter.adapter_class.index_data_points = tracked

    from src.cognee import client  # noqa: F401 — wraps the (now tracked) method

    async def driver():
        adapter = fake_lance_adapter.adapter_class()
        N = 10
        await asyncio.gather(*[adapter.index_data_points(f"t{i}", "f", []) for i in range(N)])

    asyncio.run(driver())
    assert max_in_flight == 1, f"writes ran concurrently — max in-flight {max_in_flight}"
    assert completed == 10


def test_serialiser_returns_underlying_result(fake_lance_adapter, monkeypatch):
    """Wrapper must pass through the underlying return value unchanged."""
    monkeypatch.setenv("VECTOR_DB_PROVIDER", "lancedb")

    async def returns_sentinel(self, index_name, index_property_name, data_points):
        return ("sentinel", index_name, index_property_name, len(data_points))

    fake_lance_adapter.adapter_class.index_data_points = returns_sentinel
    from src.cognee import client  # noqa: F401

    async def driver():
        adapter = fake_lance_adapter.adapter_class()
        return await adapter.index_data_points("t1", "field_x", [1, 2, 3])

    out = asyncio.run(driver())
    assert out == ("sentinel", "t1", "field_x", 3)


def test_installer_handles_missing_lancedb_module(monkeypatch):
    """If LanceDBAdapter import fails, installer returns gracefully (test env safety)."""
    monkeypatch.setenv("VECTOR_DB_PROVIDER", "lancedb")
    # Inject a fake cognee top-level without the lancedb subpath.
    fake = ModuleType("cognee")
    fake.add = AsyncMock()
    fake.cognify = AsyncMock()
    fake.memify = AsyncMock()
    fake.search = AsyncMock()
    monkeypatch.setitem(sys.modules, "cognee", fake)
    # Ensure the lancedb path is NOT in sys.modules
    for key in list(sys.modules):
        if key.startswith("cognee.infrastructure"):
            monkeypatch.delitem(sys.modules, key, raising=False)
    users_methods = ModuleType("cognee.modules.users.methods")
    users_methods.get_user_by_email = AsyncMock(return_value=None)
    users_methods.create_user = AsyncMock()
    monkeypatch.setitem(sys.modules, "cognee.modules.users.methods", users_methods)
    sys.modules.pop("src.cognee.client", None)
    sys.modules.pop("src.cognee", None)

    # Must not raise.
    from src.cognee import client  # noqa: F401
