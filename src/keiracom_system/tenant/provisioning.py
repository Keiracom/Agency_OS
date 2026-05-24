"""provisioning.py — Keiracom System tenant provisioning service.

Signup → tier→topology decision → schema creation (Topology B) or VPC hook
(Topology A) → tenant config materialisation → `tenant_provisioned` event.

The interface contract Orion needs from the resulting row (per dispatch):
    SELECT row by tenant_id returning a dict with at minimum:
      {llm_api_key, llm_model, embedding_dim, tier, allowed_fields}

Implemented as `get_tenant_config()` (see bottom of this module) and used by
the KeiracomTenantExtension Orion is building in parallel.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

log = logging.getLogger(__name__)

# ---- domain constants (mirror migration enums) ----
ALLOWED_TIERS = ("solo", "pro", "scale")
ALLOWED_TOPOLOGIES = ("A_per_vpc", "B_shared_schema")
DEFAULT_EMBEDDING_DIM = 384  # BGE-small-en-v1.5 per eleven_agreed_positions #1
SHARED_TIER_TOPOLOGY = "B_shared_schema"
VPC_TIER_TOPOLOGY = "A_per_vpc"


class KeiracomTenantProvisioningError(RuntimeError):
    """Raised when provisioning cannot complete."""


class _DBProtocol(Protocol):
    """Minimal Supabase-like surface so tests can mock without psycopg pulled in."""

    def insert_tenant(self, row: dict[str, Any]) -> dict[str, Any]: ...

    def select_tenant(self, tenant_id: str) -> dict[str, Any] | None: ...

    def create_schema(self, schema_name: str) -> None: ...


class _EventEmitterProtocol(Protocol):
    def emit(self, event_name: str, payload: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class TenantRecord:
    """Mirrors the keiracom_tenants Postgres row shape (sans timestamps)."""

    tenant_id: str
    tier: str
    topology: str
    llm_api_key_encrypted: str
    llm_model: str
    embedding_dim: int = DEFAULT_EMBEDDING_DIM
    schema_name: str | None = None
    vpc_id: str | None = None
    status: str = "provisioning"


@dataclass(frozen=True)
class TenantConfig:
    """The contract Orion's KeiracomTenantExtension consumes per request.

    `allowed_fields` is a forward-compat hook — currently surfaces tier-derived
    feature flags; richer policy lands in a later PR per Orion's interface ask.
    """

    llm_api_key: str
    llm_model: str
    embedding_dim: int
    tier: str
    allowed_fields: dict[str, Any] = field(default_factory=dict)


def tier_to_topology(tier: str) -> str:
    """Topology B for Solo/Pro (shared instance + schema-per-tenant);
    Topology A for Scale (per-tenant VPC)."""
    if tier not in ALLOWED_TIERS:
        raise KeiracomTenantProvisioningError(f"unknown tier {tier!r}; allowed: {ALLOWED_TIERS}")
    return VPC_TIER_TOPOLOGY if tier == "scale" else SHARED_TIER_TOPOLOGY


def _build_tenant_row(
    *,
    tenant_id: str,
    tier: str,
    llm_api_key_encrypted: str,
    llm_model: str,
    embedding_dim: int,
    vpc_id: str | None,
) -> TenantRecord:
    if not llm_api_key_encrypted:
        raise KeiracomTenantProvisioningError("llm_api_key_encrypted required")
    if not llm_model:
        raise KeiracomTenantProvisioningError("llm_model required")
    if embedding_dim <= 0:
        raise KeiracomTenantProvisioningError(f"embedding_dim must be >0, got {embedding_dim}")
    topology = tier_to_topology(tier)
    if topology == SHARED_TIER_TOPOLOGY:
        schema_name = f"keiracom_{tenant_id.replace('-', '_')}"
        chosen_vpc_id = None
    else:
        if not vpc_id:
            raise KeiracomTenantProvisioningError("Topology A requires vpc_id")
        schema_name = None
        chosen_vpc_id = vpc_id
    return TenantRecord(
        tenant_id=tenant_id,
        tier=tier,
        topology=topology,
        llm_api_key_encrypted=llm_api_key_encrypted,
        llm_model=llm_model,
        embedding_dim=embedding_dim,
        schema_name=schema_name,
        vpc_id=chosen_vpc_id,
        status="active",
    )


def provision_tenant(
    *,
    db: _DBProtocol,
    events: _EventEmitterProtocol,
    tier: str,
    llm_api_key_encrypted: str,
    llm_model: str,
    embedding_dim: int = DEFAULT_EMBEDDING_DIM,
    vpc_id: str | None = None,
    tenant_id: str | None = None,
) -> TenantRecord:
    """Provision a new tenant. Idempotent on retry: if `tenant_id` is supplied
    and already exists, returns the existing row without re-creating state.

    Topology B path: create the Postgres schema for the tenant's Hindsight data.
    Topology A path: call out to the (separately-built) VPC provisioner; the
    `vpc_id` arg is the already-allocated VPC handle.

    Always emits `tenant_provisioned` on success (idempotent re-runs included).
    """
    chosen_tenant_id = tenant_id or str(uuid.uuid4())
    existing = db.select_tenant(chosen_tenant_id)
    if existing:
        log.info(
            "provision_tenant: tenant_id=%s already exists; returning existing row",
            chosen_tenant_id,
        )
        events.emit(
            "tenant_provisioned", {"tenant_id": chosen_tenant_id, "idempotent_replay": True}
        )
        return TenantRecord(
            **{k: v for k, v in existing.items() if k in TenantRecord.__annotations__}
        )

    record = _build_tenant_row(
        tenant_id=chosen_tenant_id,
        tier=tier,
        llm_api_key_encrypted=llm_api_key_encrypted,
        llm_model=llm_model,
        embedding_dim=embedding_dim,
        vpc_id=vpc_id,
    )
    if record.topology == SHARED_TIER_TOPOLOGY and record.schema_name:
        db.create_schema(record.schema_name)
    db.insert_tenant(asdict(record))
    log.info(
        "provision_tenant: tenant_id=%s tier=%s topology=%s",
        record.tenant_id,
        record.tier,
        record.topology,
    )
    events.emit(
        "tenant_provisioned",
        {
            "tenant_id": record.tenant_id,
            "tier": record.tier,
            "topology": record.topology,
            "idempotent_replay": False,
        },
    )
    return record


def get_tenant_config(db: _DBProtocol, tenant_id: str) -> TenantConfig:
    """The interface contract Orion's KeiracomTenantExtension calls per request.

    Raises KeiracomTenantProvisioningError if the tenant does not exist.
    """
    row = db.select_tenant(tenant_id)
    if row is None:
        raise KeiracomTenantProvisioningError(f"tenant {tenant_id} not found")
    return TenantConfig(
        llm_api_key=row["llm_api_key_encrypted"],
        llm_model=row["llm_model"],
        embedding_dim=int(row["embedding_dim"]),
        tier=row["tier"],
        allowed_fields={
            "tier": row["tier"],
            "topology": row.get("topology"),
            "byok_sovereign": True,
            "cross_tenant_inference_allowed": False,
        },
    )
