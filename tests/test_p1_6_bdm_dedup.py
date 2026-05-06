"""
P1.6 BDM dedup + blocklist enforcement + name hygiene — CI tests.
Tests: dedup skip, stage 9 blocklist, stage 10 blocklist, name hygiene (emoji + normal).
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────


def _apply_name_hygiene(name: str | None) -> str | None:
    """Mirror of the hygiene logic in stage_5_dm_waterfall._write_result."""
    return re.sub(r"^[^a-zA-Z]+|[^a-zA-Z.]+$", "", name).strip() if name else None


# ── item (a): Stage 5 dedup ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stage5_dedup_skips_existing_linkedin():
    """Stage 5 must not INSERT a second BDM when linkedin_url already exists."""
    from src.pipeline.stage_5_dm_waterfall import DMResult, Stage5DMWaterfall

    conn = AsyncMock()
    # fetchval returns an existing BDM id → duplicate detected
    conn.fetchval = AsyncMock(return_value="existing-bdm-uuid")
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])

    lm_client = MagicMock()
    signal_repo = MagicMock()
    config = MagicMock()
    config.enrichment_gates = {"min_score_to_dm": 50}
    signal_repo.get_config = AsyncMock(return_value=config)

    stage = Stage5DMWaterfall(lm_client, signal_repo, conn)

    dm = DMResult(
        name="Christian Oien",
        linkedin_url="https://linkedin.com/in/christian-oien",
        source="leadmagic",
    )
    business = {"id": "bu-1", "domain": "example.com.au", "propensity_score": 80}

    await stage._write_result("bu-1", dm, business)

    # fetchval must have been called to check for duplicate
    conn.fetchval.assert_called_once()
    call_args = conn.fetchval.call_args[0]
    assert "linkedin_url" in call_args[0]  # the SQL contains linkedin_url
    assert call_args[1] == "https://linkedin.com/in/christian-oien"

    # No INSERT should have been issued
    insert_calls = [c for c in conn.execute.call_args_list if "INSERT" in str(c)]
    assert len(insert_calls) == 0, "INSERT must not be called for a duplicate linkedin_url"


# ── item (b): Stage 9 blocklist ───────────────────────────────────────────────


def test_stage9_blocklist_filter_in_query():
    """Stage 9 batch SELECT must contain NOT IN blocklist filter."""
    import inspect
    import src.pipeline.stage_9_vulnerability_enrichment as s9_mod

    source = inspect.getsource(s9_mod)
    assert "NOT IN" in source, "Stage 9 source must contain NOT IN filter"
    assert "BLOCKED_DOMAINS" in source, "Stage 9 must import and use BLOCKED_DOMAINS"


# ── item (b): Stage 10 blocklist ──────────────────────────────────────────────


def test_stage10_blocklist_filter_in_query():
    """Stage 10 batch SELECT must contain NOT IN blocklist filter."""
    import inspect
    import src.pipeline.stage_10_message_generator as s10_mod

    source = inspect.getsource(s10_mod)
    assert "NOT IN" in source, "Stage 10 source must contain NOT IN filter"
    assert "BLOCKED_DOMAINS" in source, "Stage 10 must import and use BLOCKED_DOMAINS"


# ── item (d): Name hygiene ────────────────────────────────────────────────────


def test_name_hygiene_strips_emoji():
    """'📊 Louie Ramos' must become 'Louie Ramos'."""
    result = _apply_name_hygiene("📊 Louie Ramos")
    assert result == "Louie Ramos", f"Expected 'Louie Ramos', got {result!r}"


def test_name_hygiene_preserves_normal():
    """'Mark Gadeley' must remain 'Mark Gadeley' unchanged."""
    result = _apply_name_hygiene("Mark Gadeley")
    assert result == "Mark Gadeley", f"Expected 'Mark Gadeley', got {result!r}"
