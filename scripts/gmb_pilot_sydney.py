#!/usr/bin/env python3
"""
scripts/gmb_pilot_sydney.py
Directive #225 — Sydney GMB Pre-Population Pilot (Batch Refactor)

Architecture:
  Step 1: Batch ALL 1,000 inputs into ONE Bright Data snapshot trigger.
          Each input: {"keyword": "{trading_name} {postcode}", "country": "AU"}
          discover_by=location. One poll loop. One download.

  Step 2: Match results to ABNs (best-effort by trading name similarity).
          UPDATE business_universe for every match.
          INSERT into gmb_pilot_results for every business.

  Step 3: For matched businesses with review_count > 0,
          fetch reviews via dataset gd_luzfs1dn2oa0teb81.

Usage:
  python scripts/gmb_pilot_sydney.py [--dry-run] [--limit 1000]
"""

import argparse
import asyncio
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import types
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
BUSINESSES_FILE = Path("/tmp/pilot_businesses.json")
RESULTS_FILE = ROOT / "data" / "gmb_pilot_results.jsonl"
SUMMARY_FILE = ROOT / "data" / "gmb_pilot_summary.json"
MCP = ROOT / "skills" / "mcp-bridge" / "scripts" / "mcp-bridge.js"
SUPABASE_PROJECT = "jatzvazlbusedwsnqxzr"

GMB_DATASET = "gd_m8ebnr0q2qlklc02fz"
REVIEWS_DATASET = "gd_luzfs1dn2oa0teb81"

# Stub structlog
try:
    import structlog  # noqa: F401
except ImportError:
    structlog = types.ModuleType("structlog")
    structlog.get_logger = lambda name="": types.SimpleNamespace(
        info=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        error=lambda *a, **k: None,
        debug=lambda *a, **k: None,
    )
    sys.modules["structlog"] = structlog

# Load BrightDataClient directly
spec = importlib.util.spec_from_file_location(
    "bright_data_client",
    ROOT / "src" / "integrations" / "bright_data_client.py",
)
bdc_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bdc_mod)
BrightDataClient = bdc_mod.BrightDataClient

from dotenv import load_dotenv
load_dotenv(Path.home() / ".config" / "agency-os" / ".env")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mcp_sql(query: str) -> list[dict]:
    """Run SQL via MCP bridge. Returns list of row dicts."""
    result = subprocess.run(
        ["node", str(MCP), "call", "supabase", "execute_sql",
         json.dumps({"project_id": SUPABASE_PROJECT, "query": query})],
        capture_output=True, text=True, timeout=60,
    )
    raw = result.stdout
    outer = json.loads(raw)
    idx = outer.find("[")
    if idx == -1:
        return []
    chunk = outer[idx:]
    return json.loads(chunk[: chunk.rindex("]") + 1])


def extract_owner_name(owner_response: str) -> str | None:
    if not owner_response:
        return None
    patterns = [
        r"(?i)(?:hi,?\s+)?i['']?m\s+([A-Z][a-z]+)",
        r"(?i)[-\u2013]\s*([A-Z][a-z]+)\s*$",
        r"(?i)([A-Z][a-z]+)\s+here\b",
        r"(?i)^([A-Z][a-z]+)\s+(?:from|at)\b",
    ]
    for pat in patterns:
        m = re.search(pat, owner_response)
        if m:
            return m.group(1)
    return None


def normalize(name: str) -> str:
    """Lowercase, strip Pty Ltd suffixes for matching."""
    name = name.lower()
    for suffix in [" pty ltd", " pty. ltd.", " pty limited", " ltd", " pty"]:
        name = name.replace(suffix, "")
    return re.sub(r"[^a-z0-9 ]", "", name).strip()


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

