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
# pipeline_stage 0 / 1 → free_enrichment.run() (Stage 1 in dispatch lingo).
# That path is OWNED by free_enrichment.py and NOT re-driven here — this flow
# focuses on stages 2..11 cohort_runner advancement. Rows with stage<2 are
# logged as `stuck:pre_enrichment_owned_by_free_enrichment`.
_PAID_CLIENT_KEYS: set[str] = {"dfs", "bd", "lm"}
_FREE_CLIENT_KEYS: set[str] = {"gemini"}

STAGE_ADVANCEMENT: dict[int, dict[str, Any]] = {
    2:  {"next_stage": 3,  "runner": "_run_stage3",  "clients": ["gemini"], "is_free": True},
    3:  {"next_stage": 5,  "runner": "_run_stage5",  "clients": [],         "is_free": True},
    # 4 advances to 5 directly when the paid stage 4 is skipped — pure logic.
    4:  {"next_stage": 5,  "runner": "_run_stage5",  "clients": [],         "is_free": True},
    5:  {"next_stage": 7,  "runner": "_run_stage7",  "clients": ["gemini"], "is_free": True},
    # Stage 6 is DFS-paid and unreachable in free-mode; rows landing at 6
    # advance via _run_stage7 (Gemini, free) when free-mode is on.
    6:  {"next_stage": 7,  "runner": "_run_stage7",  "clients": ["gemini"], "is_free": True},
    7:  {"next_stage": 9,  "runner": "_run_stage9",  "clients": ["bd"],     "is_free": False},
    8:  {"next_stage": 9,  "runner": "_run_stage9",  "clients": ["bd"],     "is_free": False},
    9:  {"next_stage": 10, "runner": "_run_stage10", "clients": [],         "is_free": True},
    10: {"next_stage": 11, "runner": "_run_stage11", "clients": [],         "is_free": True},
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
        db_url, min_size=2, max_size=4, statement_cache_size=0, init=_init_jsonb_codec,
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
                   COALESCE(
                       (SELECT MAX((value)::timestamptz)
                          FROM jsonb_each_text(stage_metrics -> 'stage_completed_at')),
                       '1970-01-01'::timestamptz
                   ) AS latest_stage_at
              FROM business_universe
             WHERE pipeline_stage < 11
               AND (filter_reason IS NULL OR filter_reason NOT LIKE 'permanent_%')
               AND domain IS NOT NULL
        )
        SELECT id, domain, category, pipeline_stage, propensity_score,
               stage_metrics, filter_reason, latest_stage_at,
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
            sql, max_rows, cadence_hot_days, cadence_warm_days, cadence_cold_days,
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
    if current_stage is None or current_stage < 2:
        return {
            "action": "skip",
            "reason": "stuck:pre_enrichment_owned_by_free_enrichment",
        }
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


def _build_domain_data(row: dict[str, Any]) -> dict[str, Any]:
    """Build the minimal domain_data dict cohort_runner._run_stageN expects.

    NOTE: production-grade reconstruction (carrying stage3 / stage4 / stage5
    intermediate dicts back from BU columns) is deferred to S3. This minimal
    dict will trigger early-exit gates inside some _run_stageN functions when
    prerequisites are missing — that is logged as `runner_early_exit` rather
    than retried.
    """
    return {
        "domain": row["domain"],
        "category": row.get("category") or "",
        "_bu_id": str(row["id"]),
    }


async def _invoke_runner(
    runner_label: str,
    domain_data: dict[str, Any],
    clients: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch to cohort_runner._run_stageN by label. Imported lazily so
    tests can patch the cohort_runner module surface."""
    from src.orchestration import cohort_runner as cr

    fn = getattr(cr, runner_label, None)
    if fn is None:
        return {**domain_data, "dropped_at": runner_label,
                "drop_reason": "runner_not_found"}
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
    return {**domain_data, "dropped_at": runner_label,
            "drop_reason": "runner_dispatch_unmapped"}


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
        logger.warning("advance_row runner=%s domain=%s failed: %s",
                       plan["runner"], row["domain"], exc)
        return {"id": row["id"], "outcome": "error",
                "reason": f"runner_exception:{type(exc).__name__}"}

    if result.get("dropped_at"):
        # S2-1 — record the attempt in stage_metrics.bu_closed_loop_attempts
        # (a JSONB array of {ts, reason, runner}). Do NOT touch
        # stage_metrics.stage_completed_at — that key drives the cursor's
        # MAX-age computation in fetch_backlog and must reflect successful
        # stage advancements only.
        outcome_reason = result.get("drop_reason", "unknown")
        attempt_entry = json.dumps({
            "ts": datetime.now(UTC).isoformat(),
            "reason": outcome_reason,
            "runner": plan["runner"],
        })
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
                       updated_at = NOW()
                   WHERE id = $1""",
                row["id"], attempt_entry,
            )
        return {"id": row["id"], "outcome": "runner_early_exit",
                "reason": outcome_reason}

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
            paid_skip_entry = json.dumps({
                "stage": paid_skip_for_current_stage,
                "skipped_at": datetime.now(UTC).isoformat(),
            })
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
                row["id"], next_stage, stage_key, paid_skip_entry,
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
                row["id"], next_stage, stage_key,
            )
    return {"id": row["id"], "outcome": "advanced",
            "from_stage": row["pipeline_stage"], "to_stage": next_stage,
            "runner": plan["runner"],
            "paid_data_skipped_stage": paid_skip_for_current_stage}


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
        logger.warning("bu_closed_loop_flow: free_mode_only=False — paid "
                       "stages would run, but client wiring is not provided "
                       "by this flow. Refusing paid invocations regardless.")
    else:
        try:
            from src.intelligence.gemini_client import GeminiClient
            clients["gemini"] = GeminiClient(api_key=os.environ.get("GEMINI_API_KEY"))
        except Exception as exc:
            logger.warning("bu_closed_loop_flow: GeminiClient init failed: %s",
                           exc)

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
            pool, max_rows, cadence_hot_days, cadence_warm_days, cadence_cold_days,
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
