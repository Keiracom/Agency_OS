"""Tests for src/orchestration/flows/bu_closed_loop_flow.py.

Hermetic — no live DB, no live Prefect server. asyncpg pool + cohort_runner
stage callables are mocked. Verifies:
  - _classify_row routes free / paid / unrecoverable rows correctly
  - free_mode_only=True blocks paid stages (Stage 8 → 9 via _run_stage9 / bd)
  - free_mode_only=True allows free stages (Stage 4 → 5 via _run_stage5)
  - bu_closed_loop_flow advances rows through STAGE_ADVANCEMENT and writes
    pipeline_stage + stage_metrics->stage_completed_at
  - stuck reasons surface in summary
"""
from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Provide DATABASE_URL so the flow's _open_pool() does not raise at import-call.
# We monkeypatch _open_pool itself for isolation, but the env var still needs
# to be readable in the lazy code path.
os.environ.setdefault("DATABASE_URL", "postgresql://stub:stub@stub:5432/stub")

from src.orchestration.flows import bu_closed_loop_flow as flow_mod  # noqa: E402


# ── _classify_row unit tests ────────────────────────────────────────────────

def test_classify_row_pre_enrichment_advances_via_free_enrichment_s3():
    """S3 — stage 0 / NULL no longer skipped. Routes to the free_enrichment
    pseudo-runner so the closed-loop driver actually fires Stage 1."""
    row = {"pipeline_stage": 0, "domain": "x.com.au", "propensity_score": 80}
    out = flow_mod._classify_row(row, free_mode_only=True)
    assert out["action"] == "advance"
    assert out["runner"] == "free_enrichment"
    assert out["next_stage"] == 1
    # Stage NULL should be coerced to 0 and routed identically.
    row_null = {"pipeline_stage": None, "domain": "y.com.au", "propensity_score": 80}
    out_null = flow_mod._classify_row(row_null, free_mode_only=True)
    assert out_null["action"] == "advance"
    assert out_null["runner"] == "free_enrichment"


def test_classify_row_terminal_stage_skipped():
    row = {"pipeline_stage": 11, "domain": "x.com.au", "propensity_score": 80}
    out = flow_mod._classify_row(row, free_mode_only=True)
    assert out["action"] == "skip"
    assert "terminal" in out["reason"]


def test_classify_row_free_stage_4_to_5_advances_under_free_mode():
    row = {"pipeline_stage": 4, "domain": "x.com.au", "propensity_score": 60}
    out = flow_mod._classify_row(row, free_mode_only=True)
    assert out["action"] == "advance"
    assert out["next_stage"] == 5
    assert out["runner"] == "_run_stage5"
    assert out["is_free"] is True


def test_classify_row_paid_stage_7_to_9_blocked_under_free_mode():
    """Stage 7 → 9 needs Bright Data; free_mode_only must refuse it."""
    row = {"pipeline_stage": 7, "domain": "x.com.au", "propensity_score": 80}
    out = flow_mod._classify_row(row, free_mode_only=True)
    assert out["action"] == "skip"
    assert "blocked_by_free_mode" in out["reason"]
    assert "_run_stage9" in out["reason"]


def test_classify_row_paid_stage_7_to_9_allowed_when_free_mode_off():
    row = {"pipeline_stage": 7, "domain": "x.com.au", "propensity_score": 80}
    out = flow_mod._classify_row(row, free_mode_only=False)
    assert out["action"] == "advance"
    assert out["runner"] == "_run_stage9"
    assert out["is_free"] is False


def test_classify_row_unmapped_stage_skipped():
    row = {"pipeline_stage": 99, "domain": "x.com.au", "propensity_score": 80}
    out = flow_mod._classify_row(row, free_mode_only=True)
    assert out["action"] == "skip"
    assert "no_advancement_path" in out["reason"]


# ── advance_row + _invoke_runner integration tests ──────────────────────────

def _make_pool(execute_calls: list) -> MagicMock:
    conn = MagicMock()
    async def _capture_execute(*args, **kwargs):
        execute_calls.append(args)
        return None
    conn.execute = AsyncMock(side_effect=_capture_execute)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=cm)
    pool.close = AsyncMock(return_value=None)
    return pool


