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
from src.integrations.leadmagic import LeadmagicClient
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
from src.pipeline.latency_tracker import LatencyTracker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Drop-reason → rejection_reason ENUM mapping
# ---------------------------------------------------------------------------
# Pipeline drop reasons map to specific ENUM values added in migration 028.
# rejection_phase='pipeline' is also written to distinguish from outreach rejections.

DROP_REASON_TO_REJECTION: dict[str, str] = {
    "stage3_exception": "stage_failed",
    "stage3_failed": "stage_failed",
    "enterprise_or_chain": "enterprise_or_chain",
    "no_dm_found": "no_dm_found",
    "score_exception": "score_below_gate",
    "viability": "viability",
    "score_below_gate": "score_below_gate",
}

_DEFAULT_REJECTION = "other"


try:
    from src.integrations.supabase import get_async_supabase_service_client as _get_supabase
except ImportError:
    _get_supabase = None  # type: ignore[assignment]


async def _persist_drop_reason(domain_data: dict) -> None:
    """Write rejection_reason to leads table for a dropped domain. Best-effort."""
    domain = domain_data.get("domain")
    drop_reason = domain_data.get("drop_reason", "")
    if not domain or not drop_reason:
        return

    # Derive the enum-safe key (strip trailing detail after ": ")
    reason_key = drop_reason.split(":")[0].strip()
    rejection_reason = DROP_REASON_TO_REJECTION.get(reason_key, _DEFAULT_REJECTION)

    try:
        if _get_supabase is None:
            logger.warning("Supabase integration unavailable — skipping rejection_reason persist for %s", domain)
            return
        sb = await _get_supabase()
        await (
            sb.table("leads")
            .update({"rejection_reason": rejection_reason, "rejection_phase": "pipeline"})
            .eq("domain", domain)
            .is_("rejection_reason", "null")
            .execute()
        )
        logger.debug("Persisted rejection_reason=%s for domain=%s", rejection_reason, domain)
    except Exception as exc:
        logger.warning("Could not persist rejection_reason for %s: %s", domain, exc)

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
    # D2.2-PREP: 4 new verticals (verified via DFS API, offset_start=50 recommended)
    "recruitment": 12371,    # Recruiting & Retention — HIGH confidence
    "itmsp": 12202,          # Computer Tech Support — MEDIUM confidence (narrow ETV)
    "webdev": 11493,         # Web Design & Development — MEDIUM-HIGH confidence
    "coaching": 11098,       # Management Consulting (proxy for business coaching) — HIGH confidence
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
    except Exception as exc:
        logger.warning("TG progress notif failed: %s", exc)


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
        "latency_report": None,
        "errors": [],
        "_latency_tracker": LatencyTracker(domain),
    }


def _tracker(domain_data: dict) -> LatencyTracker:
    """Return the domain's LatencyTracker, creating a fallback if absent."""
    t = domain_data.get("_latency_tracker")
    if t is None:
        t = LatencyTracker(domain_data.get("domain", "unknown"))
        domain_data["_latency_tracker"] = t
    return t


# ---------------------------------------------------------------------------
# Stage wrappers
# ---------------------------------------------------------------------------


async def _run_stage2(domain_data: dict, dfs: DFSLabsClient) -> dict:
    """Stage 2 VERIFY — 5 SERP queries per domain."""
    _tracker(domain_data).start_stage("stage2")
    t0 = time.monotonic()
    try:
        result = await run_serp_verify(dfs, domain_data["domain"])
        domain_data["stage2"] = result
        domain_data["cost_usd"] += result.get("_cost", 0)
    except Exception as exc:
        domain_data["errors"].append(f"stage2: {exc}")
        domain_data["stage2"] = {}
    domain_data["timings"]["stage2"] = round(time.monotonic() - t0, 2)
    _tracker(domain_data).end_stage("stage2")
    return domain_data


