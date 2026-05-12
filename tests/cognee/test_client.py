"""Tests for src/cognee/client.py — mocked Cognee SDK, no live calls.

Per Phase 0 dispatch (Elliot ts 1778562982): tests mock the Cognee SDK so they
pass in CI before/regardless of cognee[fastembed] being pip-installed. Smoke
test against real Cognee runs separately as Phase 0 evidence items 2-3.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


# Inject a fake `cognee` module into sys.modules BEFORE importing client.py so
# the `import cognee` line in client.py picks up the mock. Real cognee SDK may
# not be installed in test environments.
@pytest.fixture(autouse=True)
def fake_cognee(monkeypatch):
    fake = SimpleNamespace(
        add=AsyncMock(return_value="add-result"),
        cognify=AsyncMock(return_value="cognify-result"),
        memify=AsyncMock(return_value="memify-result"),
        search=AsyncMock(return_value=["search-result"]),
    )
    monkeypatch.setitem(sys.modules, "cognee", fake)
    sys.modules.pop("src.cognee.client", None)
    sys.modules.pop("src.cognee", None)
    return fake


@pytest.fixture
def client(fake_cognee):
    from src.cognee import client as c

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


# add ────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_calls_sdk_with_dataset_and_node_set(client, fake_cognee):
    result = await client.add(
        "hello",
        org_id="keiracom_platform",
        app_id="agency_os",
        agent_id="aiden",
        node_set=["test"],
    )
    fake_cognee.add.assert_awaited_once_with(
        "hello",
        dataset_name="keiracom_platform__agency_os",
        node_set=["agent:aiden", "test"],
    )
    assert result == "add-result"


@pytest.mark.asyncio
async def test_add_handles_none_node_set(client, fake_cognee):
    await client.add(
        "hello",
        org_id="o",
        app_id="a",
        agent_id="aiden",
    )
    _, kwargs = fake_cognee.add.call_args
    assert kwargs["node_set"] == ["agent:aiden"]


@pytest.mark.asyncio
async def test_add_requires_agent_id(client):
    with pytest.raises(ValueError, match="agent_id"):
        await client.add("hello", org_id="o", app_id="a", agent_id="")


# cognify / memify ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cognify_delegates(client, fake_cognee):
    result = await client.cognify()
    fake_cognee.cognify.assert_awaited_once_with()
    assert result == "cognify-result"


@pytest.mark.asyncio
async def test_memify_delegates(client, fake_cognee):
    result = await client.memify()
    fake_cognee.memify.assert_awaited_once_with()
    assert result == "memify-result"


# search ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_without_agent_id_omits_node_set(client, fake_cognee):
    result = await client.search(
        "what is X?",
        org_id="keiracom_platform",
        app_id="agency_os",
    )
    fake_cognee.search.assert_awaited_once_with(
        "what is X?",
        datasets=["keiracom_platform__agency_os"],
    )
    assert result == ["search-result"]


@pytest.mark.asyncio
async def test_search_with_agent_id_scopes_to_node_set(client, fake_cognee):
    await client.search(
        "what is X?",
        org_id="o",
        app_id="a",
        agent_id="aiden",
    )
    _, kwargs = fake_cognee.search.call_args
    assert kwargs["node_set"] == ["agent:aiden"]
    assert kwargs["datasets"] == ["o__a"]
