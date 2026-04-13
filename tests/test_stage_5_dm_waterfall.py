"""Tests for Stage5DMWaterfall — Directive #263"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.pipeline.stage_5_dm_waterfall import (
    Stage5DMWaterfall, DMResult, GMBContactExtractor,
    WebsiteContactScraper, LeadmagicPersonFinder,
    PIPELINE_STAGE_S5, DM_SOURCE_NONE,
)
from src.enrichment.signal_config import SignalConfig, ServiceSignal


# ─── Fixtures ────────────────────────────────────────────────────────────────

def make_config():
    import uuid
    return SignalConfig(
        id=str(uuid.uuid4()), vertical="marketing_agency",
        services=[ServiceSignal("paid_ads", "Paid Ads", ["Google Ads"], [], {})],
        discovery_config={},
        enrichment_gates={"min_score_to_enrich": 30, "min_score_to_dm": 50, "min_score_to_outreach": 65},
        competitor_config={},
        channel_config={},
        created_at=datetime.now(), updated_at=datetime.now(),
    )


def make_row(**overrides):
    defaults = {
        "id": "uuid-1", "domain": "acme.com.au",
        "display_name": "Acme Marketing", "phone": "+61 3 1234 5678",
        "address": "123 Main St", "gmb_place_id": "ChIJ123",
        "propensity_score": 65, "reachability_score": 40,
        "dm_email": None, "dm_phone": None,
    }
    defaults.update(overrides)
    row = MagicMock()
    row.__iter__ = lambda self: iter(defaults.items())
    row.__getitem__ = lambda self, k: defaults[k]
    row.get = lambda k, d=None: defaults.get(k, d)
    row.keys = lambda: defaults.keys()
    return row


def make_conn(rows=None):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[make_row()] if rows is None else rows)
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_lm_client(employees=None, email="dm@acme.com.au"):
    lm = MagicMock()
    lm.find_employees = AsyncMock(return_value=employees or [
        {"first_name": "John", "last_name": "Smith", "title": "Director", "linkedin_url": "https://linkedin.com/in/jsmith"}
    ])
    lm.find_email = AsyncMock(return_value={"email": email})
    lm.find_by_role = AsyncMock(return_value=None)
    return lm


def make_stage(rows=None, lm_client=None, extra_sources=None):
    conn = make_conn(rows)
    lm = lm_client or make_lm_client()
    signal_repo = MagicMock()
    signal_repo.get_config = AsyncMock(return_value=make_config())
    stage = Stage5DMWaterfall(lm, signal_repo, conn, extra_sources=extra_sources)
    return stage, conn, signal_repo


# ─── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_finds_dm_from_gmb_first():
    """GMBContactExtractor is tried first; waterfall stops on first valid result."""
    mock_source = MagicMock()
    mock_source.source_name = "gmb"
    mock_source.find = AsyncMock(return_value=DMResult(
        name="Jane Owner", email="jane@biz.com.au", source="gmb"
    ))
    stage, conn, _ = make_stage()
    stage.sources = [mock_source]
    result = await stage.run("marketing_agency")
    assert result["found"] == 1
    mock_source.find.assert_called_once()


@pytest.mark.asyncio
async def test_waterfall_gmb_then_leadmagic_only():
    """Waterfall has exactly 2 sources: GMB then Leadmagic. No Jina/website."""
    lm = MagicMock()
    signal_repo = MagicMock()
    conn = MagicMock()
    stage = Stage5DMWaterfall(lm, signal_repo, conn)
    source_names = [s.source_name for s in stage.sources]
    assert "gmb" in source_names[0].lower() or "gmb" in type(stage.sources[0]).__name__.lower()
    assert "leadmagic" in source_names[-1].lower() or "leadmagic" in type(stage.sources[-1]).__name__.lower()
    assert not any("website" in n.lower() or "jina" in n.lower() for n in source_names)


@pytest.mark.asyncio
async def test_falls_through_to_leadmagic():
    """Both free sources return None → Leadmagic is tried."""
    source_1 = MagicMock(source_name="gmb")
    source_1.find = AsyncMock(return_value=None)
    source_2 = MagicMock(source_name="website")
    source_2.find = AsyncMock(return_value=None)
    source_3 = MagicMock(source_name="leadmagic")
    source_3.find = AsyncMock(return_value=DMResult(
        name="Alice CEO", email="alice@acme.com.au", source="leadmagic"
    ))
    stage, conn, _ = make_stage()
    stage.sources = [source_1, source_2, source_3]
    result = await stage.run("marketing_agency")
    assert result["found"] == 1
    assert result["sources_used"]["leadmagic"] == 1


@pytest.mark.asyncio
async def test_stops_at_first_successful_source():
    """Waterfall stops after first valid result — subsequent sources not called."""
    source_1 = MagicMock(source_name="cheap")
    source_1.find = AsyncMock(return_value=DMResult(
        name="Winner", email="w@biz.com.au", source="cheap"
    ))
    source_2 = MagicMock(source_name="expensive")
    source_2.find = AsyncMock(return_value=None)
    stage, conn, _ = make_stage()
    stage.sources = [source_1, source_2]
    await stage.run("marketing_agency")
    source_2.find.assert_not_called()


@pytest.mark.asyncio
async def test_handles_no_dm_found():
    """All sources fail → row still progresses to stage 5 (BU pipeline state updated)."""
    source = MagicMock(source_name="gmb")
    source.find = AsyncMock(return_value=None)
    stage, conn, _ = make_stage()
    stage.sources = [source]
    result = await stage.run("marketing_agency")
    assert result["not_found"] == 1
    # #338-PART-B: BU update only sets pipeline_stage + reachability, no dm_* fields
    conn.execute.assert_called_once()
    args = conn.execute.call_args[0]
    assert PIPELINE_STAGE_S5 in args


@pytest.mark.asyncio
async def test_respects_enrichment_gate_threshold():
    """Only rows with propensity_score >= min_score_to_dm are processed."""
    stage, conn, _ = make_stage()
    await stage.run("marketing_agency", batch_size=25)
    fetch_sql = conn.fetch.call_args[0][0]
    assert "propensity_score >= $1" in fetch_sql
    assert conn.fetch.call_args[0][1] == 50  # min_score_to_dm


@pytest.mark.asyncio
async def test_skips_below_threshold_businesses():
    """DB query filters low-propensity rows — they don't enter the waterfall."""
    stage, conn, _ = make_stage(rows=[])  # empty = nothing above threshold
    result = await stage.run("marketing_agency")
    assert result["found"] == 0
    assert result["not_found"] == 0


