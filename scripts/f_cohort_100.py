"""DEPRECATED — v1 pipeline. Do not run. Replaced by Directive D1 cohort runner for Pipeline F v2.1.

Original: Pipeline F v1 — 100-domain cohort runner.
F-TASK-B-100: 10 categories × 10 domains → F3a→F6 pipeline.
"""

import os
import sys

sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS")

from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncio
import json
import logging
import time
from collections import Counter
from datetime import UTC, datetime
from typing import Any

import httpx as _httpx

from src.clients.dfs_labs_client import DFSLabsClient
from src.config.category_etv_windows import CATEGORY_ETV_WINDOWS, get_etv_window
from src.intelligence.contact_waterfall import (
    fetch_dm_posts,
    run_contact_waterfall,
)
from src.intelligence.dfs_signal_bundle import build_signal_bundle
from src.intelligence.enhanced_vr import run_enhanced_vr
from src.intelligence.funnel_classifier import classify_prospect
from src.intelligence.gemini_client import GeminiClient
from src.intelligence.verify_fills import run_verify_fills
from src.utils.domain_blocklist import is_blocked

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CATEGORIES = {
    13462: "Plumbing",
    11295: "Electrical Wiring",
    10333: "Hair Salons & Styling Services",
    10020: "Dining & Nightlife",
    10531: "Real Estate Investments",
    11093: "Accounting & Auditing",
    13686: "Attorneys & Law Firms",
    10193: "Vehicle Repair & Maintenance",
    10123: "Fitness",
    11979: "Veterinary",
}

DOMAINS_PER_CATEGORY = 10
BATCH_SIZE = 10
NOT_TRYING = {"NOT_TRYING", "DORMANT"}
OUTREACH_SUBS = {"{{agency_contact_name}}": "Test Contact", "{{agency_name}}": "Test Agency"}
BUDGET_TOTAL, BUDGET_GEMINI, BUDGET_APIFY, BUDGET_WARN_PCT = 25.0, 2.0, 8.0, 0.80


def _tg(msg: str) -> None:
    import contextlib

    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        return
    with contextlib.suppress(Exception):
        _httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": "7267788033", "text": f"[EVO] {msg}"},
            timeout=10,
        )


