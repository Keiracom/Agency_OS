import asyncio, json, os, sys, time, httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

CO_KEY = os.getenv("CONTACTOUT_API_KEY", "")
CO_URL = "https://api.contactout.com/v1/people/enrich"


async def enrich_dm(client, dm):
    url = dm.get("dm_linkedin_url")
    if not url:
        return {"domain": dm["domain"], "profile_enriched": False, "reason": "no_url"}

    resp = await client.post(
        CO_URL,
        headers={"authorization": "basic", "token": CO_KEY},
        json={"linkedin_url": url, "include": ["work_email", "personal_email", "phone"]},
    )

    if resp.status_code != 200:
        return {
            "domain": dm["domain"],
            "profile_enriched": False,
            "reason": f"http_{resp.status_code}",
            "response_body": resp.text[:500],
        }

    data = resp.json()
    profile = data.get("profile") or data.get("data") or data

    # Extract ALL fields (principle #8: extract everything)
    experience = profile.get("experience") or profile.get("positions") or []
    skills = profile.get("skills") or []
    education = profile.get("education") or []

    return {
        "domain": dm["domain"],
        "dm_name": dm.get("dm_name"),
        "linkedin_url": url,
        "profile_enriched": True,
        "headline": profile.get("headline") or profile.get("title"),
        "experience": experience,
        "experience_count": len(experience),
        "skills": skills,
        "skills_count": len(skills),
        "education": education,
        "education_count": len(education),
        "seniority": profile.get("seniority"),
        "job_function": profile.get("job_function"),
        "about": profile.get("summary") or profile.get("about"),
        "connections_count": profile.get("connections") or profile.get("num_connections"),
        "profile_source": "contactout",
        "company_name": (
            profile.get("company", {}).get("name")
            if isinstance(profile.get("company"), dict)
            else profile.get("company")
        ),
        "raw_payload": data,  # full raw for principle #8
        "raw_payload_size_bytes": len(json.dumps(data, default=str)),
    }


async def main():
    # Load DMs
    input_path = "/home/elliotbot/clawd/Agency_OS/scripts/output/332_stage_6.json"
    with open(input_path) as f:
        s6 = json.load(f)
    dms = [r for r in s6["domains"] if r["dm_found"] and r.get("dm_linkedin_url")]

    print(f"Stage 9: {len(dms)} DMs with LinkedIn URLs")
    if not dms:
        print("No DMs with LinkedIn URLs found — aborting.")
        return

    results = []
    sem = asyncio.Semaphore(10)
    t0 = time.time()

    async with httpx.AsyncClient(timeout=30.0) as client:

        async def gated(dm):
            async with sem:
                return await enrich_dm(client, dm)

        results = await asyncio.gather(*[gated(dm) for dm in dms])

    elapsed = time.time() - t0

    enriched = [r for r in results if r.get("profile_enriched")]
    headlines = [r for r in enriched if r.get("headline")]
    has_exp = [r for r in enriched if r.get("experience_count", 0) > 0]
    has_skills = [r for r in enriched if r.get("skills_count", 0) > 0]
    has_edu = [r for r in enriched if r.get("education_count", 0) > 0]

    # Strip raw_payload for summary (keep in full output)
    summary_results = []
    for r in results:
        sr = {
            k: v
            for k, v in r.items()
            if k not in ("raw_payload", "experience", "skills", "education")
        }
        summary_results.append(sr)

    print(f"\n=== STAGE 9 RESULTS ===")
    print(f"Processed: {len(results)}")
    print(f"Enriched: {len(enriched)}/{len(results)} ({len(enriched) / len(results) * 100:.0f}%)")
    print(f"Headline: {len(headlines)}")
    print(
        f"Experience: {len(has_exp)} (avg {sum(r.get('experience_count', 0) for r in enriched) / max(len(enriched), 1):.1f} entries)"
    )
    print(
        f"Skills: {len(has_skills)} (avg {sum(r.get('skills_count', 0) for r in enriched) / max(len(enriched), 1):.1f})"
    )
    print(f"Education: {len(has_edu)}")
    print(
        f"Cost: {len(enriched)} × $0.033 = ${len(enriched) * 0.033:.2f} USD (${len(enriched) * 0.033 * 1.55:.2f} AUD)"
    )
    print(f"Wall time: {elapsed:.1f}s")

    output_path = "/home/elliotbot/clawd/Agency_OS/scripts/output/338_1_stage_9_live_fire.json"
    with open(output_path, "w") as f:
        json.dump(
            {
                "total": len(results),
                "enriched": len(enriched),
                "cost_usd": round(len(enriched) * 0.033, 3),
                "cost_aud": round(len(enriched) * 0.033 * 1.55, 3),
                "wall_time_s": round(elapsed, 1),
                "summary_results": summary_results,
                "results": results,
            },
            f,
            indent=2,
            default=str,
        )

    print(f"\nOutput: {output_path}")

    # Per-DM detail
    print("\n=== PER DM ===")
    for r in results:
        status = "OK" if r.get("profile_enriched") else f"FAIL:{r.get('reason', '?')}"
        print(
            f"  {r['domain']} | {r.get('dm_name', '')} | {status} | "
            f"headline={'Y' if r.get('headline') else 'N'} | "
            f"exp={r.get('experience_count', '-')} | "
            f"skills={r.get('skills_count', '-')} | "
            f"edu={r.get('education_count', '-')}"
        )


asyncio.run(main())