@pytest.mark.asyncio
async def test_recalculates_reachability_after_dm():
    """Reachability score is updated after DM is found with email + phone."""
    source = MagicMock(source_name="leadmagic")
    source.find = AsyncMock(return_value=DMResult(
        name="Sue Director", email="sue@biz.com.au", phone="+61412345678", source="leadmagic"
    ))
    stage, conn, _ = make_stage()
    stage.sources = [source]
    await stage.run("marketing_agency")
    args = conn.execute.call_args[0]
    # email(30) + phone(25) + address(15) + gmb(10) = 80
    assert 80 in args


@pytest.mark.asyncio
async def test_tracks_cost_per_source():
    """sources_used dict tracks which sources were used."""
    source = MagicMock(source_name="leadmagic")
    source.find = AsyncMock(return_value=DMResult(
        name="Dan Owner", email="dan@biz.com.au", source="leadmagic"
    ))
    stage, conn, _ = make_stage()
    stage.sources = [source]
    result = await stage.run("marketing_agency")
    assert "leadmagic" in result["sources_used"]
    assert result["sources_used"]["leadmagic"] == 1


@pytest.mark.asyncio
async def test_respects_batch_size():
    """run() passes batch_size to DB query."""
    stage, conn, _ = make_stage()
    await stage.run("marketing_agency", batch_size=10)
    assert conn.fetch.call_args[0][2] == 10  # LIMIT $2


@pytest.mark.asyncio
async def test_waterfall_is_extensible():
    """extra_sources parameter adds sources to the waterfall."""
    extra = MagicMock(source_name="bd_linkedin")
    extra.find = AsyncMock(return_value=None)
    stage, conn, _ = make_stage(extra_sources=[extra])
    assert any(s.source_name == "bd_linkedin" for s in stage.sources)