def _sub_placeholders(obj: Any) -> Any:
    if isinstance(obj, str):
        for k, v in OUTREACH_SUBS.items():
            obj = obj.replace(k, v)
        return obj
    if isinstance(obj, dict):
        return {k: _sub_placeholders(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sub_placeholders(i) for i in obj]
    return obj


async def discover_category(
    dfs: DFSLabsClient,
    category_code: int,
    category_name: str,
    target: int = DOMAINS_PER_CATEGORY,
    max_pages: int = 3,
) -> tuple[list[str], float]:
    """Return (domains, cost_usd) for one category."""
    window = CATEGORY_ETV_WINDOWS[category_code]
    etv_min, etv_max = get_etv_window(category_code)
    offset_start = window["offset_start"]
    domains: list[str] = []
    cost = 0.0

    for page in range(max_pages):
        offset = offset_start + page * 100
        results = await dfs.domain_metrics_by_categories(
            category_codes=[category_code],
            limit=100,
            offset=offset,
        )
        cost += 0.10  # ~$0.10/call

        for row in results:
            d = row.get("domain", "")
            etv = row.get("organic_etv", 0.0)
            if not d or is_blocked(d):
                continue
            if etv_min <= etv <= etv_max:
                if d not in domains:
                    domains.append(d)
            if len(domains) >= target:
                break

        logger.info(
            "[F1] %s page=%d offset=%d found=%d/%d",
            category_name,
            page,
            offset,
            len(domains),
            target,
        )
        if len(domains) >= target:
            break

    return domains[:target], cost


async def run_f1_discovery(dfs: DFSLabsClient) -> tuple[dict[str, list[str]], float]:
    """Discover 10 domains per category. Returns {category_name: [domains]}, cost."""
    tasks = [discover_category(dfs, code, name) for code, name in CATEGORIES.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    category_domains: dict[str, list[str]] = {}
    total_cost = 0.0

    for (_code, name), result in zip(CATEGORIES.items(), results, strict=True):
        if isinstance(result, Exception):
            logger.error("[F1] %s discovery failed: %s", name, result)
            category_domains[name] = []
        else:
            domains, cost = result
            category_domains[name] = domains
            total_cost += cost
            logger.info("[F1] %s → %d domains, cost=$%.3f", name, len(domains), cost)

    return category_domains, total_cost


def _build_card(
    domain: str,
    f3a: dict,
    f3b: dict | None,
    f4: dict,
    f5: dict,
    dm_candidate: dict,
    classification: dict,
    enhanced_vr_result: dict | None,
    raw_posts: list,
    filtered_posts: list,
    f3a_result: dict,
    signal_bundle: dict,
    f3b_result: dict,
    cost: float,
) -> dict:
    evr_content = enhanced_vr_result.get("content") if enhanced_vr_result else None
    return {
        "domain": domain,
        "business_name": f3a.get("business_name"),
        "location": f3a.get("location"),
        "industry_category": f3a.get("industry_category"),
        "entity_type_hint": f3a.get("entity_type_hint"),
        "staff_estimate_band": f3a.get("staff_estimate_band"),
        "primary_phone": f3a.get("primary_phone"),
        "primary_email": f3a.get("primary_email"),
        "abn": f4.get("abn"),
        "abn_status": f4.get("abn_status"),
        "dm_candidate": f3a.get("dm_candidate"),
        "dm_linkedin_url": f4.get("dm_linkedin_url") or dm_candidate.get("linkedin_url"),
        "contacts": f5,
        "intent_band": f3b.get("intent_band_final") if f3b else f3a.get("intent_band_preliminary"),
        "affordability_score": f3a.get("affordability_score"),
        "affordability_gate": f3a.get("affordability_gate"),
        "buyer_match_score": f3a.get("buyer_match_score"),
        "vulnerability_report": f3b.get("vulnerability_report") if f3b else None,
        "classification": classification,
        "outreach": {
            "draft_email": f3b.get("draft_email") if f3b else None,
            "draft_linkedin_note": f3b.get("draft_linkedin_note") if f3b else None,
            "draft_voice_script": f3b.get("draft_voice_script") if f3b else None,
            "enhanced": evr_content,
        },
        "dm_posts": {
            "total_fetched": len(raw_posts),
            "after_author_filter": len(filtered_posts),
            "posts": filtered_posts,
        },
        "cost_breakdown": {
            "f3a_usd": f3a_result.get("cost_usd", 0.0),
            "f2_usd": signal_bundle.get("cost_usd", 0.0),
            "f3b_usd": f3b_result.get("cost_usd", 0.0),
            "f4_usd": f4.get("_cost") or 0.006,
            "f5_usd": 0.0,
            "f6_enhanced_vr_usd": enhanced_vr_result.get("cost_usd", 0.0)
            if enhanced_vr_result
            else 0.0,
            "total_usd": round(cost, 6),
            "total_aud": round(cost * 1.55, 4),
        },
    }


# ── Per-domain pipeline ──────────────────────────────────────────────────────


async def run_pipeline_f(
    domain: str,
    category_name: str,
    dfs: DFSLabsClient,
    gemini: GeminiClient,
) -> dict:
    wall_start = time.monotonic()
    result: dict = {
        "domain": domain,
        "category": category_name,
        "business_name": None,
        "dm_name": None,
        "classification": "dropped",
        "verification_level": "minimal",
        "f3a_status": "pending",
        "f3a_drop_reason": None,
        "f3b_status": "pending",
        "f4_abn": None,
        "f4_abn_status": None,
        "f4_company_linkedin": None,
        "f5_linkedin_source": None,
        "f5_linkedin_match_type": None,
        "f5_linkedin_match_company": None,
        "f5_linkedin_match_confidence": None,
        "f5_email_tier": None,
        "f5_email_source": None,
        "f5_mobile_tier": None,
        "f5_posts_fetched": 0,
        "f5_posts_authored": 0,
        "f6_enhanced_vr_triggered": False,
        "cost_usd": 0.0,
        "wall_clock_s": 0.0,
        "card": {},
        "error": None,
    }

    try:
        # Snapshot DFS cumulative cost before this domain (for delta computation)
        dfs_cost_before = dfs.total_cost_usd
        stage_times: dict[str, float] = {}

        # ── F3a COMPREHEND ───────────────────────────────────────────────────
        t0 = time.monotonic()
        f3a_result = await gemini.call_f3a(domain=domain, dfs_base_metrics={})
        stage_times["f3a"] = round(time.monotonic() - t0, 2)
        f3a_status = f3a_result.get("f_status", "failed")
        f3a_content: dict = f3a_result.get("content") or {}
        result["f3a_status"] = f3a_status
        result["business_name"] = f3a_content.get("business_name")
        cost = f3a_result.get("cost_usd", 0.0)

        afford_gate = f3a_content.get("affordability_gate", "")
        intent_prelim = f3a_content.get("intent_band_preliminary", "")

        if f3a_status != "success":
            result["f3a_drop_reason"] = f3a_result.get("f_failure_reason", "f3a_failed")
            result["cost_usd"] = cost
            result["wall_clock_s"] = time.monotonic() - wall_start
            result["stage_times"] = stage_times
            return result

        if afford_gate == "cannot_afford" or intent_prelim.upper() in NOT_TRYING:
            result["f3a_drop_reason"] = f"gate={afford_gate} intent={intent_prelim}"
            result["cost_usd"] = cost
            result["wall_clock_s"] = time.monotonic() - wall_start
            result["stage_times"] = stage_times
            return result

        # ── F2 SIGNAL ────────────────────────────────────────────────────────
        t0 = time.monotonic()
        dfs_pre_f2 = dfs.total_cost_usd
        signal_bundle = await build_signal_bundle(dfs, domain)
        stage_times["f2"] = round(time.monotonic() - t0, 2)
        cost += dfs.total_cost_usd - dfs_pre_f2  # delta, not cumulative

        # ── F3b COMPILE ──────────────────────────────────────────────────────
        t0 = time.monotonic()
        f3b_result = await gemini.call_f3b(f3a_output=f3a_content, signal_bundle=signal_bundle)
        stage_times["f3b"] = round(time.monotonic() - t0, 2)
        f3b_status = f3b_result.get("f_status", "failed")
        f3b_content: dict | None = f3b_result.get("content")
        result["f3b_status"] = f3b_status
        cost += f3b_result.get("cost_usd", 0.0)

        if f3b_status != "success":
            logger.warning("[F3b] %s failed — continuing with F3a-only data", domain)
            f3b_content = None

        # ── F4 VERIFY ────────────────────────────────────────────────────────
        t0 = time.monotonic()
        dfs_pre_f4 = dfs.total_cost_usd
        f4_result = await run_verify_fills(dfs=dfs, f3a_output=f3a_content)
        stage_times["f4"] = round(time.monotonic() - t0, 2)
        cost += dfs.total_cost_usd - dfs_pre_f4  # delta, not hardcoded _cost
        result["f4_abn"] = f4_result.get("abn")
        result["f4_abn_status"] = f4_result.get("abn_status")
        result["f4_company_linkedin"] = f4_result.get("company_linkedin_url")

        # ── F5 CONTACT ───────────────────────────────────────────────────────
        t0 = time.monotonic()
        dm_candidate = f3a_content.get("dm_candidate") or {}
        result["dm_name"] = dm_candidate.get("name")
        f5_result = await run_contact_waterfall(
            dm_name=dm_candidate.get("name"),
            dm_title=dm_candidate.get("role"),
            business_name=f3a_content.get("business_name", ""),
            domain=domain,
            f3a_linkedin_url=dm_candidate.get("linkedin_url"),
            f4_linkedin_url=f4_result.get("dm_linkedin_url"),
            company_linkedin_url=f4_result.get("company_linkedin_url"),
            entity_type=f3a_content.get("entity_type_hint"),
            business_phone=f3a_content.get("primary_phone"),
        )
        stage_times["f5_contact"] = round(time.monotonic() - t0, 2)
        li = f5_result.get("linkedin", {})
        em = f5_result.get("email", {})
        mo = f5_result.get("mobile", {})
        result["f5_linkedin_source"] = li.get("source")
        result["f5_linkedin_match_type"] = li.get("match_type")
        result["f5_linkedin_match_company"] = li.get("match_company")
        result["f5_linkedin_match_confidence"] = li.get("match_confidence")
        result["f5_email_tier"] = em.get("tier")
        result["f5_email_source"] = em.get("source")
        result["f5_mobile_tier"] = mo.get("tier")

        # ── F5 DM POSTS ──────────────────────────────────────────────────────
        t0 = time.monotonic()
        dm_linkedin_url = (
            f4_result.get("dm_linkedin_url")
            or dm_candidate.get("linkedin_url")
            or li.get("linkedin_url")
        )
        li_match_type = li.get("match_type", "no_match")
        raw_posts: list[dict] = []
        filtered_posts: list[dict] = []

        if dm_linkedin_url and li_match_type != "no_match":
            filtered_posts = await fetch_dm_posts(
                dm_linkedin_url=dm_linkedin_url,
                dm_name=dm_candidate.get("name"),
            )
            raw_posts = filtered_posts
        stage_times["f5_posts"] = round(time.monotonic() - t0, 2)

        result["f5_posts_fetched"] = len(raw_posts)
        result["f5_posts_authored"] = len(filtered_posts)

        # ── F6 CLASSIFY ──────────────────────────────────────────────────────
        classification = classify_prospect(
            f3a_output=f3a_content,
            f3b_output=f3b_content,
            contacts=f5_result,
        )
        result["classification"] = classification.get("classification", "dropped")
        result["verification_level"] = classification.get("dm_verification_level", "minimal")

        # ── F6 ENHANCED VR ───────────────────────────────────────────────────
        t0 = time.monotonic()
        enhanced_vr_result: dict | None = None
        if classification.get("classification") in ("ready", "near_ready") and f3b_content:
            enhanced_vr_result = await run_enhanced_vr(
                f3b_output=f3b_content,
                dm_posts=filtered_posts,
                contact_details=f5_result,
            )
            cost += enhanced_vr_result.get("cost_usd", 0.0) if enhanced_vr_result else 0.0
            result["f6_enhanced_vr_triggered"] = True
        stage_times["f6_evr"] = round(time.monotonic() - t0, 2)

        # ── Build card ───────────────────────────────────────────────────────
        result["card"] = _sub_placeholders(
            _build_card(
                domain=domain,
                f3a=f3a_content,
                f3b=f3b_content,
                f4=f4_result,
                f5=f5_result,
                dm_candidate=dm_candidate,
                classification=classification,
                enhanced_vr_result=enhanced_vr_result,
                raw_posts=raw_posts,
                filtered_posts=filtered_posts,
                f3a_result=f3a_result,
                signal_bundle=signal_bundle,
                f3b_result=f3b_result,
                cost=cost,
            )
        )
        result["cost_usd"] = cost
        result["dfs_cost_delta"] = dfs.total_cost_usd - dfs_cost_before
        result["stage_times"] = stage_times

    except Exception as exc:
        logger.error("[pipeline] %s error: %s", domain, exc, exc_info=True)
        result["error"] = str(exc)

    result["wall_clock_s"] = time.monotonic() - wall_start
    return result


# ── Summary builder ──────────────────────────────────────────────────────────


def _median(lst: list) -> float:
    if not lst:
        return 0.0
    return sorted(lst)[len(lst) // 2]


def _build_summary(results: list[dict], cost_total: float, wall_total: float) -> dict:
    clf = Counter(r.get("classification", "dropped") for r in results)
    vl = Counter(r.get("verification_level", "minimal") for r in results)
    costs = [r.get("cost_usd", 0.0) for r in results]
    walls = [r.get("wall_clock_s", 0.0) for r in results]

    def _count(key: str, val: str | None = None) -> int:
        return sum(1 for r in results if (r.get(key) == val if val else bool(r.get(key))))

    return {
        "total": len(results),
        "f3a_success": _count("f3a_status", "success"),
        "f3a_dropped": _count("f3a_drop_reason"),
        "f3b_success": _count("f3b_status", "success"),
        "classification": dict(clf),
        "verification": dict(vl),
        "f4_abn_verified": _count("f4_abn"),
        "f4_company_linkedin_resolved": _count("f4_company_linkedin"),
        "f5_linkedin_l2_attempted": _count("f5_linkedin_source"),
        "f5_linkedin_l2_direct_match": _count("f5_linkedin_match_type", "direct_match"),
        "f5_linkedin_l2_no_match": _count("f5_linkedin_match_type", "no_match"),
        "f5_email_resolved": sum(
            1 for r in results if r.get("f5_email_source") not in (None, "none")
        ),
        "f5_mobile_resolved": sum(
            1 for r in results if r.get("f5_mobile_tier") not in (None, "unresolved")
        ),
        "cost_total_usd": round(cost_total, 4),
        "cost_total_aud": round(cost_total * 1.55, 4),
        "cost_per_prospect_median": round(_median(costs), 6),
        "wall_clock_total_s": round(wall_total, 2),
        "wall_clock_per_prospect_median": round(_median(walls), 2),
    }


# ── Budget check ─────────────────────────────────────────────────────────────


def _check_budget(cost_total: float, cost_gemini: float, cost_apify: float) -> None:
    for label, spent, limit in [
        ("total", cost_total, BUDGET_TOTAL),
        ("gemini", cost_gemini, BUDGET_GEMINI),
        ("apify", cost_apify, BUDGET_APIFY),
    ]:
        pct = spent / limit if limit else 0
        if pct >= 1.0:
            raise RuntimeError(f"Budget HARD STOP: {label} ${spent:.3f} >= ${limit}")
        if pct >= BUDGET_WARN_PCT:
            logger.warning("Budget warning: %s %.0f%% of $%.2f", label, pct * 100, limit)


# ── Main ─────────────────────────────────────────────────────────────────────


async def main() -> None:
    run_start = time.monotonic()
    logger.info("=== F-TASK-B-100 cohort runner starting ===")

    dfs = DFSLabsClient(
        login=os.environ["DATAFORSEO_LOGIN"],
        password=os.environ["DATAFORSEO_PASSWORD"],
    )
    gemini = GeminiClient()

    # ── Phase 1: Discovery ────────────────────────────────────────────────────
    logger.info("Phase 1: F1 discovery — 10 categories × 10 domains")
    category_domains, discovery_cost = await run_f1_discovery(dfs)

    total_found = sum(len(v) for v in category_domains.values())
    logger.info("F1 complete: %d domains discovered, cost=$%.3f", total_found, discovery_cost)
    _tg(
        f"F1 complete: {total_found} domains across {len(category_domains)} categories | cost=${discovery_cost:.3f}"
    )

    # Flatten to (domain, category_name) pairs preserving category order
    domain_pairs: list[tuple[str, str]] = []
    for cat_name, domains in category_domains.items():
        for d in domains:
            domain_pairs.append((d, cat_name))

    # ── Phase 2: Pipeline F — batched ────────────────────────────────────────
    logger.info("Phase 2: Pipeline F on %d domains (batch_size=%d)", len(domain_pairs), BATCH_SIZE)
    all_results: list[dict] = []
    cost_total = discovery_cost
    completed = 0

    for batch_start in range(0, len(domain_pairs), BATCH_SIZE):
        batch = domain_pairs[batch_start : batch_start + BATCH_SIZE]
        logger.info("Batch %d-%d", batch_start + 1, batch_start + len(batch))

        batch_results = await asyncio.gather(
            *[run_pipeline_f(domain, cat, dfs, gemini) for domain, cat in batch],
            return_exceptions=True,
        )

        for item in batch_results:
            if isinstance(item, Exception):
                logger.error("Batch item exception: %s", item)
                all_results.append({"error": str(item), "classification": "dropped"})
            else:
                all_results.append(item)
                cost_total += item.get("cost_usd", 0.0)

        completed += len(batch)

        # Progress Telegram every 25 completions
        if completed % 25 == 0 or completed == len(domain_pairs):
            clf = Counter(r.get("classification", "dropped") for r in all_results)
            _tg(
                f"Progress: {completed}/{len(domain_pairs)} | "
                f"Ready={clf['ready']} Near={clf['near_ready']} "
                f"Watch={clf['watchlist']} Drop={clf['dropped']} | "
                f"cost=${cost_total:.3f}"
            )

        _check_budget(cost_total, 0.0, 0.0)  # apify/gemini sub-tracking not implemented inline

    # ── Summary & output ──────────────────────────────────────────────────────
    wall_total = time.monotonic() - run_start
    summary = _build_summary(all_results, cost_total, wall_total)
    clf = summary["classification"]

    output = {
        "directive": "F-TASK-B-100",
        "timestamp": datetime.now(UTC).isoformat(),
        "discovery": {
            "categories": category_domains,
            "total_domains": total_found,
            "discovery_cost_usd": round(discovery_cost, 4),
        },
        "results": all_results,
        "summary": summary,
    }

    out_path = "/home/elliotbot/clawd/Agency_OS/scripts/output/f_cohort_100_results.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(output, fh, indent=2, default=str)

    logger.info("COHORT COMPLETE | %s | $%.4f USD | %.1fs", dict(clf), cost_total, wall_total)
    logger.info("Output: %s", out_path)
    _tg(
        f"COHORT COMPLETE: {len(all_results)}/{len(domain_pairs)} | cost=${cost_total:.3f} | wall={wall_total:.0f}s"
    )


if __name__ == "__main__":
    asyncio.run(main())
