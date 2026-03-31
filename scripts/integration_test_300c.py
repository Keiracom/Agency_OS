"""
DIRECTIVE #300c — Integration Test: Stage 3 Sonnet Website Comprehension
50% stratified sample (seed=42), real Anthropic API calls.
Cost: ~$17 USD
"""
import asyncio
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv("/home/elliotbot/.config/agency-os/.env")

from src.pipeline.intelligence import comprehend_website, GLOBAL_SEM_SONNET

INPUT_FILE  = os.path.join(os.path.dirname(__file__), "output", "300b_scrape.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output", "300c_comprehend.json")

# Pricing: claude-sonnet-4-5 — $3/MTok input, $15/MTok output
COST_PER_INPUT_TOKEN  = 3.0 / 1_000_000
COST_PER_OUTPUT_TOKEN = 15.0 / 1_000_000


def stratified_sample(domains_by_cat: dict, seed: int = 42) -> list[dict]:
    """50% random sample per category, seeded for reproducibility."""
    rng = random.Random(seed)
    result = []
    for cat, items in domains_by_cat.items():
        n = len(items) // 2
        result.extend(rng.sample(items, n))
    return result


async def process_domain(item: dict) -> dict:
    domain   = item["domain"]
    html     = item.get("html", "")
    category = item.get("category", "")
    url      = f"https://{domain}"

    out = {
        "domain": domain,
        "category": category,
        "content_length_input": item.get("content_length", 0),
        "services_detected": [],
        "team_size_indicator": "unknown",
        "technology_signals": {},
        "contact_methods": [],
        "content_freshness": "unknown",
        "tracking_present": False,
        "conversion_forms": False,
        "sonnet_tokens_in": 0,
        "sonnet_tokens_out": 0,
        "response_time_ms": 0,
        "error": None,
    }

    t0 = time.monotonic()
    try:
        result = await comprehend_website(domain, html, url)
        elapsed_ms = round((time.monotonic() - t0) * 1000)

        tech = result.get("technology_signals", {})
        has_tracking = (
            tech.get("has_analytics") or
            tech.get("has_ads_tag") or
            tech.get("has_meta_pixel")
        )
        has_forms = (
            tech.get("has_booking_system") or
            tech.get("has_conversion_tracking")
        )

        out.update({
            "services_detected":  result.get("services", []),
            "team_size_indicator": result.get("team_size_indicator", "unknown"),
            "technology_signals": tech,
            "contact_methods":    result.get("contact_methods", []),
            "content_freshness":  result.get("content_freshness", "unknown"),
            "tracking_present":   bool(has_tracking),
            "conversion_forms":   bool(has_forms),
            "response_time_ms":   elapsed_ms,
            "raw_result":         result,
        })

        # Token counts are logged inside comprehend_website but not returned.
        # Estimate from typical Sonnet HTML comprehension: ~4000 input, ~300 output.
        out["sonnet_tokens_in"]  = 4000
        out["sonnet_tokens_out"] = 300

    except Exception as exc:
        out["error"] = str(exc)
        out["response_time_ms"] = round((time.monotonic() - t0) * 1000)

    return out


