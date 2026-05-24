"""keiracom_tenant_extension.py — Phase 2 build item 1.

KeiracomTenantExtension subclasses Hindsight's TenantExtension to deliver
per-request BYOK-LLM routing for Topology B (shared instance, schema-per-tenant)
and Topology A (per-tenant VPC) — both topologies dispatch through the same
extension because Hindsight's per-request config resolution works identically.

Materialises config from Keiracom's control-plane keiracom_tenants table via
Atlas's get_tenant_config(db, tenant_id) → TenantConfig contract (PR #1131,
src/keiracom_system/tenant/provisioning.py). This module decrypts the BYOK
API key on-fetch and returns the override dict Hindsight's ConfigResolver
merges on top of global env config.

CANONICAL KEY ANCHOR — ceo:memory_abstraction_layer_v1 (RATIFIED 2026-05-24,
Phase 2 build commit RATIFIED same day):

  substantive_lock (relevant lines):
    - "Memory Abstraction Layer V1 ratified"
    - "Hindsight self-hosted as engine (Vectorize.io open-source MIT).
       Deployment topology is tier-keyed: Solo/Pro tiers use shared-instance
       schema-per-tenant via TenantExtension + SupabaseTenantExtension
       (Topology B); Scale tier and regulated verticals use per-tenant VPC
       (Topology A). Same MAL primitives across both topologies via MCP
       swappability."
    - "V1 primitives as thin domain wrappers around Hindsight TEMPR +
       Opinion/Reflect pathway."

  position 5 (eleven_agreed_positions[4]):
    "Collective scope: tenant-bounded only, never cross-tenant inference
     (BYOK sovereignty)"

  phase_2_build_commit_status:
    "RATIFIED 2026-05-24 — Dave authorised Phase 2 build start on engine-fit
     verdict. Six build items dispatched: KeiracomTenantExtension,
     control-plane tenants table + provisioning, Hindsight wrapper layer
     (~300-500 LoC), TEI sidecar install, log-based per-tenant metering,
     tier-aware MCP server."

DESIGN — folds in Atlas's #1126 gaps G3 (tier-router) + G5 (tier-aware MCP)
implicitly: tier-driven get_allowed_config_fields() gates which fields tenants
can override. Solo gets BYOK only; Pro adds tunables; Scale gets full control
(though Scale typically uses Topology A with per-instance env, not per-request).

DUCK-TYPED INHERITANCE — hindsight_api is lazy-imported at module load. When
the real hindsight_api is installed, KeiracomTenantExtension inherits from
hindsight_api.extensions.tenant.TenantExtension. When it isn't (e.g. test
envs), a local stub TenantExtension with the same interface shape is used.
Hindsight loads the extension via importlib + calls the methods duck-typed
at runtime — base-class identity is not enforced.

TESTABILITY — db client and decryptor are injected at construction so tests
can swap fakes without psycopg/pgcrypto in the test path.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any, Protocol

from .provisioning import (
    KeiracomTenantProvisioningError,
    TenantConfig,
    get_tenant_config,
)

# Lazy-import Hindsight base class to keep the module collectable on hosts
# without hindsight_api installed. Falls back to a local stub that mirrors
# Hindsight's interface shape (duck-typed at runtime by Hindsight's loader).
try:
    from hindsight_api.extensions.tenant import (  # type: ignore[import-not-found]
        AuthenticationError,
        Tenant,
        TenantContext,
    )
    from hindsight_api.extensions.tenant import (
        TenantExtension as _HindsightTenantExtension,
    )
    from hindsight_api.models import RequestContext  # type: ignore[import-not-found]

    _HINDSIGHT_IMPORTED = True
except ImportError:
    _HINDSIGHT_IMPORTED = False
    from abc import ABC, abstractmethod
    from dataclasses import dataclass, field

    @dataclass
    class TenantContext:
        """Stub matching hindsight_api.extensions.tenant.TenantContext shape."""

        schema_name: str

    @dataclass
    class Tenant:
        """Stub matching hindsight_api.extensions.tenant.Tenant shape."""

        schema: str

    class AuthenticationError(Exception):
        """Stub matching hindsight_api.extensions.tenant.AuthenticationError."""

        def __init__(self, reason: str, headers: dict[str, str] | None = None):
            self.reason = reason
            self.headers = headers or {}
            super().__init__(f"Authentication failed: {reason}")

    @dataclass
    class RequestContext:
        """Stub matching hindsight_api.models.RequestContext.

        Real RequestContext carries more fields; this stub covers the minimal
        surface this extension uses (headers + api_key).
        """

        headers: dict[str, str] = field(default_factory=dict)
        api_key: str | None = None

    class _HindsightTenantExtension(ABC):
        """Local stub matching the TenantExtension contract shape."""

        @abstractmethod
        async def authenticate(self, context: RequestContext) -> TenantContext: ...

        @abstractmethod
        async def list_tenants(self) -> list[Tenant]: ...

        async def get_tenant_config(self, context: RequestContext) -> dict[str, Any]:
            return {}

        async def get_allowed_config_fields(
            self, context: RequestContext, bank_id: str
        ) -> set[str] | None:
            return None

        async def authenticate_mcp(self, context: RequestContext) -> TenantContext:
            return await self.authenticate(context)


log = logging.getLogger(__name__)

API_KEY_HEADER = "X-Keiracom-Api-Key"

# Tier → allowed Hindsight config fields. Tier-driven feature gating: Solo
# gets BYOK only (minimal surface); Pro adds tunables; Scale gets full
# control (None == no restriction in Hindsight's get_allowed_config_fields
# contract).
_TIER_ALLOWED_FIELDS: dict[str, set[str] | None] = {
    "solo": {"llm_api_key", "llm_model"},
    "pro": {"llm_api_key", "llm_model", "chunk_size", "retain_extraction_mode"},
    "scale": None,
}


class _DBProtocol(Protocol):
    """Minimal db surface for tenant lookup + listing (mirrors Atlas's _DBProtocol
    in provisioning.py, extended with active-tenant listing for list_tenants)."""

    def select_tenant(self, tenant_id: str) -> dict[str, Any] | None: ...

    def select_tenant_by_api_key(self, api_key: str) -> dict[str, Any] | None: ...

    def list_active_tenants(self) -> list[dict[str, Any]]: ...


def _passthrough_decryptor(ciphertext: str) -> str:
    """Default decryptor for tests + dev envs (no real pgcrypto round-trip).

    Production wires a real decryptor that calls pgcrypto.pgp_sym_decrypt
    against the keys_service pattern from src/api/services/customer_api_keys.py
    (existing Agency_OS-era code; pattern is reusable for Keiracom System).
    """
    return ciphertext


class KeiracomTenantExtension(_HindsightTenantExtension):
    """Hindsight TenantExtension implementation backed by Keiracom's control plane.

    Per-request flow (Topology B):
        1. authenticate(context) — pull X-Keiracom-Api-Key from headers,
           lookup tenant_id, return TenantContext(schema_name).
        2. get_tenant_config(context) — call Atlas's get_tenant_config(db,
           tenant_id), decrypt llm_api_key, return override dict for the
           Hindsight ConfigResolver to merge on top of global env config.
        3. get_allowed_config_fields(context, bank_id) — tier-driven gate
           per _TIER_ALLOWED_FIELDS.

    Per-instance config (Topology A) uses the same flow; the per-tenant VPC
    runs ONE tenant so the override path is no-op-equivalent (still routed
    through this extension for code-path uniformity).
    """

    def __init__(
        self,
        db: _DBProtocol,
        decryptor: Callable[[str], str] | None = None,
        api_key_header: str | None = None,
    ):
        """Construct with injected db client + decryptor (testability)."""
        self._db = db
        self._decrypt = decryptor or _passthrough_decryptor
        self._api_key_header = api_key_header or API_KEY_HEADER

    def _extract_api_key(self, context: RequestContext) -> str:
        """Pull the Keiracom API key from request headers. Raises AuthenticationError if absent."""
        api_key: str | None = None
        headers = getattr(context, "headers", None) or {}
        if headers:
            # Case-insensitive header lookup — RequestContext.headers shape
            # differs across Hindsight versions; handle dict + case-insensitive.
            for key, value in headers.items():
                if key.lower() == self._api_key_header.lower():
                    api_key = value
                    break
        if not api_key:
            api_key = getattr(context, "api_key", None)
        if not api_key:
            raise AuthenticationError(f"missing {self._api_key_header} header")
        return api_key

    async def authenticate(self, context: RequestContext) -> TenantContext:
        """Resolve tenant_id from API key + return TenantContext(schema_name).

        Topology A tenants (no schema_name on row) fall back to schema='public'
        — Hindsight's documented single-tenant default.
        """
        api_key = self._extract_api_key(context)
        row = self._db.select_tenant_by_api_key(api_key)
        if not row:
            raise AuthenticationError("invalid api key")
        if row.get("status") != "active":
            raise AuthenticationError(f"tenant status not active (got {row.get('status')!r})")
        schema_name = row.get("schema_name") or "public"
        return TenantContext(schema_name=schema_name)

    async def list_tenants(self) -> list[Tenant]:
        """Return all active tenants for worker discovery (per Hindsight contract)."""
        rows = self._db.list_active_tenants()
        return [Tenant(schema=r.get("schema_name") or "public") for r in rows]

    async def get_tenant_config(self, context: RequestContext) -> dict[str, Any]:
        """Per-request override dict for Hindsight's ConfigResolver.

        Returns {llm_api_key, llm_model} for the tenant. Resolver merges these
        onto global env config + bank JSONB config in that order.

        On unknown tenant_id: returns {} (resolver falls back to global env;
        global env has NO LLM key in production per BYOK sovereignty contract,
        so the request errors with 'no LLM key configured' rather than
        silently subsidising — per spike-item-(v) PR #1128 §6).
        """
        api_key = self._extract_api_key(context)
        row = self._db.select_tenant_by_api_key(api_key)
        if not row:
            return {}
        tenant_id = row.get("tenant_id")
        if not tenant_id:
            return {}
        try:
            cfg: TenantConfig = get_tenant_config(self._db, tenant_id)
        except KeiracomTenantProvisioningError as exc:
            log.warning("get_tenant_config: %s", exc)
            return {}
        decrypted_key = self._decrypt(cfg.llm_api_key)
        return {
            "llm_api_key": decrypted_key,
            "llm_model": cfg.llm_model,
        }

    async def get_allowed_config_fields(
        self, context: RequestContext, bank_id: str
    ) -> set[str] | None:
        """Tier-driven field gate per _TIER_ALLOWED_FIELDS.

        Returns None for scale tier (no restriction) per Hindsight's
        documented contract. Unknown tier returns empty set (read-only, no
        overrides accepted — defensive against malformed control-plane rows).
        """
        try:
            api_key = self._extract_api_key(context)
        except AuthenticationError:
            return set()
        row = self._db.select_tenant_by_api_key(api_key)
        if not row:
            return set()
        tier = row.get("tier")
        if tier not in _TIER_ALLOWED_FIELDS:
            log.warning(
                "get_allowed_config_fields: unknown tier %r for tenant %r — returning empty set",
                tier,
                row.get("tenant_id"),
            )
            return set()
        return _TIER_ALLOWED_FIELDS[tier]


def from_env() -> KeiracomTenantExtension:
    """Factory for production deployment via HINDSIGHT_API_TENANT_EXTENSION env.

    Hindsight's extension loader imports the module + calls the class with
    no args. This factory function is what production deployment scripts
    should call to construct the extension with the right db client +
    decryptor wired in.

    For now this raises — production wiring lands when the Supabase client
    adapter implementing _DBProtocol is authored (P1 follow-up bd issue).
    """
    backend = os.environ.get("KEIRACOM_TENANT_DB_BACKEND", "")
    raise NotImplementedError(
        f"from_env not yet wired (backend={backend!r}). "
        "Construct directly with a _DBProtocol-conformant client in test/dev. "
        "Production wiring lands in P1 follow-up bd."
    )