def test_advance_row_writes_pipeline_stage_on_success():
    execute_calls: list = []
    pool = _make_pool(execute_calls)

    row = {"id": "11111111-1111-1111-1111-111111111111",
           "domain": "ex.com.au", "category": "dental", "pipeline_stage": 4}
    plan = {"next_stage": 5, "runner": "_run_stage5", "clients": [], "is_free": True}

    fake_runner = AsyncMock(return_value={"domain": "ex.com.au"})  # no dropped_at
    with patch("src.orchestration.cohort_runner._run_stage5", fake_runner):
        result = asyncio.run(
            flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": None})
        )

    assert result["outcome"] == "advanced"
    assert result["from_stage"] == 4
    assert result["to_stage"] == 5
    # The UPDATE SQL should advance pipeline_stage and stamp the marker.
    assert any("pipeline_stage = $2" in str(c[0]) for c in execute_calls)
    # Marker key passed as third positional arg ($3 in SQL).
    marker_calls = [c for c in execute_calls if "stage_completed_at" in str(c[0])]
    assert marker_calls, "expected stage_completed_at write"
    assert any("stage_5" == c[3] for c in marker_calls if len(c) >= 4)


def test_advance_row_records_runner_early_exit():
    """If the runner returns dropped_at, advance_row marks an attempt without
    advancing pipeline_stage."""
    execute_calls: list = []
    pool = _make_pool(execute_calls)

    row = {"id": "22222222-2222-2222-2222-222222222222",
           "domain": "ex.com.au", "category": "legal", "pipeline_stage": 4}
    plan = {"next_stage": 5, "runner": "_run_stage5", "clients": [], "is_free": True}

    fake_runner = AsyncMock(return_value={
        "domain": "ex.com.au",
        "dropped_at": "stage5",
        "drop_reason": "missing_prereqs",
    })
    with patch("src.orchestration.cohort_runner._run_stage5", fake_runner):
        result = asyncio.run(
            flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": None})
        )

    assert result["outcome"] == "runner_early_exit"
    assert result["reason"] == "missing_prereqs"
    # pipeline_stage NOT advanced.
    assert not any("pipeline_stage = $2" in str(c[0]) for c in execute_calls)
    # bu_closed_loop_attempt marker is written instead.
    assert any("bu_closed_loop_attempt" in str(c[0]) for c in execute_calls)


def test_advance_row_handles_runner_exception():
    execute_calls: list = []
    pool = _make_pool(execute_calls)
    row = {"id": "33333333-3333-3333-3333-333333333333",
           "domain": "ex.com.au", "category": "fitness", "pipeline_stage": 4}
    plan = {"next_stage": 5, "runner": "_run_stage5", "clients": [], "is_free": True}

    fake_runner = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("src.orchestration.cohort_runner._run_stage5", fake_runner):
        result = asyncio.run(
            flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": None})
        )

    assert result["outcome"] == "error"
    assert "RuntimeError" in result["reason"]


# ── End-to-end flow test with mocked DB + cohort runner ─────────────────────