async def _run_stage3(domain_data: dict, gemini: GeminiClient) -> dict:
    """Stage 3 IDENTIFY — Gemini identity + DM extraction."""
    _tracker(domain_data).start_stage("stage3")
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
        _tracker(domain_data).end_stage("stage3")
        await _persist_drop_reason(domain_data)
        return domain_data

    domain_data["cost_usd"] += result.get("cost_usd", 0)
    domain_data["timings"]["stage3"] = round(time.monotonic() - t0, 2)
    content = result.get("content") or {}
    domain_data["stage3"] = content

    if result.get("f_status") != "success":
        domain_data["dropped_at"] = "stage3"
        domain_data["drop_reason"] = f"stage3_failed: {result.get('f_failure_reason')}"
        _tracker(domain_data).end_stage("stage3")
        await _persist_drop_reason(domain_data)
        return domain_data
    if content.get("is_enterprise_or_chain"):
        domain_data["dropped_at"] = "stage3"
        domain_data["drop_reason"] = "enterprise_or_chain"
        _tracker(domain_data).end_stage("stage3")
        await _persist_drop_reason(domain_data)
        return domain_data
    if not (content.get("dm_candidate") or {}).get("name"):
        domain_data["dropped_at"] = "stage3"
        domain_data["drop_reason"] = "no_dm_found"
        _tracker(domain_data).end_stage("stage3")
        await _persist_drop_reason(domain_data)
        return domain_data
    _tracker(domain_data).end_stage("stage3")
    return domain_data


async def _persist_stage4_to_bu(domain: str, bundle: dict) -> None:
    """H3: Write DFS bundle to BU immediately after Stage 4, before Stage 5 gate.

    Best-effort — failure does not block pipeline. Uses asyncpg directly to avoid
    ORM overhead in a hot parallel path. Writes raw bundle + scalar extracts so
    data survives even if domain drops at Stage 5.
    """
    import asyncpg as _asyncpg

    db_url_raw = os.environ.get("DATABASE_URL", "")
    if not db_url_raw:
        logger.warning("H3 BU write skipped: DATABASE_URL not set for domain=%s", domain)
        return
    db_url = db_url_raw.replace("postgresql+asyncpg://", "postgresql://")
    rank = bundle.get("rank_overview") or {}
    backlinks = bundle.get("backlinks") or {}
    try:
        conn = await _asyncpg.connect(db_url, statement_cache_size=0)
        try:
            await conn.execute(
                """INSERT INTO business_universe (domain, display_name,
                       dfs_organic_etv, dfs_organic_keywords, backlinks_count, domain_rank,
                       stage_metrics)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain != '' DO UPDATE SET
                       dfs_organic_etv = COALESCE(EXCLUDED.dfs_organic_etv, business_universe.dfs_organic_etv),
                       dfs_organic_keywords = COALESCE(EXCLUDED.dfs_organic_keywords, business_universe.dfs_organic_keywords),
                       backlinks_count = COALESCE(EXCLUDED.backlinks_count, business_universe.backlinks_count),
                       domain_rank = COALESCE(EXCLUDED.domain_rank, business_universe.domain_rank),
                       stage_metrics = business_universe.stage_metrics || $7::jsonb,
                       updated_at = NOW()""",
                domain,
                domain.split(".")[0].replace("-", " ").title(),
                rank.get("organic_etv"),
                rank.get("organic_keywords"),
                backlinks.get("backlinks_num"),
                rank.get("rank"),
                json.dumps({"stage4": bundle}),
            )
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning("H3 stage4 BU write attempt 1 failed for %s: %s — retrying", domain, exc)
        try:
            await asyncio.sleep(1)
            conn = await _asyncpg.connect(db_url, statement_cache_size=0)
            try:
                await conn.execute(
                    """INSERT INTO business_universe (domain, display_name,
                           dfs_organic_etv, dfs_organic_keywords, backlinks_count, domain_rank,
                           stage_metrics)
                       VALUES ($1, $2, $3, $4, $5, $6, $7)
                       ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain != '' DO UPDATE SET
                           dfs_organic_etv = COALESCE(EXCLUDED.dfs_organic_etv, business_universe.dfs_organic_etv),
                           dfs_organic_keywords = COALESCE(EXCLUDED.dfs_organic_keywords, business_universe.dfs_organic_keywords),
                           backlinks_count = COALESCE(EXCLUDED.backlinks_count, business_universe.backlinks_count),
                           domain_rank = COALESCE(EXCLUDED.domain_rank, business_universe.domain_rank),
                           stage_metrics = COALESCE(business_universe.stage_metrics, '{}'::jsonb) || $7::jsonb,
                           updated_at = NOW()""",
                    domain,
                    domain.split(".")[0].replace("-", " ").title(),
                    rank.get("organic_etv"),
                    rank.get("organic_keywords"),
                    backlinks.get("backlinks_num"),
                    rank.get("rank"),
                    json.dumps({"stage4": bundle}),
                )
            finally:
                await conn.close()
        except Exception as exc2:
            logger.error("H3 stage4 BU write FAILED permanently for %s: %s (GOV-8 data loss)", domain, exc2)


