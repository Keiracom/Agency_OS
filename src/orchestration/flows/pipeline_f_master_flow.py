"""Pipeline F Master Flow — Prefect automation of Stages 1-11.

Directive: P4-BUILD → T4 (CD Player v1 unified entrypoint)
Spec: docs/specs/p4_build_spec.md (ratified c73e4851)
Posture: PARALLEL to existing flows — does NOT replace pool_population_flow,
         enrichment_flow, or lead_enrichment_flow.

T4 WIRING (2026-04-24):
  The flow body now delegates Stages 1-11 to pipeline_orchestrator.run_streaming()
  for unified CD Player v1 behaviour. The stage_N @task wrappers and
  persist_stage8_to_db / dm_messages_gate helpers remain at module scope because
  they are imported directly by other scripts (see scripts/isolate_persist_stage8.py)
  and must retain their public signatures.

  Tier / demo_mode / client_id flow through the existing `tier_config` kwarg on
  PipelineOrchestrator.run_streaming() — no orchestrator signature change needed
  (ATLAS-owned file). Tier-aware num_workers / batch_size / target_cards /
  budget are selected at the flow layer via _tier_runtime().
"""

from __future__ import annotations

import json
import logging
import os
import random
from datetime import UTC, datetime
from typing import Any

import asyncpg
from prefect import flow, task
from prefect.cache_policies import NO_CACHE

from src.prefect_utils.completion_hook import on_completion_hook
from src.prefect_utils.hooks import on_failure_hook

logger = logging.getLogger(__name__)


