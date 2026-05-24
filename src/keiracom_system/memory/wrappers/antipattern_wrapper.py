"""antipattern_wrapper.py — AntiPattern → Hindsight Opinion (wrapper required).

The single gap from PR #1129 spike item vi: Hindsight has no native Opinion
primitive. The wrapper implements the AntiPattern-Graveyard idea from
eleven_agreed_positions #11 by:

  1. Tagging the memory with `entity_label="anti-pattern"` so recall can
     surface the Graveyard view via `recall(tags=["anti-pattern"])`.
  2. Carrying a `supersedes` edge in metadata pointing at the contradicted
     world/experience fact's memory id. The supersession-via-AntiPattern V1
     pattern from eleven_agreed_positions #4 is realised through this edge —
     the contradicted item stays in the bank but the AntiPattern's existence
     marks it as superseded, queryable via the Graveyard tag.
  3. Mandatory `failed_path` + `verified_path` fields aligned with the v2
     discovery-log format (CLAUDE.md §Discovery Log) — both required so the
     AntiPattern carries the positive+negative pair LLMs need to learn from.
"""

from __future__ import annotations

from typing import Any

from ._base import HindsightClient, TenantExtensionProtocol, stringify_metadata

_TAGS = ["mal_node:antipattern", "anti-pattern"]


class AntiPatternWrapper:
    def __init__(self, client: HindsightClient, tenant_extension: TenantExtensionProtocol) -> None:
        self.client = client
        self.tenants = tenant_extension

    def ingest(
        self,
        *,
        tenant_id: str,
        context: str,
        failed_path: str,
        verified_path: str,
        supersedes_memory_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Both paths mandatory per CLAUDE.md §Discovery Log — negative-only is
        # weaker than positive+negative for LLM retrieval consumption.
        if not context:
            raise ValueError("AntiPattern context must be non-empty")
        if not failed_path:
            raise ValueError("AntiPattern failed_path required (negative path)")
        if not verified_path:
            raise ValueError("AntiPattern verified_path required (positive path)")
        content = (
            f"AntiPattern — context: {context}\n"
            f"failed_path: {failed_path}\n"
            f"verified_path: {verified_path}"
        )
        bank_id = self.tenants.get_bank_id(tenant_id)
        meta = {
            **(metadata or {}),
            "mal_node": "antipattern",
            "failed_path": failed_path,
            "verified_path": verified_path,
        }
        if supersedes_memory_id:
            meta["supersedes"] = supersedes_memory_id
        item = {
            "content": content,
            "tags": list(_TAGS),
            "metadata": stringify_metadata(meta),
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

    def graveyard(
        self,
        *,
        tenant_id: str,
        top_k: int = 100,
    ) -> list[dict[str, Any]]:
        """Return all AntiPatterns in the bank (Graveyard view). Empty query =
        engine returns recency-ordered set of the tagged subset."""
        bank_id = self.tenants.get_bank_id(tenant_id)
        return self.client.recall(bank_id=bank_id, query="", tags=["anti-pattern"], top_k=top_k)