async def run_pilot(businesses: list[dict], dry_run: bool) -> dict:
    api_key = os.environ["BRIGHTDATA_API_KEY"]
    client = BrightDataClient(api_key=api_key)

    abn_map = {normalize(b["trading_name"]): b for b in businesses}

    print(f"\n{'='*60}")
    print(f"{'DRY RUN — ' if dry_run else ''}SYDNEY GMB PILOT")
    print(f"Businesses: {len(businesses)}")
    print(f"{'='*60}\n")

    if dry_run:
        print("First 5 businesses:")
        for b in businesses[:5]:
            print(f"  ABN={b['abn']}  name={b['trading_name']}  postcode={b['postcode']}")
        print("\nDry-run complete. No API calls made.")
        return {}

    # ------------------------------------------------------------------
    # STEP 1 — Single batch snapshot (all 1,000 inputs in one trigger)
    # ------------------------------------------------------------------
    inputs = [
        {"keyword": f"{b['trading_name']} {b['postcode']}", "country": "AU"}
        for b in businesses
    ]

    t0 = time.time()
    print(f"[{datetime.now(timezone.utc).isoformat()}] Triggering batch snapshot ({len(inputs)} inputs)...")
    results = await client._scraper_request(GMB_DATASET, inputs, discover_by="location")
    elapsed_discovery = time.time() - t0
    print(f"[{datetime.now(timezone.utc).isoformat()}] Snapshot complete in {elapsed_discovery:.1f}s — {len(results)} GMB records returned\n")

    # ------------------------------------------------------------------
    # STEP 2 — Match results → ABNs, write-backs
    # ------------------------------------------------------------------
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    pilot_rows = []
    matched, not_found = 0, 0
    bu_updates = 0

    # Build ABN lookup by best name match
    result_by_name = {}
    for r in results:
        title = normalize(r.get("title") or r.get("name") or "")
        if title and title not in result_by_name:
            result_by_name[title] = r

    for b in businesses:
        norm = normalize(b["trading_name"])
        gmb = result_by_name.get(norm)

        # Fallback: partial match (first word)
        if not gmb:
            first_word = norm.split()[0] if norm.split() else ""
            if len(first_word) > 4:
                gmb = next((v for k, v in result_by_name.items() if k.startswith(first_word)), None)

        serp_found = gmb is not None
        low_activity = serp_found and int(gmb.get("reviews_cnt") or 0) == 0

        if serp_found:
            matched += 1
            cat = (gmb.get("category") or [{}])
            cat_title = cat[0].get("title") if isinstance(cat, list) and cat else str(cat)

            place_id = gmb.get("map_id_encoded") or ""
            fid = gmb.get("map_id") or gmb.get("fid") or ""
            domain = gmb.get("display_link") or ""
            rating = gmb.get("rating") or 0
            reviews_cnt = int(gmb.get("reviews_cnt") or 0)
            address = gmb.get("address") or ""
            phone = gmb.get("phone") or ""
            city = address.split(",")[0].strip() if "," in address else ""
            lat = gmb.get("latitude") or 0
            lon = gmb.get("longitude") or 0

            # UPDATE business_universe
            safe = lambda s: str(s).replace("'", "''") if s else ""
            mcp_sql(f"""
                UPDATE business_universe SET
                  gmb_place_id = '{safe(place_id)}',
                  gmb_cid = '{safe(fid)}',
                  gmb_category = '{safe(cat_title)}',
                  gmb_rating = {float(rating) if rating else 'NULL'},
                  gmb_review_count = {reviews_cnt},
                  gmb_domain = '{safe(domain)}',
                  gmb_phone = '{safe(phone)}',
                  gmb_address = '{safe(address)}',
                  gmb_city = '{safe(city)}',
                  gmb_latitude = {float(lat) if lat else 'NULL'},
                  gmb_longitude = {float(lon) if lon else 'NULL'},
                  gmb_enriched_at = NOW(),
                  updated_at = NOW()
                WHERE abn = '{b["abn"]}';
            """)
            bu_updates += 1
        else:
            not_found += 1
            cat_title, domain, rating, reviews_cnt = None, None, None, 0

        row = {
            "abn": b["abn"],
            "trading_name": b["trading_name"],
            "postcode": b["postcode"],
            "serp_found": serp_found,
            "serp_title": gmb.get("title") if gmb else None,
            "serp_domain": domain if serp_found else None,
            "serp_rating": rating if serp_found else None,
            "serp_reviews_cnt": reviews_cnt if serp_found else 0,
            "serp_category": cat_title if serp_found else None,
            "low_activity": low_activity,
            "not_found": not serp_found,
        }
        pilot_rows.append(row)

        # INSERT gmb_pilot_results
        safe = lambda s: str(s).replace("'", "''") if s else ""
        mcp_sql(f"""
            INSERT INTO gmb_pilot_results
              (abn, trading_name, serp_match, gmb_category, gmb_rating, gmb_review_count, gmb_domain, match_confidence)
            VALUES (
              '{b["abn"]}', '{safe(b["trading_name"])}',
              {'true' if serp_found else 'false'},
              {'\''+safe(cat_title)+'\'' if cat_title else 'NULL'},
              {float(rating) if rating else 'NULL'},
              {reviews_cnt},
              {'\''+safe(domain)+'\'' if domain else 'NULL'},
              '{'high' if serp_found else 'none'}'
            );
        """)

        if len(pilot_rows) % 100 == 0:
            elapsed = time.time() - t0
            est_cost = (matched * 0.001 * 1.55)
            print(f"[Pilot] {len(pilot_rows)}/1000 processed — {matched} found, {not_found} not found, {est_cost:.4f} AUD spent")

    # ------------------------------------------------------------------
    # STEP 3b — Reviews for businesses with reviews_cnt > 0
    # ------------------------------------------------------------------
    review_candidates = [
        (pilot_rows[i], results[i] if i < len(results) else None)
        for i, b in enumerate(businesses)
        if pilot_rows[i]["serp_found"] and pilot_rows[i]["serp_reviews_cnt"] > 0
    ]

    print(f"\nFetching reviews for {len(review_candidates)} businesses with review_count > 0...")
    total_reviews = 0
    owner_names_found = 0

    for row, gmb in review_candidates:
        place_id = gmb.get("map_id_encoded") or "" if gmb else ""
        if not place_id:
            continue
        try:
            reviews = await client._scraper_request(
                REVIEWS_DATASET,
                [{"url": f"https://www.google.com/maps/place/?q=place_id:{place_id}"}],
                discover_by=None,
            )
            most_recent = None
            owner_name = None
            for rev in reviews:
                reviewer = rev.get("reviewer_name") or rev.get("author_name") or ""
                rating = rev.get("rating") or rev.get("stars") or 0
                text = rev.get("review_text") or rev.get("text") or ""
                date_str = rev.get("review_date") or rev.get("date") or ""
                owner_resp = rev.get("owner_response") or rev.get("response") or ""
                owner_resp_date = rev.get("owner_response_date") or ""

                if not owner_name:
                    owner_name = extract_owner_name(owner_resp)

                safe = lambda s: str(s).replace("'", "''") if s else ""
                mcp_sql(f"""
                    INSERT INTO business_reviews
                      (abn, gmb_place_id, reviewer_name, review_rating, review_text,
                       review_date, owner_response, owner_response_date, owner_name)
                    VALUES (
                      '{row["abn"]}', '{safe(place_id)}', '{safe(reviewer)}',
                      {int(rating) if rating else 'NULL'}, '{safe(text[:2000])}',
                      {("'"+safe(date_str)+"'") if date_str else 'NULL'},
                      '{safe(owner_resp[:2000])}',
                      {("'"+safe(owner_resp_date)+"'") if owner_resp_date else 'NULL'},
                      {("'"+safe(owner_name)+"'") if owner_name else 'NULL'}
                    );
                """)
                total_reviews += 1

            if owner_name:
                owner_names_found += 1
                safe = lambda s: str(s).replace("'", "''") if s else ""
                mcp_sql(f"""
                    UPDATE business_universe SET
                      gmb_owner_name = '{safe(owner_name)}',
                      gmb_reviews_fetched_at = NOW()
                    WHERE abn = '{row["abn"]}';
                """)
        except Exception as e:
            print(f"[Reviews] {row['trading_name']}: {e}")

    await client.close()

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    elapsed_total = time.time() - t0
    cost_aud = ((matched * 0.001) + (len(review_candidates) * 0.001) + (len(businesses) * 0.0015)) * 1.55

    with open(RESULTS_FILE, "w") as f:
        for r in pilot_rows:
            f.write(json.dumps(r) + "\n")

    summary = {
        "total": len(businesses),
        "serp_found": matched,
        "serp_not_found": not_found,
        "gmb_bu_updated": bu_updates,
        "reviews_fetched": total_reviews,
        "owner_names_extracted": owner_names_found,
        "wall_clock_seconds": round(elapsed_total, 1),
        "cost_aud_estimate": round(cost_aud, 4),
    }
    with open(SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total processed:              {summary['total']}")
    print(f"SERP matches found:           {summary['serp_found']} ({summary['serp_found']/summary['total']*100:.1f}%)")
    print(f"Not found:                    {summary['serp_not_found']}")
    print(f"business_universe updated:    {summary['gmb_bu_updated']}")
    print(f"Reviews fetched:              {summary['reviews_fetched']}")
    print(f"Owner names extracted:        {summary['owner_names_extracted']}")
    print(f"Wall-clock time:              {summary['wall_clock_seconds']}s ({summary['wall_clock_seconds']/60:.1f} min)")
    print(f"Estimated cost:               ${summary['cost_aud_estimate']:.4f} AUD")

    return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Sydney GMB Pre-Population Pilot")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    # Ensure migration applied
    if not args.dry_run:
        subprocess.run(
            ["node", str(MCP), "call", "supabase", "execute_sql",
             json.dumps({"project_id": SUPABASE_PROJECT, "query": """
                CREATE TABLE IF NOT EXISTS gmb_pilot_results (
                  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                  abn TEXT, trading_name TEXT, serp_match BOOLEAN,
                  gmb_category TEXT, gmb_rating NUMERIC, gmb_review_count INTEGER,
                  gmb_domain TEXT, match_confidence TEXT,
                  created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS business_reviews (
                  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                  abn TEXT NOT NULL, gmb_place_id TEXT, reviewer_name TEXT,
                  review_rating INTEGER, review_text TEXT, review_date TIMESTAMPTZ,
                  owner_response TEXT, owner_response_date TIMESTAMPTZ,
                  owner_name TEXT, created_at TIMESTAMPTZ DEFAULT NOW()
                );
                ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS gmb_owner_name TEXT;
                ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS gmb_reviews_fetched_at TIMESTAMPTZ;
                ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS gmb_last_review_date TIMESTAMPTZ;
             """})],
            capture_output=True, text=True, timeout=30,
        )

    businesses = json.loads(BUSINESSES_FILE.read_text())[: args.limit]
    asyncio.run(run_pilot(businesses, args.dry_run))


if __name__ == "__main__":
    main()
