"""
DIRECTIVE #300g+h — Integration Test: Stage 7 (Email) + Stage 8 (Mobile)

260 DM-found domains from Stage 6.
Email waterfall: contact registry (free) → website HTML → pattern → Leadmagic → Bright Data
Mobile waterfall: contact registry (free) → HTML regex → Leadmagic → Bright Data

Cost estimate: ~$35-42 combined
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

from src.config.settings import settings
from src.integrations.httpx_scraper import HttpxScraper
from src.pipeline.email_waterfall import discover_email
from src.pipeline.mobile_waterfall import run_mobile_waterfall, extract_mobile_from_html
from src.utils.asyncpg_connection import get_asyncpg_pool

INPUT_DM = os.path.join(os.path.dirname(__file__), "output", "300f_dm.json")
INPUT_SCRAPE = os.path.join(os.path.dirname(__file__), "output", "300b_scrape.json")
INPUT_AFFORD = os.path.join(os.path.dirname(__file__), "output", "300d_afford.json")
OUTPUT_EMAIL = os.path.join(os.path.dirname(__file__), "output", "300g_email.json")
OUTPUT_MOBILE = os.path.join(os.path.dirname(__file__), "output", "300h_mobile.json")
OUTPUT_COMBINED = os.path.join(os.path.dirname(__file__), "output", "300gh_combined.json")

# Semaphores
SEM_EMAIL = asyncio.Semaphore(10)
SEM_MOBILE = asyncio.Semaphore(10)


def _empty_contact() -> dict:
    """Return empty contact_data using new schema."""
    return {
        "company_email": None,
        "company_phone": None,
        "company_mobile": None,
        "linkedin_company": None,
        "linkedin_dm": None,
        "dm_email": None,
        "dm_email_verified": False,
        "dm_mobile": None,
    }


async def upsert_contact(
    pool,
    domain: str,
    email: str | None,
    mobile: str | None,
    company_email: str | None,
    company_phone: str | None,
    company_mobile: str | None,
) -> None:
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE business_universe SET
                    dm_email         = COALESCE($2, dm_email),
                    dm_phone         = COALESCE($3, dm_phone),
                    pipeline_stage   = GREATEST(pipeline_stage, 7)
                WHERE domain = $1
                """,
                domain,
                email,
                mobile,
            )
    except Exception:
        pass


