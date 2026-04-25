"""Tests for src/orchestration/flows/outreach_flow.py budget gates.

BU-CLOSED-LOOP-C1 — replicates the CD Player budget enforcement pattern.
Hermetic — no live DB, no live channel adapters.

Coverage:
  - Domain at cap is skipped (refuse-to-send returns structured skip).
  - Customer at cap is skipped (tier-based daily AUD ceiling).
  - Customer with credits_remaining<=0 is skipped before any channel cost.
  - Normal under-cap send proceeds + admit_send advances counters.
  - Edge case: customer at exactly the cap before this send (this_send + spent
    > cap → skip).
  - Edge case: customer just under cap (this_send + spent <= cap → proceed).
  - In-memory snapshot mutation via _admit_send is reflected in next gate call.
  - Gate skip rows carry stable reason strings ('budget_cap_per_domain_exceeded',
    'budget_cap_per_customer_exceeded') so CIS records the refusal.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest


os.environ.setdefault("DATABASE_URL", "postgresql://stub:stub@stub:5432/stub")

import importlib  # noqa: E402

flow_mod = importlib.import_module("src.orchestration.flows.outreach_flow")


# ── helpers ─────────────────────────────────────────────────────────────────

def _empty_snapshot(client_id: str = "client-1",
                    domain: str = "example.com.au",
                    tier: str = "ignition",
                    credits: int = 1000,
                    spent_client: float = 0.0,
                    spent_domain: float = 0.0) -> dict[str, dict]:
    return {
        "by_client": {client_id: spent_client},
        "by_domain": {domain: spent_domain},
        "by_client_credits": {client_id: credits},
        "by_client_tier": {client_id: tier},
    }


def _lead(channel_resource: str = "email-resource",
          client_id: str = "client-1",
          domain: str = "example.com.au",
          lead_id: str = "lead-A") -> dict:
    return {
        "lead_id": lead_id,
        "client_id": client_id,
        "campaign_id": "camp-1",
        "domain": domain,
        "tier": "ignition",
        "permission_mode": "autopilot",
        "resource": channel_resource,
    }


# ── Gate behaviour — core matrix ────────────────────────────────────────────

def test_gate_admits_normal_under_cap_send():
    """Empty snapshot, sane caps → gate returns None (admit)."""
    snap = _empty_snapshot()
    out = flow_mod._check_budget_gate(snap, _lead(), "email")
    assert out is None


def test_gate_skips_domain_at_cap():
    """Domain has already spent the cap today; one more send breaches."""
    snap = _empty_snapshot(spent_domain=flow_mod.DEFAULT_DOMAIN_DAILY_AUD_CAP)
    out = flow_mod._check_budget_gate(snap, _lead(), "linkedin")
    assert out is not None
    assert out["reason"] == "budget_cap_per_domain_exceeded"
    assert out["success"] is False
    assert out["skipped"] is True
    assert out["channel"] == "linkedin"
    assert out["domain"] == "example.com.au"
    assert "domain_cap_aud" in out["detail"]


def test_gate_skips_domain_exactly_at_cap_when_send_would_breach():
    """Edge: spent == cap, this_send > 0, spent + this_send > cap → skip."""
    snap = _empty_snapshot(spent_domain=flow_mod.DEFAULT_DOMAIN_DAILY_AUD_CAP)
    # email costs 0.0006 AUD — pushes 5.0 + 0.0006 > 5.0 → must skip.
    out = flow_mod._check_budget_gate(snap, _lead(), "email")
    assert out is not None
    assert out["reason"] == "budget_cap_per_domain_exceeded"


def test_gate_admits_when_spent_just_under_cap():
    """Edge: spent + this_send <= cap → admit. Use a value below the
    domain cap minus the email cost to land cleanly under."""
    snap = _empty_snapshot(spent_domain=flow_mod.DEFAULT_DOMAIN_DAILY_AUD_CAP
                                         - flow_mod.CHANNEL_COST_AUD["email"]
                                         - 0.001)
    out = flow_mod._check_budget_gate(snap, _lead(), "email")
    assert out is None


def test_gate_skips_customer_at_tier_cap():
    """Customer has spent the tier daily cap today (ignition = 50 AUD)."""
    snap = _empty_snapshot(tier="ignition",
                           spent_client=flow_mod.TIER_DAILY_AUD_CAP["ignition"])
    out = flow_mod._check_budget_gate(snap, _lead(), "voice")
    assert out is not None
    assert out["reason"] == "budget_cap_per_customer_exceeded"
    assert "tier=ignition" in out["detail"]
    assert "cap_aud=50.00" in out["detail"]


def test_gate_skips_customer_with_zero_credits_remaining():
    """credits_remaining<=0 → blanket refuse all channels."""
    snap = _empty_snapshot(credits=0)
    out = flow_mod._check_budget_gate(snap, _lead(), "email")
    assert out is not None
    assert out["reason"] == "budget_cap_per_customer_exceeded"
    assert out["detail"] == "credits_remaining<=0"


def test_gate_uses_correct_per_tier_cap_for_spark():
    """Spark tier has a 25 AUD daily ceiling (lower than ignition)."""
    snap = _empty_snapshot(tier="spark",
                           spent_client=flow_mod.TIER_DAILY_AUD_CAP["spark"])
    out = flow_mod._check_budget_gate(snap, _lead(), "voice")
    assert out is not None
    assert out["reason"] == "budget_cap_per_customer_exceeded"
    assert "tier=spark" in out["detail"]
    assert "cap_aud=25.00" in out["detail"]


def test_gate_uses_correct_per_tier_cap_for_velocity():
    """Velocity tier has a 100 AUD daily ceiling (highest active)."""
    snap = _empty_snapshot(tier="velocity",
                           spent_client=99.99)
    # voice cost is 0.14 → 99.99 + 0.14 > 100 → skip.
    out = flow_mod._check_budget_gate(snap, _lead(), "voice")
    assert out is not None
    assert out["reason"] == "budget_cap_per_customer_exceeded"
    assert "tier=velocity" in out["detail"]


def test_gate_falls_back_to_ignition_cap_when_tier_unknown():
    """Defensive: an unknown tier string falls back to ignition cap (50)."""
    snap = _empty_snapshot(tier="bogus-tier",
                           spent_client=flow_mod.TIER_DAILY_AUD_CAP["ignition"])
    out = flow_mod._check_budget_gate(snap, _lead(), "voice")
    assert out is not None
    assert out["reason"] == "budget_cap_per_customer_exceeded"


def test_gate_admits_when_no_domain_attached():
    """If lead.domain is empty, the per-domain gate is skipped silently —
    customer + credits gates still apply."""
    snap = _empty_snapshot()
    lead = _lead(domain="")
    out = flow_mod._check_budget_gate(snap, lead, "email")
    assert out is None


# ── _admit_send behaviour ───────────────────────────────────────────────────

def test_admit_send_advances_counters():
    """After admit_send, the snapshot reflects the new spend and the next
    gate call sees it. Mirrors the CD Player shared-counter pattern."""
    snap = _empty_snapshot(spent_client=49.0, tier="ignition")  # 1 AUD headroom
    lead = _lead()
    # First send: voice = 0.14 → admitted, leaves 0.86 headroom.
    assert flow_mod._check_budget_gate(snap, lead, "voice") is None
    flow_mod._admit_send(snap, lead, "voice")
    assert pytest.approx(snap["by_client"]["client-1"], abs=0.001) == 49.14
    # Subsequent admit_send pushes total over 50 → next gate must refuse.
    for _ in range(7):
        flow_mod._admit_send(snap, lead, "voice")
    refused = flow_mod._check_budget_gate(snap, lead, "voice")
    assert refused is not None
    assert refused["reason"] == "budget_cap_per_customer_exceeded"


def test_admit_send_advances_domain_counter_too():
    snap = _empty_snapshot()
    lead = _lead()
    flow_mod._admit_send(snap, lead, "linkedin")
    assert pytest.approx(snap["by_domain"]["example.com.au"], abs=0.001) \
        == flow_mod.CHANNEL_COST_AUD["linkedin"]


def test_admit_send_no_op_when_lead_has_no_domain_or_client():
    """Defensive: lead missing domain/client_id should not raise."""
    snap = _empty_snapshot()
    flow_mod._admit_send(snap, {"lead_id": "x"}, "email")
    # Counters are unchanged.
    assert snap["by_client"]["client-1"] == 0.0


# ── Skip-row contract ───────────────────────────────────────────────────────

def test_skip_row_carries_required_fields_for_cis():
    """CIS consumers expect lead_id, channel, success=False, reason.
    The structured skip dict from the gate must include all of these."""
    snap = _empty_snapshot(credits=0)
    skip = flow_mod._check_budget_gate(snap, _lead(), "email")
    assert skip is not None
    for required_key in ("lead_id", "channel", "success", "reason",
                         "client_id", "skipped"):
        assert required_key in skip
    assert skip["success"] is False
    assert skip["skipped"] is True
    assert skip["lead_id"] == "lead-A"
    assert skip["channel"] == "email"


# ── Module-level cost / tier cap constants ──────────────────────────────────

def test_channel_cost_aud_covers_all_required_channels():
    """Every channel surfaced in the flow body must have a cost entry."""
    for ch in ("email", "linkedin", "sms", "voice"):
        assert ch in flow_mod.CHANNEL_COST_AUD
        assert flow_mod.CHANNEL_COST_AUD[ch] > 0


# ── OB-1..OB-6 review-fix regressions ───────────────────────────────────────

def test_ob1_snapshot_failure_emits_loud_alert(monkeypatch):
    """OB-1: snapshot SQL silent-fail must call _emit_snapshot_failure_alert
    (logger.error + best-effort Telegram broadcast) — never logger.warning."""
    calls: list[tuple[str, str]] = []

    def fake_emit(stage: str, exc: Exception) -> None:
        calls.append((stage, type(exc).__name__))

    monkeypatch.setattr(flow_mod, "_emit_snapshot_failure_alert", fake_emit)

    # Stub get_db_session so every conn.execute raises — exercises all three
    # try/except branches inside snapshot_outreach_spend_task.
    import contextlib
    from unittest.mock import AsyncMock, MagicMock

    failing_db = MagicMock()
    failing_db.execute = AsyncMock(side_effect=RuntimeError("supabase down"))

    @contextlib.asynccontextmanager
    async def fake_session():
        yield failing_db

    monkeypatch.setattr(flow_mod, "get_db_session", fake_session)

    import asyncio
    snap = asyncio.run(flow_mod.snapshot_outreach_spend_task.fn(
        client_ids=["client-1"], domains=["example.com.au"],
    ))

    # All three failure branches fired the loud alert.
    stages = sorted(stage for stage, _ in calls)
    assert stages == ["by_client", "by_domain", "clients"]
    # Every alert flagged the same RuntimeError.
    assert all(exc_name == "RuntimeError" for _, exc_name in calls)
    # Snapshot still returns a usable shape (defence-in-depth — gate runs anyway).
    assert "by_client" in snap
    assert "by_domain" in snap


def test_ob2_spend_window_is_module_level_constant():
    """OB-2: _today_window_sql() helper replaced by _SPEND_WINDOW_SQL constant."""
    assert hasattr(flow_mod, "_SPEND_WINDOW_SQL")
    assert isinstance(flow_mod._SPEND_WINDOW_SQL, str)
    # The old function should be gone.
    assert not hasattr(flow_mod, "_today_window_sql")


def test_ob6_spend_window_uses_calendar_day_utc_not_rolling_24h():
    """OB-6: window aligned to CURRENT_DATE (calendar-day-UTC) matching
    src/services/jit_validator.py:431 daily-quota convention. NOT a
    rolling 24h interval — Stripe has no daily rule, so prior comment was
    misleading and SQL is now consistent with the existing JIT rate
    limiter (cap resets at UTC midnight)."""
    assert flow_mod._SPEND_WINDOW_SQL == "CURRENT_DATE"
    # The snapshot SQL embeds the constant via f-string — verify the
    # constant reference appears, not the resolved value (inspect.getsource
    # returns source text with the {var} substitution in place).
    import inspect
    src = inspect.getsource(flow_mod.snapshot_outreach_spend_task)
    assert "{_SPEND_WINDOW_SQL}" in src
    # Old rolling-24h marker must be gone.
    assert "INTERVAL '24 hours'" not in src
    # Module-level docstring should not retain the misleading Stripe phrase.
    mod_src = inspect.getsource(flow_mod)
    assert "matches Stripe day rule" not in mod_src


def test_ob3_tier_coercion_is_pinned_to_enum_value():
    """OB-3: source code pins tier_value to tier.value with the only
    fallback being None -> 'ignition'. The old hasattr() / str() fallback
    chain is removed."""
    import inspect
    src = inspect.getsource(flow_mod.get_leads_ready_for_outreach_task)
    assert "tier.value if tier is not None else \"ignition\"" in src
    # The old defensive chain must be gone.
    assert 'hasattr(tier, "value")' not in src


def test_ob4_domain_cap_documented_as_roadmap_marker():
    """OB-4: DEFAULT_DOMAIN_DAILY_AUD_CAP carries a roadmap-polish marker
    noting the value should become per-customer-tier configurable
    post-revenue. Comment-only verification."""
    import inspect
    src = inspect.getsource(flow_mod)
    # The roadmap marker text must appear adjacent to the constant.
    assert "per-customer-tier configurable post-revenue" in src
    # Constant value remains 5.0.
    assert flow_mod.DEFAULT_DOMAIN_DAILY_AUD_CAP == 5.0


def test_ob5_channel_cost_aud_documents_canonical_source():
    """OB-5: CHANNEL_COST_AUD comment block points to canonical settings
    sources for future updates."""
    import inspect
    src = inspect.getsource(flow_mod)
    # The OB-5 marker text must appear adjacent to the dict.
    assert "src/config/settings.py" in src
    assert "voice_agent_telnyx.py" in src


def test_tier_daily_aud_cap_covers_active_tiers():
    """spark / ignition / velocity must be present; dominance kept for
    DB-migration tolerance per src/config/tiers.py."""
    for t in ("spark", "ignition", "velocity"):
        assert t in flow_mod.TIER_DAILY_AUD_CAP
        assert flow_mod.TIER_DAILY_AUD_CAP[t] > 0
    # Ordering invariant: spark < ignition < velocity (cheaper plans cap lower).
    assert (flow_mod.TIER_DAILY_AUD_CAP["spark"]
            < flow_mod.TIER_DAILY_AUD_CAP["ignition"]
            < flow_mod.TIER_DAILY_AUD_CAP["velocity"])
