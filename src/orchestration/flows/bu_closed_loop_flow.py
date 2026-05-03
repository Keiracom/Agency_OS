"""BU Closed-Loop — backlog driver flow.

Directive: BU Closed-Loop Engine — Substep 2 of 4.
Purpose:    Daily safety-net flow that picks up BU rows stuck at pipeline_stage<11
            and advances them by one stage where free-mode permits.
Posture:    PAUSED by default in prefect.yaml. Schedule: daily 04:00 UTC.

Design constraints (from dispatch):
  - Query BU for rows with pipeline_stage < 11 and not permanently dropped.
  - Group by current pipeline_stage; each group enters at its NEXT stage.
  - Age-tiered cadence by propensity_score:
        hot  (>70):    14 days
        warm (50-70):  60 days
        cold (<50/NULL): 180 days
  - Free-mode only (default): refuse stages that require paid API calls.
        Paid stages: 2 (DFS SERP), 4 (DFS signals), 6 (DFS historical),
                     8 (waterfall paid tiers), 9 (Bright Data social).
        Free stages: 3 (Gemini free tier), 5 (scoring logic),
                     7 (Gemini analyse), 10 (VR + msg logic), 11 (card logic).
  - Write updated pipeline_stage + stage_completed_at marker after each
    advancement (stage_completed_at lives inside stage_metrics jsonb per
    BU Closed-Loop S1 column-mapping decision).
  - Budget AUD 0 enforced — paid stages never invoked while free_mode_only=True.
  - Log: rows queried, advanced per stage, stuck, reasons.

NOT in scope (deferred to S3 / S4):
  - Reconstructing full domain_data from BU columns (this flow uses minimal
    {domain, category, ...} dicts; some _run_stageN functions may early-exit
    when prerequisites are missing — that is logged but not retried here).
  - Live execution — flow ships PAUSED.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import asyncpg
from prefect import flow, task
from prefect.cache_policies import NO_CACHE

from src.prefect_utils.completion_hook import on_completion_hook
from src.prefect_utils.hooks import on_failure_hook

logger = logging.getLogger(__name__)


# ── Stage advancement map ────────────────────────────────────────────────────
# Each entry: pipeline_stage on the BU row → (next_stage_num, runner_label,
# requires_clients, is_free).
#
# requires_clients enumerates which paid clients the stage's _run_stageN
# function consumes. Free-mode refuses any stage where a paid client is
# required. Gemini is treated as free tier (per dispatch).
#
# S3: pipeline_stage 0 (NULL coerced) and 1 advance via the
# free_enrichment runner. Rows with stage 0 are first promoted to stage 1
# inside advance_row's _invoke_runner branch, then enriched in the same
# logical pass.
_PAID_CLIENT_KEYS: set[str] = {"dfs", "bd", "lm"}
_FREE_CLIENT_KEYS: set[str] = {"gemini"}

STAGE_ADVANCEMENT: dict[int, dict[str, Any]] = {
    # S3 — Stage 0 / 1 (post-discovery, pre-enrichment) advances via
    # free_enrichment. Pure local: DNS + httpx + abn_registry. AUD 0.
    0: {"next_stage": 1, "runner": "free_enrichment", "clients": [], "is_free": True},
    # S3-2 — Stage 1 -> 1 self-advancement is INTENTIONAL, not a bug.
    # free_enrichment is the free-mode terminal stage (no paid path forward
    # without human spend approval). Stamping stage_completed_at on each
    # cycle is the cadence-backoff that prevents tight re-enrichment loops.
    # Combined with S3-1's free_enrichment_completed_at short-circuit in
    # _classify_row, the actual scrape only re-runs after the deliberate
    # cadence (hot=14d / warm=60d / cold=180d) AND the row has not yet been
    # enriched. Looks like an S2-1-class self-loop bug at first glance but
    # is the correct semantics for the free-mode terminal.
    1: {"next_stage": 1, "runner": "free_enrichment", "clients": [], "is_free": True},
    2: {"next_stage": 3, "runner": "_run_stage3", "clients": ["gemini"], "is_free": True},
    3: {"next_stage": 5, "runner": "_run_stage5", "clients": [], "is_free": True},
    # 4 advances to 5 directly when the paid stage 4 is skipped — pure logic.
    4: {"next_stage": 5, "runner": "_run_stage5", "clients": [], "is_free": True},
    5: {"next_stage": 7, "runner": "_run_stage7", "clients": ["gemini"], "is_free": True},
    # Stage 6 is DFS-paid and unreachable in free-mode; rows landing at 6
    # advance via _run_stage7 (Gemini, free) when free-mode is on.
    6: {"next_stage": 7, "runner": "_run_stage7", "clients": ["gemini"], "is_free": True},
    7: {"next_stage": 9, "runner": "_run_stage9", "clients": ["bd"], "is_free": False},
    8: {"next_stage": 9, "runner": "_run_stage9", "clients": ["bd"], "is_free": False},
    9: {"next_stage": 10, "runner": "_run_stage10", "clients": [], "is_free": True},
    10: {"next_stage": 11, "runner": "_run_stage11", "clients": [], "is_free": True},
}


# ── DB helpers ───────────────────────────────────────────────────────────────


async def _init_jsonb_codec(conn):
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def _open_pool() -> asyncpg.pool.Pool:
    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.create_pool(
        db_url,
        min_size=2,
        max_size=4,
        statement_cache_size=0,
        init=_init_jsonb_codec,
    )


# ── Cursor: age-tiered backlog query ─────────────────────────────────────────


@task(name="bu-closed-loop-fetch-backlog", retries=1, cache_policy=NO_CACHE)
async def fetch_backlog(
    pool: asyncpg.pool.Pool,
    max_rows: int,
    cadence_hot_days: int,
    cadence_warm_days: int,
    cadence_cold_days: int,
) -> list[dict[str, Any]]:
    """Pull stuck rows whose latest stage_completed_at marker is older than the
    cadence threshold for their propensity tier."""
    sql = """
        WITH stage_age AS (
            SELECT id, domain, dfs_discovery_category AS category,
                   pipeline_stage, propensity_score,
                   stage_metrics, filter_reason,
                   free_enrichment_completed_at,
                   COALESCE(
                       (SELECT MAX((value)::timestamptz)
                          FROM jsonb_each_text(stage_metrics -> 'stage_completed_at')),
                       '1970-01-01'::timestamptz
                   ) AS latest_stage_at
              FROM business_universe
             WHERE pipeline_stage < 11
               AND (filter_reason IS NULL OR filter_reason NOT LIKE 'permanent_%')
               AND (filter_reason IS NULL
                    OR filter_reason NOT IN (
                        'free_enrichment_http_unreachable',
                        'free_enrichment_exception'
                    )
                    OR updated_at < NOW() - INTERVAL '7 days'
                   )
               AND domain IS NOT NULL
        )
        SELECT id, domain, category, pipeline_stage, propensity_score,
               stage_metrics, filter_reason, free_enrichment_completed_at,
               latest_stage_at,
               CASE
                   WHEN COALESCE(propensity_score, 0) >= 70 THEN 'hot'
                   WHEN COALESCE(propensity_score, 0) >= 50 THEN 'warm'
                   ELSE 'cold'
               END AS propensity_tier
          FROM stage_age
         WHERE NOW() - latest_stage_at >= (
                   CASE
                       WHEN COALESCE(propensity_score, 0) >= 70 THEN ($2 || ' days')::interval
                       WHEN COALESCE(propensity_score, 0) >= 50 THEN ($3 || ' days')::interval
                       ELSE ($4 || ' days')::interval
                   END
               )
         ORDER BY latest_stage_at ASC
         LIMIT $1
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(
            sql,
            max_rows,
            cadence_hot_days,
            cadence_warm_days,
            cadence_cold_days,
        )
    return [dict(r) for r in records]


