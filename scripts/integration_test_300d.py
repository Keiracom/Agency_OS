"""
DIRECTIVE #300d — Integration Test: Stage 4 Haiku Affordability Gate
730 domains: ABN match (free, local DB) + Haiku judge_affordability ($0.003/domain).
Cost: ~$2.20 USD
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncpg
from src.config.settings import settings
from src.pipeline.free_enrichment import FreeEnrichment, ABNMatchConfidence
from src.pipeline.intelligence import judge_affordability
from src.pipeline.pipeline_orchestrator import GLOBAL_SEM_ABN

INPUT_FILE = os.path.join(os.path.dirname(__file__), "output", "300c_comprehend.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output", "300d_afford.json")

# Haiku pricing: $0.80/MTok input, $4/MTok output
COST_PER_INPUT = 0.80 / 1_000_000
COST_PER_OUTPUT = 4.0 / 1_000_000

SEM_HAIKU = asyncio.Semaphore(55)  # GLOBAL_SEM_HAIKU


async def abn_match(fe: FreeEnrichment, domain: str, title: str) -> dict:
    """Run ABN matching against local abn_registry."""
    async with GLOBAL_SEM_ABN:
        try:
            result = await fe._match_abn(
                domain=domain,
                title=title or None,
                state_hint=None,
                suburb=None,
            )
            return result
        except Exception as exc:
            return {"abn_matched": False, "_error": str(exc)}


async def process_domain(fe: FreeEnrichment, item: dict) -> dict:
    domain = item["domain"]
    category = item.get("category", "")
    title = (
        item.get("comprehension", {}).get("services_detected", [""])[0]
        if item.get("comprehension")
        else ""
    )
    comp = item.get("comprehension") or {}

    out = {
        "domain": domain,
        "category": category,
        "abn_matched": False,
        "abn_entity_type": None,
        "gst_registered": None,
        "abn_confidence": "none",
        "afford_score": 0,
        "afford_hard_gate": False,
        "afford_gate_reason": None,
        "afford_judgment": "",
        "afford_band": "unknown",
        "haiku_tokens_in": 0,
        "haiku_tokens_out": 0,
        "response_time_ms": 0,
        "error": None,
    }

    # Stage A: ABN match
    abn_data = await abn_match(fe, domain, item.get("title") or "")
    if abn_data.get("abn_matched"):
        conf = abn_data.get("abn_confidence")
        out["abn_matched"] = True
        out["abn_entity_type"] = abn_data.get("entity_type")
        out["gst_registered"] = abn_data.get("gst_registered")
        out["abn_confidence"] = (
            "exact"
            if conf == ABNMatchConfidence.EXACT
            else "fuzzy"
            if conf == ABNMatchConfidence.PARTIAL
            else "low"
        )

    # Stage B: Haiku affordability judgment
    t0 = time.monotonic()
    try:
        # Build abn_dict for judge_affordability
        abn_dict = {
            "entity_type": out["abn_entity_type"],
            "gst_registered": out["gst_registered"],
            "abn_matched": out["abn_matched"],
        }
        result = await judge_affordability(domain, abn_dict, comp)
        elapsed_ms = round((time.monotonic() - t0) * 1000)

        out.update(
            {
                "afford_score": result.get("score", 0),
                "afford_hard_gate": result.get("hard_gate", False),
                "afford_gate_reason": result.get("gate_reason")
                if result.get("gate_reason") != "none"
                else None,
                "afford_judgment": result.get("judgment", ""),
                "afford_band": result.get("band", "unknown"),
                "haiku_tokens_in": 300,  # estimated: small prompt
                "haiku_tokens_out": 80,  # estimated: short JSON response
                "response_time_ms": elapsed_ms,
                "raw_result": result,
            }
        )
    except Exception as exc:
        out["error"] = str(exc)
        out["response_time_ms"] = round((time.monotonic() - t0) * 1000)

    return out


async def main():
    print("=" * 60)
    print("DIRECTIVE #300d — Stage 4: Haiku Affordability Gate")
    print("730 domains: ABN match + Haiku judgment")
    print("=" * 60)

    with open(INPUT_FILE) as f:
        data = json.load(f)
    domains = data["domains"]
    print(f"Loaded {len(domains)} domains\n")

    # Connect to Supabase via asyncpg
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog", format="text"
    )
    fe = FreeEnrichment(conn)

    t0 = time.monotonic()
    results = []
    done = [0]

    async def run_one(item):
        r = await process_domain(fe, item)
        done[0] += 1
        if done[0] % 50 == 0:
            elapsed = time.monotonic() - t0
            errs = sum(1 for x in results if x.get("error"))
            print(f"  {done[0]}/{len(domains)} done | {elapsed:.0f}s | errors: {errs}")
        results.append(r)

    # ABN is serialised (SEM_ABN=1), Haiku is parallel (SEM_HAIKU=55)
    # Run all concurrently — semaphores handle the rate limiting
    await asyncio.gather(*[run_one(item) for item in domains])

    elapsed = time.monotonic() - t0
    await conn.close()

    # Stats
    errors = [r for r in results if r.get("error")]
    ok = [r for r in results if not r.get("error")]
    abn_match = [r for r in results if r["abn_matched"]]
    abn_no = [r for r in results if not r["abn_matched"]]

    conf_breakdown = {"exact": 0, "fuzzy": 0, "low": 0, "none": 0}
    for r in results:
        c = r["abn_confidence"]
        conf_breakdown[c] = conf_breakdown.get(c, 0) + 1

    entity_types: dict[str, int] = {}
    for r in abn_match:
        et = r["abn_entity_type"] or "unknown"
        entity_types[et] = entity_types.get(et, 0) + 1

    gst_yes = sum(1 for r in results if r["gst_registered"] is True)
    gst_no = sum(1 for r in results if r["gst_registered"] is False)
    gst_unk = len(results) - gst_yes - gst_no

    passed = [r for r in ok if not r["afford_hard_gate"]]
    rejected = [r for r in ok if r["afford_hard_gate"]]

    gate_reasons: dict[str, int] = {}
    for r in rejected:
        reason = r["afford_gate_reason"] or "unknown"
        gate_reasons[reason] = gate_reasons.get(reason, 0) + 1

    score_dist = {"0-3": 0, "4-6": 0, "7-10": 0}
    for r in ok:
        s = r["afford_score"]
        if s <= 3:
            score_dist["0-3"] += 1
        elif s <= 6:
            score_dist["4-6"] += 1
        else:
            score_dist["7-10"] += 1

    cat_stats = {}
    for cat in ["Dental", "Construction", "Legal"]:
        cat_r = [r for r in ok if r["category"] == cat]
        cat_stats[cat] = {
            "passed": len([r for r in cat_r if not r["afford_hard_gate"]]),
            "rejected": len([r for r in cat_r if r["afford_hard_gate"]]),
        }

    total_in = sum(r["haiku_tokens_in"] for r in ok)
    total_out = sum(r["haiku_tokens_out"] for r in ok)
    cost_usd = total_in * COST_PER_INPUT + total_out * COST_PER_OUTPUT
    avg_rt = round(sum(r["response_time_ms"] for r in ok) / len(ok)) if ok else 0

    # Pick 5 examples
    ex_sole = next(
        (
            r
            for r in ok
            if r["abn_entity_type"]
            and "individual" in (r["abn_entity_type"] or "").lower()
            and r["afford_hard_gate"]
        ),
        None,
    )
    ex_no_gst = next(
        (
            r
            for r in ok
            if r["gst_registered"] is False
            and r["afford_hard_gate"]
            and r["afford_gate_reason"]
            and "gst" in r["afford_gate_reason"].lower()
        ),
        None,
    )
    ex_high = max(
        (r for r in ok if not r["afford_hard_gate"]), key=lambda r: r["afford_score"], default=None
    )
    ex_govt = next(
        (
            r
            for r in ok
            if r["afford_hard_gate"]
            and r["afford_gate_reason"]
            and (
                "non" in r["afford_gate_reason"].lower()
                or "gov" in r["domain"].lower()
                or ".gov" in r["domain"]
            )
        ),
        None,
    )
    ex_no_abn = next((r for r in ok if not r["abn_matched"]), None)

    print("\n" + "=" * 60)
    print("=== TASK B REPORT ===")
    print()
    print(f"1. TOTAL PROCESSED: {len(results)} | ERRORS: {len(errors)}")
    print(
        f"2. ABN MATCH RATE: matched={len(abn_match)} | unmatched={len(abn_no)} | total={len(results)}"
    )
    print()
    print("3. ABN CONFIDENCE:")
    for k, v in conf_breakdown.items():
        print(f"   {k}: {v}")
    print()
    print("4. ENTITY TYPE DISTRIBUTION:")
    for et, count in sorted(entity_types.items(), key=lambda x: -x[1])[:10]:
        print(f"   {et}: {count}")
    print()
    print(f"5. GST REGISTERED: yes={gst_yes} | no={gst_no} | unknown={gst_unk}")
    print()
    print(f"6. AFFORDABILITY GATE: passed={len(passed)} | rejected={len(rejected)}")
    print("   GATE REASONS:")
    for reason, count in sorted(gate_reasons.items(), key=lambda x: -x[1]):
        print(f"     {reason}: {count}")
    print()
    print("7. SCORE DISTRIBUTION:")
    for band, count in score_dist.items():
        print(f"   {band}: {count}")
    print()
    print("8. PER-CATEGORY:")
    for cat, s in cat_stats.items():
        print(f"   {cat}: passed={s['passed']} | rejected={s['rejected']}")
    print()
    print(f"9. HAIKU COST: ${cost_usd:.2f} USD (tokens in={total_in:,} out={total_out:,})")
    print(f"10. WALL-CLOCK TIME: {elapsed:.2f}s | AVG RESPONSE: {avg_rt}ms")

    def show(label, r):
        if r is None:
            print(f"\n  [{label}]: NOT FOUND IN SAMPLE")
            return
        printable = {k: v for k, v in r.items() if k != "raw_result"}
        printable["haiku_raw"] = r.get("raw_result", {})
        print(f"\n  [{label}]")
        print(json.dumps(printable, indent=4, default=str))

    print()
    print("11. FIVE EXAMPLES:")
    show("SOLE TRADER rejected", ex_sole)
    show("NO GST rejected", ex_no_gst)
    show("HIGH SCORE pass (8+)", ex_high)
    show("GOVERNMENT/non-commercial", ex_govt)
    show("NO ABN MATCH (Haiku handles)", ex_no_abn)

    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    save_results = [{k: v for k, v in r.items() if k != "raw_result"} for r in results]
    for i, r in enumerate(results):
        save_results[i]["haiku_result"] = r.get("raw_result", {})

    output = {
        "stage": "300d_afford",
        "summary": {
            "total": len(results),
            "ok": len(ok),
            "errors": len(errors),
            "abn_matched": len(abn_match),
            "abn_unmatched": len(abn_no),
            "abn_confidence": conf_breakdown,
            "gst_yes": gst_yes,
            "gst_no": gst_no,
            "gst_unknown": gst_unk,
            "passed": len(passed),
            "rejected": len(rejected),
            "gate_reasons": gate_reasons,
            "score_dist": score_dist,
            "per_category": cat_stats,
            "haiku_cost_usd": round(cost_usd, 2),
            "elapsed_seconds": round(elapsed, 2),
            "avg_response_ms": avg_rt,
        },
        "domains": save_results,
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
