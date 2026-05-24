"""deprovisioning.py — Keiracom System tenant GDPR-delete path.

Lifecycle (FSM transitions, app-enforced + matches migration enum):
    active|suspended -> deprovisioning -> deleted

Steps:
  1. Mark `deprovisioning` (FSM stop-the-bleed; further provision_tenant
     replays return the existing row but downstream policy can refuse new work).
  2. Revoke any in-flight API credentials for the tenant (caller-supplied
     `revoke_credentials` hook — Hindsight TenantExtension token, MCP server
     bearer, etc).
  3. Drop the Postgres schema (Topology B) OR call the VPC destroyer
     (Topology A) via the supplied destroyer hook.
  4. Mark `deleted`; emit `tenant_deprovisioned` event.

Idempotent: repeated calls on an already-`deleted` tenant are no-ops + still
emit the event with `idempotent_replay=True` so downstream subscribers can
log + drop without alarm.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from .provisioning import (
    SHARED_TIER_TOPOLOGY,
    VPC_TIER_TOPOLOGY,
    KeiracomTenantProvisioningError,
)

log = logging.getLogger(__name__)


class KeiracomTenantDeprovisioningError(RuntimeError):
    """Raised when deprovisioning cannot proceed."""


class _DBProtocol(Protocol):
    def select_tenant(self, tenant_id: str) -> dict[str, Any] | None: ...

    def update_tenant_status(self, tenant_id: str, status: str) -> None: ...

    def drop_schema(self, schema_name: str) -> None: ...


class _EventEmitterProtocol(Protocol):
    def emit(self, event_name: str, payload: dict[str, Any]) -> None: ...


def deprovision_tenant(
    *,
    db: _DBProtocol,
    events: _EventEmitterProtocol,
    tenant_id: str,
    revoke_credentials: Any = None,
    destroy_vpc: Any = None,
) -> dict[str, Any]:
    """Deprovision a tenant. Idempotent. Returns the final state + emitted-event
    payload for caller observability."""
    row = db.select_tenant(tenant_id)
    if row is None:
        raise KeiracomTenantDeprovisioningError(f"tenant {tenant_id} not found")

    if row.get("status") == "deleted":
        log.info("deprovision_tenant: tenant %s already deleted; idempotent replay", tenant_id)
        events.emit("tenant_deprovisioned", {"tenant_id": tenant_id, "idempotent_replay": True})
        return {"tenant_id": tenant_id, "status": "deleted", "idempotent_replay": True}

    # Step 1 — mark deprovisioning (stop-the-bleed)
    db.update_tenant_status(tenant_id, "deprovisioning")
    log.info("deprovision_tenant: %s -> deprovisioning", tenant_id)

    # Step 2 — revoke creds (caller hook; safe no-op if None)
    if revoke_credentials is not None:
        try:
            revoke_credentials(tenant_id)
        except Exception:  # noqa: BLE001 — caller log; do not halt the FSM
            log.exception("deprovision_tenant: revoke_credentials raised for %s", tenant_id)

    # Step 3 — topology-specific destruction
    topology = row.get("topology")
    if topology == SHARED_TIER_TOPOLOGY:
        schema_name = row.get("schema_name")
        if not schema_name:
            raise KeiracomTenantDeprovisioningError(
                f"tenant {tenant_id} topology=B but schema_name missing — refusing to proceed"
            )
        db.drop_schema(schema_name)
        log.info("deprovision_tenant: dropped schema %s for tenant %s", schema_name, tenant_id)
    elif topology == VPC_TIER_TOPOLOGY:
        vpc_id = row.get("vpc_id")
        if not vpc_id:
            raise KeiracomTenantDeprovisioningError(
                f"tenant {tenant_id} topology=A but vpc_id missing — refusing to proceed"
            )
        if destroy_vpc is not None:
            destroy_vpc(vpc_id)
            log.info("deprovision_tenant: destroyed VPC %s for tenant %s", vpc_id, tenant_id)
        else:
            log.warning(
                "deprovision_tenant: topology=A tenant %s but no destroy_vpc hook; VPC %s left in place",
                tenant_id,
                vpc_id,
            )
    else:
        raise KeiracomTenantDeprovisioningError(f"tenant {tenant_id} unknown topology {topology!r}")

    # Step 4 — mark deleted + emit
    db.update_tenant_status(tenant_id, "deleted")
    log.info("deprovision_tenant: %s -> deleted", tenant_id)
    payload = {
        "tenant_id": tenant_id,
        "topology": topology,
        "idempotent_replay": False,
    }
    events.emit("tenant_deprovisioned", payload)
    return {"tenant_id": tenant_id, "status": "deleted", "idempotent_replay": False}


# Re-export so callers can disambiguate provisioning vs deprovisioning errors
# without two imports when both paths matter (e.g. in the control-plane API).
__all__ = [
    "KeiracomTenantDeprovisioningError",
    "KeiracomTenantProvisioningError",
    "deprovision_tenant",
]