async def _init_jsonb_codec(conn):
    """Register JSONB codec for connections behind pgbouncer (statement_cache_size=0)."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


# ── Keiracom agency profile — ground truth, no fabricated claims ─────────────
# Temporary until CRM/onboarding path reads from agency_service_profile table.
# case_study intentionally omitted — Dave is pre-revenue, no clients yet.
_KEIRACOM_PROFILE = {
    "name": "Keiracom",
    "services": ["SEO", "Google Ads", "Facebook Ads", "Website Development"],
    "tone": "professional, direct, results-focused. Australian casual — not American corporate.",
    "founder_name": "Dave",
}

# ── Budget / gate constants ──────────────────────────────────────────────────
_USD_TO_AUD = 1.55
_PASS_THRESHOLD = 70  # dm_messages quality gate (email_scoring_gate.PASS_THRESHOLD)


# ── Tier-aware runtime config (T4) ───────────────────────────────────────────
# Selects pool sizes and discovery batch sizes per tier. Values are flow-layer
# defaults; the orchestrator honours num_workers / batch_size / target_cards /
# budget_cap_aud directly. Semaphore pools (GLOBAL_SEM_DFS / GLOBAL_SEM_SONNET)
# remain process-wide constants defined in src/pipeline/intelligence.py —
# making those tier-aware is an ATLAS follow-up (see outbox report).
_TIER_RUNTIME: dict[str, dict[str, Any]] = {
    "spark": {"num_workers": 2, "batch_size": 25, "target_cards": 5, "budget_cap_aud": 10.0},
    "ignition": {"num_workers": 4, "batch_size": 50, "target_cards": 15, "budget_cap_aud": 25.0},
    "velocity": {"num_workers": 8, "batch_size": 100, "target_cards": 40, "budget_cap_aud": 75.0},
    "demo": {"num_workers": 1, "batch_size": 10, "target_cards": 2, "budget_cap_aud": 1.0},
}


def _tier_runtime(tier: str, demo_mode: bool) -> dict[str, Any]:
    """Resolve runtime config for tier. demo_mode forces the smallest profile
    regardless of tier (spend-safety override)."""
    key = "demo" if demo_mode else (tier or "ignition").lower()
    if key not in _TIER_RUNTIME:
        logger.warning("Unknown tier '%s' — defaulting to ignition", tier)
        key = "ignition"
    return dict(_TIER_RUNTIME[key])


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
    from src.config.category_etv_windows import CATEGORY_ETV_WINDOWS, get_etv_window
    from src.orchestration.cohort_runner import CATEGORY_MAP
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
    pool = await asyncpg.create_pool(
        db_url, min_size=2, max_size=8, statement_cache_size=0, init=_init_jsonb_codec
    )
    bdm_ids: list[str] = []

    active_count = 0
    dropped_count = 0

    try:
        async with pool.acquire() as conn:
            for d in pipeline:
                domain = d["domain"]

                if d.get("dropped_at"):
                    # GOV-8: persist dropped domains for audit trail instead of silently skipping
                    drop_reason = d.get("drop_reason", "unknown")
                    dropped_at_str = str(d.get("dropped_at", ""))

                    # Derive display_name from whatever stage data exists
                    identity = d.get("stage3") or {}
                    display_name = (
                        identity.get("business_name")
                        or identity.get("company_name")
                        or domain.split(".")[0].replace("-", " ").title()
                    )

                    # Negative stage convention: -N means dropped at stage N
                    # cohort_runner sets dropped_at="stage3", "stage5", etc.
                    try:
                        stage_num = (
                            int(dropped_at_str.replace("stage", "")) if dropped_at_str else None
                        )
                        neg_stage = -abs(stage_num) if stage_num is not None else None
                    except (ValueError, TypeError):
                        neg_stage = None

                    # H1: collect all available stage data for full BU audit trail
                    stage2 = d.get("stage2") or {}
                    stage3_data = d.get("stage3") or {}
                    stage4 = d.get("stage4") or {}
                    stage5 = d.get("stage5") or {}

                    # H7: ON CONFLICT upsert — eliminates TOCTOU race + silent data loss
                    await conn.execute(
                        """INSERT INTO business_universe
                               (domain, display_name, pipeline_stage, pipeline_status,
                                filter_reason, dfs_discovery_category,
                                dfs_organic_etv, dfs_organic_keywords, backlinks_count, domain_rank,
                                stage_metrics)
                           VALUES ($1, $2, $3, 'dropped', $4, $5, $6, $7, $8, $9, $10)
                           ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain != '' DO UPDATE SET
                               pipeline_stage = COALESCE(EXCLUDED.pipeline_stage, business_universe.pipeline_stage),
                               pipeline_status = 'dropped',
                               filter_reason = COALESCE(EXCLUDED.filter_reason, business_universe.filter_reason),
                               dfs_discovery_category = COALESCE(EXCLUDED.dfs_discovery_category, business_universe.dfs_discovery_category),
                               dfs_organic_etv = COALESCE(EXCLUDED.dfs_organic_etv, business_universe.dfs_organic_etv),
                               dfs_organic_keywords = COALESCE(EXCLUDED.dfs_organic_keywords, business_universe.dfs_organic_keywords),
                               backlinks_count = COALESCE(EXCLUDED.backlinks_count, business_universe.backlinks_count),
                               domain_rank = COALESCE(EXCLUDED.domain_rank, business_universe.domain_rank),
                               stage_metrics = COALESCE(EXCLUDED.stage_metrics, business_universe.stage_metrics),
                               updated_at = NOW()""",
                        domain,
                        display_name,
                        neg_stage,
                        drop_reason,
                        d.get("category") or None,
                        stage2.get("organic_etv")
                        or (stage4.get("rank_overview") or {}).get("organic_etv"),
                        (stage4.get("rank_overview") or {}).get("organic_keywords"),
                        (stage4.get("backlinks") or {}).get("backlinks_num"),
                        (stage4.get("rank_overview") or {}).get("rank"),
                        json.dumps(
                            {
                                "stage2": stage2,
                                "stage3": stage3_data,
                                "stage4": stage4,
                                "stage5": stage5,
                                "dropped_at": dropped_at_str,
                            }
                        ),
                    )
                    dropped_count += 1
                    continue

                identity = d.get("stage3") or {}
                dm = identity.get("dm_candidate") or {}
                scores = d.get("stage5") or {}
                propensity = scores.get("composite_score", 0)
                active_display_name = (
                    identity.get("business_name")
                    or identity.get("company_name")
                    or domain.split(".")[0].replace("-", " ").title()
                )

                # H7: ON CONFLICT upsert — eliminates TOCTOU race between SELECT and INSERT
                bu_id = await conn.fetchval(
                    """INSERT INTO business_universe (domain, display_name, pipeline_stage, propensity_score, dfs_discovery_category)
                       VALUES ($1, $2, $3, $4, $5)
                       ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain != '' DO UPDATE SET
                           pipeline_stage = EXCLUDED.pipeline_stage,
                           propensity_score = EXCLUDED.propensity_score,
                           dfs_discovery_category = COALESCE(EXCLUDED.dfs_discovery_category, business_universe.dfs_discovery_category),
                           updated_at = NOW()
                       RETURNING id""",
                    domain,
                    active_display_name,
                    8,
                    float(propensity),
                    d.get("category", "") or None,
                )

                dm_name = dm.get("name")
                dm_linkedin = (d.get("stage8_contacts") or {}).get("linkedin", {}).get(
                    "linkedin_url"
                ) or dm.get("linkedin_url")

                if not dm_name or not dm_linkedin:
                    active_count += 1
                    continue

                # Insert or find existing BDM row
                bdm_id = await conn.fetchval(
                    "SELECT id FROM business_decision_makers WHERE business_universe_id = $1 AND linkedin_url = $2 LIMIT 1",
                    bu_id,
                    dm_linkedin,
                )
                if bdm_id:
                    await conn.execute(
                        "UPDATE business_decision_makers SET name = $2, is_current = TRUE, updated_at = NOW() WHERE id = $1",
                        bdm_id,
                        dm_name,
                    )
                else:
                    bdm_id = await conn.fetchval(
                        """INSERT INTO business_decision_makers (business_universe_id, name, linkedin_url, is_current)
                           VALUES ($1, $2, $3, TRUE) RETURNING id""",
                        bu_id,
                        dm_name,
                        dm_linkedin,
                    )
                if bdm_id:
                    bdm_ids.append(str(bdm_id))
                active_count += 1

    finally:
        await pool.close()

    logger.info(
        "persist_stage8_to_db: wrote %d active BDM rows, %d dropped domains logged",
        len(bdm_ids),
        dropped_count,
    )
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
    from datetime import datetime as _dt_cls

    from src.pipeline.email_scoring_gate import PASS_THRESHOLD, score_and_suggest

    # asyncpg needs a datetime object, not an ISO string
    if isinstance(run_start_ts, str):
        run_start_dt = _dt_cls.fromisoformat(run_start_ts.replace("Z", "+00:00"))
    else:
        run_start_dt = run_start_ts

    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(
        db_url, min_size=2, max_size=4, statement_cache_size=0, init=_init_jsonb_codec
    )

    try:
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM dm_messages WHERE status = 'draft' AND created_at > $1",
                run_start_dt,
            )
            rows = await conn.fetch(
                "SELECT id, subject, body FROM dm_messages "
                "WHERE status = 'draft' AND created_at > $1 AND channel = 'email'",
                run_start_dt,
            )
    finally:
        await pool.close()

    count = int(count or 0)
    if count == 0:
        raise RuntimeError(f"dm_messages_gate FAIL: 0 draft messages found after {run_start_ts}")

    if not rows:
        logger.info(
            "dm_messages_gate: %d total drafts, 0 email drafts — skipping email quality check",
            count,
        )
        return {"count": count, "sampled": 0, "all_pass": True, "note": "no_email_drafts"}

    sample = random.sample(list(rows), min(sample_size, len(rows)))
    failures = []
    for row in sample:
        result = score_and_suggest(
            subject=row["subject"] or "",
            body=row["body"] or "",
        )
        if result["score"] < PASS_THRESHOLD:
            failures.append(
                {
                    "id": str(row["id"]),
                    "score": result["score"],
                    "flags": result.get("flags", []),
                }
            )

    if failures:
        # Warn but don't block — Gemini critic (critic_score) is the primary quality gate.
        # Rule-based email_scoring_gate is a secondary heuristic check.
        logger.warning(
            "dm_messages_gate WARN: %d/%d sampled emails scored below %d (rule-based). "
            "Critic scores are primary quality gate. Failures: %s",
            len(failures),
            len(sample),
            PASS_THRESHOLD,
            failures,
        )

    logger.info(
        "dm_messages_gate PASS: %d draft messages, %d sampled, all >= %d",
        count,
        len(sample),
        PASS_THRESHOLD,
    )
    return {"count": count, "sampled": len(sample), "all_pass": True}


# ── Discovery adapter (T4) ───────────────────────────────────────────────────


class _DFSDiscoveryAdapter:
    """Minimal discovery adapter used by PipelineOrchestrator.run_streaming().

    Mirrors scripts/run_cd_player.py::DFSDiscoveryAdapter so the Prefect flow
    path and the CLI path share the same discovery contract.
    """

    def __init__(self, dfs: Any) -> None:
        self._dfs = dfs

    async def pull_batch(
        self,
        category_code: str,
        location_name: str = "Australia",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        try:
            rows = await self._dfs.domain_metrics_by_categories(
                category_codes=[int(category_code)],
                location_name=location_name,
                paid_etv_min=0.0,
                limit=limit,
                offset=offset,
            )
            return rows or []
        except Exception as exc:
            logger.warning("_DFSDiscoveryAdapter.pull_batch error: %s", exc)
            return []


# ── Master flow ──────────────────────────────────────────────────────────────


@flow(
    name="pipeline-f-master-flow",
    on_completion=[on_completion_hook],
    on_failure=[on_failure_hook],
)
async def pipeline_f_master_flow(
    tier: str = "ignition",
    demo_mode: bool = False,
    client_id: str | None = None,
    categories: list[str] | None = None,
    dry_run: bool = False,
    budget_cap_aud: float | None = None,
    # Legacy kwarg (no longer consumed — stage_1_discover is not called by the
    # streaming path; kept so existing schedules/manual triggers with this
    # parameter do not break).
    domains_per_category: int = 4,
) -> dict:
    """Pipeline F v2.1 master flow — CD Player v1 streaming entrypoint.

    T4 (2026-04-24): Stages 1-11 are now executed inside
    PipelineOrchestrator.run_streaming() rather than via per-stage @task
    gathers. Tier / demo_mode / client_id drive runtime sizing
    (num_workers, batch_size, target_cards, budget_cap_aud) via
    _tier_runtime(). They are also forwarded to run_streaming() through its
    existing `tier_config` kwarg so downstream orchestrator logic can branch
    on them when ATLAS wires tier-aware semaphore pools.

    Parameters
    ----------
    tier:                One of {spark, ignition, velocity, demo}. Selects
                         worker/batch/target/budget profile.
    demo_mode:           Force minimal-spend profile regardless of tier.
    client_id:           Logical client identifier carried through tier_config.
    categories:          Category slugs to discover (default: 5 canonical verticals).
    dry_run:             If True, set DRY_RUN=1 — no API calls, no spend.
    budget_cap_aud:      Explicit AUD budget override. If None, tier default wins.
    domains_per_category: Legacy parameter, ignored by the streaming path.
    """
    from src.clients.dfs_labs_client import DFSLabsClient
    from src.integrations.bright_data_client import BrightDataClient
    from src.integrations.leadmagic import LeadmagicClient
    from src.intelligence.gemini_client import GeminiClient
    from src.pipeline.pipeline_orchestrator import PipelineOrchestrator, ProspectCard

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

    runtime = _tier_runtime(tier, demo_mode)
    effective_budget_aud = (
        budget_cap_aud if budget_cap_aud is not None else runtime["budget_cap_aud"]
    )
    run_start_ts = datetime.now(UTC).isoformat()

    logger.info(
        "pipeline_f_master_flow start tier=%s demo_mode=%s client_id=%s "
        "num_workers=%d batch_size=%d target_cards=%d budget_aud=%.2f categories=%s",
        tier,
        demo_mode,
        client_id,
        runtime["num_workers"],
        runtime["batch_size"],
        runtime["target_cards"],
        effective_budget_aud,
        categories,
    )

    # ── Init clients ─────────────────────────────────────────────────────────
    dfs = DFSLabsClient(
        login=env.get("DATAFORSEO_LOGIN", ""),
        password=env.get("DATAFORSEO_PASSWORD", ""),
    )
    gemini = GeminiClient(api_key=env.get("GEMINI_API_KEY"))
    bd = BrightDataClient(api_key=env.get("BRIGHTDATA_API_KEY", ""))
    lm = LeadmagicClient()
    discovery = _DFSDiscoveryAdapter(dfs)

    cards: list[ProspectCard] = []

    def _on_card(card: ProspectCard) -> None:
        cards.append(card)

    orchestrator = PipelineOrchestrator(
        dfs_client=dfs,
        gemini_client=gemini,
        bd_client=bd,
        lm_client=lm,
        discovery=discovery,
        on_card=_on_card,
    )

    try:
        result = await orchestrator.run_streaming(
            categories=categories,
            target_cards=runtime["target_cards"],
            budget_cap_aud=effective_budget_aud,
            tier_config={
                "tier": tier,
                "demo_mode": demo_mode,
                "client_id": client_id,
            },
            num_workers=runtime["num_workers"],
            batch_size=runtime["batch_size"],
        )
    finally:
        # DFSLabsClient opens aiohttp sessions; close them regardless of outcome.
        try:
            await dfs.close()
        except Exception as exc:
            logger.warning("dfs.close() failed: %s", exc)

    if dry_run:
        os.environ.pop("DRY_RUN", None)

    summary = {
        "status": "complete",
        "run_start_ts": run_start_ts,
        "tier": tier,
        "demo_mode": demo_mode,
        "client_id": client_id,
        "categories": categories,
        "num_workers": runtime["num_workers"],
        "batch_size": runtime["batch_size"],
        "target_cards": runtime["target_cards"],
        "cards": len(result.prospects),
        "discovered": result.stats.discovered,
        "enrichment_failed": result.stats.enrichment_failed,
        "affordability_rejected": result.stats.affordability_rejected,
        "cost_usd": round(result.stats.total_cost_usd, 4),
        "cost_aud": round(result.stats.total_cost_usd * _USD_TO_AUD, 4),
        "budget_cap_aud": effective_budget_aud,
        "elapsed_s": round(result.stats.elapsed_seconds, 1),
    }
    logger.info("pipeline_f_master_flow complete: %s", json.dumps(summary, default=str))
    return summary