def test_flow_advances_free_rows_and_blocks_paid_rows():
    """Mixed batch: one stage-4 row (free → advances) + one stage-7 row
    (paid → blocked by free mode). Summary should reflect both outcomes."""
    rows = [
        {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
         "domain": "free.com.au", "category": "dental",
         "pipeline_stage": 4, "propensity_score": 90,
         "stage_metrics": {}, "filter_reason": None,
         "latest_stage_at": None, "propensity_tier": "hot"},
        {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
         "domain": "paid.com.au", "category": "legal",
         "pipeline_stage": 7, "propensity_score": 80,
         "stage_metrics": {}, "filter_reason": None,
         "latest_stage_at": None, "propensity_tier": "hot"},
    ]

    execute_calls: list = []
    pool = _make_pool(execute_calls)

    fake_open_pool = AsyncMock(return_value=pool)
    fake_fetch_backlog = AsyncMock(return_value=rows)
    fake_stage5 = AsyncMock(return_value={"domain": "free.com.au"})

    with patch.object(flow_mod, "_open_pool", fake_open_pool), \
         patch.object(flow_mod.fetch_backlog, "fn", fake_fetch_backlog), \
         patch("src.orchestration.cohort_runner._run_stage5", fake_stage5):
        # Patch GeminiClient init so the lazy import does not raise on
        # missing API key in the test environment.
        with patch("src.intelligence.gemini_client.GeminiClient",
                   return_value=MagicMock()):
            summary = asyncio.run(flow_mod.bu_closed_loop_flow.fn(
                max_rows=10,
                free_mode_only=True,
            ))

    assert summary["queried"] == 2
    # Free row advanced from stage 4 → 5.
    assert summary["advanced_per_stage"].get("stage_4_to_5") == 1
    # Paid row blocked.
    blocked = [k for k in summary["stuck_per_reason"]
               if "blocked_by_free_mode" in k]
    assert blocked, f"expected paid-stage block; got {summary['stuck_per_reason']}"
    assert summary["free_mode_only"] is True
    assert summary["cadence_days"] == {"hot": 14, "warm": 60, "cold": 180}


def test_flow_advances_pre_enrichment_rows_via_free_enrichment_s3():
    """S3 — stage 1 row routes to free_enrichment runner and advances on
    success. Free_enrichment is mocked at module surface so no real DNS /
    httpx / abn_registry I/O happens."""
    rows = [{"id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
             "domain": "early.com.au", "category": "x",
             "pipeline_stage": 1, "propensity_score": 30,
             "stage_metrics": {}, "filter_reason": None,
             "latest_stage_at": None, "propensity_tier": "cold"}]

    execute_calls: list = []
    pool = _make_pool(execute_calls)

    fake_invoke = AsyncMock(side_effect=lambda d: d)  # no-op; success path

    with patch.object(flow_mod, "_open_pool", AsyncMock(return_value=pool)), \
         patch.object(flow_mod.fetch_backlog, "fn", AsyncMock(return_value=rows)), \
         patch.object(flow_mod, "_invoke_free_enrichment", fake_invoke), \
         patch("src.intelligence.gemini_client.GeminiClient",
               return_value=MagicMock()):
        summary = asyncio.run(flow_mod.bu_closed_loop_flow.fn(max_rows=10))

    assert summary["queried"] == 1
    assert summary["advanced_per_stage"].get("stage_1_to_1") == 1
    fake_invoke.assert_awaited_once()


# ── S2-1 — runner_early_exit must NOT touch stage_completed_at ──────────────

def test_s2_1_runner_early_exit_writes_to_attempts_array_not_stage_completed_at():
    """Regression for S2-1: an early-exit must record into
    stage_metrics.bu_closed_loop_attempts (an array of {ts, reason, runner})
    and must leave stage_metrics.stage_completed_at untouched so the cursor's
    MAX-age computation only counts real stage completions."""
    execute_calls: list = []
    pool = _make_pool(execute_calls)

    row = {"id": "44444444-4444-4444-4444-444444444444",
           "domain": "earlyexit.com.au", "category": "x", "pipeline_stage": 4}
    plan = {"next_stage": 5, "runner": "_run_stage5", "clients": [], "is_free": True}

    fake_runner = AsyncMock(return_value={
        "domain": "earlyexit.com.au",
        "dropped_at": "stage5",
        "drop_reason": "missing_prereqs",
    })
    with patch("src.orchestration.cohort_runner._run_stage5", fake_runner):
        result = asyncio.run(
            flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": None})
        )

    assert result["outcome"] == "runner_early_exit"
    # Exactly one UPDATE for the early-exit path.
    assert len(execute_calls) == 1
    sql = execute_calls[0][0]
    # Must write into bu_closed_loop_attempts, not stage_completed_at.
    assert "bu_closed_loop_attempts" in sql
    assert "stage_completed_at" not in sql
    assert "pipeline_stage" not in sql  # pipeline_stage NOT advanced
    # The appended JSON entry must carry ts + reason + runner.
    appended = execute_calls[0][2]
    import json as _json
    payload = _json.loads(appended)
    assert set(payload.keys()) == {"ts", "reason", "runner"}
    assert payload["reason"] == "missing_prereqs"
    assert payload["runner"] == "_run_stage5"