async def process_domain(
    domain: str,
    category: str,
    intent_band: str,
    intent_score: int,
    dm_name: str | None,
    dm_linkedin: str | None,
    contact_data: dict,
    company_name: str | None,
    pool,
    done: list,
    total: int,
    t0: float,
) -> dict:
    result = {
        "domain": domain,
        "category": category,
        "intent_band": intent_band,
        "intent_score": intent_score,
        "dm_name": dm_name,
        "contact_data_prefill": {
            "company_email": contact_data.get("company_email") or contact_data.get("email"),
            "company_phone": contact_data.get("company_phone") or contact_data.get("landline"),
            "company_mobile": contact_data.get("company_mobile") or contact_data.get("mobile"),
            "linkedin_dm": contact_data.get("linkedin_dm") or contact_data.get("linkedin"),
            "linkedin_company": contact_data.get("linkedin_company"),
        },
        # Email fields
        "email_found": False,
        "email": None,
        "email_verified": False,
        "email_source": "none",
        "email_layers_attempted": 0,
        "email_cost_usd": 0.0,
        # Mobile fields
        "mobile_found": False,
        "mobile": None,
        "mobile_source": None,
        "mobile_layers_attempted": 0,
        "mobile_cost_usd": 0.0,
    }

    # ── Stage 7: Email waterfall ──────────────────────────────────────────────
    layers_attempted = 0

    # Layer 0: Contact registry handled inside discover_email via contact_data param
    async with SEM_EMAIL:
        try:
            email_res = await discover_email(
                domain=domain,
                dm_name=dm_name or domain.split(".")[0],
                dm_linkedin=dm_linkedin,
                html=None,
                company_name=company_name,
                contact_data=contact_data,
            )
            # Count layers attempted
            source = email_res.source
            if source == "contact_registry":
                layers_attempted = 0
            elif source == "website":
                layers_attempted = 1
            elif source == "pattern":
                layers_attempted = 2
            elif source == "leadmagic":
                layers_attempted = 3
            elif source == "brightdata":
                layers_attempted = 4
            else:
                layers_attempted = 4  # all tried, none found

            result.update(
                {
                    "email_found": email_res.email is not None,
                    "email": email_res.email,
                    "email_verified": email_res.verified,
                    "email_source": source,
                    "email_layers_attempted": layers_attempted,
                    "email_cost_usd": email_res.cost_usd,
                }
            )
        except Exception as exc:
            result["_email_error"] = str(exc)

    # ── Stage 8: Mobile waterfall ─────────────────────────────────────────────
    mobile_layers = 0

    # Layer 0: Contact registry handled inside run_mobile_waterfall via contact_data param
    async with SEM_MOBILE:
        try:
            # Import LeadmagicClient lazily
            leadmagic = None
            try:
                from src.integrations.leadmagic import LeadmagicClient

                leadmagic = LeadmagicClient(api_key=settings.leadmagic_api_key)
            except Exception:
                pass

            mobile_res = await run_mobile_waterfall(
                domain=domain,
                dm_linkedin_url=dm_linkedin,
                contact_data=contact_data,
                leadmagic_client=leadmagic,
                brightdata_client=None,  # skip BD for now — Leadmagic first
            )

            if mobile_res.tier_used == 1:
                mobile_layers = 0  # HTML regex (free)
            elif mobile_res.tier_used == 2:
                mobile_layers = 1  # Leadmagic
            elif mobile_res.tier_used == 3:
                mobile_layers = 2  # BD
            else:
                mobile_layers = 2  # all tried

            result.update(
                {
                    "mobile_found": mobile_res.mobile is not None,
                    "mobile": mobile_res.mobile,
                    "mobile_source": mobile_res.source,
                    "mobile_layers_attempted": mobile_layers,
                    "mobile_cost_usd": float(mobile_res.cost_usd),
                }
            )
        except Exception as exc:
            result["_mobile_error"] = str(exc)

    # Upsert to BU
    prefill = result.get("contact_data_prefill", {})
    await upsert_contact(
        pool,
        domain,
        result.get("email"),
        result.get("mobile"),
        prefill.get("company_email"),
        prefill.get("company_phone"),
        prefill.get("company_mobile"),
    )

    done[0] += 1
    if done[0] % 20 == 0:
        elapsed = time.monotonic() - t0
        rate = done[0] / elapsed
        eta = (total - done[0]) / rate if rate > 0 else 0
        print(f"  {done[0]}/{total} | {elapsed:.0f}s | ETA {eta:.0f}s")

    return result


