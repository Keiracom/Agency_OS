"""_base.py — shared Protocol surface for the Hindsight wrappers.

The wrappers are domain-typed (Decision / Artifact / TaskContext / AntiPattern)
but all consume the same two collaborators:

  * `client` — a Hindsight HTTP surface (retain / recall / reflect)
  * `tenant_extension` — Orion's KeiracomTenantExtension (PR #1132) for
    per-request routing + BYOK key materialisation

Protocols here let the wrappers stay loose-coupled — tests mock without
pulling in psycopg or a real Hindsight client.
"""

from __future__ import annotations

from typing import Any, Protocol


class HindsightClient(Protocol):
    def retain(self, *, bank_id: str, items: list[dict[str, Any]]) -> dict[str, Any]: ...

    def recall(
        self, *, bank_id: str, query: str, tags: list[str] | None = ..., top_k: int = ...
    ) -> list[dict[str, Any]]: ...

    def reflect(self, *, bank_id: str, query: str) -> dict[str, Any]: ...


class TenantExtensionProtocol(Protocol):
    """Subset of Orion's KeiracomTenantExtension surface the wrappers need.

    `get_bank_id(tenant_id)` returns the Hindsight memory-bank scoped to the
    tenant; Hindsight retain/recall/reflect calls then path-segment on it
    (per the openapi probe in PR #1130: /v1/default/banks/{bank_id}/...).
    """

    def get_bank_id(self, tenant_id: str) -> str: ...


def stringify_metadata(meta: dict[str, Any]) -> dict[str, str]:
    """Hindsight metadata values must be strings (PR #1130 G2 finding)."""
    return {
        k: (",".join(map(str, v)) if isinstance(v, list) else str(v))
        for k, v in meta.items()
        if v is not None
    }
