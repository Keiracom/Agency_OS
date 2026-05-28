"""tests for keiracom_system.memory.wrappers.primitives — YELLOW-3 audit fix.

Coverage matrix (Aiden gate-validator discipline: >=4 negatives per primitive):
- synthesize       — 3 positive + 5 negative
- trace            — 3 positive + 4 negative
- complete_delete  — 2 positive + 6 negative
- integration      — 1 end-to-end (ingest -> supersede -> trace -> delete)

DB / Hindsight / TenantExtension mocked end-to-end; no live engine required.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.keiracom_system.memory.wrappers import (
    AntiPatternWrapper,
    DecisionWrapper,
    DeleteRecord,
    ProvenanceChain,
    SynthesisResult,
    complete_delete,
    synthesize,
    trace,
)


class _FakeClient:
    def __init__(self) -> None:
        self.retain_calls: list[dict[str, Any]] = []
        self.recall_calls: list[dict[str, Any]] = []
        self.delete_calls: list[dict[str, Any]] = []
        self.reflect_resp: dict[str, Any] = {
            "answer": "Hindsight was chosen because the spike showed favourable fit.",
            "citations": ["mem-100", "mem-101", "mem-102"],
            "reasoning_chain": [
                {"step": 1, "tool": "search_observations", "result": "found 3 obs"},
                {"step": 2, "tool": "done", "result": "answer composed"},
            ],
            "otel_trace_id": "trace-fake-001",
        }
        self.recall_resp: list[dict[str, Any]] = []
        self.delete_resp: dict[str, Any] = {"ok": True, "otel_trace_id": "trace-del-001"}
        self.next_memory_id = 200

    def retain(self, *, bank_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        self.retain_calls.append({"bank_id": bank_id, "items": items})
        ids = [f"mem-{self.next_memory_id + i}" for i, _ in enumerate(items)]
        self.next_memory_id += len(items)
        return {"ok": True, "memory_ids": ids}

    def recall(
        self, *, bank_id: str, query: str, tags: list[str] | None = None, top_k: int = 5
    ) -> list[dict[str, Any]]:
        self.recall_calls.append({"bank_id": bank_id, "query": query, "tags": tags, "top_k": top_k})
        return list(self.recall_resp)

    def reflect(self, *, bank_id: str, query: str) -> dict[str, Any]:
        return dict(self.reflect_resp)

    def delete(self, *, bank_id: str, memory_id: str) -> dict[str, Any]:
        self.delete_calls.append({"bank_id": bank_id, "memory_id": memory_id})
        return dict(self.delete_resp)


class _FakeTenants:
    def __init__(self, bank_map: dict[str, str] | None = None) -> None:
        self.bank_map = bank_map or {"tenant-acme": "bank-acme"}

    def get_bank_id(self, tenant_id: str) -> str:
        if tenant_id not in self.bank_map:
            raise KeyError(f"unknown tenant {tenant_id}")
        return self.bank_map[tenant_id]


@pytest.fixture
def client():
    return _FakeClient()


@pytest.fixture
def tenants():
    return _FakeTenants()


# ============== synthesize ==============


def test_synthesize_returns_source_atom_pointers(client, tenants):
    rec = synthesize(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        query="Why was Hindsight chosen?",
    )
    assert isinstance(rec, SynthesisResult)
    assert rec.source_atom_ids == ["mem-100", "mem-101", "mem-102"]
    assert rec.synthesized_answer.startswith("Hindsight was chosen")
    assert rec.otel_trace_id == "trace-fake-001"
    assert rec.schema_version == "1.0"


def test_synthesize_handles_dict_citation_shape(client, tenants):
    # Hindsight version drift: citations may be objects with id+content.
    client.reflect_resp = {
        "answer": "x",
        "citations": [{"id": "obj-1", "content": "a"}, {"id": "obj-2"}],
        "reasoning_chain": [],
    }
    rec = synthesize(client=client, tenant_extension=tenants, tenant_id="tenant-acme", query="x?")
    assert rec.source_atom_ids == ["obj-1", "obj-2"]


def test_synthesize_falls_back_to_cited_memory_ids_field(client, tenants):
    # Older Hindsight versions used 'cited_memory_ids' not 'citations'.
    client.reflect_resp = {
        "synthesised_answer": "alt-answer",
        "cited_memory_ids": ["alt-1", "alt-2"],
        "trace": [{"x": 1}],
    }
    rec = synthesize(client=client, tenant_extension=tenants, tenant_id="tenant-acme", query="x?")
    assert rec.source_atom_ids == ["alt-1", "alt-2"]
    assert rec.synthesized_answer == "alt-answer"
    assert rec.reasoning_chain == [{"x": 1}]


def test_synthesize_rejects_zero_citations_aiden_drift_guard(client, tenants):
    # Aiden Phase-2 mitigation: zero citations = synthesis drift = FAIL.
    client.reflect_resp = {"answer": "floating answer", "citations": []}
    with pytest.raises(ValueError, match="zero source-atom pointers"):
        synthesize(client=client, tenant_extension=tenants, tenant_id="tenant-acme", query="x?")


def test_synthesize_rejects_empty_tenant_id(client, tenants):
    with pytest.raises(ValueError, match="tenant_id required"):
        synthesize(client=client, tenant_extension=tenants, tenant_id="", query="x?")


def test_synthesize_rejects_empty_query(client, tenants):
    with pytest.raises(ValueError, match="query required"):
        synthesize(client=client, tenant_extension=tenants, tenant_id="tenant-acme", query="")


def test_synthesize_rejects_unknown_tenant(client, tenants):
    with pytest.raises(KeyError, match="unknown tenant"):
        synthesize(client=client, tenant_extension=tenants, tenant_id="tenant-ghost", query="x?")


def test_synthesize_filters_empty_citation_ids(client, tenants):
    # Defensive: a citation object with no id field must not produce empty
    # string source-atom IDs (would defeat the drift guard).
    client.reflect_resp = {
        "answer": "x",
        "citations": [{"id": "ok-1"}, {"content": "no-id"}, ""],
        "reasoning_chain": [],
    }
    rec = synthesize(client=client, tenant_extension=tenants, tenant_id="tenant-acme", query="x?")
    assert rec.source_atom_ids == ["ok-1"]


# ============== trace ==============


def test_trace_returns_provenance_chain_with_supersedes_edge(client, tenants):
    # Setup: target memory mem-A is superseded by mem-B (AntiPattern with
    # metadata.supersedes=mem-A).
    client.recall_resp = [
        {
            "id": "mem-A",
            "content": "original decision",
            "metadata": {
                "author": "atlas",
                "timestamp": "2026-05-20T10:00:00Z",
                "mal_node": "decision",
            },
        },
        {
            "id": "mem-B",
            "content": "antipattern superseding mem-A",
            "metadata": {
                "author": "scout",
                "timestamp": "2026-05-27T12:00:00Z",
                "supersedes": "mem-A",
                "mal_node": "antipattern",
            },
        },
    ]
    chain = trace(
        client=client, tenant_extension=tenants, tenant_id="tenant-acme", memory_id="mem-A"
    )
    assert isinstance(chain, ProvenanceChain)
    assert chain.target_memory_id == "mem-A"
    assert chain.tenant_id == "tenant-acme"
    assert chain.superseded_by == ["mem-B"]
    assert chain.supersedes == []
    assert len(chain.events) == 2
    # Events ordered oldest -> newest
    assert chain.events[0].event_type == "ingest"
    assert chain.events[0].memory_id == "mem-A"
    assert chain.events[0].actor == "atlas"
    assert chain.events[1].event_type == "supersede"
    assert chain.events[1].memory_id == "mem-B"


def test_trace_captures_outbound_supersedes_on_self(client, tenants):
    # If the target itself supersedes an earlier memory, that edge appears
    # in chain.supersedes.
    client.recall_resp = [
        {
            "id": "mem-A",
            "metadata": {
                "author": "scout",
                "timestamp": "2026-05-27T11:00:00Z",
                "supersedes": "mem-OLD",
            },
        }
    ]
    chain = trace(
        client=client, tenant_extension=tenants, tenant_id="tenant-acme", memory_id="mem-A"
    )
    assert chain.supersedes == ["mem-OLD"]
    assert chain.superseded_by == []


def test_trace_returns_empty_chain_when_no_related_memories(client, tenants):
    client.recall_resp = []
    chain = trace(
        client=client, tenant_extension=tenants, tenant_id="tenant-acme", memory_id="mem-X"
    )
    assert chain.target_memory_id == "mem-X"
    assert chain.events == []
    assert chain.supersedes == []
    assert chain.superseded_by == []


def test_trace_rejects_empty_tenant_id(client, tenants):
    with pytest.raises(ValueError, match="tenant_id required"):
        trace(client=client, tenant_extension=tenants, tenant_id="", memory_id="mem-A")


def test_trace_rejects_empty_memory_id(client, tenants):
    with pytest.raises(ValueError, match="memory_id required"):
        trace(client=client, tenant_extension=tenants, tenant_id="tenant-acme", memory_id="")


def test_trace_rejects_unknown_tenant(client, tenants):
    with pytest.raises(KeyError):
        trace(
            client=client,
            tenant_extension=tenants,
            tenant_id="tenant-ghost",
            memory_id="mem-A",
        )


def test_trace_skips_malformed_rows_without_id(client, tenants):
    # Defensive: rows without an id field must be ignored, not crash.
    client.recall_resp = [
        {"content": "no id here"},
        {"id": "mem-A", "metadata": {"author": "atlas", "timestamp": "2026-05-20T10:00:00Z"}},
    ]
    chain = trace(
        client=client, tenant_extension=tenants, tenant_id="tenant-acme", memory_id="mem-A"
    )
    assert len(chain.events) == 1
    assert chain.events[0].memory_id == "mem-A"


# ============== complete_delete ==============


def test_complete_delete_calls_engine_and_returns_record(client, tenants):
    rec = complete_delete(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        memory_id="mem-X",
        actor="scout",
        reason="GDPR right-to-be-forgotten request",
    )
    assert isinstance(rec, DeleteRecord)
    assert rec.memory_id == "mem-X"
    assert rec.tenant_id == "tenant-acme"
    assert rec.actor == "scout"
    assert rec.reason == "GDPR right-to-be-forgotten request"
    assert rec.audit_purpose == "general"
    assert rec.otel_trace_id == "trace-del-001"
    assert rec.schema_version == "1.0"
    assert len(client.delete_calls) == 1
    assert client.delete_calls[0] == {"bank_id": "bank-acme", "memory_id": "mem-X"}


def test_complete_delete_carries_audit_purpose_hipaa(client, tenants):
    rec = complete_delete(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        memory_id="mem-PHI",
        actor="scout",
        reason="PHI scrub per HIPAA breach response",
        audit_purpose="hipaa",
    )
    assert rec.audit_purpose == "hipaa"


def test_complete_delete_rejects_empty_tenant(client, tenants):
    with pytest.raises(ValueError, match="tenant_id required"):
        complete_delete(
            client=client,
            tenant_extension=tenants,
            tenant_id="",
            memory_id="mem-X",
            actor="scout",
            reason="r",
        )


def test_complete_delete_rejects_empty_memory_id(client, tenants):
    with pytest.raises(ValueError, match="memory_id required"):
        complete_delete(
            client=client,
            tenant_extension=tenants,
            tenant_id="tenant-acme",
            memory_id="",
            actor="scout",
            reason="r",
        )


def test_complete_delete_rejects_empty_actor_audit_invariant(client, tenants):
    # Audit-trail invariant: a delete with no actor is forbidden.
    with pytest.raises(ValueError, match="actor required"):
        complete_delete(
            client=client,
            tenant_extension=tenants,
            tenant_id="tenant-acme",
            memory_id="mem-X",
            actor="",
            reason="r",
        )


def test_complete_delete_rejects_empty_reason_audit_invariant(client, tenants):
    # Audit-trail invariant: a delete with no reason is forbidden.
    with pytest.raises(ValueError, match="reason required"):
        complete_delete(
            client=client,
            tenant_extension=tenants,
            tenant_id="tenant-acme",
            memory_id="mem-X",
            actor="scout",
            reason="",
        )


def test_complete_delete_rejects_unknown_audit_purpose(client, tenants):
    with pytest.raises(ValueError, match="unknown audit_purpose"):
        complete_delete(
            client=client,
            tenant_extension=tenants,
            tenant_id="tenant-acme",
            memory_id="mem-X",
            actor="scout",
            reason="r",
            audit_purpose="marketing",
        )


def test_complete_delete_rejects_unknown_tenant(client, tenants):
    with pytest.raises(KeyError):
        complete_delete(
            client=client,
            tenant_extension=tenants,
            tenant_id="tenant-ghost",
            memory_id="mem-X",
            actor="scout",
            reason="r",
        )


def test_complete_delete_synthesises_trace_id_when_engine_omits_it(client, tenants):
    # If the engine returns no otel_trace_id, complete_delete must still
    # produce one so the audit log row has a non-empty correlator.
    client.delete_resp = {"ok": True}
    rec = complete_delete(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        memory_id="mem-X",
        actor="scout",
        reason="r",
    )
    assert rec.otel_trace_id  # non-empty (uuid-generated fallback)


# ============== integration ==============


def test_integration_ingest_supersede_trace_delete_chain(client, tenants):
    """End-to-end: ingest a decision, write an antipattern that supersedes
    it, trace the provenance chain, then hard-delete the original."""
    decision_w = DecisionWrapper(client, tenants)
    antipattern_w = AntiPatternWrapper(client, tenants)

    decision_w.ingest(
        tenant_id="tenant-acme",
        content="Decision: pick X.",
        metadata={"decision_ref": "DEC-1"},
    )
    target_id = client.retain_calls[0]["items"][0]
    target_mem_id = "mem-200"  # first id from _FakeClient seed
    # Note: real ID comes from retain response; we use the fake-seed value
    # here. The wrapper layer returns it to callers in practice.
    assert target_id["metadata"]["decision_ref"] == "DEC-1"

    antipattern_w.ingest(
        tenant_id="tenant-acme",
        context="X was wrong",
        failed_path="picked X under bad assumption",
        verified_path="pick Y instead — backed by spike data",
        supersedes_memory_id=target_mem_id,
    )

    # Set up recall response so trace finds the supersession edge.
    client.recall_resp = [
        {
            "id": target_mem_id,
            "metadata": {"author": "scout", "timestamp": "2026-05-27T10:00:00Z"},
        },
        {
            "id": "mem-201",
            "metadata": {
                "author": "scout",
                "timestamp": "2026-05-27T11:00:00Z",
                "supersedes": target_mem_id,
            },
        },
    ]
    chain = trace(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        memory_id=target_mem_id,
    )
    assert chain.superseded_by == ["mem-201"]
    assert len(chain.events) == 2

    # Hard-delete the original now that supersession is in place.
    rec = complete_delete(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        memory_id=target_mem_id,
        actor="scout",
        reason="superseded — operator-requested hard-delete",
        audit_purpose="accounting",
    )
    assert rec.memory_id == target_mem_id
    assert rec.audit_purpose == "accounting"
    assert len(client.delete_calls) == 1
    assert client.delete_calls[0]["memory_id"] == target_mem_id
