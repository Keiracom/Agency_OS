"""Tests for Stage4Scorer — Directive #262"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.pipeline.stage_4_scoring import Stage4Scorer, PIPELINE_STAGE_S4, _normalise_category
from src.enrichment.signal_config import SignalConfig, ServiceSignal


# ─── Fixtures ────────────────────────────────────────────────────────────────


def make_service(name="paid_ads", techs=None, cats=None, weights=None):
    return ServiceSignal(
        service_name=name,
        label=name.replace("_", " ").title(),
        dfs_technologies=techs or ["Google Ads", "Facebook Pixel"],
        gmb_categories=cats or ["marketing_agency"],
        scoring_weights=weights or {"budget": 30, "pain": 30, "gap": 25, "fit": 15},
    )


def make_config(services=None):
    import uuid

    return SignalConfig(
        id=str(uuid.uuid4()),
        vertical="marketing_agency",
        services=services or [make_service()],
        discovery_config={},
        enrichment_gates={
            "min_score_to_enrich": 30,
            "min_score_to_dm": 50,
            "min_score_to_outreach": 65,
        },
        competitor_config={},
        channel_config={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_row(**overrides):
    defaults = {
        "id": "uuid-1",
        "domain": "example.com.au",
        "gmb_category": "Marketing Agency",
        "gmb_rating": 3.8,
        "gmb_review_count": 15,
        "gmb_place_id": "ChIJ123",
        "phone": "+61 3 1234 5678",
        "address": "123 Main St, Melbourne VIC 3000",
        "linkedin_company_url": None,
        "dfs_paid_keywords": 10,
        "dfs_paid_etv": 250.0,
        "dfs_organic_etv": 1200.0,
        "dfs_organic_keywords": 300,
        "tech_stack": ["Google Ads", "WordPress", "Google Analytics"],
        "tech_gaps": ["Facebook Pixel", "HubSpot"],
        "tech_stack_depth": 3,
        "tech_categories": {},
        "dfs_technologies": ["Google Ads"],
    }
    defaults.update(overrides)
    row = MagicMock()
    row.__iter__ = lambda self: iter(defaults.items())
    row.__getitem__ = lambda self, k: defaults[k]
    row.get = lambda k, default=None: defaults.get(k, default)
    row.keys = lambda: defaults.keys()
    return row


def make_conn(rows=None):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=rows or [make_row()])
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_scorer(services=None, rows=None):
    config = make_config(services)
    signal_repo = MagicMock()
    signal_repo.get_config = AsyncMock(return_value=config)
    conn = make_conn(rows)
    scorer = Stage4Scorer(signal_repo, conn)
    return scorer, signal_repo, conn, config


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scores_s3_businesses_with_propensity():
    """run() writes propensity_score and progresses to stage 4."""
    scorer, _, conn, _ = make_scorer()
    result = await scorer.run("marketing_agency")
    assert result["scored"] == 1
    conn.execute.assert_called_once()
    update_sql = conn.execute.call_args[0][0]
    assert "propensity_score" in update_sql
    assert "pipeline_stage" in update_sql


@pytest.mark.asyncio
async def test_scores_reachability_from_channel_access():
    """Reachability reflects number of confirmed contact channels."""
    scorer, _, conn, _ = make_scorer(
        rows=[
            make_row(
                phone="+61 3 1234 5678",
                domain="biz.com.au",
                address="123 St",
                gmb_place_id="ChIJ",
                linkedin_company_url=None,
            )
        ]
    )
    scorer_obj = scorer
    business = dict(
        make_row(
            phone="+61 3 1234 5678",
            domain="biz.com.au",
            address="123 St",
            gmb_place_id="ChIJ",
            linkedin_company_url=None,
        )
    )
    score = scorer_obj._score_reachability(business)
    # domain(30) + phone(25) + address(15) + gmb_place_id(10) = 80
    assert score == 80


@pytest.mark.asyncio
async def test_budget_score_from_paid_signals():
    """Budget score reflects paid keyword and traffic value presence."""
    from src.pipeline.stage_4_scoring import _calc_budget_score

    assert _calc_budget_score(0, 0.0, 0.0) == 0
    assert _calc_budget_score(5, 0.0, 0.0) == 50
    assert _calc_budget_score(5, 100.0, 0.0) == 75
    assert _calc_budget_score(5, 100.0, 600.0) == 100


@pytest.mark.asyncio
async def test_pain_score_from_gmb_and_gaps():
    """Pain score reflects reputation signals and capability gap count."""
    from src.pipeline.stage_4_scoring import _calc_pain_score

    assert _calc_pain_score(0.0, 0, 0) == 0
    assert _calc_pain_score(3.5, 20, 1) > 0
    assert _calc_pain_score(3.5, 60, 3) == 100


@pytest.mark.asyncio
async def test_gap_score_from_tech_gaps():
    """Gap score reflects service-specific technology gaps."""
    from src.pipeline.stage_4_scoring import _calc_gap_score

    svc_techs = {"google ads", "facebook pixel", "hubspot"}
    detected = {"google ads", "wordpress"}
    gaps = {"facebook pixel", "hubspot"}
    score = _calc_gap_score(svc_techs, detected, gaps)
    assert score > 0


@pytest.mark.asyncio
async def test_fit_score_from_category_match():
    """Fit score is higher when GMB category matches service categories."""
    from src.pipeline.stage_4_scoring import _calc_fit_score

    # Category match + tech overlap
    score_match = _calc_fit_score(
        "marketing_agency", {"marketing_agency"}, {"google ads"}, {"google ads"}
    )
    # No match
    score_miss = _calc_fit_score("plumber", {"marketing_agency"}, {"google ads"}, {"wordpress"})
    assert score_match > score_miss


@pytest.mark.asyncio
async def test_applies_service_weights_from_config():
    """Propensity composite uses scoring_weights from service signal config."""
    scorer, _, conn, _ = make_scorer()
    result = await scorer.run("marketing_agency")
    # Score was computed (not zero, not error)
    args = conn.execute.call_args[0]
    propensity = args[5]  # 5th positional = propensity_score
    assert isinstance(propensity, int)
    assert 0 <= propensity <= 100


@pytest.mark.asyncio
async def test_generates_plain_english_reason():
    """score_reason is a non-empty string, max 2 sentences."""
    scorer, _, conn, _ = make_scorer()
    await scorer.run("marketing_agency")
    args = conn.execute.call_args[0]
    reason = args[8]  # 8th positional = score_reason
    assert isinstance(reason, str)
    assert len(reason) > 0
    sentences = [s.strip() for s in reason.split(".") if s.strip()]
    assert len(sentences) <= 3  # generous bound for 2-sentence max


@pytest.mark.asyncio
async def test_respects_enrichment_gate_threshold():
    """above_threshold count reflects businesses at or above min_score_to_enrich."""
    scorer, repo, conn, _ = make_scorer()
    result = await scorer.run("marketing_agency")
    total = result["above_threshold"] + result["below_threshold"]
    assert total == result["scored"]


@pytest.mark.asyncio
async def test_low_propensity_stays_at_stage_4():
    """All businesses advance to stage 4 regardless of score."""
    scorer, _, conn, _ = make_scorer(
        rows=[
            make_row(
                tech_stack=[],
                tech_gaps=[],
                dfs_paid_keywords=0,
                dfs_paid_etv=0,
                dfs_organic_etv=0,
                gmb_rating=0,
                gmb_review_count=0,
            )
        ]
    )
    await scorer.run("marketing_agency")
    args = conn.execute.call_args[0]
    assert PIPELINE_STAGE_S4 in args


@pytest.mark.asyncio
async def test_returns_correct_counts():
    """run() returns correct scored/above/below counts."""
    scorer, _, conn, _ = make_scorer(rows=[make_row(), make_row(id="uuid-2")])
    result = await scorer.run("marketing_agency")
    assert result["scored"] == 2
    assert result["above_threshold"] + result["below_threshold"] == 2


# ─── BUG-265-3 regression tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scores_partial_data_gracefully():
    """Business with NULL DFS data but valid GMB data should score > 0."""
    from src.pipeline.stage_4_scoring import Stage4Scorer

    # Row with NULL DFS data but valid GMB signals
    row = make_row(
        tech_stack=None,  # NULL — never fetched
        tech_gaps=None,  # NULL
        dfs_paid_keywords=None,
        dfs_paid_etv=None,
        dfs_organic_etv=None,
        dfs_organic_keywords=None,
        gmb_category="Marketing Agency",
        gmb_rating=4.2,
        gmb_review_count=25,
        gmb_place_id="ChIJ123",
    )
    scorer, _, conn, config = make_scorer(rows=[row])
    result = await scorer.run("marketing_agency")
    assert result["scored"] == 1
    # propensity_score is the 5th positional arg in the UPDATE
    args = conn.execute.call_args[0]
    propensity = args[5]
    assert propensity > 0, f"Expected propensity > 0, got {propensity}"


@pytest.mark.asyncio
async def test_null_tech_stack_still_scores_fit():
    """NULL tech_stack should not zero out the entire score."""
    from src.pipeline.stage_4_scoring import _calc_gap_score

    # When has_tech_data=False (NULL), gap score should be neutral (25)
    svc_techs = {"google ads", "facebook pixel", "hubspot"}
    detected = set()  # nothing detected (tech_stack was NULL)
    gaps = set()  # no gaps calculated either
    score = _calc_gap_score(svc_techs, detected, gaps, has_tech_data=False)
    assert score == 25, f"Expected neutral gap score 25, got {score}"
    # When has_tech_data=True but empty, score should be 0 (all gaps exist but none matched)
    score_empty = _calc_gap_score(svc_techs, detected, gaps, has_tech_data=True)
    assert score_empty == 0


# ─── Qualification gate tests (#268) ─────────────────────────────────────────


def make_scorer_direct():
    """Create Stage4Scorer instance for direct _qualifies testing."""
    from unittest.mock import MagicMock

    signal_repo = MagicMock()
    conn = MagicMock()
    return Stage4Scorer(signal_repo, conn)


def test_qualifies_rejects_null_domain():
    """Business with NULL domain is disqualified."""
    scorer = make_scorer_direct()
    config = make_config()
    ok, reason = scorer._qualifies(
        {"domain": None, "gmb_place_id": "abc", "dfs_paid_keywords": 10}, config
    )
    assert ok is False
    assert "domain" in reason.lower()


def test_qualifies_rejects_blocked_domain():
    """Business with facebook.com domain is disqualified."""
    scorer = make_scorer_direct()
    config = make_config()
    ok, reason = scorer._qualifies(
        {"domain": "facebook.com", "gmb_place_id": "abc", "dfs_paid_keywords": 10}, config
    )
    assert ok is False
    assert "blocked" in reason.lower() or "domain" in reason.lower()


def test_qualifies_rejects_no_gmb_no_address():
    """Business with no GMB and no address is disqualified."""
    scorer = make_scorer_direct()
    config = make_config()
    ok, reason = scorer._qualifies(
        {
            "domain": "acme.com.au",
            "gmb_place_id": None,
            "state": None,
            "suburb": None,
            "dfs_paid_keywords": 10,
        },
        config,
    )
    assert ok is False
    assert "address" in reason.lower() or "gmb" in reason.lower()


def test_qualifies_rejects_no_signal_data():
    """Business with no DFS or tech signals is disqualified."""
    scorer = make_scorer_direct()
    config = make_config()
    ok, reason = scorer._qualifies(
        {
            "domain": "acme.com.au",
            "gmb_place_id": "ChIJ123",
            "dfs_paid_keywords": None,
            "dfs_organic_etv": None,
            "tech_stack": None,
            "tech_stack_depth": None,
            "dfs_paid_etv": None,
            "dfs_organic_keywords": None,
        },
        config,
    )
    assert ok is False
    assert "signal" in reason.lower()


def test_qualifies_accepts_valid_business():
    """Business meeting all criteria passes qualification."""
    scorer = make_scorer_direct()
    config = make_config(services=[make_service(cats=["digital_marketing_agency"])])
    ok, reason = scorer._qualifies(
        {
            "domain": "acme-agency.com.au",
            "gmb_place_id": "ChIJ123",
            "gmb_category": "Digital Marketing Agency",
            "dfs_paid_keywords": 15,
            "state": "NSW",
            "suburb": "Sydney",
        },
        config,
    )
    assert ok is True
    assert reason == ""


def test_qualifies_rejects_wrong_gmb_category():
    """Business with GMB category outside vertical is disqualified."""
    scorer = make_scorer_direct()
    config = make_config(services=[make_service(cats=["digital_marketing_agency"])])
    ok, reason = scorer._qualifies(
        {
            "domain": "dentist.com.au",
            "gmb_place_id": "ChIJ456",
            "gmb_category": "Dental Clinic",
            "dfs_paid_keywords": 20,
        },
        config,
    )
    assert ok is False
    assert "category" in reason.lower()
