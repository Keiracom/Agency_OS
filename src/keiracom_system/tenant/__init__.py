"""Keiracom System tenant control-plane.

Provisioning, deprovisioning, and the contract Orion's KeiracomTenantExtension
relies on for per-request routing:

    get_tenant_config(tenant_id) -> {
        "llm_api_key":   str,   # encrypted at rest; caller decrypts
        "llm_model":     str,
        "embedding_dim": int,
        "tier":          str,   # 'solo' | 'pro' | 'scale'
        "allowed_fields": dict, # downstream policy hooks
    }
"""

from .deprovisioning import (
    KeiracomTenantDeprovisioningError,
    deprovision_tenant,
)
from .provisioning import (
    ALLOWED_TIERS,
    DEFAULT_EMBEDDING_DIM,
    KeiracomTenantProvisioningError,
    TenantConfig,
    TenantRecord,
    get_tenant_config,
    provision_tenant,
    tier_to_topology,
)

__all__ = [
    "ALLOWED_TIERS",
    "DEFAULT_EMBEDDING_DIM",
    "KeiracomTenantDeprovisioningError",
    "KeiracomTenantProvisioningError",
    "TenantConfig",
    "TenantRecord",
    "deprovision_tenant",
    "get_tenant_config",
    "provision_tenant",
    "tier_to_topology",
]
