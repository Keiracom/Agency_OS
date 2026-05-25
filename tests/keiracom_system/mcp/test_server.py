"""MCPServer tests — dispatch + tier gating + dual-backend parity (Aiden Gate E).

Two clients exercised against the same MCPServer surface:
- _HindsightFakeClient — mimics a real Hindsight HTTP client shape
- _NoOpClient          — records calls but returns canned shapes; proves
                         agent integration works against ANY backend that
                         implements the wrapper Protocols (Gate E).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.keiracom_system.mcp import (
    ALL_TOOLS,
    TOOL_DELETE,
    TOOL_INGEST,
    TOOL_RECALL,
    TOOL_SUPERSEDE,
    TOOL_SYNTHESIZE,
    TOOL_TRACE,
    MCPServer,
    TierGateError,
    ToolInvocationError,
)


class _HindsightFakeClient:
    """Records calls; returns ids/shapes mimicking Hindsight HTTP responses."""

    backend_id = "hindsight"

    def __init__(self) -> None:
        self.retain_calls: list[dict[str, Any]] = []
        self.recall_calls: list[dict[str, Any]] = []
        self.consolidate_calls: list[str] = []
        self.delete_calls: list[tuple[str, str]] = []
        self.reflect_calls: list[dict[str, Any]] = []

    def retain(self, *, bank_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        self.retain_calls.append({"bank_id": bank_id, "items": items})
        return {"ok": True, "memory_ids": [f"hs-mem-{i}" for i, _ in enumerate(items)]}

    def recall(
        self, *, bank_id: str, query: str, tags: list[str] | None = None, top_k: int = 5
    ) -> list[dict[str, Any]]:
        self.recall_calls.append({"bank_id": bank_id, "query": query, "tags": tags, "top_k": top_k})
        return [{"id": "hs-mem-r1", "content": "fake recall result"}]

    def reflect(self, *, bank_id: str, query: str) -> dict[str, Any]:
        self.reflect_calls.append({"bank_id": bank_id, "query": query})
        return {"citations": ["hs-cite-1"], "reasoning_chain": [], "otel_trace_id": "hs-trace-1"}

    def consolidate(self, *, bank_id: str) -> dict[str, Any]:
        self.consolidate_calls.append(bank_id)
        return {"ok": True, "processed": 5}

    def delete_memory(self, *, bank_id: str, memory_id: str) -> dict[str, Any]:
        self.delete_calls.append((bank_id, memory_id))
        return {"ok": True, "deleted": memory_id}


class _NoOpClient:
    """Aiden Gate E dual-backend proof — agents see the same six tools whether
    the underlying engine is Hindsight or this stub. Records calls; returns
    deterministic canned shapes."""

    backend_id = "noop"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def retain(self, *, bank_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        self.calls.append("retain")
        return {"ok": True, "memory_ids": [f"noop-mem-{i}" for i, _ in enumerate(items)]}

    def recall(
        self, *, bank_id: str, query: str, tags: list[str] | None = None, top_k: int = 5
    ) -> list[dict[str, Any]]:
        self.calls.append("recall")
        return [{"id": "noop-r1", "content": ""}]

    def reflect(self, *, bank_id: str, query: str) -> dict[str, Any]:
        self.calls.append("reflect")
        return {"citations": [], "reasoning_chain": [], "otel_trace_id": "noop-trace"}

    def consolidate(self, *, bank_id: str) -> dict[str, Any]:
        self.calls.append("consolidate")
        return {"ok": True, "processed": 0}

    def delete_memory(self, *, bank_id: str, memory_id: str) -> dict[str, Any]:
        self.calls.append("delete")
        return {"ok": True, "deleted": memory_id}


class _FakeTenants:
    def get_bank_id(self, tenant_id: str) -> str:
        return f"bank-{tenant_id}"


class _FakeTierLookup:
    def __init__(self, tier_by_tenant: dict[str, str]) -> None:
        self.tier_by_tenant = tier_by_tenant

    def get_tier(self, tenant_id: str) -> str:
        if tenant_id not in self.tier_by_tenant:
            raise KeyError(f"unknown tenant {tenant_id}")
        return self.tier_by_tenant[tenant_id]


@pytest.fixture
def hs_client():
    return _HindsightFakeClient()


@pytest.fixture
def noop_client():
    return _NoOpClient()


@pytest.fixture
def tenants():
    return _FakeTenants()


@pytest.fixture
def tier_lookup():
    return _FakeTierLookup({"tenant-solo": "solo", "tenant-pro": "pro", "tenant-scale": "scale"})


@pytest.fixture
def server(hs_client, tenants, tier_lookup):
    return MCPServer(client=hs_client, tenant_extension=tenants, tier_lookup=tier_lookup)


# ============== list_tools — per-tier surface visibility ==============


def test_list_tools_solo_returns_two_tools(server):
    assert set(server.list_tools("tenant-solo")) == {TOOL_INGEST, TOOL_RECALL}


def test_list_tools_pro_returns_four_tools(server):
    assert set(server.list_tools("tenant-pro")) == {
        TOOL_INGEST,
        TOOL_RECALL,
        TOOL_SYNTHESIZE,
        TOOL_SUPERSEDE,
    }


def test_list_tools_scale_returns_all_six(server):
    assert set(server.list_tools("tenant-scale")) == set(ALL_TOOLS)


# ============== invoke — tier gating ==============


def test_invoke_rejects_empty_tenant_id(server):
    with pytest.raises(ToolInvocationError, match="tenant_id required"):
        server.invoke(tool_name=TOOL_INGEST, tenant_id="")


def test_invoke_rejects_unknown_tool(server):
    with pytest.raises(ToolInvocationError, match="unknown tool"):
        server.invoke(tool_name="exfiltrate", tenant_id="tenant-solo")


def test_invoke_solo_blocked_from_trace(server):
    with pytest.raises(TierGateError, match="tier 'solo'"):
        server.invoke(
            tool_name=TOOL_TRACE,
            tenant_id="tenant-solo",
            operation="reflect",
            query="x",
        )


def test_invoke_pro_blocked_from_delete(server):
    with pytest.raises(TierGateError, match="tier 'pro'"):
        server.invoke(tool_name=TOOL_DELETE, tenant_id="tenant-pro", memory_id="x")


def test_invoke_solo_blocked_from_synthesize(server):
    with pytest.raises(TierGateError, match="tier 'solo'"):
        server.invoke(tool_name=TOOL_SYNTHESIZE, tenant_id="tenant-solo")


# ============== invoke — dispatch round-trips against Hindsight client ==============


def test_invoke_ingest_decision_routes_to_decision_wrapper(server, hs_client):
    result = server.invoke(
        tool_name=TOOL_INGEST,
        tenant_id="tenant-solo",
        node_type="decision",
        content="Decision: adopt Hindsight engine.",
    )
    assert result["ok"] is True
    assert len(hs_client.retain_calls) == 1
    assert "mal_node:decision" in hs_client.retain_calls[0]["items"][0]["tags"]


def test_invoke_recall_routes_correctly(server, hs_client):
    out = server.invoke(
        tool_name=TOOL_RECALL,
        tenant_id="tenant-solo",
        query="why Hindsight?",
        node_type="decision",
    )
    assert hs_client.recall_calls[0]["tags"] == ["mal_node:decision"]
    assert isinstance(out, list)


def test_invoke_synthesize_pro_calls_consolidate(server, hs_client):
    out = server.invoke(tool_name=TOOL_SYNTHESIZE, tenant_id="tenant-pro")
    assert hs_client.consolidate_calls == ["bank-tenant-pro"]
    assert out["ok"] is True


def test_invoke_supersede_pro_routes_to_antipattern_wrapper(server, hs_client):
    server.invoke(
        tool_name=TOOL_SUPERSEDE,
        tenant_id="tenant-pro",
        superseded_memory_id="mem-old-99",
        context="prior decision was wrong",
        failed_path="bad approach",
        verified_path="good approach",
    )
    item = hs_client.retain_calls[0]["items"][0]
    assert "anti-pattern" in item["tags"]
    assert item["metadata"]["supersedes"] == "mem-old-99"


def test_invoke_trace_scale_produces_audit_record(server, hs_client):
    rec = server.invoke(
        tool_name=TOOL_TRACE,
        tenant_id="tenant-scale",
        operation="reflect",
        query="why was X decided?",
        audit_purpose="accounting",
    )
    assert rec.tenant_id == "tenant-scale"
    assert rec.audit_purpose == "accounting"
    assert rec.citations == ["hs-cite-1"]


def test_invoke_delete_scale_routes_to_delete_memory(server, hs_client):
    out = server.invoke(
        tool_name=TOOL_DELETE,
        tenant_id="tenant-scale",
        memory_id="mem-99",
    )
    assert hs_client.delete_calls == [("bank-tenant-scale", "mem-99")]
    assert out["deleted"] == "mem-99"


# ============== Aiden Gate E — dual-backend parity ==============


def test_gate_e_dual_backend_parity_ingest_works_against_noop(noop_client, tenants, tier_lookup):
    """Same MCPServer.invoke surface works against NoOp client identically —
    the Gate E proof that agent integration is backend-swappable. If this
    test ever fails, the wrappers leaked a Hindsight-specific assumption."""
    server = MCPServer(client=noop_client, tenant_extension=tenants, tier_lookup=tier_lookup)
    out = server.invoke(
        tool_name=TOOL_INGEST,
        tenant_id="tenant-solo",
        node_type="decision",
        content="test",
    )
    assert out["ok"] is True
    assert "retain" in noop_client.calls


def test_gate_e_dual_backend_parity_full_tool_surface_works_against_noop(
    noop_client, tenants, tier_lookup
):
    """Exercise every tier-allowed tool against NoOp. Surface parity = no
    operation ever hardcodes an engine-specific path."""
    server = MCPServer(client=noop_client, tenant_extension=tenants, tier_lookup=tier_lookup)
    server.invoke(
        tool_name=TOOL_INGEST,
        tenant_id="tenant-scale",
        node_type="decision",
        content="x",
    )
    server.invoke(
        tool_name=TOOL_RECALL,
        tenant_id="tenant-scale",
        query="x",
        node_type="decision",
    )
    server.invoke(tool_name=TOOL_SYNTHESIZE, tenant_id="tenant-scale")
    server.invoke(
        tool_name=TOOL_SUPERSEDE,
        tenant_id="tenant-scale",
        superseded_memory_id="m-old",
        context="c",
        failed_path="f",
        verified_path="v",
    )
    server.invoke(
        tool_name=TOOL_TRACE,
        tenant_id="tenant-scale",
        operation="reflect",
        query="x",
    )
    server.invoke(
        tool_name=TOOL_DELETE,
        tenant_id="tenant-scale",
        memory_id="m-99",
    )
    # Each call routed correctly to the NoOp backend
    assert noop_client.calls == [
        "retain",
        "recall",
        "consolidate",
        "retain",
        "reflect",
        "delete",
    ]


def test_gate_e_tier_gating_applies_regardless_of_backend(noop_client, tenants, tier_lookup):
    """Tier gates fire BEFORE the backend dispatch — proves the tier_router
    is engine-agnostic policy, not Hindsight-specific."""
    server = MCPServer(client=noop_client, tenant_extension=tenants, tier_lookup=tier_lookup)
    with pytest.raises(TierGateError):
        server.invoke(tool_name=TOOL_DELETE, tenant_id="tenant-pro", memory_id="x")
    # NoOp never received the call — gate intercepted upstream
    assert "delete" not in noop_client.calls
