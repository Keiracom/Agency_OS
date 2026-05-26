"""TenantBudgetPolicy — Phase A7 sub-task 2.

Policy data hook for temp.inline.token_gate (LLM-call workflow #2 enforces;
A7 only ships the data + Postgres table).

CANONICAL DESIGN — docs/architecture/design/a7_cache_architecture.md §6 + §13
CB-3 (point-in-time schema, no effective_from/until) + CB-9 (tier CHECK).

CONSUMERS:
  - LLM-call workflow #2 token_gate activity — calls from_db(db, tenant_id),
    enforces per_call_cap_tokens + daily_pool_tokens + monthly_pool_tokens
    before each LLM call.
  - 48h baseline observation script — reads default tier policies for the
    cost-attribution report.

DEPENDENCY INJECTION: caller passes any object implementing _DBProtocol
(execute(query, *params) + fetchone()). This avoids direct asyncpg/psycopg
import inside the cache module — required by boundary-matrix-v1 guard (b)
which exempts only memory/ + control_plane/ paths (see PR #1169 +
docs/governance/boundary_matrix_v1.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

# Tier identifiers — mirror the CHECK constraint in the SQL migration.
# Keep in sync with supabase/migrations/20260526_keiracom_tenant_budgets.sql.
TIER_SANDBOX = "sandbox"
TIER_SOLO = "solo"
TIER_PRO = "pro"
TIER_TEAM = "team"
TIER_ENTERPRISE = "enterprise"

VALID_TIERS: frozenset[str] = frozenset(
    {TIER_SANDBOX, TIER_SOLO, TIER_PRO, TIER_TEAM, TIER_ENTERPRISE}
)


class TenantBudgetPolicyError(RuntimeError):
    """Raised on invalid tier or missing tenant budget row."""


class _DBProtocol(Protocol):
    """Subset of a DB cursor/connection we depend on for from_db().

    Mirrors the protocol-injection pattern from PR #1132 KeiracomTenantExtension.
    Lets unit tests inject a fake without importing asyncpg/psycopg here.
    """

    def execute(self, query: str, *params: Any) -> Any: ...
    def fetchone(self) -> Any: ...


# Default per-tier model cost calibration weight. Mirrors design §6.
# Keys are LiteLLM model identifiers (provider/model) per gov.litellm_router.
# Values are multipliers vs Haiku-baseline (Haiku 3.5 = 1.0x).
DEFAULT_MODEL_COST_CALIBRATION: dict[str, float] = {
    "anthropic/claude-3-5-sonnet": 3.0,
    "anthropic/claude-3-5-haiku": 1.0,
    "openai/gpt-4o": 2.5,
    "openai/gpt-4o-mini": 0.8,
    "google/gemini-2.5-flash": 0.5,
}


@dataclass(frozen=True, kw_only=True)
class TenantBudgetPolicy:
    """Per-tenant policy data the token_gate enforces against.

    Frozen dataclass — policies are immutable values; mutations create a new
    instance and UPDATE the row. updated_at column tracks the last write.
    Per CB-3 point-in-time schema; no effective_from/until history.
    """

    tenant_id: str
    tier: str
    per_call_cap_tokens: int
    daily_pool_tokens: int
    monthly_pool_tokens: int
    model_cost_calibration: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.tier not in VALID_TIERS:
            raise TenantBudgetPolicyError(f"tier {self.tier!r} not in {sorted(VALID_TIERS)}")
        if self.per_call_cap_tokens <= 0:
            raise TenantBudgetPolicyError("per_call_cap_tokens must be > 0")
        if self.daily_pool_tokens <= 0:
            raise TenantBudgetPolicyError("daily_pool_tokens must be > 0")
        if self.monthly_pool_tokens <= 0:
            raise TenantBudgetPolicyError("monthly_pool_tokens must be > 0")

    @classmethod
    def from_db(cls, db: _DBProtocol, tenant_id: str) -> TenantBudgetPolicy:
        """Load policy from Postgres for a given tenant_id.

        Raises TenantBudgetPolicyError if the tenant has no budget row.
        Caller injects any object with execute() + fetchone() — keeps this
        module driver-agnostic per boundary-matrix-v1 guard (b).
        """
        db.execute(
            "SELECT tier, per_call_cap_tokens, daily_pool_tokens, "
            "monthly_pool_tokens, model_cost_calibration "
            "FROM keiracom_tenant_budgets WHERE tenant_id = %s",
            tenant_id,
        )
        row = db.fetchone()
        if row is None:
            raise TenantBudgetPolicyError(
                f"no budget row for tenant_id={tenant_id!r}; seed via migration"
            )
        return cls(
            tenant_id=tenant_id,
            tier=row[0],
            per_call_cap_tokens=int(row[1]),
            daily_pool_tokens=int(row[2]),
            monthly_pool_tokens=int(row[3]),
            model_cost_calibration=dict(row[4]) if row[4] else {},
        )


# Default per-tier policies (V1 PROPOSAL — pressure-test in Phase 2 per design §6).
# Sandbox 50K/day cap per amendment 2 (Agency_OS-tpxj).
# Enterprise = sentinel record; per-tenant operator override required at onboard.
TIER_DEFAULTS: dict[str, dict[str, int]] = {
    TIER_SANDBOX: {
        "per_call_cap_tokens": 10_000,
        "daily_pool_tokens": 50_000,
        "monthly_pool_tokens": 500_000,
    },
    TIER_SOLO: {
        "per_call_cap_tokens": 50_000,
        "daily_pool_tokens": 1_000_000,
        "monthly_pool_tokens": 30_000_000,
    },
    TIER_PRO: {
        "per_call_cap_tokens": 100_000,
        "daily_pool_tokens": 5_000_000,
        "monthly_pool_tokens": 150_000_000,
    },
    TIER_TEAM: {
        "per_call_cap_tokens": 200_000,
        "daily_pool_tokens": 20_000_000,
        "monthly_pool_tokens": 600_000_000,
    },
    # Enterprise = custom; placeholder values that will be overridden by
    # operator at onboarding. Non-zero because the dataclass invariant
    # forbids zero — operator MUST replace these with real per-tenant caps.
    TIER_ENTERPRISE: {
        "per_call_cap_tokens": 1_000_000,
        "daily_pool_tokens": 100_000_000,
        "monthly_pool_tokens": 3_000_000_000,
    },
}
