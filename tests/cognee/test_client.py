"""Tests for src/cognee/client.py — mocked Cognee SDK, no live calls.

Per Phase 0 dispatch (Elliot ts 1778562982) + tenant-isolation amendment
(Scout Q4 + Elliot ts 1778565xxx): tests mock both the top-level cognee
module AND `cognee.modules.users.methods` so the wrapper's User-minting
path can be exercised without a live cognee install.
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def _make_user(email: str, tenant_id: str | None = None):
    return SimpleNamespace(id=f"uid-{email}", email=email, tenant_id=tenant_id)


@pytest.fixture(autouse=True)
def fake_cognee(monkeypatch):
    """Inject a fake `cognee` module + `cognee.modules.users.methods` submodule
    BEFORE importing client.py, so its top-of-module imports + lazy submodule
    import inside `_get_or_create_user` both resolve to mocks.
    """
    fake = SimpleNamespace(
        add=AsyncMock(return_value="add-result"),
        cognify=AsyncMock(return_value="cognify-result"),
        memify=AsyncMock(return_value="memify-result"),
        search=AsyncMock(return_value=["search-result"]),
    )

    users_methods = ModuleType("cognee.modules.users.methods")
    users_methods.get_user_by_email = AsyncMock(return_value=None)
    users_methods.create_user = AsyncMock(
        side_effect=lambda email, tenant_id=None, **_: _make_user(email, tenant_id)
    )

    monkeypatch.setitem(sys.modules, "cognee", fake)
    monkeypatch.setitem(sys.modules, "cognee.modules.users.methods", users_methods)
    sys.modules.pop("src.cognee.client", None)
    sys.modules.pop("src.cognee", None)
    return SimpleNamespace(top=fake, users=users_methods)


@pytest.fixture
def client(fake_cognee):
    from src.cognee import client as c

    # Clear the in-process User cache between tests so mint/lookup paths are
    # independent.
    c._USER_CACHE.clear()
    return c


# _dataset_name ──────────────────────────────────────────────────────────────


def test_dataset_name_composes_org_and_app(client):
    assert client._dataset_name("keiracom_platform", "agency_os") == "keiracom_platform__agency_os"


def test_dataset_name_rejects_empty_org(client):
    with pytest.raises(ValueError, match="org_id"):
        client._dataset_name("", "agency_os")


def test_dataset_name_rejects_empty_app(client):
    with pytest.raises(ValueError, match="app_id"):
        client._dataset_name("keiracom_platform", "")


# _agent_node_set ────────────────────────────────────────────────────────────


def test_agent_node_set_prepends_agent_tag(client):
    assert client._agent_node_set("aiden", ["test", "phase0"]) == [
        "agent:aiden",
        "test",
        "phase0",
    ]


def test_agent_node_set_handles_none_extras(client):
    assert client._agent_node_set("aiden", None) == ["agent:aiden"]


def test_agent_node_set_rejects_empty_agent_id(client):
    with pytest.raises(ValueError, match="agent_id"):
        client._agent_node_set("", ["test"])


# _tenant_email ──────────────────────────────────────────────────────────────


def test_tenant_email_uses_keiracom_local_convention(client):
    assert client._tenant_email("keiracom_platform") == "keiracom_platform@keiracom.local"


def test_tenant_email_rejects_empty_org(client):
    with pytest.raises(ValueError, match="org_id"):
        client._tenant_email("")


# _get_or_create_user ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_or_create_user_mints_when_missing(client, fake_cognee):
    user = await client._get_or_create_user("acme_co")
    fake_cognee.users.get_user_by_email.assert_awaited_once_with("acme_co@keiracom.local")
    fake_cognee.users.create_user.assert_awaited_once_with(
        email="acme_co@keiracom.local", tenant_id="acme_co", is_superuser=False
    )
    assert user.email == "acme_co@keiracom.local"
    assert user.tenant_id == "acme_co"


@pytest.mark.asyncio
async def test_get_or_create_user_reuses_existing_via_lookup(client, fake_cognee):
    existing = _make_user("acme_co@keiracom.local", tenant_id="acme_co")
    fake_cognee.users.get_user_by_email.return_value = existing

    user = await client._get_or_create_user("acme_co")
    fake_cognee.users.get_user_by_email.assert_awaited_once_with("acme_co@keiracom.local")
    fake_cognee.users.create_user.assert_not_awaited()
    assert user is existing


@pytest.mark.asyncio
async def test_get_or_create_user_caches_in_process(client, fake_cognee):
    user1 = await client._get_or_create_user("acme_co")
    user2 = await client._get_or_create_user("acme_co")
    assert user1 is user2
    # Lookup only on first call; cache serves the second.
    fake_cognee.users.get_user_by_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_user_distinct_per_org(client, fake_cognee):
    a = await client._get_or_create_user("acme_co")
    b = await client._get_or_create_user("bravo_inc")
    assert a is not b
    assert a.tenant_id == "acme_co"
    assert b.tenant_id == "bravo_inc"


# add ────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_passes_dataset_node_set_and_user(client, fake_cognee):
    result = await client.add(
        "hello",
        org_id="keiracom_platform",
        app_id="agency_os",
        agent_id="aiden",
        node_set=["test"],
    )
    fake_cognee.top.add.assert_awaited_once()
    _, kwargs = fake_cognee.top.add.call_args
    assert kwargs["dataset_name"] == "keiracom_platform__agency_os"
    assert kwargs["node_set"] == ["agent:aiden", "test"]
    assert kwargs["user"].email == "keiracom_platform@keiracom.local"
    assert kwargs["user"].tenant_id == "keiracom_platform"
    assert result == "add-result"


@pytest.mark.asyncio
async def test_add_handles_none_node_set(client, fake_cognee):
    await client.add("hello", org_id="o", app_id="a", agent_id="aiden")
    _, kwargs = fake_cognee.top.add.call_args
    assert kwargs["node_set"] == ["agent:aiden"]


@pytest.mark.asyncio
async def test_add_requires_agent_id(client):
    with pytest.raises(ValueError, match="agent_id"):
        await client.add("hello", org_id="o", app_id="a", agent_id="")


# cognify / memify ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cognify_delegates(client, fake_cognee):
    result = await client.cognify()
    fake_cognee.top.cognify.assert_awaited_once_with()
    assert result == "cognify-result"


@pytest.mark.asyncio
async def test_memify_delegates(client, fake_cognee):
    result = await client.memify()
    fake_cognee.top.memify.assert_awaited_once_with()
    assert result == "memify-result"


# search ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_passes_dataset_and_user_without_agent(client, fake_cognee):
    result = await client.search("what is X?", org_id="keiracom_platform", app_id="agency_os")
    _, kwargs = fake_cognee.top.search.call_args
    assert kwargs["datasets"] == ["keiracom_platform__agency_os"]
    assert kwargs["user"].tenant_id == "keiracom_platform"
    assert "node_set" not in kwargs
    assert result == ["search-result"]


@pytest.mark.asyncio
async def test_search_with_agent_id_scopes_to_node_set(client, fake_cognee):
    await client.search("what is X?", org_id="o", app_id="a", agent_id="aiden")
    _, kwargs = fake_cognee.top.search.call_args
    assert kwargs["node_set"] == ["agent:aiden"]
    assert kwargs["datasets"] == ["o__a"]
    assert kwargs["user"].tenant_id == "o"


# Cross-tenant isolation — Dave's Validation Query 4 ───────────────────────


@pytest.mark.asyncio
async def test_different_orgs_get_different_users(client, fake_cognee):
    """The architectural guarantee that closes Dave's Query 4 — distinct
    org_id values mint distinct Cognee Users (distinct owner_id + tenant_id),
    so cross-namespace search returns empty at the auth layer regardless of
    what dataset_name strings the caller supplies.
    """
    await client.add(
        "agency content", org_id="keiracom_platform", app_id="agency_os", agent_id="aiden"
    )
    await client.add("other content", org_id="other_org", app_id="other_app", agent_id="aiden")
    # 2 adds with different orgs → 2 distinct users passed to cognee.add
    add_users = [call.kwargs["user"] for call in fake_cognee.top.add.call_args_list]
    assert add_users[0] is not add_users[1]
    assert add_users[0].tenant_id == "keiracom_platform"
    assert add_users[1].tenant_id == "other_org"
