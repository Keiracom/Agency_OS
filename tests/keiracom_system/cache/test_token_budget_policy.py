"""TenantBudgetPolicy unit tests — Phase A7 sub-task 2.

Covers:
  - tier defaults present for all 5 tiers
  - dataclass validation (tier whitelist + positive caps)
  - from_db() factory with injected fake DB
  - missing tenant row raises TenantBudgetPolicyError
"""

import pytest

from src.keiracom_system.cache.token_budget_policy import (
    DEFAULT_MODEL_COST_CALIBRATION,
    TIER_DEFAULTS,
    TIER_ENTERPRISE,
    TIER_PRO,
    TIER_SANDBOX,
    TIER_SOLO,
    TIER_TEAM,
    VALID_TIERS,
    TenantBudgetPolicy,
    TenantBudgetPolicyError,
)


class _FakeDB:
    """Minimal DB fake matching _DBProtocol — no asyncpg/psycopg dependency."""

    def __init__(self, row: tuple | None):
        self._row = row
        self.executed: list[tuple[str, tuple]] = []

    def execute(self, query: str, *params):
        self.executed.append((query, params))

    def fetchone(self):
        return self._row


def test_all_five_tiers_have_defaults():
    assert set(TIER_DEFAULTS.keys()) == VALID_TIERS
    assert set(TIER_DEFAULTS.keys()) == {
        TIER_SANDBOX,
        TIER_SOLO,
        TIER_PRO,
        TIER_TEAM,
        TIER_ENTERPRISE,
    }


def test_sandbox_amendment_2_daily_cap():
    """Sandbox 50K/day per amendment 2 (Agency_OS-tpxj)."""
    assert TIER_DEFAULTS[TIER_SANDBOX]["daily_pool_tokens"] == 50_000


def test_tier_default_pools_increase_by_tier():
    """Pool sizes monotonically increase Sandbox → Enterprise."""
    pools = [
        TIER_DEFAULTS[t]["daily_pool_tokens"]
        for t in [TIER_SANDBOX, TIER_SOLO, TIER_PRO, TIER_TEAM, TIER_ENTERPRISE]
    ]
    assert pools == sorted(pools)


def test_per_call_caps_increase_by_tier():
    caps = [
        TIER_DEFAULTS[t]["per_call_cap_tokens"]
        for t in [TIER_SANDBOX, TIER_SOLO, TIER_PRO, TIER_TEAM, TIER_ENTERPRISE]
    ]
    assert caps == sorted(caps)


def test_policy_rejects_invalid_tier():
    with pytest.raises(TenantBudgetPolicyError, match="tier 'bogus'"):
        TenantBudgetPolicy(
            tenant_id="t1",
            tier="bogus",
            per_call_cap_tokens=1,
            daily_pool_tokens=1,
            monthly_pool_tokens=1,
        )


def test_policy_rejects_zero_per_call_cap():
    with pytest.raises(TenantBudgetPolicyError, match="per_call_cap_tokens must be > 0"):
        TenantBudgetPolicy(
            tenant_id="t1",
            tier=TIER_SOLO,
            per_call_cap_tokens=0,
            daily_pool_tokens=1,
            monthly_pool_tokens=1,
        )


def test_policy_rejects_zero_daily_pool():
    with pytest.raises(TenantBudgetPolicyError, match="daily_pool_tokens must be > 0"):
        TenantBudgetPolicy(
            tenant_id="t1",
            tier=TIER_SOLO,
            per_call_cap_tokens=1,
            daily_pool_tokens=0,
            monthly_pool_tokens=1,
        )


def test_policy_rejects_zero_monthly_pool():
    with pytest.raises(TenantBudgetPolicyError, match="monthly_pool_tokens must be > 0"):
        TenantBudgetPolicy(
            tenant_id="t1",
            tier=TIER_SOLO,
            per_call_cap_tokens=1,
            daily_pool_tokens=1,
            monthly_pool_tokens=0,
        )


def test_policy_frozen_dataclass_immutable():
    """Frozen — policies are immutable values; UPDATEs create new instances."""
    p = TenantBudgetPolicy(
        tenant_id="t1",
        tier=TIER_SOLO,
        per_call_cap_tokens=50_000,
        daily_pool_tokens=1_000_000,
        monthly_pool_tokens=30_000_000,
    )
    with pytest.raises((AttributeError, Exception)):
        p.per_call_cap_tokens = 999  # type: ignore[misc]


def test_from_db_returns_policy_for_team_tier():
    fake = _FakeDB(
        row=(
            "team",
            200_000,
            20_000_000,
            600_000_000,
            DEFAULT_MODEL_COST_CALIBRATION,
        )
    )
    p = TenantBudgetPolicy.from_db(fake, "00000000-0000-0000-0000-000000000001")
    assert p.tier == TIER_TEAM
    assert p.per_call_cap_tokens == 200_000
    assert p.daily_pool_tokens == 20_000_000
    assert p.monthly_pool_tokens == 600_000_000
    assert p.model_cost_calibration == DEFAULT_MODEL_COST_CALIBRATION


def test_from_db_handles_null_calibration():
    """NULL JSONB column → empty dict."""
    fake = _FakeDB(
        row=(
            "solo",
            50_000,
            1_000_000,
            30_000_000,
            None,
        )
    )
    p = TenantBudgetPolicy.from_db(fake, "t1")
    assert p.model_cost_calibration == {}


def test_from_db_raises_when_no_row():
    fake = _FakeDB(row=None)
    with pytest.raises(TenantBudgetPolicyError, match="no budget row"):
        TenantBudgetPolicy.from_db(fake, "nonexistent-tenant")


def test_default_model_cost_calibration_keys():
    """Calibration covers the 5 LiteLLM model identifiers per design §6."""
    assert "anthropic/claude-3-5-sonnet" in DEFAULT_MODEL_COST_CALIBRATION
    assert "anthropic/claude-3-5-haiku" in DEFAULT_MODEL_COST_CALIBRATION
    assert "openai/gpt-4o" in DEFAULT_MODEL_COST_CALIBRATION
    assert "openai/gpt-4o-mini" in DEFAULT_MODEL_COST_CALIBRATION
    assert "google/gemini-2.5-flash" in DEFAULT_MODEL_COST_CALIBRATION


def test_haiku_baseline_weight_is_1():
    assert DEFAULT_MODEL_COST_CALIBRATION["anthropic/claude-3-5-haiku"] == 1.0
