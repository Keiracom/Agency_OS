"""artifact_wrapper.py — Artifact → Hindsight Experience.

DIRECT mapping per PR #1129 spike item vi: Hindsight infers `experience` fact
type for content describing events (PRs merged, commits, docs published).
The wrapper carries the actor + temporal context the Trace primitive consumes.
"""

from __future__ import annotations

from typing import Any

from ._base import HindsightClient, TenantExtensionProtocol, stringify_metadata

_TAGS = ["mal_node:artifact"]


class ArtifactWrapper:
    def __init__(self, client: HindsightClient, tenant_extension: TenantExtensionProtocol) -> None:
        self.client = client
        self.tenants = tenant_extension

    def ingest(
        self,
        *,
        tenant_id: str,
        content: str,
        author: str,
        artifact_ref: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Author + artifact_ref are mandatory because the Trace primitive needs them
        # to reconstruct provenance — surfaced as a wrapper-level invariant rather
        # than an engine-level check (Hindsight will accept content without either).
        if not content:
            raise ValueError("Artifact content must be non-empty")
        if not author:
            raise ValueError("Artifact requires an author for Trace provenance")
        if not artifact_ref:
            raise ValueError("Artifact requires an artifact_ref (e.g. 'pr:1131')")
        bank_id = self.tenants.get_bank_id(tenant_id)
        item = {
            "content": content,
            "tags": list(_TAGS),
            "metadata": stringify_metadata(
                {
                    **(metadata or {}),
                    "mal_node": "artifact",
                    "author": author,
                    "artifact_ref": artifact_ref,
                }
            ),
        }
        return self.client.retain(bank_id=bank_id, items=[item])

    def recall(
        self,
        *,
        tenant_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        bank_id = self.tenants.get_bank_id(tenant_id)
        return self.client.recall(bank_id=bank_id, query=query, tags=list(_TAGS), top_k=top_k)
