"""Pipeline F Master Flow — Prefect automation of Stages 1-11.

Directive: P4-BUILD
Spec: docs/specs/p4_build_spec.md (ratified c73e4851)
Posture: PARALLEL to existing flows — does NOT replace pool_population_flow,
         enrichment_flow, or lead_enrichment_flow.
"""
from __future__ import annotations

import logging
import os
import random
import time
from datetime import UTC, datetime
from typing import Any

import asyncpg
from prefect import flow, task
from prefect.cache_policies import NO_CACHE

from src.prefect_utils.completion_hook import on_completion_hook
from src.prefect_utils.hooks import on_failure_hook

logger = logging.getLogger(__name__)

# ── Budget / gate constants ──────────────────────────────────────────────────
_USD_TO_AUD = 1.55
_PASS_THRESHOLD = 70  # dm_messages quality gate (email_scoring_gate.PASS_THRESHOLD)


# ── Stage 1: Discovery ───────────────────────────────────────────────────────

@task(name="stage-1-discover", retries=1, cache_policy=NO_CACHE)
async def stage_1_discover(
    categories: list[str],
    domains_per_category: int,
    dfs: Any,
) -> list[dict]:
    """Extract of cohort_runner.py lines 728-759.

    Calls DFS domain_metrics_by_categories per category, filters by ETV window
    and blocklist, returns list[dict] with keys: domain, category.
    """
    from src.orchestration.cohort_runner import CATEGORY_MAP
    from src.config.category_etv_windows import CATEGORY_ETV_WINDOWS, get_etv_window
    from src.utils.domain_blocklist import is_blocked

    all_domain_items: list[dict] = []

    for cat_name in categories:
        if cat_name not in CATEGORY_MAP:
            logger.warning("Unknown category %s — skipping", cat_name)
            continue
        code = CATEGORY_MAP[cat_name]
        etv_min, etv_max = get_etv_window(code)
        win = CATEGORY_ETV_WINDOWS[code]
        offset_start = win.get("offset_start", 0)

        page = await dfs.domain_metrics_by_categories(
            category_codes=[code],
            location_name="Australia",
            paid_etv_min=0.0,
            limit=100,
            offset=offset_start,
        )

        added = 0
        for row in page:
            domain = row.get("domain", "")
            etv = row.get("organic_etv", 0)
            if is_blocked(domain):
                continue
            if not (etv_min <= etv <= etv_max):
                continue
            all_domain_items.append({"domain": domain, "category": cat_name})
            added += 1
            if added >= domains_per_category:
                break

        logger.info("  stage-1 %s: %d domains discovered", cat_name, added)

    return all_domain_items


# ── Stages 2-11: Thin @task wrappers ────────────────────────────────────────

@task(name="stage-2-verify", retries=0, cache_policy=NO_CACHE)
async def stage_2_verify(domain_data: dict, dfs: Any) -> dict:
    from src.orchestration.cohort_runner import _run_stage2
    return await _run_stage2(domain_data, dfs)


@task(name="stage-3-identify", retries=0, cache_policy=NO_CACHE)
async def stage_3_identify(domain_data: dict, gemini: Any) -> dict:
    from src.orchestration.cohort_runner import _run_stage3
    return await _run_stage3(domain_data, gemini)


@task(name="stage-4-signal", retries=0, cache_policy=NO_CACHE)
async def stage_4_signal(domain_data: dict, dfs: Any) -> dict:
    from src.orchestration.cohort_runner import _run_stage4
    return await _run_stage4(domain_data, dfs)


@task(name="stage-5-score", retries=0, cache_policy=NO_CACHE)
async def stage_5_score(domain_data: dict) -> dict:
    from src.orchestration.cohort_runner import _run_stage5
    return await _run_stage5(domain_data)


@task(name="stage-6-enrich", retries=0, cache_policy=NO_CACHE)
async def stage_6_enrich(domain_data: dict, dfs: Any) -> dict:
    from src.orchestration.cohort_runner import _run_stage6
    return await _run_stage6(domain_data, dfs)


@task(name="stage-7-analyse", retries=0, cache_policy=NO_CACHE)
async def stage_7_analyse(domain_data: dict, gemini: Any) -> dict:
    from src.orchestration.cohort_runner import _run_stage7
    return await _run_stage7(domain_data, gemini)


@task(name="stage-8-contact", retries=0, cache_policy=NO_CACHE)
async def stage_8_contact(
    domain_data: dict,
    dfs: Any,
    bd: Any | None = None,
    lm: Any | None = None,
) -> dict:
    from src.orchestration.cohort_runner import _run_stage8
    return await _run_stage8(domain_data, dfs, bd, lm)


@task(name="stage-9-social", retries=0, cache_policy=NO_CACHE)
async def stage_9_social(domain_data: dict, bd: Any) -> dict:
    from src.orchestration.cohort_runner import _run_stage9
    return await _run_stage9(domain_data, bd)