# ── S2-2 — free-mode paid-data-skipped marker on 4->5 / 6->7 ────────────────

def test_s2_2_free_mode_4_to_5_writes_paid_skip_marker():
    """When advancement bypasses paid stage 4, BU must record
    stage_metrics.free_mode_paid_data_skipped with stage=4."""
    execute_calls: list = []
    pool = _make_pool(execute_calls)

    row = {"id": "55555555-5555-5555-5555-555555555555",
           "domain": "skip4.com.au", "category": "dental", "pipeline_stage": 4}
    plan = {"next_stage": 5, "runner": "_run_stage5", "clients": [], "is_free": True}

    fake_runner = AsyncMock(return_value={"domain": "skip4.com.au"})
    with patch("src.orchestration.cohort_runner._run_stage5", fake_runner):
        result = asyncio.run(
            flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": None})
        )

    assert result["outcome"] == "advanced"
    assert result["paid_data_skipped_stage"] == 4
    sql = execute_calls[0][0]
    assert "free_mode_paid_data_skipped" in sql
    assert "stage_completed_at" in sql  # still stamps the success marker
    # The appended JSON entry names the bypassed stage.
    import json as _json
    appended = execute_calls[0][4]  # 4-arg form: id, next_stage, stage_key, paid_skip_entry
    payload = _json.loads(appended)
    assert payload["stage"] == 4
    assert "skipped_at" in payload


def test_s2_2_free_mode_6_to_7_writes_paid_skip_marker():
    execute_calls: list = []
    pool = _make_pool(execute_calls)

    row = {"id": "66666666-6666-6666-6666-666666666666",
           "domain": "skip6.com.au", "category": "legal", "pipeline_stage": 6}
    plan = {"next_stage": 7, "runner": "_run_stage7", "clients": ["gemini"], "is_free": True}

    fake_runner = AsyncMock(return_value={"domain": "skip6.com.au"})
    with patch("src.orchestration.cohort_runner._run_stage7", fake_runner):
        result = asyncio.run(
            flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": MagicMock()})
        )

    assert result["outcome"] == "advanced"
    assert result["paid_data_skipped_stage"] == 6
    sql = execute_calls[0][0]
    assert "free_mode_paid_data_skipped" in sql
    import json as _json
    appended = execute_calls[0][4]
    payload = _json.loads(appended)
    assert payload["stage"] == 6


def test_s2_2_no_paid_skip_marker_on_normal_advancement():
    """A 5 -> 7 advancement is free-only; no paid stage was bypassed, so the
    free_mode_paid_data_skipped marker must NOT be written."""
    execute_calls: list = []
    pool = _make_pool(execute_calls)

    row = {"id": "77777777-7777-7777-7777-777777777777",
           "domain": "normal.com.au", "category": "x", "pipeline_stage": 5}
    plan = {"next_stage": 7, "runner": "_run_stage7", "clients": ["gemini"], "is_free": True}

    fake_runner = AsyncMock(return_value={"domain": "normal.com.au"})
    with patch("src.orchestration.cohort_runner._run_stage7", fake_runner):
        result = asyncio.run(
            flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": MagicMock()})
        )

    assert result["outcome"] == "advanced"
    assert result["paid_data_skipped_stage"] is None
    sql = execute_calls[0][0]
    assert "free_mode_paid_data_skipped" not in sql


# ── S2-3 — propensity tier boundaries inclusive on both ends ────────────────

def test_s2_3_propensity_70_is_hot():
    """propensity_score == 70 must classify as 'hot' (>=70), not warm.
    Smoke-tested via the SQL CASE in fetch_backlog by matching the SQL text."""
    import inspect
    src = inspect.getsource(flow_mod.fetch_backlog)
    # Must use >= 70, not > 70.
    assert "COALESCE(propensity_score, 0) >= 70" in src
    assert "COALESCE(propensity_score, 0) > 70" not in src
    # warm boundary stays >= 50.
    assert "COALESCE(propensity_score, 0) >= 50" in src