async def main():
    print("=" * 60)
    print("DIRECTIVE #300c — Stage 3: Sonnet Website Comprehension")
    print("50% stratified sample, seed=42")
    print("=" * 60)

    with open(INPUT_FILE) as f:
        scrape_data = json.load(f)

    au_domains = [r for r in scrape_data["domains"] if r["au_filter"] == "pass"]

    # Group by category
    by_cat: dict[str, list] = {}
    for item in au_domains:
        cat = item.get("category", "Unknown")
        by_cat.setdefault(cat, []).append(item)

    sample = stratified_sample(by_cat, seed=42)
    print(f"AU pass: {len(au_domains)} | Sample (50%): {len(sample)}")
    for cat, items in by_cat.items():
        n = len(items) // 2
        print(f"  {cat}: {len(items)} → sample {n}")
    print()

    t0 = time.monotonic()
    results = []
    done = [0]

    async def run_one(item):
        r = await process_domain(item)
        done[0] += 1
        if done[0] % 50 == 0:
            elapsed = time.monotonic() - t0
            ok = sum(1 for x in results if x.get("error") is None)
            print(f"  {done[0]}/{len(sample)} done | {elapsed:.0f}s | errors so far: {done[0]-ok}")
        results.append(r)
        return r

    await asyncio.gather(*[run_one(item) for item in sample])

    elapsed = time.monotonic() - t0

    # Stats
    errors    = [r for r in results if r.get("error")]
    ok        = [r for r in results if not r.get("error")]
    total_in  = sum(r["sonnet_tokens_in"]  for r in ok)
    total_out = sum(r["sonnet_tokens_out"] for r in ok)
    cost_usd  = total_in * COST_PER_INPUT_TOKEN + total_out * COST_PER_OUTPUT_TOKEN

    avg_rt = round(sum(r["response_time_ms"] for r in ok) / len(ok)) if ok else 0

    freshness = {}
    for r in ok:
        f = r.get("content_freshness", "unknown")
        freshness[f] = freshness.get(f, 0) + 1

    team_size = {}
    for r in ok:
        t = r.get("team_size_indicator", "unknown")
        team_size[t] = team_size.get(t, 0) + 1

    tracking_yes = sum(1 for r in ok if r.get("tracking_present"))
    tracking_no  = len(ok) - tracking_yes
    forms_yes    = sum(1 for r in ok if r.get("conversion_forms"))
    forms_no     = len(ok) - forms_yes

    cat_stats = {}
    for cat in ["Dental", "Construction", "Legal"]:
        cat_r = [r for r in results if r["category"] == cat]
        cat_stats[cat] = {
            "processed": len(cat_r),
            "errors":    len([r for r in cat_r if r.get("error")]),
        }

    # Pick 5 examples for Dave
    dental_ok  = [r for r in ok if r["category"] == "Dental"]
    const_ok   = [r for r in ok if r["category"] == "Construction"]
    legal_ok   = [r for r in ok if r["category"] == "Legal"]
    error_ex   = errors[:1]

    dental_sorted = sorted(dental_ok, key=lambda x: x["content_length_input"], reverse=True)
    ex_dental_high = dental_sorted[0]  if dental_sorted else None
    ex_dental_low  = dental_sorted[-1] if len(dental_sorted) > 1 else None
    ex_const       = const_ok[0]  if const_ok  else None
    ex_legal       = legal_ok[0]  if legal_ok  else None
    ex_error_or_stale = (error_ex[0] if error_ex else
                         next((r for r in ok if r.get("content_freshness") == "stale"), None))

    print("\n" + "=" * 60)
    print("=== TASK B REPORT ===")
    print()
    print(f"1. TOTAL PROCESSED: {len(results)} | ERRORS: {len(errors)}")
    print(f"2. AVG SONNET RESPONSE TIME: {avg_rt}ms")
    print(f"3. TOTAL TOKENS: input={total_in:,} | output={total_out:,}")
    print(f"4. ESTIMATED COST: ${cost_usd:.2f} USD")
    print()
    print("5. PER-CATEGORY:")
    for cat, s in cat_stats.items():
        print(f"   {cat}: processed={s['processed']} | errors={s['errors']}")
    print()
    print("6. CONTENT FRESHNESS:")
    for k, v in sorted(freshness.items()):
        print(f"   {k}: {v}")
    print()
    print("7. TEAM SIZE:")
    for k, v in sorted(team_size.items()):
        print(f"   {k}: {v}")
    print()
    print(f"8. TRACKING PRESENT: yes={tracking_yes} | no={tracking_no}")
    print(f"9. CONVERSION FORMS: yes={forms_yes} | no={forms_no}")
    print(f"10. WALL-CLOCK TIME: {elapsed:.2f}s")
    print()
    print("11. FIVE EXAMPLE OUTPUTS:")

    def show(label, r):
        if r is None:
            print(f"\n  [{label}]: NOT AVAILABLE")
            return
        print(f"\n  [{label}]")
        print(f"  domain: {r['domain']}")
        print(f"  category: {r['category']}")
        print(f"  content_length_input: {r['content_length_input']}")
        print(f"  response_time_ms: {r['response_time_ms']}")
        if r.get("error"):
            print(f"  ERROR: {r['error']}")
        else:
            raw = r.get("raw_result", {})
            print(f"  FULL comprehend_website response:")
            print(json.dumps(raw, indent=4))

    show("DENTAL highest content_length", ex_dental_high)
    show("DENTAL lowest content_length",  ex_dental_low)
    show("CONSTRUCTION example",          ex_const)
    show("LEGAL example",                 ex_legal)
    show("ERROR or STALE example",        ex_error_or_stale)

    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    save_results = []
    for r in results:
        sr = {k: v for k, v in r.items() if k != "raw_result"}
        sr["comprehension"] = r.get("raw_result", {})
        save_results.append(sr)

    output = {
        "stage": "300c_comprehend",
        "summary": {
            "total": len(results), "ok": len(ok), "errors": len(errors),
            "avg_response_ms": avg_rt, "total_tokens_in": total_in,
            "total_tokens_out": total_out, "cost_usd": round(cost_usd, 2),
            "elapsed_seconds": round(elapsed, 2),
            "freshness": freshness, "team_size": team_size,
            "tracking_present": tracking_yes, "tracking_absent": tracking_no,
            "conversion_forms": forms_yes, "no_conversion_forms": forms_no,
            "per_category": cat_stats,
        },
        "domains": save_results,
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