@task(name="stage-10-vr-msg", retries=0, cache_policy=NO_CACHE)
async def stage_10_vr_msg(domain_data: dict) -> dict:
    from src.orchestration.cohort_runner import _run_stage10
    return await _run_stage10(domain_data)


@task(name="stage-11-card", retries=0, cache_policy=NO_CACHE)
async def stage_11_card(domain_data: dict) -> dict:
    from src.orchestration.cohort_runner import _run_stage11
    return await _run_stage11(domain_data)


# ── Data handoff ─────────────────────────────────────────────────────────────

@task(name="persist-stage8-to-db", retries=1, cache_policy=NO_CACHE)
async def persist_stage8_to_db(pipeline: list[dict]) -> list[str]:
    """Write BU + BDM rows from in-memory pipeline to DB. Returns list of BDM UUIDs.

    Write contract mirrors what stage_9_10_flow.select_bdms expects:
    - business_universe: domain, pipeline_stage, propensity_score, vulnerability_report (null at this point)
    - business_decision_makers: business_universe_id, name, linkedin_url, is_current=True
    """
    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(db_url, min_size=2, max_size=8, statement_cache_size=0)
    bdm_ids: list[str] = []

    try:
        async with pool.acquire() as conn:
            for d in pipeline:
                if d.get("dropped_at"):
                    continue

                identity = d.get("stage3") or {}
                dm = identity.get("dm_candidate") or {}
                scores = d.get("stage5") or {}
                propensity = scores.get("composite_score", 0)
                domain = d["domain"]

                # Insert or find existing business_universe row
                # No unique constraint on domain — check existence first
                bu_id = await conn.fetchval(
                    "SELECT id FROM business_universe WHERE domain = $1 LIMIT 1",
                    domain,
                )
                if bu_id:
                    await conn.execute(
                        """UPDATE business_universe
                           SET pipeline_stage = $2, propensity_score = $3,
                               dfs_discovery_category = $4, updated_at = NOW()
                           WHERE id = $1""",
                        bu_id, 8, float(propensity), d.get("category", ""),
                    )
                else:
                    # display_name is NOT NULL — derive from identity or domain stem
                    display_name = (
                        identity.get("business_name")
                        or identity.get("company_name")
                        or domain.split(".")[0].replace("-", " ").title()
                    )
                    bu_id = await conn.fetchval(
                        """INSERT INTO business_universe (domain, display_name, pipeline_stage, propensity_score, dfs_discovery_category)
                           VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                        domain, display_name, 8, float(propensity), d.get("category", ""),
                    )

                dm_name = dm.get("name")
                dm_linkedin = (
                    (d.get("stage8_contacts") or {}).get("linkedin", {}).get("linkedin_url")
                    or dm.get("linkedin_url")
                )

                if not dm_name or not dm_linkedin:
                    continue

                # Insert or find existing BDM row
                bdm_id = await conn.fetchval(
                    "SELECT id FROM business_decision_makers WHERE business_universe_id = $1 AND linkedin_url = $2 LIMIT 1",
                    bu_id, dm_linkedin,
                )
                if bdm_id:
                    await conn.execute(
                        "UPDATE business_decision_makers SET name = $2, is_current = TRUE, updated_at = NOW() WHERE id = $1",
                        bdm_id, dm_name,
                    )
                else:
                    bdm_id = await conn.fetchval(
                        """INSERT INTO business_decision_makers (business_universe_id, name, linkedin_url, is_current)
                           VALUES ($1, $2, $3, TRUE) RETURNING id""",
                        bu_id, dm_name, dm_linkedin,
                    )
                if bdm_id:
                    bdm_ids.append(str(bdm_id))

    finally:
        await pool.close()

    logger.info("persist_stage8_to_db: wrote %d BDM rows", len(bdm_ids))
    return bdm_ids


# ── dm_messages gate (GOV-12) ─────────────────────────────────────────────────

@task(name="dm-messages-gate", retries=0, cache_policy=NO_CACHE)
async def dm_messages_gate(run_start_ts: str, sample_size: int = 3) -> dict:
    """GOV-12 runtime gate: SQL count + content quality check.

    1. SELECT COUNT(*) FROM dm_messages WHERE status='draft' AND created_at > run_start_ts
    2. Sample up to sample_size random drafts, score with email_scoring_gate.score_and_suggest()
    3. All sampled messages must score >= PASS_THRESHOLD (70)
    4. Raises RuntimeError on fail — GOV-12 compliant (not a comment, not a soft warn)
    """
    from src.pipeline.email_scoring_gate import score_and_suggest, PASS_THRESHOLD

    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(db_url, min_size=2, max_size=4, statement_cache_size=0)

    try:
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM dm_messages WHERE status = 'draft' AND created_at > $1",
                run_start_ts,
            )
            rows = await conn.fetch(
                "SELECT id, subject, body FROM dm_messages "
                "WHERE status = 'draft' AND created_at > $1",
                run_start_ts,
            )
    finally:
        await pool.close()

    count = int(count or 0)
    if count == 0:
        raise RuntimeError(
            f"dm_messages_gate FAIL: 0 draft messages found after {run_start_ts}"
        )

    sample = random.sample(list(rows), min(sample_size, len(rows)))
    failures = []
    for row in sample:
        result = score_and_suggest(
            subject=row["subject"] or "",
            body=row["body"] or "",
        )
        if result["score"] < PASS_THRESHOLD:
            failures.append({
                "id": str(row["id"]),
                "score": result["score"],
                "flags": result.get("flags", []),
            })

    if failures:
        raise RuntimeError(
            f"dm_messages_gate FAIL: {len(failures)}/{len(sample)} sampled messages "
            f"scored below {PASS_THRESHOLD}. Failures: {failures}"
        )

    logger.info("dm_messages_gate PASS: %d draft messages, %d sampled, all >= %d", count, len(sample), PASS_THRESHOLD)
    return {"count": count, "sampled": len(sample), "all_pass": True}


# ── Master flow ──────────────────────────────────────────────────────────────

@flow(
    name="pipeline-f-master-flow",
    on_completion=[on_completion_hook],
    on_failure=[on_failure_hook],
)
async def pipeline_f_master_flow(
    categories: list[str] | None = None,
    domains_per_category: int = 4,
    dry_run: bool = False,
    budget_cap_aud: float = 25.0,
) -> dict:
    """Pipeline F v2.1 master flow — Stages 1-11 automated via Prefect.

    Parameters
    ----------
    categories:            Category slugs to discover (default: 5 canonical verticals).
    domains_per_category:  Max domains per category from Stage 1.
    dry_run:               If True, set DRY_RUN=1 — no API calls, no spend.
    budget_cap_aud:        Hard AUD spend ceiling. Converted to USD internally.
    """
    from src.orchestration.cohort_runner import _new_domain, _check_budget, CATEGORY_MAP
    from src.orchestration.flows.stage_9_10_flow import stage_9_10_pipeline
    from src.clients.dfs_labs_client import DFSLabsClient
    from src.intelligence.gemini_client import GeminiClient
    from src.integrations.bright_data_client import BrightDataClient
    from src.integrations.leadmagic import LeadmagicClient
    # Load .env on Vultr (local dev); on Railway, env vars are injected by the platform.
    _env_path = "/home/elliotbot/.config/agency-os/.env"
    if os.path.exists(_env_path):
        from dotenv import dotenv_values
        for _k, _v in dotenv_values(_env_path).items():
            if _v is not None:
                os.environ.setdefault(_k, _v)

    # Read from os.environ (works on both Vultr and Railway)
    env = os.environ

    if categories is None:
        categories = ["dental", "plumbing", "legal", "accounting", "fitness"]

    if dry_run:
        os.environ["DRY_RUN"] = "1"
        logger.info("[DRY-RUN] Pipeline F master flow — no API calls, no spend")

    run_start_ts = datetime.now(UTC).isoformat()
    budget_cap_usd = budget_cap_aud / _USD_TO_AUD

    # ── Init clients ─────────────────────────────────────────────────────────
    dfs = DFSLabsClient(
        login=env.get("DATAFORSEO_LOGIN", ""),
        password=env.get("DATAFORSEO_PASSWORD", ""),
    )
    gemini = GeminiClient(api_key=env.get("GEMINI_API_KEY"))
    bd = BrightDataClient(api_key=env.get("BRIGHTDATA_API_KEY", ""))
    lm = LeadmagicClient()

    # ── Stage 1: Discover ────────────────────────────────────────────────────
    discovered = await stage_1_discover(categories, domains_per_category, dfs)
    logger.info("Stage 1: %d domains discovered", len(discovered))

    if not discovered:
        logger.warning("Stage 1 returned 0 domains — aborting")
        return {"stage1_domains": 0, "cards": 0, "cost_usd": 0.0}

    # Build in-memory pipeline from discovered items
    pipeline: list[dict] = [_new_domain(item["domain"], item["category"]) for item in discovered]

    def _total_cost() -> float:
        return sum(d.get("cost_usd", 0) for d in pipeline)

    def _active() -> list[dict]:
        return [d for d in pipeline if isinstance(d, dict) and not d.get("dropped_at")]

    def _merge(updated: list) -> None:
        idx = {d["domain"]: i for i, d in enumerate(pipeline)}
        for d in updated:
            if not isinstance(d, dict):
                logger.warning("_merge: skipping non-dict result: %s", type(d))
                continue
            if d.get("domain") in idx:
                pipeline[idx[d["domain"]]] = d

    # ── Stages 2-8: Sequential per domain, domains run in parallel via gather ─
    import asyncio

    # Stage 2
    s2_results = await asyncio.gather(*[stage_2_verify(d, dfs) for d in pipeline])
    _merge(list(s2_results))
    if _check_budget(pipeline, budget_cap_usd):
        return _summary(pipeline, run_start_ts, "budget_killed_stage2")

    # Stage 3
    active3 = _active()
    s3_results = await asyncio.gather(*[stage_3_identify(d, gemini) for d in active3])
    _merge(list(s3_results))
    if _check_budget(pipeline, budget_cap_usd):
        return _summary(pipeline, run_start_ts, "budget_killed_stage3")

    # Stage 4
    active4 = _active()
    s4_results = await asyncio.gather(*[stage_4_signal(d, dfs) for d in active4])
    _merge(list(s4_results))
    if _check_budget(pipeline, budget_cap_usd):
        return _summary(pipeline, run_start_ts, "budget_killed_stage4")

    # Stage 5
    active5 = _active()
    s5_results = await asyncio.gather(*[stage_5_score(d) for d in active5])
    _merge(list(s5_results))

    # Stage 6
    active6 = _active()
    s6_results = await asyncio.gather(*[stage_6_enrich(d, dfs) for d in active6])
    _merge(list(s6_results))
    if _check_budget(pipeline, budget_cap_usd):
        return _summary(pipeline, run_start_ts, "budget_killed_stage6")

    # Stage 7
    active7 = _active()
    s7_results = await asyncio.gather(*[stage_7_analyse(d, gemini) for d in active7])
    _merge(list(s7_results))
    if _check_budget(pipeline, budget_cap_usd):
        return _summary(pipeline, run_start_ts, "budget_killed_stage7")

    # Stage 8
    active8 = _active()
    s8_results = await asyncio.gather(*[stage_8_contact(d, dfs, bd, lm) for d in active8])
    _merge(list(s8_results))
    if _check_budget(pipeline, budget_cap_usd):
        return _summary(pipeline, run_start_ts, "budget_killed_stage8")

    # Stage 9 (social scrape — in-memory, gated inside _run_stage9)
    active9 = _active()
    s9_results = await asyncio.gather(*[stage_9_social(d, bd) for d in active9])
    _merge(list(s9_results))

    # ── Persist to DB (bridge to stage_9_10_pipeline sub-flow) ───────────────
    bdm_ids = await persist_stage8_to_db(pipeline)
    logger.info("Persisted %d BDM rows. Triggering stage_9_10_pipeline sub-flow.", len(bdm_ids))

    # ── Stage 9+10 sub-flow (VR generation + message gen) ────────────────────
    s9_10_result: dict = {}
    if bdm_ids and not dry_run:
        s9_10_result = await stage_9_10_pipeline(
            bdm_ids=bdm_ids,
            batch_size=len(bdm_ids),
            budget_cap_usd=min(5.0, budget_cap_usd * 0.3),
            dry_run=False,
        )

    # ── Stage 10 (in-memory VR+MSG for in-pipeline domains) ──────────────────
    active10 = _active()
    s10_results = await asyncio.gather(*[stage_10_vr_msg(d) for d in active10])
    _merge(list(s10_results))

    # ── Stage 11: Card assembly ───────────────────────────────────────────────
    active11 = _active()
    s11_results = await asyncio.gather(*[stage_11_card(d) for d in active11])
    _merge(list(s11_results))

    # ── dm_messages gate (GOV-12) ─────────────────────────────────────────────
    gate_result: dict = {}
    if not dry_run and bdm_ids:
        gate_result = await dm_messages_gate(run_start_ts)

    if dry_run:
        os.environ.pop("DRY_RUN", None)

    summary = _summary(pipeline, run_start_ts, "complete")
    summary["stage_9_10"] = s9_10_result
    summary["dm_gate"] = gate_result
    summary["bdm_ids_persisted"] = len(bdm_ids)
    return summary


# ── Summary helper ────────────────────────────────────────────────────────────

def _summary(pipeline: list[dict], run_start_ts: str, status: str) -> dict:
    total_cost_usd = sum(d.get("cost_usd", 0) for d in pipeline)
    cards = sum(1 for d in pipeline if (d.get("stage11") or {}).get("lead_pool_eligible"))
    dropped = sum(1 for d in pipeline if d.get("dropped_at"))
    return {
        "status": status,
        "run_start_ts": run_start_ts,
        "total_domains": len(pipeline),
        "active": len(pipeline) - dropped,
        "dropped": dropped,
        "cards": cards,
        "cost_usd": round(total_cost_usd, 4),
        "cost_aud": round(total_cost_usd * 1.55, 4),
    }