# ── S2-4 — pre-flight gemini_client_unavailable gate ────────────────────────

def test_s2_4_classify_row_skips_when_gemini_required_but_missing():
    """Stage 5 -> 7 needs gemini. If clients['gemini'] is None, classify_row
    must skip with stuck:gemini_client_unavailable BEFORE the runner is
    invoked."""
    row = {"pipeline_stage": 5, "domain": "x.com.au", "propensity_score": 80}
    out = flow_mod._classify_row(row, free_mode_only=True,
                                 clients={"gemini": None})
    assert out["action"] == "skip"
    assert out["reason"] == "stuck:gemini_client_unavailable"


def test_s2_4_classify_row_advances_when_gemini_available():
    """Same row but gemini present — must advance."""
    row = {"pipeline_stage": 5, "domain": "x.com.au", "propensity_score": 80}
    out = flow_mod._classify_row(row, free_mode_only=True,
                                 clients={"gemini": MagicMock()})
    assert out["action"] == "advance"
    assert out["runner"] == "_run_stage7"


def test_s2_4_classify_row_does_not_block_logic_only_stages_when_gemini_missing():
    """Stage 4 -> 5 is pure-logic — must advance even if gemini is None."""
    row = {"pipeline_stage": 4, "domain": "x.com.au", "propensity_score": 80}
    out = flow_mod._classify_row(row, free_mode_only=True,
                                 clients={"gemini": None})
    assert out["action"] == "advance"
    assert out["runner"] == "_run_stage5"


def test_s2_4_flow_records_gemini_unavailable_when_init_fails():
    """End-to-end: when GeminiClient init raises, the flow continues with
    clients['gemini']=None and the per-row gate logs the skip reason."""
    rows = [{"id": "88888888-8888-8888-8888-888888888888",
             "domain": "needsgem.com.au", "category": "dental",
             "pipeline_stage": 5, "propensity_score": 80,
             "stage_metrics": {}, "filter_reason": None,
             "latest_stage_at": None, "propensity_tier": "hot"}]

    execute_calls: list = []
    pool = _make_pool(execute_calls)

    with patch.object(flow_mod, "_open_pool", AsyncMock(return_value=pool)), \
         patch.object(flow_mod.fetch_backlog, "fn", AsyncMock(return_value=rows)), \
         patch("src.intelligence.gemini_client.GeminiClient",
               side_effect=RuntimeError("no api key")):
        summary = asyncio.run(flow_mod.bu_closed_loop_flow.fn(max_rows=10))

    assert summary["queried"] == 1
    assert summary["advanced_per_stage"] == {}
    assert summary["stuck_per_reason"].get("stuck:gemini_client_unavailable") == 1


# ── S3 — production-grade domain_data reconstruction ─────────────────────────

def test_s3_build_domain_data_pulls_stages_from_stage_metrics_jsonb():
    """High-fidelity path: stage_metrics jsonb carries stage2/3/4/5 from
    prior _persist_stage4_to_bu / pipeline_f_master_flow writes. Reconstruction
    must surface those dicts verbatim."""
    row = {
        "id": "11111111-1111-1111-1111-111111111111",
        "domain": "rich.com.au",
        "category": "dental",
        "stage_metrics": {
            "stage2": {"serp_abn": "12345678901"},
            "stage3": {"business_name": "Rich Dental",
                       "dm_candidate": {"name": "Dr X"}},
            "stage4": {"rank_overview": {"organic_etv": 2500.0,
                                          "organic_keywords": 120}},
            "stage5": {"composite_score": 78, "is_viable_prospect": True},
        },
    }
    dd = flow_mod._build_domain_data(row)
    assert dd["domain"] == "rich.com.au"
    assert dd["category"] == "dental"
    assert dd["stage2"] == {"serp_abn": "12345678901"}
    assert dd["stage3"]["business_name"] == "Rich Dental"
    assert dd["stage4"]["rank_overview"]["organic_etv"] == 2500.0
    assert dd["stage5"]["composite_score"] == 78
    # Mutable scaffolding present for runners to write into.
    assert dd["errors"] == []
    assert dd["cost_usd"] == 0.0
    assert dd["timings"] == {}
    assert dd["dropped_at"] is None


