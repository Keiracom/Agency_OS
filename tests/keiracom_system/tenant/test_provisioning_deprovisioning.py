"""tests for keiracom_system.tenant — Phase 2 build item 2 (Atlas).

Covers the dispatch's required scope:
- Positive-path provisioning (Topology B and Topology A)
- GDPR-delete path (deprovisioning)
- Idempotency on retry (both provision + deprovision)
- Invalid-tier rejection + other negative-path locks

DB + event emitter are mocked end-to-end so the suite runs without a live
Supabase connection. The Postgres migration is verified separately via
`supabase apply_migration` at deploy time.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.keiracom_system.tenant import (
    ALLOWED_TIERS,
    DEFAULT_EMBEDDING_DIM,
    KeiracomTenantDeprovisioningError,
    KeiracomTenantProvisioningError,
    deprovision_tenant,
    get_tenant_config,
    provision_tenant,
    tier_to_topology,
)


class _FakeDB:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.schemas_created: list[str] = []
        self.schemas_dropped: list[str] = []
        self.status_updates: list[tuple[str, str]] = []

    def insert_tenant(self, row: dict[str, Any]) -> dict[str, Any]:
        self.rows[row["tenant_id"]] = dict(row)
        return self.rows[row["tenant_id"]]

    def select_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        return self.rows.get(tenant_id)

    def create_schema(self, schema_name: str) -> None:
        self.schemas_created.append(schema_name)

    def drop_schema(self, schema_name: str) -> None:
        self.schemas_dropped.append(schema_name)

    def update_tenant_status(self, tenant_id: str, status: str) -> None:
        self.status_updates.append((tenant_id, status))
        if tenant_id in self.rows:
            self.rows[tenant_id]["status"] = status


class _FakeEvents:
    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict[str, Any]]] = []

    def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        self.emitted.append((event_name, payload))


@pytest.fixture
def db():
    return _FakeDB()


@pytest.fixture
def events():
    return _FakeEvents()


# ----------------- tier→topology mapping -----------------


def test_tier_to_topology_solo_is_shared():
    assert tier_to_topology("solo") == "B_shared_schema"


def test_tier_to_topology_pro_is_shared():
    assert tier_to_topology("pro") == "B_shared_schema"


def test_tier_to_topology_scale_is_per_vpc():
    assert tier_to_topology("scale") == "A_per_vpc"


def test_tier_to_topology_rejects_unknown():
    with pytest.raises(KeiracomTenantProvisioningError, match="unknown tier"):
        tier_to_topology("enterprise")


def test_allowed_tiers_is_exhaustive():
    """Schema enum + Python constants must agree (drift-detection lock)."""
    assert set(ALLOWED_TIERS) == {"solo", "pro", "scale"}


# ----------------- provision positive paths -----------------


def test_provision_solo_creates_schema_topology_b(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="solo",
        llm_api_key_encrypted="enc:keymat",
        llm_model="gpt-4o-mini",
    )
    assert rec.topology == "B_shared_schema"
    assert rec.schema_name is not None
    assert rec.vpc_id is None
    assert rec.embedding_dim == DEFAULT_EMBEDDING_DIM
    assert len(db.schemas_created) == 1
    assert db.schemas_created[0] == rec.schema_name
    assert events.emitted[0][0] == "tenant_provisioned"
    assert events.emitted[0][1]["idempotent_replay"] is False


def test_provision_pro_uses_topology_b(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="pro",
        llm_api_key_encrypted="enc:keymat",
        llm_model="claude-opus-4-7",
    )
    assert rec.topology == "B_shared_schema"
    assert rec.schema_name and rec.vpc_id is None


def test_provision_scale_uses_topology_a_with_vpc(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="scale",
        llm_api_key_encrypted="enc:keymat",
        llm_model="gpt-4o",
        vpc_id="vpc-prod-acme-001",
    )
    assert rec.topology == "A_per_vpc"
    assert rec.vpc_id == "vpc-prod-acme-001"
    assert rec.schema_name is None
    assert db.schemas_created == [], "Topology A must NOT create a shared-instance schema"


def test_provision_persists_to_db(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="solo",
        llm_api_key_encrypted="enc:keymat",
        llm_model="gpt-4o-mini",
    )
    row = db.select_tenant(rec.tenant_id)
    assert row is not None
    assert row["tier"] == "solo"
    assert row["llm_api_key_encrypted"] == "enc:keymat"
    assert row["status"] == "active"


def test_provision_idempotent_replay_returns_existing_row(db, events):
    rec_first = provision_tenant(
        db=db,
        events=events,
        tier="solo",
        llm_api_key_encrypted="enc:keymat",
        llm_model="gpt-4o-mini",
    )
    rec_replay = provision_tenant(
        db=db,
        events=events,
        tier="solo",
        llm_api_key_encrypted="enc:keymat-NEW",  # different key — must be ignored
        llm_model="something-different",
        tenant_id=rec_first.tenant_id,
    )
    assert rec_replay.tenant_id == rec_first.tenant_id
    assert rec_replay.llm_api_key_encrypted == "enc:keymat"  # original preserved
    # Schema created only once across the two calls
    assert len(db.schemas_created) == 1
    # Both emits: the replay flag distinguishes them
    assert events.emitted[1][1]["idempotent_replay"] is True


# ----------------- provision negative paths -----------------


def test_provision_rejects_invalid_tier(db, events):
    with pytest.raises(KeiracomTenantProvisioningError, match="unknown tier"):
        provision_tenant(
            db=db,
            events=events,
            tier="enterprise",
            llm_api_key_encrypted="enc:keymat",
            llm_model="gpt-4o",
        )


def test_provision_rejects_missing_llm_api_key(db, events):
    with pytest.raises(KeiracomTenantProvisioningError, match="llm_api_key_encrypted required"):
        provision_tenant(
            db=db,
            events=events,
            tier="solo",
            llm_api_key_encrypted="",
            llm_model="gpt-4o-mini",
        )


def test_provision_rejects_missing_llm_model(db, events):
    with pytest.raises(KeiracomTenantProvisioningError, match="llm_model required"):
        provision_tenant(
            db=db,
            events=events,
            tier="solo",
            llm_api_key_encrypted="enc:keymat",
            llm_model="",
        )


def test_provision_rejects_zero_embedding_dim(db, events):
    with pytest.raises(KeiracomTenantProvisioningError, match="embedding_dim must be >0"):
        provision_tenant(
            db=db,
            events=events,
            tier="solo",
            llm_api_key_encrypted="enc:keymat",
            llm_model="gpt-4o-mini",
            embedding_dim=0,
        )


def test_provision_scale_without_vpc_id_fails(db, events):
    with pytest.raises(KeiracomTenantProvisioningError, match="Topology A requires vpc_id"):
        provision_tenant(
            db=db,
            events=events,
            tier="scale",
            llm_api_key_encrypted="enc:keymat",
            llm_model="gpt-4o",
        )


# ----------------- get_tenant_config (Orion's interface contract) -----------------


def test_get_tenant_config_returns_orion_contract_shape(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="pro",
        llm_api_key_encrypted="enc:keymat",
        llm_model="claude-opus-4-7",
    )
    cfg = get_tenant_config(db, rec.tenant_id)
    # Spec from dispatch: {llm_api_key, llm_model, embedding_dim, tier, allowed_fields}
    assert cfg.llm_api_key == "enc:keymat"
    assert cfg.llm_model == "claude-opus-4-7"
    assert cfg.embedding_dim == DEFAULT_EMBEDDING_DIM
    assert cfg.tier == "pro"
    assert isinstance(cfg.allowed_fields, dict)
    assert cfg.allowed_fields["byok_sovereign"] is True
    assert cfg.allowed_fields["cross_tenant_inference_allowed"] is False


def test_get_tenant_config_rejects_unknown_tenant(db):
    with pytest.raises(KeiracomTenantProvisioningError, match="not found"):
        get_tenant_config(db, "00000000-0000-0000-0000-000000000000")


# ----------------- deprovision positive paths -----------------


def test_deprovision_topology_b_drops_schema(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="solo",
        llm_api_key_encrypted="enc:keymat",
        llm_model="gpt-4o-mini",
    )
    result = deprovision_tenant(db=db, events=events, tenant_id=rec.tenant_id)
    assert result["status"] == "deleted"
    assert rec.schema_name in db.schemas_dropped
    # FSM order: deprovisioning -> deleted
    statuses = [s for tid, s in db.status_updates if tid == rec.tenant_id]
    assert statuses == ["deprovisioning", "deleted"]


def test_deprovision_topology_a_calls_destroy_vpc_hook(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="scale",
        llm_api_key_encrypted="enc:keymat",
        llm_model="gpt-4o",
        vpc_id="vpc-prod-acme-001",
    )
    destroyed = []
    deprovision_tenant(
        db=db,
        events=events,
        tenant_id=rec.tenant_id,
        destroy_vpc=lambda vpc: destroyed.append(vpc),
    )
    assert destroyed == ["vpc-prod-acme-001"]
    assert db.schemas_dropped == [], "Topology A must NOT drop a shared schema"


def test_deprovision_emits_event(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="solo",
        llm_api_key_encrypted="enc:keymat",
        llm_model="gpt-4o-mini",
    )
    deprovision_tenant(db=db, events=events, tenant_id=rec.tenant_id)
    deprov_events = [e for e in events.emitted if e[0] == "tenant_deprovisioned"]
    assert len(deprov_events) == 1
    assert deprov_events[0][1]["idempotent_replay"] is False


def test_deprovision_calls_revoke_credentials_hook(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="solo",
        llm_api_key_encrypted="enc:keymat",
        llm_model="gpt-4o-mini",
    )
    revoked = []
    deprovision_tenant(
        db=db,
        events=events,
        tenant_id=rec.tenant_id,
        revoke_credentials=lambda tid: revoked.append(tid),
    )
    assert revoked == [rec.tenant_id]


def test_deprovision_idempotent_on_already_deleted(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="solo",
        llm_api_key_encrypted="enc:keymat",
        llm_model="gpt-4o-mini",
    )
    deprovision_tenant(db=db, events=events, tenant_id=rec.tenant_id)
    # Second call must NOT drop the schema again
    schemas_before_replay = list(db.schemas_dropped)
    result = deprovision_tenant(db=db, events=events, tenant_id=rec.tenant_id)
    assert result["idempotent_replay"] is True
    assert db.schemas_dropped == schemas_before_replay
    # Final emit carries the replay flag
    last_event = [e for e in events.emitted if e[0] == "tenant_deprovisioned"][-1]
    assert last_event[1]["idempotent_replay"] is True


# ----------------- deprovision negative paths -----------------


def test_deprovision_rejects_unknown_tenant(db, events):
    with pytest.raises(KeiracomTenantDeprovisioningError, match="not found"):
        deprovision_tenant(
            db=db,
            events=events,
            tenant_id="00000000-0000-0000-0000-000000000000",
        )


def test_deprovision_revoke_credentials_failure_does_not_halt_fsm(db, events):
    rec = provision_tenant(
        db=db,
        events=events,
        tier="solo",
        llm_api_key_encrypted="enc:keymat",
        llm_model="gpt-4o-mini",
    )

    def _bad_revoke(_tid):
        raise RuntimeError("vault unreachable")

    # Must not raise — FSM continues to deleted; failure is logged
    result = deprovision_tenant(
        db=db,
        events=events,
        tenant_id=rec.tenant_id,
        revoke_credentials=_bad_revoke,
    )
    assert result["status"] == "deleted"
    assert rec.schema_name in db.schemas_dropped