# ── Per-row advancement ──────────────────────────────────────────────────────


def _classify_row(
    row: dict[str, Any],
    free_mode_only: bool,
    clients: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide what to do with one BU row. Returns dict with keys
    {action, next_stage, runner, reason}.

    `clients` is optional for unit tests but required at runtime for the
    S2-4 Gemini pre-flight gate: any plan that needs `gemini` is skipped
    with reason `stuck:gemini_client_unavailable` when clients['gemini']
    is None. Skipping early avoids an inevitable runner_exception during
    advance_row.
    """
    current_stage = row["pipeline_stage"]
    # S3 — stage 0 / NULL now route to free_enrichment via STAGE_ADVANCEMENT
    # rather than being skipped as "owned by another flow". Treat NULL as 0.
    if current_stage is None:
        current_stage = 0
    if current_stage == 11:
        return {"action": "skip", "reason": "stuck:already_at_terminal_stage"}
    plan = STAGE_ADVANCEMENT.get(current_stage)
    if plan is None:
        return {
            "action": "skip",
            "reason": f"stuck:no_advancement_path_for_stage_{current_stage}",
        }
    if free_mode_only and not plan["is_free"]:
        return {
            "action": "skip",
            "reason": f"stuck:blocked_by_free_mode (would invoke {plan['runner']} requiring {plan['clients']})",
        }
    # S3-1 — pre-flight skip when the row has already been free-enriched.
    # Without this gate, a stage-1 row that completed enrichment in a prior
    # cycle would re-scrape on every closed-loop pass once the cadence
    # threshold elapses. The cadence-backoff via stage_completed_at marker
    # only mutes consecutive cycles, not the eventual re-scrape — this gate
    # makes the no-op explicit and keeps the AUD 0 invariant tight.
    if plan["runner"] == "free_enrichment" and row.get("free_enrichment_completed_at"):
        return {
            "action": "skip",
            "reason": "stuck:already_free_enriched",
        }
    # S2-4 — pre-flight gate: refuse plans whose required clients are not
    # actually wired up. Today only Gemini is initialised in the flow body
    # under free-mode; if it failed to init (missing API key, etc.) we must
    # not call the runner.
    needs_gemini = "gemini" in (plan.get("clients") or [])
    if needs_gemini and (clients is None or clients.get("gemini") is None):
        return {
            "action": "skip",
            "reason": "stuck:gemini_client_unavailable",
        }
    return {
        "action": "advance",
        "next_stage": plan["next_stage"],
        "runner": plan["runner"],
        "clients": plan["clients"],
        "is_free": plan["is_free"],
        "reason": "ok",
    }


def _coerce_dict(value: Any) -> dict[str, Any]:
    """Return a dict from value: passthrough dicts, parse JSON strings, else {}."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, json.JSONDecodeError):
            return {}
    return {}


def _stage4_from_columns(row: dict[str, Any]) -> dict[str, Any]:
    """Fall-back reconstruction of the stage4 signal bundle from BU scalars
    when stage_metrics->'stage4' is missing. _run_stage5 reads this dict via
    `signal_bundle=...` so the keys must match build_signal_bundle output:
    rank_overview / backlinks / etc."""
    rank_overview: dict[str, Any] = {}
    if row.get("dfs_organic_etv") is not None:
        rank_overview["organic_etv"] = row["dfs_organic_etv"]
    if row.get("dfs_organic_keywords") is not None:
        rank_overview["organic_keywords"] = row["dfs_organic_keywords"]
    if row.get("domain_rank") is not None:
        rank_overview["rank"] = row["domain_rank"]

    backlinks: dict[str, Any] = {}
    if row.get("backlinks_count") is not None:
        backlinks["backlinks_num"] = row["backlinks_count"]

    bundle: dict[str, Any] = {}
    if rank_overview:
        bundle["rank_overview"] = rank_overview
    if backlinks:
        bundle["backlinks"] = backlinks
    return bundle


def _stage5_from_columns(row: dict[str, Any]) -> dict[str, Any]:
    """Fall-back reconstruction of stage5 scores. _run_stage5 normally
    populates this; on re-entry past stage 5 we want the existing scores
    visible to stage7/10/11 even if stage_metrics->'stage5' is missing."""
    scores: dict[str, Any] = {}
    if row.get("propensity_score") is not None:
        scores["composite_score"] = row["propensity_score"]
        scores["is_viable_prospect"] = bool(row["propensity_score"])
    for col_key, score_key in (
        ("score_budget", "budget"),
        ("score_pain", "pain"),
        ("score_gap", "gap"),
        ("score_fit", "fit"),
    ):
        if row.get(col_key) is not None:
            scores[score_key] = row[col_key]
    return scores


def _stage3_from_columns(row: dict[str, Any]) -> dict[str, Any]:
    """Fall-back reconstruction of stage3 identity. _run_stage5 / 7 read
    business_name + dm_candidate from this dict."""
    identity: dict[str, Any] = {}
    name = row.get("trading_name") or row.get("abr_trading_name") or row.get("legal_name")
    if name:
        identity["business_name"] = str(name)
    dm: dict[str, Any] = {}
    if row.get("dm_phone"):
        dm["phone"] = row["dm_phone"]
    if row.get("linkedin_company_url"):
        dm["linkedin_url"] = row["linkedin_company_url"]
    if dm:
        identity["dm_candidate"] = dm
    if row.get("entity_type"):
        identity["entity_type"] = row["entity_type"]
    return identity


def _build_domain_data(row: dict[str, Any]) -> dict[str, Any]:
    """Production-grade reconstruction of the domain_data dict each
    cohort_runner._run_stageN expects (S3 replacement of the minimal stub).

    Strategy:
      1. Read stage_metrics jsonb on BU — that JSONB carries stage2, stage3,
         stage4, stage5 keys when persisted by _persist_stage4_to_bu and
         pipeline_f_master_flow. High-fidelity path.
      2. Fall back to BU column scalars for stage3 / stage4 / stage5 when
         stage_metrics is empty (e.g., row enriched before stage_metrics
         existed, or partial-state row). Keys match what each runner reads.
      3. Carry the mutable scaffolding fields (errors, cost_usd, timings,
         _latency_tracker) so runners do not crash on dict-missing keys.

    Returns:
        Dict with keys: domain, category, stage2, stage3, stage4, stage5,
        stage6, stage7, stage8_verify, stage8_contacts, stage9, stage10,
        stage11, errors, cost_usd, timings, dropped_at, drop_reason, _bu_id.
    """
    # Late import — avoids a hard dep on cohort_runner at module-load time
    # (so unit tests that don't exercise advance_row don't pay the cost).
    from src.orchestration.cohort_runner import LatencyTracker

    sm = _coerce_dict(row.get("stage_metrics"))

    # Stage data — JSONB-preserved first, BU-column fallback second.
    stage3 = _coerce_dict(sm.get("stage3")) or _stage3_from_columns(row)
    stage4 = _coerce_dict(sm.get("stage4")) or _stage4_from_columns(row)
    stage5 = _coerce_dict(sm.get("stage5")) or _stage5_from_columns(row)

    return {
        "domain": row["domain"],
        "category": row.get("category") or "",
        "stage2": _coerce_dict(sm.get("stage2")),
        "stage3": stage3,
        "stage4": stage4,
        "stage5": stage5,
        "stage6": _coerce_dict(sm.get("stage6")),
        "stage7": _coerce_dict(sm.get("stage7")),
        "stage8_verify": _coerce_dict(sm.get("stage8_verify")),
        "stage8_contacts": _coerce_dict(sm.get("stage8_contacts")),
        "stage9": _coerce_dict(sm.get("stage9")),
        "stage10": _coerce_dict(sm.get("stage10")),
        "stage11": _coerce_dict(sm.get("stage11")),
        # Mutable scaffolding the runners write into.
        "errors": [],
        "cost_usd": 0.0,
        "timings": {},
        "dropped_at": None,
        "drop_reason": None,
        "_latency_tracker": LatencyTracker(row["domain"]),
        "_bu_id": str(row["id"]),
    }


async def _invoke_free_enrichment(domain_data: dict[str, Any]) -> dict[str, Any]:
    """S3 — single-domain free_enrichment runner. Calls the existing
    FreeEnrichment.enrich_from_spider() entrypoint (DNS + scrape + ABN
    match) and folds the result back into domain_data.

    AUD 0: local DNS, httpx scrape, local abn_registry lookups. Spider
    fallback inside FreeEnrichment is gated by SPIDER_API_KEY env var.

    The result populates domain_data with website_data + dns_data + abn_data
    fields under stage2-equivalent keys so downstream stages see them. We do
    NOT write to BU here — the per-row caller (advance_row) is the only DB
    writer in the closed-loop flow.
    """
    from src.pipeline.free_enrichment import FreeEnrichment

    engine = FreeEnrichment()
    domain = domain_data["domain"]
    try:
        spider_data = await engine.scrape_website(domain)
    except Exception as exc:
        domain_data["errors"].append(f"free_enrichment_scrape: {exc}")
        spider_data = {}
    try:
        result = await engine.enrich_from_spider(domain, spider_data or {}) or {}
    except Exception as exc:
        domain_data["errors"].append(f"free_enrichment: {exc}")
        domain_data["dropped_at"] = "free_enrichment"
        domain_data["drop_reason"] = f"free_enrichment_exception: {exc}"
        return domain_data

    # Fold enrichment result fields into domain_data so downstream stages
    # see them. The keys mirror what _process_domain would have written
    # to BU columns; we expose them on stage2 / stage3 surrogates.
    domain_data["stage2"] = {
        **(domain_data.get("stage2") or {}),
        "website_cms": result.get("website_cms"),
        "website_tech_stack": result.get("website_tech_stack"),
        "website_contact_emails": result.get("website_contact_emails"),
        "dns_mx_provider": result.get("dns_mx_provider"),
        "dns_has_spf": result.get("dns_has_spf"),
        "dns_has_dkim": result.get("dns_has_dkim"),
        "non_au": result.get("non_au"),
        "serp_abn": result.get("abn"),
    }
    if result.get("abn_matched") and result.get("company_name"):
        existing_stage3 = domain_data.get("stage3") or {}
        if not existing_stage3.get("business_name"):
            existing_stage3["business_name"] = result["company_name"]
            domain_data["stage3"] = existing_stage3
    return domain_data


async def _invoke_runner(
    runner_label: str,
    domain_data: dict[str, Any],
    clients: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch to cohort_runner._run_stageN by label, or the free_enrichment
    pseudo-runner. Imported lazily so tests can patch module surfaces."""
    if runner_label == "free_enrichment":
        return await _invoke_free_enrichment(domain_data)

    from src.orchestration import cohort_runner as cr

    fn = getattr(cr, runner_label, None)
    if fn is None:
        return {**domain_data, "dropped_at": runner_label, "drop_reason": "runner_not_found"}
    if runner_label == "_run_stage3":
        return await fn(domain_data, clients["gemini"])
    if runner_label == "_run_stage5":
        return await fn(domain_data)
    if runner_label == "_run_stage7":
        return await fn(domain_data, clients["gemini"])
    if runner_label == "_run_stage9":
        return await fn(domain_data, clients["bd"])
    if runner_label == "_run_stage10":
        return await fn(domain_data)
    if runner_label == "_run_stage11":
        return await fn(domain_data)
    return {**domain_data, "dropped_at": runner_label, "drop_reason": "runner_dispatch_unmapped"}


@task(name="bu-closed-loop-advance-row", retries=0, cache_policy=NO_CACHE)
async def advance_row(
    pool: asyncpg.pool.Pool,
    row: dict[str, Any],
    plan: dict[str, Any],
    clients: dict[str, Any],
) -> dict[str, Any]:
    """Run the planned stage runner against a minimal domain_data, then write
    pipeline_stage + stage_metrics->stage_completed_at to BU."""
    domain_data = _build_domain_data(row)
    try:
        result = await _invoke_runner(plan["runner"], domain_data, clients)
    except Exception as exc:
        logger.warning(
            "advance_row runner=%s domain=%s failed: %s", plan["runner"], row["domain"], exc
        )
        return {
            "id": row["id"],
            "outcome": "error",
            "reason": f"runner_exception:{type(exc).__name__}",
        }

    if result.get("dropped_at"):
        # S2-1 — record the attempt in stage_metrics.bu_closed_loop_attempts
        # (a JSONB array of {ts, reason, runner}). Do NOT touch
        # stage_metrics.stage_completed_at — that key drives the cursor's
        # MAX-age computation in fetch_backlog and must reflect successful
        # stage advancements only.
        outcome_reason = result.get("drop_reason", "unknown")
        attempt_entry = json.dumps(
            {
                "ts": datetime.now(UTC).isoformat(),
                "reason": outcome_reason,
                "runner": plan["runner"],
            }
        )
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE business_universe SET
                       stage_metrics = jsonb_set(
                           COALESCE(stage_metrics, '{}'::jsonb),
                           '{bu_closed_loop_attempts}',
                           COALESCE(stage_metrics -> 'bu_closed_loop_attempts', '[]'::jsonb)
                               || $2::jsonb,
                           true
                       ),
                       filter_reason = $3,  -- gap #2 — instrument transient-drop filter_reason for BU audit
                       updated_at = NOW()
                   WHERE id = $1""",
                row["id"],
                attempt_entry,
                outcome_reason,
            )
        return {"id": row["id"], "outcome": "runner_early_exit", "reason": outcome_reason}

    # Success — advance pipeline_stage and stamp stage_completed_at marker.
    next_stage = plan["next_stage"]
    stage_key = plan["runner"].replace("_run_stage", "stage_")
    # S2-2 — when the advancement bypasses a paid stage (4 -> 5 skips paid 4,
    # 6 -> 7 skips paid 6), append a free_mode_paid_data_skipped marker so
    # downstream consumers know which paid data is missing on this row.
    paid_skip_for_current_stage: int | None = None
    if row["pipeline_stage"] == 4 and next_stage == 5:
        paid_skip_for_current_stage = 4
    elif row["pipeline_stage"] == 6 and next_stage == 7:
        paid_skip_for_current_stage = 6

    async with pool.acquire() as conn:
        if paid_skip_for_current_stage is not None:
            paid_skip_entry = json.dumps(
                {
                    "stage": paid_skip_for_current_stage,
                    "skipped_at": datetime.now(UTC).isoformat(),
                }
            )
            await conn.execute(
                """UPDATE business_universe SET
                       pipeline_stage = $2,
                       stage_metrics = jsonb_set(
                           jsonb_set(
                               COALESCE(stage_metrics, '{}'::jsonb),
                               ARRAY['stage_completed_at', $3::text],
                               to_jsonb(NOW()::text),
                               true
                           ),
                           '{free_mode_paid_data_skipped}',
                           COALESCE(stage_metrics -> 'free_mode_paid_data_skipped', '[]'::jsonb)
                               || $4::jsonb,
                           true
                       ),
                       updated_at = NOW()
                   WHERE id = $1""",
                row["id"],
                next_stage,
                stage_key,
                paid_skip_entry,
            )
        else:
            await conn.execute(
                """UPDATE business_universe SET
                       pipeline_stage = $2,
                       stage_metrics = jsonb_set(
                           COALESCE(stage_metrics, '{}'::jsonb),
                           ARRAY['stage_completed_at', $3::text],
                           to_jsonb(NOW()::text),
                           true
                       ),
                       updated_at = NOW()
                   WHERE id = $1""",
                row["id"],
                next_stage,
                stage_key,
            )
    return {
        "id": row["id"],
        "outcome": "advanced",
        "from_stage": row["pipeline_stage"],
        "to_stage": next_stage,
        "runner": plan["runner"],
        "paid_data_skipped_stage": paid_skip_for_current_stage,
    }


# ── Master flow ──────────────────────────────────────────────────────────────


@flow(
    name="bu-closed-loop-flow",
    on_completion=[on_completion_hook],
    on_failure=[on_failure_hook],
)
async def bu_closed_loop_flow(
    max_rows: int = 500,
    free_mode_only: bool = True,
    cadence_hot_days: int = 14,
    cadence_warm_days: int = 60,
    cadence_cold_days: int = 180,
) -> dict[str, Any]:
    """Daily backlog driver — re-enters stuck BU rows at their next stage in
    free-mode (zero AUD spend by default)."""
    run_start = datetime.now(UTC).isoformat()
    pool = await _open_pool()

    # Build free-tier-only client bag. Paid clients stay None so any accidental
    # paid-stage invocation surfaces as a TypeError immediately.
    clients: dict[str, Any] = {"dfs": None, "bd": None, "lm": None, "gemini": None}
    if not free_mode_only:
        # Real-mode client wiring belongs in a separate directive — emit a
        # warning here so anyone flipping the flag sees it.
        logger.warning(
            "bu_closed_loop_flow: free_mode_only=False — paid "
            "stages would run, but client wiring is not provided "
            "by this flow. Refusing paid invocations regardless."
        )
    else:
        try:
            from src.intelligence.gemini_client import GeminiClient

            clients["gemini"] = GeminiClient(api_key=os.environ.get("GEMINI_API_KEY"))
        except Exception as exc:
            logger.warning("bu_closed_loop_flow: GeminiClient init failed: %s", exc)

    summary: dict[str, Any] = {
        "run_start_ts": run_start,
        "max_rows": max_rows,
        "free_mode_only": free_mode_only,
        "cadence_days": {
            "hot": cadence_hot_days,
            "warm": cadence_warm_days,
            "cold": cadence_cold_days,
        },
        "queried": 0,
        "advanced_per_stage": defaultdict(int),
        "stuck_per_reason": defaultdict(int),
        "errors": 0,
    }

    try:
        rows = await fetch_backlog(
            pool,
            max_rows,
            cadence_hot_days,
            cadence_warm_days,
            cadence_cold_days,
        )
        summary["queried"] = len(rows)
        logger.info("bu_closed_loop_flow: queried=%d rows", len(rows))

        for row in rows:
            decision = _classify_row(row, free_mode_only, clients)
            if decision["action"] == "skip":
                summary["stuck_per_reason"][decision["reason"]] += 1
                continue
            outcome = await advance_row(pool, row, decision, clients)
            if outcome["outcome"] == "advanced":
                key = f"stage_{outcome['from_stage']}_to_{outcome['to_stage']}"
                summary["advanced_per_stage"][key] += 1
            elif outcome["outcome"] == "runner_early_exit":
                summary["stuck_per_reason"][f"runner_early_exit:{outcome['reason']}"] += 1
            else:
                summary["errors"] += 1
                summary["stuck_per_reason"][outcome["reason"]] += 1

    finally:
        await pool.close()

    # Convert defaultdicts for JSON serialisation downstream.
    summary["advanced_per_stage"] = dict(summary["advanced_per_stage"])
    summary["stuck_per_reason"] = dict(summary["stuck_per_reason"])
    logger.info("bu_closed_loop_flow complete: %s", json.dumps(summary, default=str))
    return summary