def test_s3_build_domain_data_falls_back_to_bu_columns_when_stage_metrics_empty():
    """Fall-back path: stage_metrics empty (legacy row), reconstruction
    uses BU column scalars to seed stage3 / stage4 / stage5."""
    row = {
        "id": "22222222-2222-2222-2222-222222222222",
        "domain": "legacy.com.au",
        "category": "legal",
        "stage_metrics": {},  # empty
        "trading_name": "Legacy Legal",
        "dm_phone": "+61400000000",
        "linkedin_company_url": "https://linkedin.com/company/legacy",
        "entity_type": "Company",
        "dfs_organic_etv": 1500.0,
        "dfs_organic_keywords": 80,
        "domain_rank": 35,
        "backlinks_count": 50,
        "propensity_score": 65,
        "score_budget": 18,
        "score_pain": 16,
        "score_gap": 17,
        "score_fit": 14,
    }
    dd = flow_mod._build_domain_data(row)
    # stage3 reconstruction.
    assert dd["stage3"]["business_name"] == "Legacy Legal"
    assert dd["stage3"]["dm_candidate"]["phone"] == "+61400000000"
    assert dd["stage3"]["dm_candidate"]["linkedin_url"] == \
        "https://linkedin.com/company/legacy"
    assert dd["stage3"]["entity_type"] == "Company"
    # stage4 reconstruction.
    assert dd["stage4"]["rank_overview"]["organic_etv"] == 1500.0
    assert dd["stage4"]["rank_overview"]["organic_keywords"] == 80
    assert dd["stage4"]["rank_overview"]["rank"] == 35
    assert dd["stage4"]["backlinks"]["backlinks_num"] == 50
    # stage5 reconstruction.
    assert dd["stage5"]["composite_score"] == 65
    assert dd["stage5"]["budget"] == 18


def test_s3_build_domain_data_handles_jsonb_stored_as_string():
    """asyncpg fetch returns JSONB as dict only when the codec is registered.
    Without it, JSONB arrives as a JSON string — reconstruction must coerce."""
    row = {
        "id": "33333333-3333-3333-3333-333333333333",
        "domain": "stringjson.com.au",
        "category": "x",
        "stage_metrics": '{"stage4": {"rank_overview": {"organic_etv": 999.0}}}',
    }
    dd = flow_mod._build_domain_data(row)
    assert dd["stage4"]["rank_overview"]["organic_etv"] == 999.0


# ── S3 — STAGE_ADVANCEMENT now covers stage 0 / 1 → free_enrichment ──────────

def test_s3_stage_advancement_map_includes_stage_0_and_1():
    assert 0 in flow_mod.STAGE_ADVANCEMENT
    assert 1 in flow_mod.STAGE_ADVANCEMENT
    assert flow_mod.STAGE_ADVANCEMENT[0]["runner"] == "free_enrichment"
    assert flow_mod.STAGE_ADVANCEMENT[1]["runner"] == "free_enrichment"
    assert flow_mod.STAGE_ADVANCEMENT[0]["is_free"] is True
    assert flow_mod.STAGE_ADVANCEMENT[1]["is_free"] is True


def test_s3_advance_row_invokes_free_enrichment_runner():
    """advance_row dispatches the free_enrichment runner via the dedicated
    pseudo-runner branch in _invoke_runner."""
    execute_calls: list = []
    pool = _make_pool(execute_calls)

    row = {"id": "44444444-4444-4444-4444-444444444444",
           "domain": "stage0.com.au", "category": "dental",
           "pipeline_stage": 0,
           "stage_metrics": {}}
    plan = {"next_stage": 1, "runner": "free_enrichment",
            "clients": [], "is_free": True}

    fake_free = AsyncMock(side_effect=lambda d: d)  # success: no dropped_at

    with patch.object(flow_mod, "_invoke_free_enrichment", fake_free):
        result = asyncio.run(
            flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": None})
        )

    assert result["outcome"] == "advanced"
    assert result["from_stage"] == 0
    assert result["to_stage"] == 1
    assert result["runner"] == "free_enrichment"
    fake_free.assert_awaited_once()


