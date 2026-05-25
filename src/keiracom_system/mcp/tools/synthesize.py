"""synthesize — explicit consolidation trigger.

Hindsight runs consolidation automatically as a background task post-retain
(PR #1130 smoke: 49 ops → 31 new + 13 updated observations in 158s). This
tool surfaces the manual `/consolidate` endpoint so a Pro/Scale operator can
force-flush pending memories into observations + entities + edges before a
recall they want to be fresh.

Pro tier and above per the dispatch tier-router (Solo gets get-data-in/out
only; consolidate is the "compounding-earned" Pro inflection per
eleven_agreed_positions #4).
"""

from __future__ import annotations

from typing import Any, Protocol

from src.keiracom_system.memory.wrappers._base import TenantExtensionProtocol


class _ConsolidatingClient(Protocol):
    def consolidate(self, *, bank_id: str) -> dict[str, Any]: ...


def synthesize_bank(
    *,
    client: _ConsolidatingClient,
    tenant_extension: TenantExtensionProtocol,
    tenant_id: str,
) -> dict[str, Any]:
    if not tenant_id:
        raise ValueError("tenant_id required for synthesize")
    bank_id = tenant_extension.get_bank_id(tenant_id)
    return client.consolidate(bank_id=bank_id)
