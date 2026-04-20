"""
Script: scripts/328_stage_1_rerun.py
Directive: #328 — Stage-By-Stage Pipeline Diagnosis
Stage: 1 RERUN — DFS Discovery with calibrated ETV windows

Same methodology as Stage 1 but using measured windows from
category_etv_windows.py (Directive #328.1) instead of hardcoded ranges.
Validates that calibration produces clean SMB output.

Categories: 10514 (dental), 10282 (construction), 10163 (legal)
Cost cap: $5 AUD (~$3.25 USD)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("328_stage1_rerun")

CATEGORIES = [10514, 10282, 10163]
CATEGORY_NAMES = {
    10514: "Dentists & Dental Services",
    10282: "Building Construction & Maintenance",
    10163: "Legal",
}
PER_CATEGORY_CAP = 34
PAGE_SIZE = 100
OUTPUT = os.path.join(os.path.dirname(__file__), "output", "328_stage_1_rerun.json")

from src.utils.domain_blocklist import is_blocked as _is_blocked


async def run_stage_1_rerun():
    start = time.time()

    env_file = Path("/home/elliotbot/.config/agency-os/.env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    from src.clients.dfs_labs_client import DFSLabsClient
    from src.config.category_etv_windows import get_etv_window, CATEGORY_ETV_WINDOWS

    dfs = DFSLabsClient(
        login=os.getenv("DATAFORSEO_LOGIN", ""),
        password=os.getenv("DATAFORSEO_PASSWORD", ""),
    )

    all_domains = []
    per_category = {}
    blocked_domains = []
    api_calls = 0
    total_cost_usd = 0.0

    for code in CATEGORIES:
        cat_name = CATEGORY_NAMES[code]
        etv_min, etv_max = get_etv_window(code)
        window_data = CATEGORY_ETV_WINDOWS[code]

        logger.info("=== Category %d: %s ===", code, cat_name)
        logger.info("  Calibrated window: etv_min=%.1f, etv_max=%.1f (from get_etv_window)",
                     etv_min, etv_max)
        logger.info("  Calibrated offset range: %d-%d, $/kw=%.2f",
                     window_data["offset_start"], window_data["offset_end"],
                     window_data["median_etv_per_keyword"])

        # Walk pages starting from offset 0, pull until we have enough SMBs
        # or exhaust the category
        raw = []
        max_pages = 20  # safety cap
        for page in range(max_pages):
            offset = page * PAGE_SIZE
            try:
                chunk = await dfs.domain_metrics_by_categories(
                    category_codes=[code],
                    location_name="Australia",
                    paid_etv_min=0.0,
                    limit=PAGE_SIZE,
                    offset=offset,
                )
                api_calls += 1
                total_cost_usd += 0.10

                for i, item in enumerate(chunk):
                    item["_offset"] = offset + i

                raw.extend(chunk)

                etvs = [d.get("organic_etv", 0) for d in chunk]
                min_etv = min(etvs) if etvs else 0

                logger.info("  offset=%d: %d domains, etv=%.0f-%.0f",
                            offset, len(chunk), min_etv, max(etvs) if etvs else 0)

                # Stop if we've walked past the SMB band floor
                if min_etv < etv_min and offset > 0:
                    logger.info("  Passed SMB floor (min_etv=%.0f < etv_min=%.0f)", min_etv, etv_min)
                    break

                if len(chunk) < PAGE_SIZE:
                    break

            except Exception as exc:
                logger.error("  DFS error offset=%d: %s", offset, exc)
                break

        # Post-filter: blocklist + calibrated ETV window
        filtered = []
        for item in raw:
            domain = item.get("domain", "")
            etv = item.get("organic_etv", 0) or 0
            paid_etv = item.get("paid_etv", 0) or 0
            kw_count = item.get("organic_count", 0) or 0
            offset_pos = item.get("_offset", -1)

            if _is_blocked(domain):
                blocked_domains.append({"domain": domain, "category": code})
                continue

            if not (etv_min <= etv <= etv_max):
                continue

            filtered.append({
                "domain": domain,
                "organic_etv": etv,
                "paid_etv": paid_etv,
                "organic_count": kw_count,
                "offset_position": offset_pos,
                "category_code": code,
                "category_name": cat_name,
            })

        # Cap
        capped = filtered[:PER_CATEGORY_CAP]
        per_category[code] = {
            "name": cat_name,
            "etv_window_used": [etv_min, etv_max],
            "calibrated_offset_range": [window_data["offset_start"], window_data["offset_end"]],
            "pages_walked": min(len(raw) // PAGE_SIZE + 1, max_pages),
            "raw_count": len(raw),
            "blocked_count": len([b for b in blocked_domains if b["category"] == code]),
            "etv_filtered_count": len(filtered),
            "final_count": len(capped),
            "offset_range_actual": [
                min(d["offset_position"] for d in capped) if capped else -1,
                max(d["offset_position"] for d in capped) if capped else -1,
            ],
            "domains": capped,
        }
        all_domains.extend(capped)

        logger.info("  Raw: %d | Blocked: %d | ETV-filtered: %d | Final: %d",
                     len(raw), per_category[code]["blocked_count"], len(filtered), len(capped))
        if capped:
            logger.info("  Offset range: %d-%d (calibrated: %d-%d)",
                        per_category[code]["offset_range_actual"][0],
                        per_category[code]["offset_range_actual"][1],
                        window_data["offset_start"], window_data["offset_end"])
        for i, d in enumerate(capped[:5], 1):
            logger.info("    %d. %s (etv=%.0f, kw=%d, offset=%d)",
                        i, d["domain"], d["organic_etv"], d["organic_count"], d["offset_position"])

    elapsed = time.time() - start

    summary = {
        "directive": "#328 Stage 1 RERUN — Calibrated ETV Windows",
        "elapsed_seconds": round(elapsed, 1),
        "api_calls": api_calls,
        "cost_usd": round(total_cost_usd, 2),
        "cost_aud": round(total_cost_usd * 1.55, 2),
        "total_domains": len(all_domains),
        "per_category": {str(c): per_category[c] for c in CATEGORIES},
        "blocked_total": len(blocked_domains),
        "domains": all_domains,
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("=== STAGE 1 RERUN COMPLETE ===")
    logger.info("Total: %d | API calls: %d | Cost: $%.2f USD ($%.2f AUD) | Time: %.1fs",
                len(all_domains), api_calls, total_cost_usd, total_cost_usd * 1.55, elapsed)
    for code in CATEGORIES:
        p = per_category[code]
        logger.info("  %s: %d domains (window %.0f-%.0f)", p["name"], p["final_count"],
                     p["etv_window_used"][0], p["etv_window_used"][1])


if __name__ == "__main__":
    asyncio.run(run_stage_1_rerun())