async def main():
    print("=" * 60)
    print("DIRECTIVE #300g+h — Stage 7 (Email) + Stage 8 (Mobile)")
    print("260 DM-found domains: contact registry → paid waterfalls")
    print("=" * 60)

    # Load inputs
    with open(INPUT_DM) as f:
        dm_data = json.load(f)
    with open(INPUT_AFFORD) as f:
        afford_data = json.load(f)

    # Build maps
    afford_map = {d["domain"]: d for d in afford_data["domains"]}

    # Filter to DM-found only
    prospects = [d for d in dm_data["domains"] if d.get("dm_found")]
    print(f"Loaded {len(prospects)} DM-found domains\n")

    # Re-scrape all DM-found domains to populate contact_data
    print("Pre-scraping domains for contact registry...")
    scraper = HttpxScraper()
    SEM_SCRAPE = asyncio.Semaphore(15)

    async def scrape_contact(domain: str) -> dict:
        async with SEM_SCRAPE:
            try:
                res = await scraper.scrape(domain)
                if res and res.get("contact_data"):
                    return res["contact_data"]
            except Exception:
                pass
        return _empty_contact()

    scrape_tasks = [scrape_contact(p["domain"]) for p in prospects]
    contact_results = await asyncio.gather(*scrape_tasks)
    scrape_map = {prospects[i]["domain"]: contact_results[i] for i in range(len(prospects))}
    populated = sum(
        1
        for v in scrape_map.values()
        if any(
            v.get(k) for k in ("company_email", "company_mobile", "company_phone", "linkedin_dm")
        )
    )
    print(f"Contact registry populated: {populated}/{len(prospects)} domains with data\n")
    await scraper.close()

    # Init pool
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgres://", "postgresql://"
    )
    pool = await get_asyncpg_pool(dsn, min_size=1, max_size=20)

    t0 = time.monotonic()
    done = [0]
    total = len(prospects)

    tasks = []
    for p in prospects:
        domain = p["domain"]
        contact_data = scrape_map.get(domain, _empty_contact())
        afford_item = afford_map.get(domain, {})
        # Derive company name
        abn_display = (
            afford_item.get("haiku_result", {}).get("company_name") if afford_item else None
        )
        d_strip = domain[4:] if domain.startswith("www.") else domain
        company_name = abn_display or d_strip.split(".")[0].replace("-", " ").title()

        tasks.append(
            process_domain(
                domain=domain,
                category=p.get("category", ""),
                intent_band=p.get("intent_band", ""),
                intent_score=p.get("intent_score", 0),
                dm_name=p.get("dm_name"),
                dm_linkedin=p.get("dm_linkedin_url"),
                contact_data=contact_data,
                company_name=company_name,
                pool=pool,
                done=done,
                total=total,
                t0=t0,
            )
        )

    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.monotonic() - t0
    await pool.close()

    # Normalise exceptions
    results: list[dict] = []
    errors = 0
    for i, r in enumerate(raw_results):
        if isinstance(r, Exception):
            results.append(
                {
                    "domain": prospects[i]["domain"],
                    "_exception": str(r),
                }
            )
            errors += 1
        else:
            results.append(r)

    ok = [r for r in results if not r.get("_exception")]

    # ── EMAIL STATS ──
    email_found = [r for r in ok if r.get("email_found")]
    email_missing = [r for r in ok if not r.get("email_found")]
    email_hit_rate = round(len(email_found) / len(ok) * 100, 1) if ok else 0

    email_sources: dict[str, int] = {}
    for r in ok:
        s = r.get("email_source", "none")
        email_sources[s] = email_sources.get(s, 0) + 1

    email_verified = sum(1 for r in ok if r.get("email_verified"))
    email_registry_saves = email_sources.get("contact_registry", 0)
    email_registry_cost_saved = round(email_registry_saves * 0.015, 2)

    email_by_cat: dict[str, dict] = {}
    for cat in ["Dental", "Construction", "Legal"]:
        cat_ok = [r for r in ok if r.get("category") == cat]
        cat_found = sum(1 for r in cat_ok if r.get("email_found"))
        email_by_cat[cat] = {
            "found": cat_found,
            "total": len(cat_ok),
            "hit_rate": round(cat_found / len(cat_ok) * 100, 1) if cat_ok else 0,
        }

    total_email_cost = round(sum(r.get("email_cost_usd", 0) for r in ok), 2)

    # ── MOBILE STATS ──
    mob_found = [r for r in ok if r.get("mobile_found")]
    mob_missing = [r for r in ok if not r.get("mobile_found")]
    mob_hit_rate = round(len(mob_found) / len(ok) * 100, 1) if ok else 0

    mob_sources: dict[str, int] = {}
    for r in ok:
        s = r.get("mobile_source") or "none"
        mob_sources[s] = mob_sources.get(s, 0) + 1

    mob_registry_saves = mob_sources.get("contact_registry", 0)
    mob_registry_cost_saved = round(mob_registry_saves * 0.077, 2)

    mob_by_cat: dict[str, dict] = {}
    for cat in ["Dental", "Construction", "Legal"]:
        cat_ok = [r for r in ok if r.get("category") == cat]
        cat_found = sum(1 for r in cat_ok if r.get("mobile_found"))
        mob_by_cat[cat] = {
            "found": cat_found,
            "total": len(cat_ok),
            "hit_rate": round(cat_found / len(cat_ok) * 100, 1) if cat_ok else 0,
        }

    total_mobile_cost = round(sum(r.get("mobile_cost_usd", 0) for r in ok), 2)

    # ── COMBINED ──
    both = sum(1 for r in ok if r.get("email_found") and r.get("mobile_found"))
    email_only = sum(1 for r in ok if r.get("email_found") and not r.get("mobile_found"))
    mobile_only = sum(1 for r in ok if not r.get("email_found") and r.get("mobile_found"))
    neither = sum(1 for r in ok if not r.get("email_found") and not r.get("mobile_found"))
    total_cost = round(total_email_cost + total_mobile_cost, 2)

    # ── 5 EXAMPLES ──
    ex_both_free = next(
        (
            r
            for r in ok
            if r.get("email_source") == "contact_registry"
            and r.get("mobile_source") == "contact_registry"
        ),
        None,
    )
    ex_email_free_mob_paid = next(
        (
            r
            for r in ok
            if r.get("email_source") in ("contact_registry", "website", "pattern")
            and r.get("mobile_source") == "leadmagic"
        ),
        None,
    )
    ex_both_paid = next(
        (
            r
            for r in ok
            if r.get("email_source") == "leadmagic" and r.get("mobile_source") == "leadmagic"
        ),
        None,
    )
    ex_email_no_mob = next(
        (r for r in ok if r.get("email_found") and not r.get("mobile_found")), None
    )
    ex_neither = next(
        (r for r in ok if not r.get("email_found") and not r.get("mobile_found")), None
    )

    print()
    print("=" * 60)
    print("=== TASK C REPORT ===")
    print()
    print("── EMAIL (Stage 7) ──")
    print(f"1.  TOTAL PROCESSED: {len(results)} | ERRORS: {errors}")
    print(f"2.  EMAIL FOUND: {len(email_found)} | NOT FOUND: {len(email_missing)}")
    print(f"3.  HIT RATE: {email_hit_rate}%")
    print("4.  SOURCE BREAKDOWN:")
    for src, count in sorted(email_sources.items(), key=lambda x: -x[1]):
        print(f"    {src}: {count}")
    print(f"5.  VERIFIED: {email_verified} | UNVERIFIED: {len(email_found) - email_verified}")
    print("6.  PER-CATEGORY:")
    for cat, s in email_by_cat.items():
        print(f"    {cat}: found={s['found']}/{s['total']} ({s['hit_rate']}%)")
    print(f"7.  TOTAL EMAIL COST: ${total_email_cost:.2f} USD")
    print(
        f"8.  CONTACT REGISTRY SAVES: {email_registry_saves} lookups = ${email_registry_cost_saved:.2f} saved"
    )
    print()
    print("── MOBILE (Stage 8) ──")
    print(f"9.  TOTAL PROCESSED: {len(results)} | ERRORS: {errors}")
    print(f"10. MOBILE FOUND: {len(mob_found)} | NOT FOUND: {len(mob_missing)}")
    print(f"11. HIT RATE: {mob_hit_rate}%")
    print("12. SOURCE BREAKDOWN:")
    for src, count in sorted(mob_sources.items(), key=lambda x: -x[1]):
        print(f"    {src}: {count}")
    print("13. PER-CATEGORY:")
    for cat, s in mob_by_cat.items():
        print(f"    {cat}: found={s['found']}/{s['total']} ({s['hit_rate']}%)")
    print(f"14. TOTAL MOBILE COST: ${total_mobile_cost:.2f} USD")
    print(
        f"15. CONTACT REGISTRY SAVES: {mob_registry_saves} lookups = ${mob_registry_cost_saved:.2f} saved"
    )
    print()
    print("── COMBINED ──")
    print(f"16. TOTAL COST: ${total_cost:.2f} USD")
    print(f"17. WALL-CLOCK: {elapsed:.1f}s")
    print(f"18. BOTH email AND mobile: {both}")
    print(f"19. Email only: {email_only}")
    print(f"20. Mobile only: {mobile_only}")
    print(f"21. Neither: {neither}")
    print()
    print("22. FIVE EXAMPLES:")

    def show(label, r):
        if r is None:
            print(f"\n[{label}]: NOT FOUND IN SAMPLE")
            return
        printable = {k: v for k, v in r.items() if not k.startswith("_")}
        print(f"\n[{label}]")
        print(json.dumps(printable, indent=4, default=str))

    show("Contact registry had both (zero paid)", ex_both_free)
    show("Email free, mobile needed Leadmagic", ex_email_free_mob_paid)
    show("Both needed paid lookups", ex_both_paid)
    show("Email found, mobile not found", ex_email_no_mob)
    show("Neither found", ex_neither)

    # ── SAVE ──
    summary = {
        "total": len(results),
        "ok": len(ok),
        "errors": errors,
        "email_found": len(email_found),
        "email_missing": len(email_missing),
        "email_hit_rate": email_hit_rate,
        "email_sources": email_sources,
        "email_verified": email_verified,
        "email_by_cat": email_by_cat,
        "email_cost_usd": total_email_cost,
        "email_registry_saves": email_registry_saves,
        "mobile_found": len(mob_found),
        "mobile_missing": len(mob_missing),
        "mobile_hit_rate": mob_hit_rate,
        "mobile_sources": mob_sources,
        "mobile_by_cat": mob_by_cat,
        "mobile_cost_usd": total_mobile_cost,
        "mobile_registry_saves": mob_registry_saves,
        "total_cost_usd": total_cost,
        "both": both,
        "email_only": email_only,
        "mobile_only": mobile_only,
        "neither": neither,
        "elapsed_seconds": round(elapsed, 1),
    }

    os.makedirs(os.path.dirname(OUTPUT_COMBINED), exist_ok=True)
    with open(OUTPUT_COMBINED, "w") as f:
        json.dump(
            {"stage": "300gh_combined", "summary": summary, "domains": results},
            f,
            indent=2,
            default=str,
        )

    # Also save split files
    with open(OUTPUT_EMAIL, "w") as f:
        json.dump(
            {
                "stage": "300g_email",
                "summary": {
                    k: v
                    for k, v in summary.items()
                    if "email" in k or k in ("total", "ok", "errors", "elapsed_seconds")
                },
                "domains": [{k: v for k, v in r.items() if "mobile" not in k} for r in results],
            },
            f,
            indent=2,
            default=str,
        )
    with open(OUTPUT_MOBILE, "w") as f:
        json.dump(
            {
                "stage": "300h_mobile",
                "summary": {
                    k: v
                    for k, v in summary.items()
                    if "mobile" in k or k in ("total", "ok", "errors", "elapsed_seconds")
                },
                "domains": [
                    {k: v for k, v in r.items() if "email" not in k or k == "domain"}
                    for r in results
                ],
            },
            f,
            indent=2,
            default=str,
        )

    print(f"\nSaved: {OUTPUT_COMBINED}")
    print(f"Saved: {OUTPUT_EMAIL}")
    print(f"Saved: {OUTPUT_MOBILE}")


if __name__ == "__main__":
    asyncio.run(main())