async def _run_stage4(domain_data: dict, dfs: DFSLabsClient) -> dict:
    """Stage 4 SIGNAL — DFS signal bundle."""
    _tracker(domain_data).start_stage("stage4")
    t0 = time.monotonic()
    biz = domain_data.get("stage3", {}).get("business_name")
    try:
        bundle = await build_signal_bundle(dfs, domain_data["domain"], business_name=biz)
        domain_data["stage4"] = bundle
        # H3: persist DFS bundle to BU immediately — survives Stage 5 drop
        await _persist_stage4_to_bu(domain_data["domain"], bundle)
    except Exception as exc:
        domain_data["errors"].append(f"stage4: {exc}")
        domain_data["stage4"] = {}
    # Fixed cost: 10 DFS endpoints sum = $0.0775, rounded up to $0.078/domain (parallel-safe)
    domain_data["cost_usd"] += STAGE4_COST_PER_DOMAIN
    domain_data["timings"]["stage4"] = round(time.monotonic() - t0, 2)
    _tracker(domain_data).end_stage("stage4")
    return domain_data


async def _run_stage5(domain_data: dict) -> dict:
    """Stage 5 SCORE — prospect viability scoring (pure logic)."""
    _tracker(domain_data).start_stage("stage5")
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
        _tracker(domain_data).end_stage("stage5")
        await _persist_drop_reason(domain_data)
        return domain_data

    domain_data["timings"]["stage5"] = round(time.monotonic() - t0, 4)
    if not scores.get("is_viable_prospect"):
        domain_data["dropped_at"] = "stage5"
        domain_data["drop_reason"] = f"viability: {scores.get('viability_reason')}"
        await _persist_drop_reason(domain_data)
    elif scores.get("composite_score", 0) < 30:
        domain_data["dropped_at"] = "stage5"
        domain_data["drop_reason"] = f"score_below_gate: {scores.get('composite_score')}"
        await _persist_drop_reason(domain_data)
    _tracker(domain_data).end_stage("stage5")
    return domain_data


async def _run_stage6(domain_data: dict, dfs: DFSLabsClient) -> dict:
    """Stage 6 ENRICH — historical rank (gated: composite_score >= 60)."""
    if (domain_data.get("stage5") or {}).get("composite_score", 0) < 60:
        return domain_data
    _tracker(domain_data).start_stage("stage6")
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
    _tracker(domain_data).end_stage("stage6")
    return domain_data


async def _run_stage7(domain_data: dict, gemini: GeminiClient) -> dict:
    """Stage 7 ANALYSE — Gemini VR + outreach generation."""
    _tracker(domain_data).start_stage("stage7")
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
    _tracker(domain_data).end_stage("stage7")
    return domain_data


def _source_to_tier(source: str) -> str:
    """Map waterfall source name to tier label."""
    return {
        "contact_registry": "L0",  # Stage 3 Gemini extracted
        "contactout": "L1",
        "hunter": "L2",
        "leadmagic": "L3",
        "contactout_stale": "L4",
        "brightdata": "L5",
        "none": "NONE",
    }.get(source, f"UNKNOWN:{source}")