def test_s3_1_classify_row_skips_already_free_enriched():
    """S3-1 regression — stage 1 row whose free_enrichment_completed_at is
    set must short-circuit with stuck:already_free_enriched BEFORE the
    runner is invoked. Prevents redundant scrapes once bu_closed_loop_flow
    eventually unpauses."""
    from datetime import datetime as _dt
    row = {
        "pipeline_stage": 1,
        "domain": "done.com.au",
        "propensity_score": 80,
        "free_enrichment_completed_at": _dt(2026, 1, 1),
    }
    out = flow_mod._classify_row(row, free_mode_only=True,
                                 clients={"gemini": MagicMock()})
    assert out["action"] == "skip"
    assert out["reason"] == "stuck:already_free_enriched"


def test_s3_1_classify_row_advances_when_free_enrichment_completed_at_is_null():
    """Same row, free_enrichment_completed_at not set → must advance via
    free_enrichment runner (the gate is opt-in)."""
    row = {
        "pipeline_stage": 1,
        "domain": "fresh.com.au",
        "propensity_score": 80,
        "free_enrichment_completed_at": None,
    }
    out = flow_mod._classify_row(row, free_mode_only=True,
                                 clients={"gemini": MagicMock()})
    assert out["action"] == "advance"
    assert out["runner"] == "free_enrichment"


def test_s3_1_classify_row_does_not_short_circuit_non_free_enrichment_stages():
    """The S3-1 gate must only trigger for the free_enrichment runner.
    A stage-4 row with free_enrichment_completed_at set still advances
    via _run_stage5 (not free_enrichment) — must not be falsely skipped."""
    from datetime import datetime as _dt
    row = {
        "pipeline_stage": 4,
        "domain": "downstream.com.au",
        "propensity_score": 80,
        "free_enrichment_completed_at": _dt(2026, 1, 1),
    }
    out = flow_mod._classify_row(row, free_mode_only=True,
                                 clients={"gemini": MagicMock()})
    assert out["action"] == "advance"
    assert out["runner"] == "_run_stage5"


def test_s3_1_fetch_backlog_sql_selects_free_enrichment_completed_at():
    """fetch_backlog must SELECT the column so the row dict carries it
    through to _classify_row's pre-flight gate."""
    import inspect
    src = inspect.getsource(flow_mod.fetch_backlog)
    # Inside the stage_age CTE we now project the column.
    assert "free_enrichment_completed_at" in src
    # Outer SELECT also propagates it onto the result row.
    # (Two appearances expected: once inside CTE, once in outer select.)
    assert src.count("free_enrichment_completed_at") >= 2


def test_s3_advance_row_records_free_enrichment_exception_as_runner_early_exit():
    """Free enrichment exception path: dropped_at set, attempt array gets
    an entry, pipeline_stage NOT advanced."""
    execute_calls: list = []
    pool = _make_pool(execute_calls)

    row = {"id": "55555555-5555-5555-5555-555555555555",
           "domain": "stage0fail.com.au", "category": "x",
           "pipeline_stage": 0, "stage_metrics": {}}
    plan = {"next_stage": 1, "runner": "free_enrichment",
            "clients": [], "is_free": True}

    async def _fail(d):
        d["dropped_at"] = "free_enrichment"
        d["drop_reason"] = "free_enrichment_exception: dns_timeout"
        return d

    with patch.object(flow_mod, "_invoke_free_enrichment", AsyncMock(side_effect=_fail)):
        result = asyncio.run(
            flow_mod.advance_row.fn(pool, row, plan, clients={"gemini": None})
        )

    assert result["outcome"] == "runner_early_exit"
    assert "dns_timeout" in result["reason"]
    sql = execute_calls[0][0]
    assert "bu_closed_loop_attempts" in sql
    assert "pipeline_stage" not in sql  # NOT advanced
