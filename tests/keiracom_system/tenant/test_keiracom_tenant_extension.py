"""Tests for src/keiracom_system/tenant/keiracom_tenant_extension.py — Phase 2 build item 1.

Negative-path discipline per Aiden's gate-validator gate
(feedback_negative_path_test_before_approve) and Max's PR #1118 / #1121
review pattern: gate/validator/permission code must have negative-path
tests on synthetic offenders before any approve.

10 cases:
  (1)  test_authenticate_with_valid_api_key_returns_schema_per_tenant
  (2)  test_authenticate_missing_api_key_raises_authentication_error
  (3)  test_authenticate_unknown_api_key_raises_authentication_error
  (4)  test_authenticate_inactive_tenant_raises_authentication_error
  (5)  test_authenticate_topology_a_no_schema_falls_back_to_public
  (6)  test_get_tenant_config_returns_decrypted_llm_overrides
  (7)  test_get_tenant_config_unknown_api_key_returns_empty_dict
  (8)  test_get_allowed_config_fields_solo_returns_byok_only
  (9)  test_get_allowed_config_fields_pro_returns_byok_plus_tunables
  (10) test_get_allowed_config_fields_scale_returns_none
  (11) test_get_allowed_config_fields_unknown_tier_returns_empty_set
  (12) test_list_tenants_returns_active_only

Fake db (FakeDB) implements _DBProtocol surface without psycopg/Supabase in
test path. Injected decryptor lets us assert encryption-decryption round-trip
without pgcrypto.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.tenant.keiracom_tenant_extension import (  # noqa: E402
    API_KEY_HEADER,
    AuthenticationError,
    KeiracomTenantExtension,
    RequestContext,
    TenantContext,
)


class FakeDB:
    """In-memory _DBProtocol implementation for tests."""

    def __init__(self, rows: list[dict] | None = None):
        self._rows = list(rows or [])

    def insert_tenant(self, row):
        self._rows.append(dict(row))
        return dict(row)

    def create_schema(self, schema_name):
        pass

    def select_tenant(self, tenant_id: str):
        for r in self._rows:
            if r.get("tenant_id") == tenant_id:
                return dict(r)
        return None

    def select_tenant_by_api_key(self, api_key: str):
        for r in self._rows:
            if r.get("_test_api_key") == api_key:
                return dict(r)
        return None

    def list_active_tenants(self):
        return [dict(r) for r in self._rows if r.get("status") == "active"]


def _row(
    *,
    tenant_id: str = "t1",
    api_key: str = "key-t1",
    tier: str = "solo",
    schema_name: str | None = "keiracom_t1",
    status: str = "active",
    llm_api_key_encrypted: str = "ENC:openai-tenant-key",
    llm_model: str = "gpt-4o-mini",
    embedding_dim: int = 384,
    topology: str = "B_shared_schema",
    vpc_id: str | None = None,
) -> dict:
    return {
        "tenant_id": tenant_id,
        "_test_api_key": api_key,
        "tier": tier,
        "schema_name": schema_name,
        "status": status,
        "llm_api_key_encrypted": llm_api_key_encrypted,
        "llm_model": llm_model,
        "embedding_dim": embedding_dim,
        "topology": topology,
        "vpc_id": vpc_id,
    }


def _ctx(api_key: str | None) -> RequestContext:
    headers = {API_KEY_HEADER: api_key} if api_key else {}
    return RequestContext(headers=headers, api_key=None)


def _run(coro):
    return asyncio.run(coro)


def test_authenticate_with_valid_api_key_returns_schema_per_tenant():
    """(1) — happy-path: valid API key → TenantContext(schema_name)."""
    db = FakeDB([_row(tenant_id="t1", api_key="key-t1", schema_name="keiracom_t1")])
    ext = KeiracomTenantExtension(db=db)
    tc = _run(ext.authenticate(_ctx("key-t1")))
    assert isinstance(tc, TenantContext)
    assert tc.schema_name == "keiracom_t1"


def test_authenticate_missing_api_key_raises_authentication_error():
    """(2) — no X-Keiracom-Api-Key header → AuthenticationError."""
    db = FakeDB()
    ext = KeiracomTenantExtension(db=db)
    with pytest.raises(AuthenticationError) as excinfo:
        _run(ext.authenticate(_ctx(None)))
    assert API_KEY_HEADER in excinfo.value.reason


def test_authenticate_unknown_api_key_raises_authentication_error():
    """(3) — API key not in db → AuthenticationError('invalid api key')."""
    db = FakeDB([_row(api_key="key-t1")])
    ext = KeiracomTenantExtension(db=db)
    with pytest.raises(AuthenticationError) as excinfo:
        _run(ext.authenticate(_ctx("key-impostor")))
    assert "invalid" in excinfo.value.reason.lower()


def test_authenticate_inactive_tenant_raises_authentication_error():
    """(4) — tenant row found but status != 'active' → AuthenticationError.

    Defensive against deprovisioned/suspended tenants whose API key was not
    rotated — we refuse the request even though the key matches.
    """
    db = FakeDB([_row(api_key="key-t1", status="suspended")])
    ext = KeiracomTenantExtension(db=db)
    with pytest.raises(AuthenticationError) as excinfo:
        _run(ext.authenticate(_ctx("key-t1")))
    assert "status not active" in excinfo.value.reason
    assert "suspended" in excinfo.value.reason


def test_authenticate_topology_a_no_schema_falls_back_to_public():
    """(5) — Topology A tenant (per-VPC, no schema_name) → schema='public'.

    Hindsight's single-tenant default. Topology A instances run one tenant
    each so 'public' is the right schema.
    """
    db = FakeDB(
        [
            _row(
                api_key="key-scale",
                tier="scale",
                schema_name=None,
                topology="A_per_vpc",
                vpc_id="vpc-abc",
            )
        ]
    )
    ext = KeiracomTenantExtension(db=db)
    tc = _run(ext.authenticate(_ctx("key-scale")))
    assert tc.schema_name == "public"


def test_get_tenant_config_returns_decrypted_llm_overrides():
    """(6) — happy-path: returns {llm_api_key (decrypted), llm_model}."""
    db = FakeDB(
        [
            _row(
                api_key="key-t1",
                llm_api_key_encrypted="ENC:sk-tenant-secret",
                llm_model="claude-opus-4-7",
            )
        ]
    )
    # Injected decryptor strips the ENC: prefix to prove the call happens.
    captured: list[str] = []

    def fake_decrypt(ct: str) -> str:
        captured.append(ct)
        assert ct.startswith("ENC:"), f"decryptor expected ciphertext, got {ct!r}"
        return ct[len("ENC:") :]

    ext = KeiracomTenantExtension(db=db, decryptor=fake_decrypt)
    overrides = _run(ext.get_tenant_config(_ctx("key-t1")))
    assert overrides == {"llm_api_key": "sk-tenant-secret", "llm_model": "claude-opus-4-7"}
    assert captured == ["ENC:sk-tenant-secret"], "decryptor should be called exactly once"


def test_get_tenant_config_unknown_api_key_returns_empty_dict():
    """(7) — unknown api_key returns {} (falls back to global env per BYOK contract).

    Per PR #1128 §6 graceful-degradation pattern: production global env has NO
    LLM key, so this surfaces as 'no key configured' error from Hindsight rather
    than a silent Keiracom subsidy.
    """
    db = FakeDB([_row(api_key="key-t1")])
    ext = KeiracomTenantExtension(db=db)
    overrides = _run(ext.get_tenant_config(_ctx("key-impostor")))
    assert overrides == {}


def test_get_allowed_config_fields_solo_returns_byok_only():
    """(8) — Solo tier: only llm_api_key + llm_model overridable (minimal surface)."""
    db = FakeDB([_row(api_key="key-solo", tier="solo")])
    ext = KeiracomTenantExtension(db=db)
    allowed = _run(ext.get_allowed_config_fields(_ctx("key-solo"), bank_id="default"))
    assert allowed == {"llm_api_key", "llm_model"}


def test_get_allowed_config_fields_pro_returns_byok_plus_tunables():
    """(9) — Pro tier: BYOK + chunk_size + retain_extraction_mode."""
    db = FakeDB([_row(api_key="key-pro", tier="pro")])
    ext = KeiracomTenantExtension(db=db)
    allowed = _run(ext.get_allowed_config_fields(_ctx("key-pro"), bank_id="default"))
    assert allowed == {
        "llm_api_key",
        "llm_model",
        "chunk_size",
        "retain_extraction_mode",
    }


def test_get_allowed_config_fields_scale_returns_none():
    """(10) — Scale tier: None means no restriction (per Hindsight contract)."""
    db = FakeDB(
        [
            _row(
                api_key="key-scale",
                tier="scale",
                schema_name=None,
                topology="A_per_vpc",
                vpc_id="vpc-1",
            )
        ]
    )
    ext = KeiracomTenantExtension(db=db)
    allowed = _run(ext.get_allowed_config_fields(_ctx("key-scale"), bank_id="default"))
    assert allowed is None


def test_get_allowed_config_fields_unknown_tier_returns_empty_set():
    """(11) — defensive: malformed row with unknown tier → empty set (read-only).

    Catches a control-plane drift where a new tier was added to the enum
    but not to _TIER_ALLOWED_FIELDS. Better fail-closed than fail-open.
    """
    db = FakeDB([_row(api_key="key-x", tier="enterprise-plus")])  # not in _TIER_ALLOWED_FIELDS
    ext = KeiracomTenantExtension(db=db)
    allowed = _run(ext.get_allowed_config_fields(_ctx("key-x"), bank_id="default"))
    assert allowed == set()


def test_list_tenants_returns_active_only():
    """(12) — list_tenants filters to status='active' (worker discovery contract)."""
    db = FakeDB(
        [
            _row(tenant_id="t1", api_key="k1", schema_name="s1", status="active"),
            _row(tenant_id="t2", api_key="k2", schema_name="s2", status="suspended"),
            _row(
                tenant_id="t3",
                api_key="k3",
                schema_name=None,
                status="active",
                topology="A_per_vpc",
                vpc_id="vpc-3",
            ),  # Topology A → schema='public' fallback
        ]
    )
    ext = KeiracomTenantExtension(db=db)
    tenants = _run(ext.list_tenants())
    schemas = {t.schema for t in tenants}
    assert schemas == {"s1", "public"}  # t2 (suspended) excluded; t3 Topology A → public