async def _run_stage8(domain_data: dict, dfs: DFSLabsClient, bd: BrightDataClient | None = None, lm: LeadmagicClient | None = None) -> dict:
    """Stage 8 CONTACT — verify fills (8a) + unified contact waterfall (8b-d)."""
    _tracker(domain_data).start_stage("stage8")
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
        contactout_result = await enrich_dm_via_contactout(
            linkedin_url=dm_linkedin,
            dm_name=dm.get("name"),
            company_name=identity.get("business_name"),
            dm_title=dm.get("role"),
        )
        if contactout_result:
            domain_data["cost_usd"] += STAGE8_WATERFALL_COST  # ContactOut credit
    except Exception as exc:
        domain_data["errors"].append(f"stage8b_contactout: {exc}")

    # 8c: Email waterfall (uses contactout_result, falls through to Hunter/Leadmagic/BD)
    # GOV-8: Stage 3 Gemini already extracted dm_email + primary_email from website.
    # Pass as contact_data so L0 contact_registry can use it without re-fetching.
    stage3_contact_data = {}
    if dm.get("email"):
        stage3_contact_data["company_email"] = dm["email"]
    elif identity.get("dm_email"):
        stage3_contact_data["company_email"] = identity["dm_email"]
    elif identity.get("primary_email"):
        stage3_contact_data["company_email"] = identity["primary_email"]

    email_result = None
    try:
        dm_verified = bool((identity.get("dm_candidate") or {}).get("_dm_verified") or identity.get("_dm_verified"))
        email_result = await discover_email(
            domain=domain_data["domain"],
            dm_name=dm.get("name", ""),
            dm_linkedin=dm_linkedin,
            company_name=identity.get("business_name"),
            contact_data=stage3_contact_data or None,
            contactout_result=contactout_result,
            dm_verified=dm_verified,
        )
    except Exception as exc:
        domain_data["errors"].append(f"stage8c_email: {exc}")

    # 8d: Mobile waterfall (uses contactout_result, no duplicate API call)
    # Pass brightdata_client (bd) and contact_data from Stage 3 identity (Fix D2.2-1)
    mobile_result = None
    try:
        contact_data_mobile: dict = {}
        dm_phone = dm.get("dm_phone") or dm.get("primary_phone") or identity.get("primary_phone")
        if dm_phone:
            contact_data_mobile["company_mobile"] = dm_phone
        mobile_result = await run_mobile_waterfall(
            domain=domain_data["domain"],
            dm_linkedin_url=dm_linkedin,
            contact_data=contact_data_mobile or None,
            contactout_result=contactout_result,
            brightdata_client=bd,
            leadmagic_client=lm,
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
    # Tier tracking for GOV-8 verification
    contacts["email_resolved_at_tier"] = _source_to_tier(email_result.source if email_result else "none")
    contacts["email_resolved_by_provider"] = email_result.source if email_result and email_result.email else None
    contacts["mobile_resolved_at_tier"] = _source_to_tier(mobile_result.source if mobile_result else "none")
    contacts["mobile_resolved_by_provider"] = mobile_result.source if mobile_result and mobile_result.mobile else None

    domain_data["stage8_contacts"] = contacts

    domain_data["timings"]["stage8"] = round(time.monotonic() - t0, 2)
    _tracker(domain_data).end_stage("stage8")
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
    _tracker(domain_data).start_stage("stage9")
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
        # H2: persist social posts to BU immediately after scrape.
        # dm_social_posts / company_social_posts columns not yet in schema —
        # written to stage_metrics JSONB until migration adds dedicated columns.
        await _persist_stage9_social_to_bu(domain_data["domain"], result)
    except Exception as exc:
        domain_data["errors"].append(f"stage9: {exc}")
    domain_data["timings"]["stage9"] = round(time.monotonic() - t0, 2)
    _tracker(domain_data).end_stage("stage9")
    return domain_data


async def _persist_stage9_social_to_bu(domain: str, social_result: dict) -> None:
    """H2: Write Stage 9 social posts to BU immediately after scrape.

    MIGRATION NEEDED: Add dm_social_posts (jsonb) and company_social_posts (jsonb)
    columns to business_universe. Until then, data is stored under stage_metrics->stage9.
    """
    import asyncpg as _asyncpg

    db_url_raw = os.environ.get("DATABASE_URL", "")
    if not db_url_raw:
        logger.warning("H2 BU write skipped: DATABASE_URL not set for domain=%s", domain)
        return
    db_url = db_url_raw.replace("postgresql+asyncpg://", "postgresql://")
    stage9_json = json.dumps({"stage9": social_result})
    try:
        conn = await _asyncpg.connect(db_url, statement_cache_size=0)
        try:
            await conn.execute(
                """INSERT INTO business_universe (domain, display_name, stage_metrics)
                   VALUES ($1, $2, $3::jsonb)
                   ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain != '' DO UPDATE SET
                       stage_metrics = COALESCE(business_universe.stage_metrics, '{}'::jsonb) || $3::jsonb,
                       updated_at = NOW()""",
                domain,
                domain.split(".")[0].replace("-", " ").title(),
                stage9_json,
            )
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning("H2 stage9 social BU write attempt 1 failed for %s: %s — retrying", domain, exc)
        try:
            await asyncio.sleep(1)
            conn = await _asyncpg.connect(db_url, statement_cache_size=0)
            try:
                await conn.execute(
                    """INSERT INTO business_universe (domain, display_name, stage_metrics)
                       VALUES ($1, $2, $3::jsonb)
                       ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain != '' DO UPDATE SET
                           stage_metrics = COALESCE(business_universe.stage_metrics, '{}'::jsonb) || $3::jsonb,
                           updated_at = NOW()""",
                    domain,
                    domain.split(".")[0].replace("-", " ").title(),
                    stage9_json,
                )
            finally:
                await conn.close()
        except Exception as exc2:
            logger.error("H2 stage9 social BU write FAILED permanently for %s: %s (GOV-8 data loss)", domain, exc2)


async def _run_stage10(domain_data: dict) -> dict:
    """Stage 10 VR+MSG — value report and outreach (gated: email found)."""
    contacts = domain_data.get("stage8_contacts") or {}
    email_data = contacts.get("email", {})
    if not email_data.get("email"):
        return domain_data
    _tracker(domain_data).start_stage("stage10")
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
    _tracker(domain_data).end_stage("stage10")
    return domain_data


async def _run_stage11(domain_data: dict) -> dict:
    """Stage 11 CARD — assemble final lead card."""
    _tracker(domain_data).start_stage("stage11")
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
    _tracker(domain_data).end_stage("stage11")
    domain_data["latency_report"] = _tracker(domain_data).report()
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

    # Tier tracking aggregates
    tier_counts_email: Counter = Counter()
    tier_counts_mobile: Counter = Counter()
    for d in pipeline:
        contacts = d.get("stage8_contacts") or {}
        tier_counts_email[contacts.get("email_resolved_at_tier", "NONE")] += 1
        tier_counts_mobile[contacts.get("mobile_resolved_at_tier", "NONE")] += 1

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
        "per_tier_hit_rate_email": dict(tier_counts_email),
        "per_tier_hit_rate_mobile": dict(tier_counts_mobile),
        "l0_hit_rate_email": tier_counts_email.get("L0", 0) / max(len(pipeline), 1),
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
    domains: list[str] | None = None,
    force_replay: bool = False,
    dry_run: bool = False,
) -> dict:
    if dry_run:
        os.environ["DRY_RUN"] = "1"
        logger.info("[DRY-RUN] All API calls will return empty responses. No spend.")
        _tg("[DRY-RUN] Trace mode — no API calls, no spend")
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
    lm = LeadmagicClient()

    # Pre-run cost estimate and hard cap
    # When --domains is used, domains_per_category=0 and categories=[], so use len(domains) directly
    total_requested = len(domains) if domains else (domains_per_category * len(categories))
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
    # Stage 1: DISCOVER (or direct domain injection via --domains)
    # ---------------------------------------------------------------------------
    all_domain_items: list[dict] = []

    if domains:
        # Bypass Stage 1 — direct domain injection
        for d in domains:
            if not d or "." not in d:
                logger.warning("Domain %s has no TLD — skipping", d)
                continue
            if is_blocked(d) and not force_replay:
                logger.warning("Domain %s is in blocklist — skipping (use --force-replay to override)", d)
                continue
            all_domain_items.append(_new_domain(d, "replay"))
        logger.info("Direct injection: %d domains (bypassed Stage 1)", len(all_domain_items))
        _tg(f"Direct injection: {len(all_domain_items)} domains (bypassed Stage 1)")
    else:
        logger.info("Stage 1 DISCOVER — categories=%s, n=%d", categories, domains_per_category)

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

        _tg(f"Stage 1 DISCOVER complete: {len(all_domain_items)} domains across {len(categories)} categories")

    if domains:
        # all_domain_items already contains _new_domain() dicts (injected above)
        pipeline: list[dict] = all_domain_items
    else:
        pipeline = [_new_domain(d["domain"], d["category"]) for d in all_domain_items]

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
    updated8 = await run_parallel(active8, lambda d: _run_stage8(d, dfs, bd, lm), concurrency=15, label="Stage 8 CONTACT")
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
    if dry_run:
        os.environ.pop("DRY_RUN", None)
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
    p.add_argument("--domains", default=None, help="Comma-separated domain list (bypasses Stage 1 discovery)")
    p.add_argument("--force-replay", action="store_true", help="Allow blocked domains through for diagnostic replay")
    p.add_argument("--dry-run", action="store_true", help="Trace decision logic without API calls (no spend)")
    return p.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()

    if args.domains:
        domain_list = [d.strip() for d in args.domains.split(",") if d.strip()]
        asyncio.run(run_cohort(
            categories=[],
            domains_per_category=0,
            output_dir=args.output_dir,
            domains=domain_list,
            force_replay=args.force_replay,
            dry_run=args.dry_run,
        ))
    else:
        cats = [c.strip() for c in args.categories.split(",") if c.strip()]
        per_cat = max(1, args.size // len(cats))
        if per_cat * len(cats) > 2 * args.size:
            print(f"ERROR: Computed {per_cat * len(cats)} domains exceeds 2× requested {args.size}")
            sys.exit(1)
        asyncio.run(run_cohort(
            categories=cats,
            domains_per_category=per_cat,
            output_dir=args.output_dir,
            force_replay=args.force_replay,
            dry_run=args.dry_run,
        ))
