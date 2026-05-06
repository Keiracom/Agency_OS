"""
DIRECTIVE #300-FIX-4 — Integration Test: Stage 7 v2 (Email only)

Re-runs email waterfall on 260 DM-found domains with:
 - New _parse_name (prefix/suffix/noise stripping)
 - New layer numbering: 0=registry, 1=HTML, 2=Leadmagic(verified), 3=BD(unverified)
 - Pattern generation removed from main flow (Leadmagic is resolver)

Input:  scripts/output/300f_dm.json
Output: scripts/output/300g_v2_email.json
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

from src.integrations.httpx_scraper import HttpxScraper
from src.pipeline.email_waterfall import discover_email

INPUT_DM = os.path.join(os.path.dirname(__file__), "output", "300f_dm.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output", "300g_v2_email.json")

SEM_SCRAPE = asyncio.Semaphore(15)
SEM_EMAIL = asyncio.Semaphore(10)

# AUD/USD exchange rate for cost reporting
AUD_PER_USD = 1.55


def _empty_contact() -> dict:
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


async def scrape_contact(scraper: HttpxScraper, domain: str) -> dict:
    async with SEM_SCRAPE:
        try:
            res = await scraper.scrape(domain)
            if res and res.get("contact_data"):
                return res["contact_data"]
        except Exception:
            pass
    return _empty_contact()


async def process_domain(
    domain: str,
    dm_name: str | None,
    dm_linkedin: str | None,
    company_name: str | None,
    contact_data: dict,
    done: list,
    total: int,
    t0: float,
) -> dict:
    result: dict = {
        "domain": domain,
        "dm_name": dm_name,
        "email_found": False,
        "email": None,
        "email_verified": False,
        "email_source": "none",
        "email_cost_usd": 0.0,
        "contact_prefill_email": contact_data.get("company_email") or contact_data.get("email"),
    }

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
            result.update(
                {
                    "email_found": email_res.email is not None,
                    "email": email_res.email,
                    "email_verified": email_res.verified,
                    "email_source": email_res.source,
                    "email_cost_usd": email_res.cost_usd,
                }
            )
        except Exception as exc:
            result["_error"] = str(exc)

    done[0] += 1
    if done[0] % 20 == 0:
        elapsed = time.monotonic() - t0
        rate = done[0] / elapsed
        eta = (total - done[0]) / rate if rate > 0 else 0
        print(f"  {done[0]}/{total} | {elapsed:.0f}s elapsed | ETA {eta:.0f}s")

    return result


async def main():
    print("=" * 60)
    print("DIRECTIVE #300-FIX-4 — Stage 7 v2 (Email only, 260 domains)")
    print("Layers: 0=registry | 1=HTML | 2=Leadmagic(✓) | 3=BD")
    print("=" * 60)

    with open(INPUT_DM) as f:
        dm_data = json.load(f)

    prospects = [d for d in dm_data["domains"] if d.get("dm_found")]
    print(f"Loaded {len(prospects)} DM-found domains\n")

    # Step 1: Re-scrape for contact_data
    print(f"Scraping {len(prospects)} domains for contact registry (15 concurrent)...")
    scraper = HttpxScraper()
    t_scrape = time.monotonic()
    scrape_tasks = [scrape_contact(scraper, p["domain"]) for p in prospects]
    contact_results = await asyncio.gather(*scrape_tasks)
    scrape_map = {prospects[i]["domain"]: contact_results[i] for i in range(len(prospects))}
    await scraper.close()
    populated = sum(
        1
        for v in scrape_map.values()
        if any(
            v.get(k) for k in ("company_email", "company_mobile", "company_phone", "linkedin_dm")
        )
    )
    print(
        f"Scrape done in {time.monotonic() - t_scrape:.0f}s | {populated}/{len(prospects)} with contact data\n"
    )

    # Step 2: Email waterfall
    print("Running email waterfall...")
    t0 = time.monotonic()
    done = [0]
    total = len(prospects)

    tasks = []
    for p in prospects:
        domain = p["domain"]
        d_strip = domain[4:] if domain.startswith("www.") else domain
        company_name = d_strip.split(".")[0].replace("-", " ").title()

        tasks.append(
            process_domain(
                domain=domain,
                dm_name=p.get("dm_name"),
                dm_linkedin=p.get("dm_linkedin_url"),
                company_name=company_name,
                contact_data=scrape_map.get(domain, _empty_contact()),
                done=done,
                total=total,
                t0=t0,
            )
        )

    raw = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.monotonic() - t0

    # Normalise exceptions
    results: list[dict] = []
    errors = 0
    for i, r in enumerate(raw):
        if isinstance(r, Exception):
            results.append({"domain": prospects[i]["domain"], "_exception": str(r)})
            errors += 1
        else:
            results.append(r)

    ok = [r for r in results if not r.get("_exception") and not r.get("_error")]

    # Save output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(
            {"meta": {"total": len(results), "errors": errors}, "domains": results}, f, indent=2
        )
    print(f"\nSaved → {OUTPUT_FILE}")

    # ── STATS ──────────────────────────────────────────────────────────────────
    found_all = [r for r in ok if r.get("email_found")]
    verified = [r for r in found_all if r.get("email_verified")]
    unverified = [r for r in found_all if not r.get("email_verified")]

    sources: dict[str, int] = {}
    for r in ok:
        s = r.get("email_source", "none")
        sources[s] = sources.get(s, 0) + 1

    lm_cost_usd = round(sum(r.get("email_cost_usd", 0) for r in ok), 4)
    lm_cost_aud = round(lm_cost_usd * AUD_PER_USD, 2)

    print()
    print("=" * 60)
    print("=== STAGE 7 v2 REPORT ===")
    print()
    print(f"1.  TOTAL PROCESSED: {len(results)} | ERRORS: {errors}")
    print(f"2.  EMAIL FOUND: {len(found_all)} / {len(ok)}")
    print(f"3.  email_verified=True  (Leadmagic/BD confirmed): {len(verified)}")
    print(f"4.  email_verified=False (website/registry only):  {len(unverified)}")
    print("5.  SOURCE BREAKDOWN:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {src}: {count}")
    print(f"6.  LEADMAGIC COST: ${lm_cost_usd:.4f} USD (~${lm_cost_aud:.2f} AUD)")
    print(f"7.  WALL-CLOCK TIME: {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
