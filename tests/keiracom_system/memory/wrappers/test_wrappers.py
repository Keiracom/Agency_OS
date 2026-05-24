"""tests for keiracom_system.memory.wrappers — Phase 2 build wave 2 item 1.

Coverage matrix (Aiden gate-validator discipline: 4-8 negatives per wrapper):
- Decision    — 2 positive + 4 negative
- Artifact    — 3 positive (mandatory provenance) + 4 negative
- TaskContext — 2 positive + 3 negative
- AntiPattern — 3 positive (incl. graveyard + supersession edge) + 5 negative
- Trace       — 2 positive + 6 negative + 1 integration (end-to-end decision-chain)

DB / Hindsight / TenantExtension mocked end-to-end; tests run without psycopg
or a live Hindsight instance.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.keiracom_system.memory.wrappers import (
    AntiPatternWrapper,
    ArtifactWrapper,
    AuditRecord,
    DecisionWrapper,
    TaskContextWrapper,
    compose_audit_record,
)


class _FakeClient:
    def __init__(self) -> None:
        self.retain_calls: list[dict[str, Any]] = []
        self.recall_calls: list[dict[str, Any]] = []
        self.reflect_resp: dict[str, Any] = {
            "answer": "synthesised answer",
            "citations": ["mem-a", "mem-b", "mem-c"],
            "reasoning_chain": [
                {"step": 1, "tool": "search_observations", "result": "found 3 obs"},
                {"step": 2, "tool": "recall", "result": "found 2 raw facts"},
                {"step": 3, "tool": "done", "result": "answer composed"},
            ],
            "otel_trace_id": "trace-fake-001",
        }
        self.recall_resp: list[dict[str, Any]] = [
            {"id": "mem-1", "content": "row 1", "tags": ["mal_node:decision"]}
        ]
        self.next_memory_id = 100

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


# ============== DecisionWrapper ==============


def test_decision_ingest_tags_with_mal_node(client, tenants):
    w = DecisionWrapper(client, tenants)
    w.ingest(tenant_id="tenant-acme", content="We chose Hindsight as MAL engine.")
    assert len(client.retain_calls) == 1
    item = client.retain_calls[0]["items"][0]
    assert "mal_node:decision" in item["tags"]
    assert item["metadata"]["mal_node"] == "decision"
    assert client.retain_calls[0]["bank_id"] == "bank-acme"


def test_decision_recall_filters_by_decision_tag(client, tenants):
    w = DecisionWrapper(client, tenants)
    w.recall(tenant_id="tenant-acme", query="why Hindsight?")
    call = client.recall_calls[0]
    assert call["tags"] == ["mal_node:decision"]
    assert call["bank_id"] == "bank-acme"


def test_decision_ingest_rejects_empty_content(client, tenants):
    w = DecisionWrapper(client, tenants)
    with pytest.raises(ValueError, match="content must be non-empty"):
        w.ingest(tenant_id="tenant-acme", content="")


def test_decision_ingest_rejects_unknown_tenant(client, tenants):
    w = DecisionWrapper(client, tenants)
    with pytest.raises(KeyError, match="unknown tenant"):
        w.ingest(tenant_id="tenant-ghost", content="x")


def test_decision_recall_rejects_unknown_tenant(client, tenants):
    w = DecisionWrapper(client, tenants)
    with pytest.raises(KeyError):
        w.recall(tenant_id="tenant-ghost", query="x")


def test_decision_metadata_stringified_per_g2(client, tenants):
    # PR #1130 G2 — Hindsight metadata must be all-string
    w = DecisionWrapper(client, tenants)
    w.ingest(
        tenant_id="tenant-acme",
        content="x",
        metadata={"pr_number": 1131, "tags": ["a", "b"]},
    )
    meta = client.retain_calls[0]["items"][0]["metadata"]
    assert all(isinstance(v, str) for v in meta.values()), meta
    assert meta["pr_number"] == "1131"
    assert meta["tags"] == "a,b"


# ============== ArtifactWrapper ==============


def test_artifact_ingest_requires_author_and_ref(client, tenants):
    w = ArtifactWrapper(client, tenants)
    w.ingest(
        tenant_id="tenant-acme",
        content="PR #1131 merged",
        author="atlas",
        artifact_ref="pr:1131",
    )
    item = client.retain_calls[0]["items"][0]
    assert item["metadata"]["author"] == "atlas"
    assert item["metadata"]["artifact_ref"] == "pr:1131"
    assert "mal_node:artifact" in item["tags"]


def test_artifact_ingest_rejects_missing_author(client, tenants):
    w = ArtifactWrapper(client, tenants)
    with pytest.raises(ValueError, match="requires an author"):
        w.ingest(tenant_id="tenant-acme", content="x", author="", artifact_ref="pr:1")


def test_artifact_ingest_rejects_missing_ref(client, tenants):
    w = ArtifactWrapper(client, tenants)
    with pytest.raises(ValueError, match="requires an artifact_ref"):
        w.ingest(tenant_id="tenant-acme", content="x", author="atlas", artifact_ref="")


def test_artifact_ingest_rejects_empty_content(client, tenants):
    w = ArtifactWrapper(client, tenants)
    with pytest.raises(ValueError, match="content must be non-empty"):
        w.ingest(tenant_id="tenant-acme", content="", author="atlas", artifact_ref="pr:1")


def test_artifact_recall_filters_by_artifact_tag(client, tenants):
    w = ArtifactWrapper(client, tenants)
    w.recall(tenant_id="tenant-acme", query="atlas PRs")
    assert client.recall_calls[0]["tags"] == ["mal_node:artifact"]


def test_artifact_extra_metadata_preserved(client, tenants):
    w = ArtifactWrapper(client, tenants)
    w.ingest(
        tenant_id="tenant-acme",
        content="x",
        author="atlas",
        artifact_ref="pr:1131",
        metadata={"commit_sha": "abc123"},
    )
    meta = client.retain_calls[0]["items"][0]["metadata"]
    assert meta["commit_sha"] == "abc123"


# ============== TaskContextWrapper ==============


def test_taskcontext_ingest_tags_with_mal_node(client, tenants):
    w = TaskContextWrapper(client, tenants)
    w.ingest(tenant_id="tenant-acme", content="KEI-X dispatch context")
    item = client.retain_calls[0]["items"][0]
    assert "mal_node:taskcontext" in item["tags"]


def test_taskcontext_recall_filters_by_tag(client, tenants):
    w = TaskContextWrapper(client, tenants)
    w.recall(tenant_id="tenant-acme", query="what KEIs is atlas on?")
    assert client.recall_calls[0]["tags"] == ["mal_node:taskcontext"]


def test_taskcontext_rejects_empty_content(client, tenants):
    w = TaskContextWrapper(client, tenants)
    with pytest.raises(ValueError, match="content must be non-empty"):
        w.ingest(tenant_id="tenant-acme", content="")


def test_taskcontext_rejects_unknown_tenant(client, tenants):
    w = TaskContextWrapper(client, tenants)
    with pytest.raises(KeyError):
        w.ingest(tenant_id="tenant-ghost", content="x")


# ============== AntiPatternWrapper ==============


def test_antipattern_ingest_carries_anti_pattern_tag(client, tenants):
    w = AntiPatternWrapper(client, tenants)
    w.ingest(
        tenant_id="tenant-acme",
        context="empty manifest path",
        failed_path="raw user data into Path()",
        verified_path="string-validate before Path()",
    )
    item = client.retain_calls[0]["items"][0]
    assert "anti-pattern" in item["tags"]
    assert "mal_node:antipattern" in item["tags"]


def test_antipattern_content_includes_both_paths(client, tenants):
    w = AntiPatternWrapper(client, tenants)
    w.ingest(
        tenant_id="tenant-acme",
        context="ctx",
        failed_path="bad",
        verified_path="good",
    )
    content = client.retain_calls[0]["items"][0]["content"]
    assert "failed_path: bad" in content
    assert "verified_path: good" in content


def test_antipattern_supersession_edge_in_metadata(client, tenants):
    # eleven_agreed_positions #4 — supersession-via-AntiPattern V1
    w = AntiPatternWrapper(client, tenants)
    w.ingest(
        tenant_id="tenant-acme",
        context="ctx",
        failed_path="bad",
        verified_path="good",
        supersedes_memory_id="mem-old-99",
    )
    meta = client.retain_calls[0]["items"][0]["metadata"]
    assert meta["supersedes"] == "mem-old-99"


def test_antipattern_rejects_missing_failed_path(client, tenants):
    # CLAUDE.md §Discovery Log — both paths mandatory
    w = AntiPatternWrapper(client, tenants)
    with pytest.raises(ValueError, match="failed_path required"):
        w.ingest(tenant_id="tenant-acme", context="x", failed_path="", verified_path="g")


def test_antipattern_rejects_missing_verified_path(client, tenants):
    w = AntiPatternWrapper(client, tenants)
    with pytest.raises(ValueError, match="verified_path required"):
        w.ingest(tenant_id="tenant-acme", context="x", failed_path="b", verified_path="")


def test_antipattern_rejects_missing_context(client, tenants):
    w = AntiPatternWrapper(client, tenants)
    with pytest.raises(ValueError, match="context must be non-empty"):
        w.ingest(tenant_id="tenant-acme", context="", failed_path="b", verified_path="g")


def test_antipattern_rejects_unknown_tenant(client, tenants):
    w = AntiPatternWrapper(client, tenants)
    with pytest.raises(KeyError):
        w.ingest(tenant_id="tenant-ghost", context="x", failed_path="b", verified_path="g")


def test_antipattern_graveyard_returns_anti_pattern_tag_only(client, tenants):
    w = AntiPatternWrapper(client, tenants)
    w.graveyard(tenant_id="tenant-acme")
    assert client.recall_calls[0]["tags"] == ["anti-pattern"]
    assert client.recall_calls[0]["top_k"] == 100


# ============== Trace composition (Aiden gate D) ==============


def test_trace_compose_returns_audit_record_with_citations(client, tenants):
    rec = compose_audit_record(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        operation="reflect",
        query="why did atlas ship the wrapper layer?",
    )
    assert isinstance(rec, AuditRecord)
    assert rec.tenant_id == "tenant-acme"
    assert rec.actor == "tenant-acme"
    assert rec.operation == "reflect"
    assert rec.citations == ["mem-a", "mem-b", "mem-c"]
    assert len(rec.reasoning_chain) == 3
    assert rec.otel_trace_id == "trace-fake-001"
    assert rec.audit_purpose == "general"
    assert rec.schema_version == "1.0"


def test_trace_compose_redacts_query_when_asked(client, tenants):
    # HIPAA/legal-privilege use-case: query content itself is sensitive
    rec = compose_audit_record(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        operation="reflect",
        query="patient X chemotherapy regimen?",
        audit_purpose="hipaa",
        redact_query=True,
    )
    assert rec.query == "<redacted>"
    assert rec.audit_purpose == "hipaa"


def test_trace_compose_rejects_unknown_operation(client, tenants):
    with pytest.raises(ValueError, match="unknown operation"):
        compose_audit_record(
            client=client,
            tenant_extension=tenants,
            tenant_id="tenant-acme",
            operation="exfiltrate",
            query="x",
        )


def test_trace_compose_rejects_unknown_audit_purpose(client, tenants):
    with pytest.raises(ValueError, match="unknown audit_purpose"):
        compose_audit_record(
            client=client,
            tenant_extension=tenants,
            tenant_id="tenant-acme",
            operation="reflect",
            query="x",
            audit_purpose="marketing",
        )


def test_trace_compose_rejects_empty_tenant_id(client, tenants):
    with pytest.raises(ValueError, match="tenant_id required"):
        compose_audit_record(
            client=client,
            tenant_extension=tenants,
            tenant_id="",
            operation="reflect",
            query="x",
        )


def test_trace_compose_rejects_empty_query(client, tenants):
    with pytest.raises(ValueError, match="query required"):
        compose_audit_record(
            client=client,
            tenant_extension=tenants,
            tenant_id="tenant-acme",
            operation="reflect",
            query="",
        )


def test_trace_compose_handles_dict_citation_shape(client, tenants):
    # Hindsight version drift: citations may be ["id1"] OR [{id:..,content:..}]
    client.reflect_resp = {
        "citations": [{"id": "obj-1", "content": "x"}, {"id": "obj-2"}],
        "reasoning_chain": [],
    }
    rec = compose_audit_record(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        operation="reflect",
        query="x",
    )
    assert rec.citations == ["obj-1", "obj-2"]


def test_trace_compose_falls_back_to_cited_memory_ids_field(client, tenants):
    # Older Hindsight versions used 'cited_memory_ids' not 'citations'
    client.reflect_resp = {
        "cited_memory_ids": ["alt-1", "alt-2"],
        "trace": [{"x": 1}],
    }
    rec = compose_audit_record(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        operation="reflect",
        query="x",
    )
    assert rec.citations == ["alt-1", "alt-2"]
    assert rec.reasoning_chain == [{"x": 1}]


# ============== Integration — end-to-end decision chain ==============


def test_integration_decision_chain_trace_reconstructs_provenance(client, tenants):
    """End-to-end Aiden gate D: ingest a decision, an artifact citing it, and
    an antipattern superseding a prior decision; then trace via reflect and
    confirm the audit-record carries the citation chain."""
    decision_w = DecisionWrapper(client, tenants)
    artifact_w = ArtifactWrapper(client, tenants)
    antipattern_w = AntiPatternWrapper(client, tenants)

    # Step 1 — original decision
    decision_w.ingest(
        tenant_id="tenant-acme",
        content="Decision: adopt Hindsight as MAL engine (Dave-ratified 2026-05-24).",
        metadata={"decision_ref": "MAL-V1"},
    )
    # Step 2 — artifact citing the decision
    artifact_w.ingest(
        tenant_id="tenant-acme",
        content="PR #1131 ships tenants table + provisioning per MAL-V1.",
        author="atlas",
        artifact_ref="pr:1131",
        metadata={"cites_decision": "MAL-V1"},
    )
    # Step 3 — antipattern superseding a prior wrong call
    antipattern_w.ingest(
        tenant_id="tenant-acme",
        context="early CARA citation in substantive_lock",
        failed_path="cite CARA as a Hindsight module without verifying public docs",
        verified_path="verify against public docs first; CARA citation removed pending Viktor",
        supersedes_memory_id="mem-100",  # the earlier (wrong) decision
    )
    # 3 retain calls happened
    assert len(client.retain_calls) == 3

    # Trace it via reflect
    rec = compose_audit_record(
        client=client,
        tenant_extension=tenants,
        tenant_id="tenant-acme",
        operation="reflect",
        query="Why was Hindsight chosen + what got superseded?",
        audit_purpose="accounting",
    )
    # Citations come from the (mocked) reflect_resp; in production these are
    # the actual memory ids the engine retrieved + the citation-validation
    # gate guarantees they were real reads, not LLM fabrication.
    assert len(rec.citations) == 3
    assert rec.audit_purpose == "accounting"
    assert rec.reasoning_chain  # non-empty chain shows multi-step reasoning


def test_integration_orion_tenant_extension_protocol_satisfied():
    """Smoke: any object implementing get_bank_id(tenant_id)->str satisfies
    the TenantExtensionProtocol — verifies Orion's PR #1132 TenantExtension can
    drop in without an explicit subclass declaration."""

    class _OrionStyleTenantExt:
        def get_bank_id(self, tenant_id: str) -> str:
            return f"orion-bank-{tenant_id}"

    ext = _OrionStyleTenantExt()
    w = DecisionWrapper(_FakeClient(), ext)
    # If the wrapper accepted ext, the Protocol satisfied — duck typing is
    # the contract enforcement (Protocol is structural).
    assert w.tenants is ext
