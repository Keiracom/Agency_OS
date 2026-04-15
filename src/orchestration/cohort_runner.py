"""Pipeline F v2.1 — Cohort Runner.

Chains all 11 stages sequentially. Within each stage, domains run in parallel
via src/intelligence/parallel.py.

Usage:
    python -m src.orchestration.cohort_runner --size 20 --categories dental,plumbing,legal,accounting,fitness

Pipeline F v2.1. Directive D1.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS")

from dotenv import dotenv_values

env = dotenv_values("/home/elliotbot/.config/agency-os/.env")

# Inject all env vars so downstream modules (GeminiClient etc.) pick them up
for _k, _v in env.items():
    if _v is not None:
        os.environ.setdefault(_k, _v)

from src.clients.dfs_labs_client import DFSLabsClient
from src.config.category_etv_windows import CATEGORY_ETV_WINDOWS, get_etv_window
from src.integrations.bright_data_client import BrightDataClient
from src.pipeline.contactout_enricher import enrich_dm_via_contactout
from src.pipeline.email_waterfall import discover_email
from src.pipeline.mobile_waterfall import run_mobile_waterfall
from src.intelligence.dfs_signal_bundle import build_signal_bundle
from src.intelligence.enhanced_vr import run_stage10_vr_and_messaging
from src.intelligence.funnel_classifier import assemble_card
from src.intelligence.gemini_client import GeminiClient
from src.intelligence.parallel import run_parallel
from src.intelligence.prospect_scorer import score_prospect
from src.intelligence.serp_verify import run_serp_verify
from src.intelligence.stage6_enrich import run_stage6_enrich
from src.intelligence.stage9_social import run_stage9_social
from src.intelligence.verify_fills import run_verify_fills
from src.utils.domain_blocklist import is_blocked

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category map (name -> DFS category code)
# ---------------------------------------------------------------------------

CATEGORY_MAP: dict[str, int] = {
    "dental": 10514,
    "plumbing": 13462,
    "electrical": 11295,
    "hair": 10333,
    "dining": 10020,
    "realestate": 10531,
    "accounting": 11093,
    "legal": 13686,
    "automotive": 10193,
    "fitness": 10123,
    "veterinary": 11979,
}

# ---------------------------------------------------------------------------
# Stage cost constants — module-level so tests can import and assert against
# these values rather than duplicating literals.
# ---------------------------------------------------------------------------

STAGE2_COST_PER_DOMAIN = 0.010  # 5 SERP queries × $0.002
STAGE4_COST_PER_DOMAIN = 0.078  # 10 DFS endpoints sum = $0.0775, rounded up
STAGE6_COST_PER_DOMAIN = 0.106  # historical_rank_overview
STAGE8_SERP_FALLBACK = 0.008    # verify_fills SERP cost if _cost field missing
STAGE8_WATERFALL_COST = 0.015   # scraper ($0.004) + ContactOut (~$0.011)
STAGE9_COST_PER_DOMAIN = 0.027  # BD LinkedIn DM ($0.002) + company ($0.025)

# ---------------------------------------------------------------------------
# Telegram helper
# ---------------------------------------------------------------------------


def _tg(msg: str) -> None:
    token = env.get("TELEGRAM_TOKEN", "")
    if not token:
        return
    try:
        import httpx

        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": "7267788033", "text": f"[EVO] {msg}"},
            timeout=10,
        )
    except Exception:
        pass


def _tg_progress(stage_label: str, pipeline: list[dict], cost_so_far: float) -> None:
    total = len(pipeline)
    dropped = sum(1 for d in pipeline if d.get("dropped_at"))
    active = total - dropped
    _tg(f"{stage_label}: {active}/{total} active, {dropped} dropped, cost=${cost_so_far:.2f}")


# ---------------------------------------------------------------------------
# Domain accumulator factory
# ---------------------------------------------------------------------------


def _new_domain(domain: str, category: str) -> dict:
    return {
        "domain": domain,
        "category": category,
        "stage2": None,
        "stage3": None,
        "stage4": None,
        "stage5": None,
        "stage6": None,
        "stage7": None,
        "stage8_verify": None,
        "stage8_contacts": None,
        "stage9": None,
        "stage10": None,
        "stage11": None,
        "dropped_at": None,
        "drop_reason": None,
        "cost_usd": 0.0,
        "timings": {},
        "errors": [],
    }


# ---------------------------------------------------------------------------
# Stage wrappers
# ---------------------------------------------------------------------------


async def _run_stage2(domain_data: dict, dfs: DFSLabsClient) -> dict:
    """Stage 2 VERIFY — 5 SERP queries per domain."""
    t0 = time.monotonic()
    try:
        result = await run_serp_verify(dfs, domain_data["domain"])
        domain_data["stage2"] = result
        domain_data["cost_usd"] += result.get("_cost", 0)
    except Exception as exc:
        domain_data["errors"].append(f"stage2: {exc}")
        domain_data["stage2"] = {}
    domain_data["timings"]["stage2"] = round(time.monotonic() - t0, 2)
    return domain_data


async def _run_stage3(domain_data: dict, gemini: GeminiClient) -> dict:
    """Stage 3 IDENTIFY — Gemini identity + DM extraction."""
    t0 = time.monotonic()
    serp = domain_data.get("stage2") or {}
    try:
        result = await gemini.call_f3a(
            domain=domain_data["domain"],
            dfs_base_metrics={},
            serp_data=serp,
        )
    except Exception as exc:
        domain_data["errors"].append(f"stage3: {exc}")
        domain_data["dropped_at"] = "stage3"
        domain_data["drop_reason"] = f"stage3_exception: {exc}"
        domain_data["timings"]["stage3"] = round(time.monotonic() - t0, 2)
        return domain_data

    domain_data["cost_usd"] += result.get("cost_usd", 0)
    domain_data["timings"]["stage3"] = round(time.monotonic() - t0, 2)
    content = result.get("content") or {}
    domain_data["stage3"] = content

    if result.get("f_status") != "success":
        domain_data["dropped_at"] = "stage3"
        domain_data["drop_reason"] = f"stage3_failed: {result.get('f_failure_reason')}"
        return domain_data
    if content.get("is_enterprise_or_chain"):
        domain_data["dropped_at"] = "stage3"
        domain_data["drop_reason"] = "enterprise_or_chain"
        return domain_data
    if not (content.get("dm_candidate") or {}).get("name"):
        domain_data["dropped_at"] = "stage3"
        domain_data["drop_reason"] = "no_dm_found"
        return domain_data
    return domain_data


async def _run_stage4(domain_data: dict, dfs: DFSLabsClient) -> dict:
    """Stage 4 SIGNAL — DFS signal bundle."""
    t0 = time.monotonic()
    biz = domain_data.get("stage3", {}).get("business_name")
    try:
        bundle = await build_signal_bundle(dfs, domain_data["domain"], business_name=biz)
        domain_data["stage4"] = bundle
    except Exception as exc:
        domain_data["errors"].append(f"stage4: {exc}")
        domain_data["stage4"] = {}
    # Fixed cost: 10 DFS endpoints sum = $0.0775, rounded up to $0.078/domain (parallel-safe)
    domain_data["cost_usd"] += STAGE4_COST_PER_DOMAIN
    domain_data["timings"]["stage4"] = round(time.monotonic() - t0, 2)
    return domain_data


async def _run_stage5(domain_data: dict) -> dict:
    """Stage 5 SCORE — prospect viability scoring (pure logic)."""
    t0 = time.monotonic()
    try:
        # FIX C1: inject Stage 2 ABN into stage3 bundle so scorer sees it
        stage3_with_abn = dict(domain_data.get("stage3", {}))
        stage3_with_abn["serp_abn"] = domain_data.get("stage2", {}).get("serp_abn")
        scores = score_prospect(
            signal_bundle=domain_data.get("stage4", {}),
            f3a_output=stage3_with_abn,
            category_name=domain_data.get("category"),
        )
        domain_data["stage5"] = scores
    except Exception as exc:
        domain_data["errors"].append(f"stage5: {exc}")
        domain_data["stage5"] = {}
        domain_data["dropped_at"] = "stage5"
        domain_data["drop_reason"] = f"score_exception: {exc}"
        domain_data["timings"]["stage5"] = round(time.monotonic() - t0, 4)
        return domain_data

    domain_data["timings"]["stage5"] = round(time.monotonic() - t0, 4)
    if not scores.get("is_viable_prospect"):
        domain_data["dropped_at"] = "stage5"
        domain_data["drop_reason"] = f"viability: {scores.get('viability_reason')}"
    elif scores.get("composite_score", 0) < 30:
        domain_data["dropped_at"] = "stage5"
        domain_data["drop_reason"] = f"score_below_gate: {scores.get('composite_score')}"
    return domain_data


async def _run_stage6(domain_data: dict, dfs: DFSLabsClient) -> dict:
    """Stage 6 ENRICH — historical rank (gated: composite_score >= 60)."""
    if (domain_data.get("stage5") or {}).get("composite_score", 0) < 60:
        return domain_data
    t0 = time.monotonic()
    composite = domain_data["stage5"]["composite_score"]
    try:
        result = await run_stage6_enrich(dfs, domain_data["domain"], composite)
        domain_data["stage6"] = result
        # Fixed cost: historical_rank_overview = $0.106/domain (parallel-safe)
        domain_data["cost_usd"] += STAGE6_COST_PER_DOMAIN
    except Exception as exc:
        domain_data["errors"].append(f"stage6: {exc}")
    domain_data["timings"]["stage6"] = round(time.monotonic() - t0, 2)
    return domain_data


async def _run_stage7(domain_data: dict, gemini: GeminiClient) -> dict:
    """Stage 7 ANALYSE — Gemini VR + outreach generation."""
    t0 = time.monotonic()
    identity = domain_data.get("stage3") or {}
    signals = domain_data.get("stage4") or {}
    try:
        result = await gemini.call_f3b(f3a_output=identity, signal_bundle=signals)
        domain_data["cost_usd"] += result.get("cost_usd", 0)
        domain_data["stage7"] = result.get("content") or {}
    except Exception as exc:
        domain_data["errors"].append(f"stage7: {exc}")
        domain_data["stage7"] = {}
    domain_data["timings"]["stage7"] = round(time.monotonic() - t0, 2)
    return domain_data


async def _run_stage8(domain_data: dict, dfs: DFSLabsClient) -> dict:
    """Stage 8 CONTACT — verify fills (8a) + unified contact waterfall (8b-d)."""
    t0 = time.monotonic()
    identity = domain_data.get("stage3") or {}
    dm = identity.get("dm_candidate") or {}

    # 8a: verify fills (unchanged)
    try:
        fills = await run_verify_fills(dfs=dfs, f3a_output=identity)
        domain_data["stage8_verify"] = fills
        serp_cost = fills.get("_cost", STAGE8_SERP_FALLBACK)
        domain_data["cost_usd"] += serp_cost
    except Exception as exc:
        domain_data["errors"].append(f"stage8a: {exc}")
        fills = {}
        domain_data["stage8_verify"] = {}

    # 8b: ContactOut enrichment (one call, captures email + mobile)
    dm_linkedin = (
        (domain_data.get("stage8_contacts") or {}).get("linkedin", {}).get("linkedin_url")
        or fills.get("dm_linkedin_url")
        or dm.get("linkedin_url")
    )
    contactout_result = None
    try:
        contactout_result = await enrich_dm_via_contactout(dm_linkedin)
        if contactout_result:
            domain_data["cost_usd"] += STAGE8_WATERFALL_COST  # ContactOut credit
    except Exception as exc:
        domain_data["errors"].append(f"stage8b_contactout: {exc}")

    # 8c: Email waterfall (uses contactout_result, falls through to Hunter/Leadmagic/BD)
    email_result = None
    try:
        email_result = await discover_email(
            domain=domain_data["domain"],
            dm_name=dm.get("name", ""),
            dm_linkedin=dm_linkedin,
            html=None,  # HTML not cached in cohort_runner
            company_name=identity.get("business_name"),
            contactout_result=contactout_result,
        )
    except Exception as exc:
        domain_data["errors"].append(f"stage8c_email: {exc}")

    # 8d: Mobile waterfall (uses contactout_result, no duplicate API call)
    mobile_result = None
    try:
        mobile_result = await run_mobile_waterfall(
            domain=domain_data["domain"],
            dm_linkedin_url=dm_linkedin,
            contact_data=None,
            contactout_result=contactout_result,
        )
    except Exception as exc:
        domain_data["errors"].append(f"stage8d_mobile: {exc}")

    # Combine into stage8_contacts — preserving nested dict format for assemble_card
    contacts = {}
    if email_result:
        contacts["email"] = {
            "email": email_result.email,
            "verified": email_result.verified,
            "source": email_result.source,
            "confidence": email_result.confidence,
            "cost_usd": email_result.cost_usd,
        }
        domain_data["cost_usd"] += email_result.cost_usd
    if mobile_result and mobile_result.mobile:
        contacts["mobile"] = {
            "mobile": mobile_result.mobile,
            "source": mobile_result.source,
            "cost_usd": float(mobile_result.cost_usd),
        }
        domain_data["cost_usd"] += float(mobile_result.cost_usd)
    # Preserve LinkedIn data from verify_fills
    contacts["linkedin"] = {
        "linkedin_url": dm_linkedin,
        "match_type": "direct_match" if dm_linkedin else "no_match",
    }
    domain_data["stage8_contacts"] = contacts

    domain_data["timings"]["stage8"] = round(time.monotonic() - t0, 2)
    return domain_data


async def _run_stage9(domain_data: dict, bd: BrightDataClient) -> dict:
    """Stage 9 SOCIAL — scrape DM + company LinkedIn posts (gated: verified LinkedIn)."""
    fills = domain_data.get("stage8_verify") or {}
    # FIX H2: use verified URL from stage8_contacts (waterfall result), not fills (unverified SERP)
    contacts = domain_data.get("stage8_contacts") or {}
    li_data = contacts.get("linkedin", {})
    dm_li = li_data.get("linkedin_url") if li_data.get("match_type") != "no_match" else None
    company_li = fills.get("company_linkedin_url") or (
        (domain_data.get("stage2") or {}).get("serp_company_linkedin")
    )
    if not dm_li and not company_li:
        return domain_data
    t0 = time.monotonic()
    identity = domain_data.get("stage3") or {}
    dm = identity.get("dm_candidate") or {}
    try:
        result = await run_stage9_social(
            bd=bd,
            dm_linkedin_url=dm_li,
            company_linkedin_url=company_li,
            dm_name=dm.get("name"),
        )
        domain_data["stage9"] = result
        # Fixed cost: ~$0.002 DM + $0.025 company = $0.027/domain (parallel-safe)
        domain_data["cost_usd"] += STAGE9_COST_PER_DOMAIN
    except Exception as exc:
        domain_data["errors"].append(f"stage9: {exc}")
    domain_data["timings"]["stage9"] = round(time.monotonic() - t0, 2)
    return domain_data


async def _run_stage10(domain_data: dict) -> dict:
    """Stage 10 VR+MSG — value report and outreach (gated: email found)."""
    contacts = domain_data.get("stage8_contacts") or {}
    email_data = contacts.get("email", {})
    if not email_data.get("email"):
        return domain_data
    t0 = time.monotonic()
    try:
        result = await run_stage10_vr_and_messaging(
            stage3_identity=domain_data.get("stage3") or {},
            stage4_signals=domain_data.get("stage4") or {},
            stage5_scores=domain_data.get("stage5") or {},
            stage7_analyse=domain_data.get("stage7") or {},
            stage8_contacts=contacts,
            stage9_social=domain_data.get("stage9") or {},
            stage6_enrich=domain_data.get("stage6") or {},
        )
        domain_data["cost_usd"] += result.get("cost_usd", 0)
        domain_data["stage10"] = result
    except Exception as exc:
        domain_data["errors"].append(f"stage10: {exc}")
    domain_data["timings"]["stage10"] = round(time.monotonic() - t0, 2)
    return domain_data


async def _run_stage11(domain_data: dict) -> dict:
    """Stage 11 CARD — assemble final lead card."""
    t0 = time.monotonic()
    try:
        # FIX M1+M2: merge stage8_verify ABN and LinkedIn into stage2 so card sees them
        stage2_merged = dict(domain_data.get("stage2") or {})
        verify = domain_data.get("stage8_verify") or {}
        if verify.get("abn"):
            stage2_merged["serp_abn"] = verify["abn"]
        if verify.get("company_linkedin_url"):
            stage2_merged["serp_company_linkedin"] = verify["company_linkedin_url"]
        card = assemble_card(
            domain=domain_data["domain"],
            stage2_verify=stage2_merged,
            stage3_identity=domain_data.get("stage3") or {},
            stage4_signals=domain_data.get("stage4") or {},
            stage5_scores=domain_data.get("stage5") or {},
            stage7_analyse=domain_data.get("stage7") or {},
            stage8_contacts=domain_data.get("stage8_contacts") or {},
            stage9_social=domain_data.get("stage9") or {},
            stage10_vr_msg=domain_data.get("stage10") or {},
            stage6_enrich=domain_data.get("stage6") or {},
        )
        domain_data["stage11"] = card
    except Exception as exc:
        domain_data["errors"].append(f"stage11: {exc}")
    domain_data["timings"]["stage11"] = round(time.monotonic() - t0, 2)
    return domain_data


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _write_outputs(pipeline: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(json.dumps(pipeline, indent=2, default=str))
    cards = [d["stage11"] for d in pipeline if (d.get("stage11") or {}).get("lead_pool_eligible")]
    (output_dir / "cards.json").write_text(json.dumps(cards, indent=2, default=str))
    logger.info("Outputs written to %s (%d cards)", output_dir, len(cards))


def _build_summary(pipeline: list[dict], wall_s: float) -> dict:
    def _survived_after(stage: str) -> int:
        return sum(
            1
            for d in pipeline
            if not d.get("dropped_at") or d["dropped_at"] > stage
        )

    total_cost = sum(d["cost_usd"] for d in pipeline)
    cards = sum(
        1 for d in pipeline if (d.get("stage11") or {}).get("lead_pool_eligible")
    )
    drop_reasons: Counter = Counter(
        d["drop_reason"] for d in pipeline if d.get("drop_reason")
    )

    per_stage_timing: dict[str, float] = {}
    for stage_key in ("stage2", "stage3", "stage4", "stage5", "stage6", "stage7", "stage8", "stage9", "stage10", "stage11"):
        timings = [d["timings"].get(stage_key) for d in pipeline if d["timings"].get(stage_key)]
        if timings:
            per_stage_timing[stage_key] = round(sorted(timings)[len(timings) // 2], 2)

    return {
        "directive": "D1",
        "timestamp": datetime.now(UTC).isoformat(),
        "total_domains": len(pipeline),
        "funnel": {
            "stage1_discovered": len(pipeline),
            "stage3_survived": _survived_after("stage3"),
            "stage5_survived": _survived_after("stage5"),
            "stage11_cards": cards,
        },
        "drop_reasons": dict(drop_reasons),
        "cost_usd": round(total_cost, 4),
        "cost_aud": round(total_cost * 1.55, 4),
        "cost_per_card": round(total_cost / cards, 4) if cards else None,
        "wall_clock_s": round(wall_s, 1),
        "per_stage_timing": per_stage_timing,
    }


# ---------------------------------------------------------------------------
# Main cohort runner
# ---------------------------------------------------------------------------


def _check_budget(pipeline: list[dict], cap: float) -> bool:
    """Return True if cumulative cost_usd across pipeline exceeds cap."""
    return sum(d.get("cost_usd", 0) for d in pipeline) > cap


async def run_cohort(
    categories: list[str],
    domains_per_category: int = 4,
    output_dir: str | None = None,
) -> dict:
    run_ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_path = Path(output_dir) if output_dir else Path("scripts/output") / f"cohort_run_{run_ts}"
    wall_start = time.monotonic()

    # Init clients
    dfs = DFSLabsClient(
        login=env.get("DATAFORSEO_LOGIN", ""),
        password=env.get("DATAFORSEO_PASSWORD", ""),
    )
    gemini = GeminiClient(api_key=env.get("GEMINI_API_KEY"))
    bd = BrightDataClient(api_key=env.get("BRIGHTDATA_API_KEY", ""))

    # Pre-run cost estimate and hard cap
    total_requested = domains_per_category * len(categories)
    estimated_cost_per_domain = 0.25  # USD, from Pipeline F v2.1 economics doc
    estimated_total = total_requested * estimated_cost_per_domain
    budget_hard_cap = estimated_total * 5
    logger.info(
        "PRE-RUN ESTIMATE: %d domains × $%.2f = $%.2f USD. Hard cap: $%.2f",
        total_requested, estimated_cost_per_domain, estimated_total, budget_hard_cap,
    )
    _tg(
        f"Pre-run estimate: {total_requested} domains × $0.25 = ${estimated_total:.2f}. "
        f"Hard cap: ${budget_hard_cap:.2f}"
    )

    # ---------------------------------------------------------------------------
    # Stage 1: DISCOVER
    # ---------------------------------------------------------------------------
    logger.info("Stage 1 DISCOVER — categories=%s, n=%d", categories, domains_per_category)
    all_domain_items: list[dict] = []

    for cat_name in categories:
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

        logger.info("  %s: %d domains discovered", cat_name, added)

    pipeline: list[dict] = [_new_domain(d["domain"], d["category"]) for d in all_domain_items]
    _tg(f"Stage 1 DISCOVER complete: {len(pipeline)} domains across {len(categories)} categories")

    if not pipeline:
        logger.warning("No domains discovered — aborting")
        await dfs.close()
        return {}

    # ---------------------------------------------------------------------------
    # Stages 2-11 — sequential between stages, parallel within
    # ---------------------------------------------------------------------------

    def _active(pl: list[dict]) -> list[dict]:
        return [d for d in pl if not d.get("dropped_at")]

    def _total_cost() -> float:
        return sum(d["cost_usd"] for d in pipeline)

    # Stage 2
    updated = await run_parallel(pipeline, lambda d: _run_stage2(d, dfs), concurrency=30, label="Stage 2 VERIFY")
    pipeline = updated
    _tg_progress("Stage 2 VERIFY", pipeline, _total_cost())
    if _check_budget(pipeline, budget_hard_cap):
        cost_now = _total_cost()
        logger.error("BUDGET HARD CAP EXCEEDED: $%.2f > $%.2f. Saving partial results.", cost_now, budget_hard_cap)
        _tg(f"BUDGET KILL: ${cost_now:.2f} exceeds cap ${budget_hard_cap:.2f}. Partial results saved.")
        await dfs.close()
        wall_s = time.monotonic() - wall_start
        summary = _build_summary(pipeline, wall_s)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        _write_outputs(pipeline, out_path)
        return summary

    # Stage 3
    active3 = _active(pipeline)
    updated3 = await run_parallel(active3, lambda d: _run_stage3(d, gemini), concurrency=20, label="Stage 3 IDENTIFY")
    _merge(pipeline, updated3)
    _tg_progress("Stage 3 IDENTIFY", pipeline, _total_cost())
    if _check_budget(pipeline, budget_hard_cap):
        cost_now = _total_cost()
        logger.error("BUDGET HARD CAP EXCEEDED: $%.2f > $%.2f. Saving partial results.", cost_now, budget_hard_cap)
        _tg(f"BUDGET KILL: ${cost_now:.2f} exceeds cap ${budget_hard_cap:.2f}. Partial results saved.")
        await dfs.close()
        wall_s = time.monotonic() - wall_start
        summary = _build_summary(pipeline, wall_s)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        _write_outputs(pipeline, out_path)
        return summary

    # Stage 4
    active4 = _active(pipeline)
    updated4 = await run_parallel(active4, lambda d: _run_stage4(d, dfs), concurrency=20, label="Stage 4 SIGNAL")
    _merge(pipeline, updated4)
    _tg_progress("Stage 4 SIGNAL", pipeline, _total_cost())
    if _check_budget(pipeline, budget_hard_cap):
        cost_now = _total_cost()
        logger.error("BUDGET HARD CAP EXCEEDED: $%.2f > $%.2f. Saving partial results.", cost_now, budget_hard_cap)
        _tg(f"BUDGET KILL: ${cost_now:.2f} exceeds cap ${budget_hard_cap:.2f}. Partial results saved.")
        await dfs.close()
        wall_s = time.monotonic() - wall_start
        summary = _build_summary(pipeline, wall_s)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        _write_outputs(pipeline, out_path)
        return summary

    # Stage 5
    active5 = _active(pipeline)
    updated5 = await run_parallel(active5, lambda d: _run_stage5(d), concurrency=50, label="Stage 5 SCORE")
    _merge(pipeline, updated5)
    _tg_progress("Stage 5 SCORE", pipeline, _total_cost())

    # Stage 6 (gated inside wrapper — runs all active, skips low scorers internally)
    active6 = _active(pipeline)
    updated6 = await run_parallel(active6, lambda d: _run_stage6(d, dfs), concurrency=10, label="Stage 6 ENRICH")
    _merge(pipeline, updated6)
    _tg_progress("Stage 6 ENRICH", pipeline, _total_cost())
    if _check_budget(pipeline, budget_hard_cap):
        cost_now = _total_cost()
        logger.error("BUDGET HARD CAP EXCEEDED: $%.2f > $%.2f. Saving partial results.", cost_now, budget_hard_cap)
        _tg(f"BUDGET KILL: ${cost_now:.2f} exceeds cap ${budget_hard_cap:.2f}. Partial results saved.")
        await dfs.close()
        wall_s = time.monotonic() - wall_start
        summary = _build_summary(pipeline, wall_s)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        _write_outputs(pipeline, out_path)
        return summary

    # Stage 7
    active7 = _active(pipeline)
    updated7 = await run_parallel(active7, lambda d: _run_stage7(d, gemini), concurrency=20, label="Stage 7 ANALYSE")
    _merge(pipeline, updated7)
    _tg_progress("Stage 7 ANALYSE", pipeline, _total_cost())
    if _check_budget(pipeline, budget_hard_cap):
        cost_now = _total_cost()
        logger.error("BUDGET HARD CAP EXCEEDED: $%.2f > $%.2f. Saving partial results.", cost_now, budget_hard_cap)
        _tg(f"BUDGET KILL: ${cost_now:.2f} exceeds cap ${budget_hard_cap:.2f}. Partial results saved.")
        await dfs.close()
        wall_s = time.monotonic() - wall_start
        summary = _build_summary(pipeline, wall_s)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        _write_outputs(pipeline, out_path)
        return summary

    # Stage 8
    active8 = _active(pipeline)
    updated8 = await run_parallel(active8, lambda d: _run_stage8(d, dfs), concurrency=15, label="Stage 8 CONTACT")
    _merge(pipeline, updated8)
    _tg_progress("Stage 8 CONTACT", pipeline, _total_cost())
    if _check_budget(pipeline, budget_hard_cap):
        cost_now = _total_cost()
        logger.error("BUDGET HARD CAP EXCEEDED: $%.2f > $%.2f. Saving partial results.", cost_now, budget_hard_cap)
        _tg(f"BUDGET KILL: ${cost_now:.2f} exceeds cap ${budget_hard_cap:.2f}. Partial results saved.")
        await dfs.close()
        wall_s = time.monotonic() - wall_start
        summary = _build_summary(pipeline, wall_s)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        _write_outputs(pipeline, out_path)
        return summary

    # Stage 9 (gated inside wrapper)
    active9 = _active(pipeline)
    updated9 = await run_parallel(active9, lambda d: _run_stage9(d, bd), concurrency=10, label="Stage 9 SOCIAL")
    _merge(pipeline, updated9)
    _tg_progress("Stage 9 SOCIAL", pipeline, _total_cost())
    if _check_budget(pipeline, budget_hard_cap):
        cost_now = _total_cost()
        logger.error("BUDGET HARD CAP EXCEEDED: $%.2f > $%.2f. Saving partial results.", cost_now, budget_hard_cap)
        _tg(f"BUDGET KILL: ${cost_now:.2f} exceeds cap ${budget_hard_cap:.2f}. Partial results saved.")
        await dfs.close()
        wall_s = time.monotonic() - wall_start
        summary = _build_summary(pipeline, wall_s)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        _write_outputs(pipeline, out_path)
        return summary

    # Stage 10 (gated inside wrapper)
    active10 = _active(pipeline)
    updated10 = await run_parallel(active10, lambda d: _run_stage10(d), concurrency=10, label="Stage 10 VR+MSG")
    _merge(pipeline, updated10)
    _tg_progress("Stage 10 VR+MSG", pipeline, _total_cost())
    if _check_budget(pipeline, budget_hard_cap):
        cost_now = _total_cost()
        logger.error("BUDGET HARD CAP EXCEEDED: $%.2f > $%.2f. Saving partial results.", cost_now, budget_hard_cap)
        _tg(f"BUDGET KILL: ${cost_now:.2f} exceeds cap ${budget_hard_cap:.2f}. Partial results saved.")
        await dfs.close()
        wall_s = time.monotonic() - wall_start
        summary = _build_summary(pipeline, wall_s)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        _write_outputs(pipeline, out_path)
        return summary

    # Stage 11 — all active get a card attempt
    active11 = _active(pipeline)
    updated11 = await run_parallel(active11, lambda d: _run_stage11(d), concurrency=50, label="Stage 11 CARD")
    _merge(pipeline, updated11)
    _tg_progress("Stage 11 CARD", pipeline, _total_cost())

    await dfs.close()

    wall_s = time.monotonic() - wall_start
    summary = _build_summary(pipeline, wall_s)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    _write_outputs(pipeline, out_path)

    cards_count = summary["funnel"]["stage11_cards"]
    cost_aud = summary["cost_aud"]
    _tg(
        f"Cohort run complete — {cards_count} cards, ${cost_aud:.2f} AUD, "
        f"{round(wall_s)}s wall-clock. Output: {out_path}"
    )
    logger.info("Done. %s", summary)
    return summary


# ---------------------------------------------------------------------------
# Merge helper (in-place update of pipeline list from parallel results)
# ---------------------------------------------------------------------------


def _merge(pipeline: list[dict], updated: list[dict]) -> None:
    """Merge updated domain_data dicts back into pipeline by domain key."""
    index = {d["domain"]: i for i, d in enumerate(pipeline)}
    for d in updated:
        key = d["domain"]
        if key in index:
            pipeline[index[key]] = d


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pipeline F v2.1 Cohort Runner")
    p.add_argument(
        "--categories",
        default="dental,plumbing,legal,accounting,fitness",
        help="Comma-separated category names (default: dental,plumbing,legal,accounting,fitness)",
    )
    p.add_argument("--size", type=int, default=20, help="Total cohort size (split across categories)")
    p.add_argument("--output-dir", default=None, help="Output directory (default: auto-timestamped)")
    return p.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()
    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    per_cat = max(1, args.size // len(cats))
    if per_cat * len(cats) > 2 * args.size:
        print(f"ERROR: Computed {per_cat * len(cats)} domains exceeds 2× requested {args.size}")
        sys.exit(1)
    asyncio.run(run_cohort(categories=cats, domains_per_category=per_cat, output_dir=args.output_dir))
