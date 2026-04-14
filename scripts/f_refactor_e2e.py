"""
Pipeline F — single-domain E2E runner.

Stage order per F-REFACTOR-01:
  F3a COMPREHEND → F2 SIGNAL → F3b COMPILE → F4 VERIFY → F5 CONTACT
  → F5 DM POSTS → F6 CLASSIFY → F6 ENHANCED VR

Default domain: taxopia.com.au
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
from typing import Any

from src.clients.dfs_labs_client import DFSLabsClient
from src.intelligence.contact_waterfall import (
    filter_dm_posts,
    run_contact_waterfall,
)
from src.intelligence.dfs_signal_bundle import build_signal_bundle
from src.intelligence.enhanced_vr import run_enhanced_vr
from src.intelligence.funnel_classifier import classify_prospect
from src.intelligence.gemini_client import GeminiClient
from src.intelligence.verify_fills import run_verify_fills

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

NOT_TRYING = {"NOT_TRYING", "DORMANT"}
OUTREACH_SUBS = {"{{agency_contact_name}}": "Test Contact", "{{agency_name}}": "Test Agency"}


def _sub_placeholders(obj: Any) -> Any:
    """Recursively substitute agency placeholders in outreach strings."""
    if isinstance(obj, str):
        for k, v in OUTREACH_SUBS.items():
            obj = obj.replace(k, v)
        return obj
    if isinstance(obj, dict):
        return {k: _sub_placeholders(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sub_placeholders(i) for i in obj]
    return obj


async def main(domain: str = "taxopia.com.au") -> None:
    print(f"\n{'='*60}")
    print(f"Pipeline F E2E — {domain}")
    print(f"{'='*60}\n")

    dfs = DFSLabsClient(
        login=os.environ["DATAFORSEO_LOGIN"],
        password=os.environ["DATAFORSEO_PASSWORD"],
    )
    gemini = GeminiClient()
    timing: dict[str, float] = {}

    # ── F3a COMPREHEND ──────────────────────────────────────────────────────
    print("─── F3a COMPREHEND ───")
    t0 = time.monotonic()
    f3a_result = await gemini.call_f3a(domain=domain, dfs_base_metrics={})
    timing["f3a"] = time.monotonic() - t0

    f3a_status = f3a_result.get("f_status", "failed")
    f3a_content: dict = f3a_result.get("content") or {}
    print(f"f_status:            {f3a_status}")
    print(f"attempts:            {f3a_result.get('attempts', 1)}")
    print(f"input_tokens:        {f3a_result.get('input_tokens', 0)}")
    print(f"output_tokens:       {f3a_result.get('output_tokens', 0)}")
    print(f"cost_usd:            {f3a_result.get('cost_usd', 0.0)}")
    print(f"grounding_queries:   {f3a_result.get('grounding_queries', 0)}")
    print("raw content JSON:")
    print(json.dumps(f3a_content, indent=2, default=str))

    afford_gate = f3a_content.get("affordability_gate", "")
    intent_prelim = f3a_content.get("intent_band_preliminary", "")
    would_drop = afford_gate == "cannot_afford" or intent_prelim.upper() in NOT_TRYING
    print(f"drop/retain:         {'DROP' if would_drop else 'RETAIN'} "
          f"(gate={afford_gate}, intent={intent_prelim})")

    if f3a_status != "success":
        print(f"F3a failed — aborting. reason: {f3a_result.get('f_failure_reason')}")
        return

    # ── F2 SIGNAL ───────────────────────────────────────────────────────────
    print("\n─── F2 SIGNAL ───")
    t0 = time.monotonic()
    signal_bundle = await build_signal_bundle(dfs, domain)
    timing["f2"] = time.monotonic() - t0

    print(f"cost_usd:            {signal_bundle.get('cost_usd', 0.0)}")
    ro = signal_bundle.get("rank_overview") or {}
    print(f"rank_overview:       etv={ro.get('organic_etv')}, organic_count={ro.get('organic_count')}")
    competitors = signal_bundle.get("competitors", [])
    print(f"competitors count:   {len(competitors)}")
    print(f"  first 3:           {[c.get('domain') or c.get('competitor_domain') for c in competitors[:3]]}")
    keywords = signal_bundle.get("keywords", [])
    print(f"keywords count:      {len(keywords)}")
    print(f"  top 5:             {[k.get('keyword') for k in keywords[:5]]}")
    print(f"technologies:        {signal_bundle.get('technologies', [])}")

    # ── F3b COMPILE ─────────────────────────────────────────────────────────
    print("\n─── F3b COMPILE ───")
    t0 = time.monotonic()
    f3b_result = await gemini.call_f3b(f3a_output=f3a_content, signal_bundle=signal_bundle)
    timing["f3b"] = time.monotonic() - t0

    f3b_status = f3b_result.get("f_status", "failed")
    f3b_content: dict | None = f3b_result.get("content")
    print(f"f_status:            {f3b_status}")
    print(f"attempts:            {f3b_result.get('attempts', 1)}")
    print(f"input_tokens:        {f3b_result.get('input_tokens', 0)}")
    print(f"output_tokens:       {f3b_result.get('output_tokens', 0)}")
    print(f"cost_usd:            {f3b_result.get('cost_usd', 0.0)}")
    if f3b_content:
        print(f"intent_band_final:   {f3b_content.get('intent_band_final')}")
        vr = f3b_content.get("vulnerability_report") or {}
        if isinstance(vr, dict):
            print(f"vulnerability top 3: {vr.get('top_vulnerabilities', [])[:3]}")
        else:
            print(f"vulnerability top 3: {vr[:3]}")
        de = f3b_content.get("draft_email") or {}
        print(f"draft_email subject: {de.get('subject') if isinstance(de, dict) else de}")
    print("raw content JSON:")
    print(json.dumps(f3b_content, indent=2, default=str))

    if f3b_status != "success":
        logger.warning("F3b failed — continuing with F3a-only data")
        f3b_content = None

    # ── F4 VERIFY ───────────────────────────────────────────────────────────
    print("\n─── F4 VERIFY ───")
    t0 = time.monotonic()
    f4_result = await run_verify_fills(dfs=dfs, f3a_output=f3a_content)
    timing["f4"] = time.monotonic() - t0

    print(f"abn:                 {f4_result.get('abn') or 'unresolved'}")
    print(f"abn_status:          {f4_result.get('abn_status')}")
    print(f"abn_source:          {f4_result.get('abn_source')}")
    print(f"dm_linkedin_url:     {f4_result.get('dm_linkedin_url') or 'not found'}")
    print(f"company_linkedin_url:{f4_result.get('company_linkedin_url') or 'not found'}")
    print(f"_cost:               {f4_result.get('_cost')}")

    # ── F5 CONTACT ──────────────────────────────────────────────────────────
    print("\n─── F5 CONTACT ───")
    t0 = time.monotonic()
    dm_candidate = f3a_content.get("dm_candidate") or {}
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
    timing["f5"] = time.monotonic() - t0

    li = f5_result.get("linkedin", {})
    em = f5_result.get("email", {})
    mo = f5_result.get("mobile", {})
    print(f"linkedin:            url={li.get('linkedin_url')}, source={li.get('source')}, "
          f"tier={li.get('tier')}, match_type={li.get('match_type')}, "
          f"match_company={li.get('match_company')}, match_confidence={li.get('match_confidence')}")
    if li.get("l1_candidate_url"):
        print(f"  l1_candidate:      {li.get('l1_candidate_url')} (from {li.get('l1_candidate_source')})")
    if li.get("l2_profile_headline"):
        print(f"  l2_rejected:       headline='{li.get('l2_profile_headline')}', companies={li.get('l2_profile_companies')}")
    print(f"email:               email={em.get('email')}, source={em.get('source')}, "
          f"tier={em.get('tier')}, verified={em.get('verified') or em.get('confidence')}")
    print(f"mobile:              mobile={mo.get('mobile')}, source={mo.get('source')}, tier={mo.get('tier')}")

    # ── F5 DM POSTS ─────────────────────────────────────────────────────────
    print("\n─── F5 DM POSTS ───")
    t0 = time.monotonic()
    dm_linkedin_url = f4_result.get("dm_linkedin_url") or dm_candidate.get("linkedin_url") or li.get("linkedin_url")
    dm_name_for_filter = dm_candidate.get("name")

    raw_posts: list[dict] = []
    filtered_posts: list[dict] = []

    li_match_type = f5_result.get("linkedin", {}).get("match_type", "no_match")
    if li_match_type == "no_match" and not dm_linkedin_url:
        logger.info("LinkedIn L2 rejected — skipping DM posts fetch")

    if dm_linkedin_url and li_match_type != "no_match":
        # fetch_dm_posts already applies filter_dm_posts internally
        # We need raw count separately — fetch without filter then re-filter
        try:
            import httpx
            apify_token = os.environ.get("APIFY_API_TOKEN", "")
            APIFY_BASE = "https://api.apify.com/v2"
            if apify_token:
                async with httpx.AsyncClient(timeout=90) as client:
                    r = await client.post(
                        f"{APIFY_BASE}/acts/apimaestro~linkedin-posts-search-scraper-no-cookies/runs"
                        f"?token={apify_token}",
                        json={"profileUrl": dm_linkedin_url, "maxPosts": 10})
                    if r.status_code in (200, 201):
                        run_id = r.json().get("data", {}).get("id")
                        if run_id:
                            for _ in range(20):
                                await asyncio.sleep(3)
                                sr = await client.get(
                                    f"{APIFY_BASE}/actor-runs/{run_id}?token={apify_token}")
                                sd = sr.json().get("data", {})
                                if sd.get("status") in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                                    if sd["status"] == "SUCCEEDED":
                                        ds_id = sd.get("defaultDatasetId")
                                        raw_posts = (await client.get(
                                            f"{APIFY_BASE}/datasets/{ds_id}/items?token={apify_token}"
                                        )).json()
                                        filtered_posts = filter_dm_posts(
                                            raw_posts, dm_name_for_filter, dm_linkedin_url)
                                    break
            else:
                logger.warning("APIFY_API_TOKEN not set — skipping DM posts fetch")
        except Exception as exc:
            logger.warning("F5 DM posts fetch failed: %s", exc)
    else:
        logger.info("No DM LinkedIn URL — skipping DM posts fetch")

    timing["f5_dm_posts"] = time.monotonic() - t0
    print(f"DM name for filter:  {dm_name_for_filter}")
    print(f"total posts fetched: {len(raw_posts)}")
    print(f"after author filter: {len(filtered_posts)}")

    # ── F6 CLASSIFY ─────────────────────────────────────────────────────────
    print("\n─── F6 CLASSIFY ───")
    t0 = time.monotonic()
    classification = classify_prospect(
        f3a_output=f3a_content,
        f3b_output=f3b_content,
        contacts=f5_result,
    )
    timing["f6_classify"] = time.monotonic() - t0
    print(json.dumps(classification, indent=2, default=str))

    # ── F6 ENHANCED VR ──────────────────────────────────────────────────────
    print("\n─── F6 ENHANCED VR ───")
    enhanced_vr_result: dict | None = None
    enhanced_vr_content: dict | None = None

    if classification.get("classification") in ("ready", "near_ready") and f3b_content:
        t0 = time.monotonic()
        enhanced_vr_result = await run_enhanced_vr(
            f3b_output=f3b_content,
            dm_posts=filtered_posts,
            contact_details=f5_result,
        )
        timing["f6_enhanced_vr"] = time.monotonic() - t0

        evr_status = enhanced_vr_result.get("f_status", "failed")
        enhanced_vr_content = enhanced_vr_result.get("content")
        print(f"f_status:            {evr_status}")
        print(f"cost_usd:            {enhanced_vr_result.get('cost_usd', 0.0)}")
        print("raw content JSON:")
        print(json.dumps(enhanced_vr_content, indent=2, default=str))
        if enhanced_vr_content:
            ee = enhanced_vr_content.get("enhanced_email") or {}
            print(f"enhanced_email subj: {ee.get('subject') if isinstance(ee, dict) else ee}")
            print(f"enhanced_email body: {ee.get('body') if isinstance(ee, dict) else ''}")
            print(f"dm_post_reference:   {enhanced_vr_content.get('dm_post_reference')}")
    else:
        timing["f6_enhanced_vr"] = 0.0
        print("Skipped (classification not ready/near_ready or F3b failed)")

    # ── Build customer card ──────────────────────────────────────────────────
    total_cost = (
        f3a_result.get("cost_usd", 0.0)
        + signal_bundle.get("cost_usd", 0.0)
        + f3b_result.get("cost_usd", 0.0)
        + (f4_result.get("_cost") or 0.0)
        + (enhanced_vr_result.get("cost_usd", 0.0) if enhanced_vr_result else 0.0)
    )

    customer_card: dict = {
        "domain": domain,
        "business_name": f3a_content.get("business_name"),
        "location": f3a_content.get("location"),
        "industry_category": f3a_content.get("industry_category"),
        "entity_type_hint": f3a_content.get("entity_type_hint"),
        "staff_estimate_band": f3a_content.get("staff_estimate_band"),
        "primary_phone": f3a_content.get("primary_phone"),
        "primary_email": f3a_content.get("primary_email"),
        "abn": f4_result.get("abn"),
        "abn_status": f4_result.get("abn_status"),
        "dm_candidate": f3a_content.get("dm_candidate"),
        "dm_linkedin_url": f4_result.get("dm_linkedin_url") or dm_candidate.get("linkedin_url"),
        "contacts": f5_result,
        "intent_band": (
            f3b_content.get("intent_band_final") if f3b_content
            else f3a_content.get("intent_band_preliminary")
        ),
        "affordability_score": f3a_content.get("affordability_score"),
        "affordability_gate": f3a_content.get("affordability_gate"),
        "buyer_match_score": f3a_content.get("buyer_match_score"),
        "vulnerability_report": f3b_content.get("vulnerability_report") if f3b_content else None,
        "classification": classification,
        "outreach": {
            "draft_email": f3b_content.get("draft_email") if f3b_content else None,
            "draft_linkedin_note": f3b_content.get("draft_linkedin_note") if f3b_content else None,
            "draft_voice_script": f3b_content.get("draft_voice_script") if f3b_content else None,
            "enhanced": enhanced_vr_content if enhanced_vr_content else None,
        },
        "dm_posts": {
            "total_fetched": len(raw_posts),
            "after_author_filter": len(filtered_posts),
            "posts": filtered_posts,
        },
        "provenance_footer": {
            "business_identity": "gemini_2.5_flash_grounded",
            "abn": f4_result.get("abn_source"),
            "dm_linkedin": (
                f"l2_verified (direct match at {li.get('match_company', '')})"
                if li.get("match_type") == "direct_match"
                else f"l2_verified (related match at {li.get('match_company', '')})"
                if li.get("match_type") == "past_or_related_match"
                else f"unresolved (l1={li.get('l1_candidate_source', 'none')}, l2={li.get('l2_status', '')})"
            ),
            "email": f5_result["email"]["source"],
            "mobile": f5_result["mobile"]["source"],
            "vulnerability_report": "gemini_2.5_flash",
            "outreach_enhanced": "gemini_2.5_flash" if enhanced_vr_content else "n/a",
        },
        "stage_metrics": {
            "f4_company_url_source": "serp" if f4_result.get("company_linkedin_url") else "none",
            "f5_linkedin_l2_match_type": f5_result["linkedin"].get("match_type", "no_match"),
            "f5_linkedin_l2_match_company": f5_result["linkedin"].get("match_company", ""),
            "f5_linkedin_l2_match_confidence": f5_result["linkedin"].get("match_confidence", 0.0),
        },
        "cost_breakdown": {
            "f3a_usd": f3a_result.get("cost_usd", 0.0),
            "f2_usd": signal_bundle.get("cost_usd", 0.0),
            "f3b_usd": f3b_result.get("cost_usd", 0.0),
            "f4_usd": 0.006,
            "f5_usd": 0.0,
            "f6_enhanced_vr_usd": enhanced_vr_result.get("cost_usd", 0.0) if enhanced_vr_result else 0.0,
            "total_usd": round(total_cost, 6),
            "total_aud": round(total_cost * 1.55, 4),
        },
        "wall_clock_s": timing,
    }

    customer_card = _sub_placeholders(customer_card)

    # ── Timing summary ───────────────────────────────────────────────────────
    print("\n─── TIMING SUMMARY ───")
    for stage, secs in timing.items():
        print(f"  {stage:<25} {secs:.2f}s")
    print(f"  {'TOTAL':<25} {sum(timing.values()):.2f}s")

    # ── Final card ───────────────────────────────────────────────────────────
    print("\n─── CUSTOMER CARD ───")
    print(json.dumps(customer_card, indent=2, default=str))

    out_path = "/home/elliotbot/clawd/Agency_OS/scripts/output/f_refactor_e2e_taxopia.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(customer_card, fh, indent=2, default=str)
    print(f"\nCustomer card saved → {out_path}")
    print(f"Total cost: ${total_cost:.6f} USD / ${round(total_cost * 1.55, 4)} AUD")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "taxopia.com.au"
    asyncio.run(main(target))
