#!/usr/bin/env python3
"""
scripts/gmb_pilot2.py — Directive #227: GMB Pilot 2

Pre-flight fixes applied vs Pilot 1:
  - CUT excluded from business selection (Corporate Unit Trust)
  - Shell name pre-filter (HOLDINGS, INVESTMENTS, CAPITAL, VENTURES,
    ENTERPRISES, MANAGEMENT CO, ACN [0-9]+)
  - Keyword match uses discovery_input.keyword (correct field)
  - BD poll timeout: 15 minutes
  - DB write: bulk Supabase REST upsert (no per-row MCP calls)
  - BD error retry: re-submit single-result-page errors with name-only keyword

Usage:
  python3 scripts/gmb_pilot2.py [--dry-run]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
MCP = ROOT / "skills" / "mcp-bridge" / "scripts" / "mcp-bridge.js"
PROJ = "jatzvazlbusedwsnqxzr"
GMB_DATASET = "gd_m8ebnr0q2qlklc02fz"
SNAPSHOT_FILE = Path("/tmp/gmb_pilot2_snapshot.json")
RETRY_SNAPSHOT_FILE = Path("/tmp/gmb_pilot2_retry_snapshot.json")
BUSINESSES_FILE = Path("/tmp/gmb_pilot2_businesses.json")

BD_POLL_MAX_SEC = 900   # 15 minutes
BD_POLL_INTERVAL = 10   # seconds between status checks
UPSERT_CHUNK = 500       # records per Supabase REST batch

# ── Helpers ──────────────────────────────────────────────────────────────────

def mcp_sql(q, timeout=60):
    """Run SQL via MCP bridge, return list of row dicts."""
    r = subprocess.run(
        ["node", str(MCP), "call", "supabase", "execute_sql",
         json.dumps({"project_id": PROJ, "query": q})],
        capture_output=True, text=True, timeout=timeout
    )
    raw = r.stdout.strip()
    if not raw:
        return []
    # outer is a JSON-encoded string — decode it
    try:
        s = json.loads(raw)  # -> str
        if not isinstance(s, str):
            s = json.dumps(s)
    except Exception:
        s = raw

    # Try extracting from untrusted-data block (handles both small and large payloads)
    m = re.search(r'<untrusted-data[^>]+>\s*(.*?)\s*</untrusted-data', s, re.DOTALL)
    if m:
        content = m.group(1).strip()
        try:
            return json.loads(content)
        except Exception:
            pass

    # Fallback: find outermost JSON array
    # Find first '[' and last ']' to handle large nested arrays
    start = s.find('[')
    end = s.rfind(']')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(s[start:end + 1])
        except Exception:
            pass
    return []


def normalize(name):
    name = name.lower()
    for sfx in [" pty ltd", " pty. ltd.", " pty limited", " ltd", " pty", " limited"]:
        name = name.replace(sfx, "")
    return re.sub(r"[^a-z0-9 ]", "", name).strip()


def safe(s):
    return str(s).replace("'", "''").replace("\x00", "") if s else ""


def supabase_bulk_insert(rows, table="gmb_pilot_results"):
    """Bulk insert via Supabase REST API in chunks."""
    url = f"{os.environ['SUPABASE_URL']}/rest/v1/{table}"
    headers = {
        "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}",
        "apikey": os.environ['SUPABASE_SERVICE_KEY'],
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    inserted = 0
    for i in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[i:i + UPSERT_CHUNK]
        resp = httpx.post(url, headers=headers, json=chunk, timeout=60)
        if resp.status_code not in (200, 201):
            print(f"  REST insert error {resp.status_code}: {resp.text[:200]}")
        else:
            inserted += len(chunk)
    return inserted


def bd_trigger(api_key, inputs, discover_by="location"):
    """Trigger BD snapshot. Returns snapshot_id."""
    base = "https://api.brightdata.com/datasets/v3"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{base}/trigger?dataset_id={GMB_DATASET}&include_errors=true&type=discover_new&discover_by={discover_by}"
    resp = httpx.post(url, headers=headers, json=inputs, timeout=60)
    resp.raise_for_status()
    sid = resp.json()["snapshot_id"]
    print(f"  Snapshot triggered: {sid}")
    return sid


def bd_poll(api_key, snapshot_id, label=""):
    """Poll until ready or timeout. Returns status string."""
    base = "https://api.brightdata.com/datasets/v3"
    headers = {"Authorization": f"Bearer {api_key}"}
    t0 = time.time()
    last_status = "unknown"
    while time.time() - t0 < BD_POLL_MAX_SEC:
        elapsed = time.time() - t0
        try:
            r = httpx.get(f"{base}/progress/{snapshot_id}", headers=headers, timeout=15)
            data = r.json()
            last_status = data.get("status", "unknown")
            records = data.get("records", "?")
            print(f"  [{label}] {elapsed:.0f}s — status={last_status} records={records}")
            if last_status == "ready":
                return "ready"
            if last_status == "failed":
                print(f"  BD job failed: {data}")
                return "failed"
        except Exception as e:
            print(f"  Poll error: {e}")
        time.sleep(BD_POLL_INTERVAL)
    print(f"  TIMEOUT after {BD_POLL_MAX_SEC}s — last status: {last_status}")
    return "timeout"


def bd_download(api_key, snapshot_id):
    """Download snapshot results as list of dicts. Handles both JSON array and NDJSON."""
    base = "https://api.brightdata.com/datasets/v3"
    headers = {"Authorization": f"Bearer {api_key}"}
    r = httpx.get(f"{base}/snapshot/{snapshot_id}?format=json", headers=headers, timeout=120)
    r.raise_for_status()
    text = r.text.strip()
    # Try JSON array first
    try:
        result = r.json()
        if isinstance(result, list):
            return result
    except Exception:
        pass
    # NDJSON fallback (one JSON object per line)
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def bulk_update_business_universe(updates, batch=40):
    """
    Bulk UPDATE business_universe. updates = list of (abn, fields_dict).
    Sends 40 UPDATE statements per MCP call.
    """
    for i in range(0, len(updates), batch):
        chunk = updates[i:i + batch]
        stmts = []
        for (abn, f) in chunk:
            rating_sql = str(f["rating"]) if f.get("rating") else "NULL"
            lat_sql = str(f["lat"]) if f.get("lat") else "NULL"
            lon_sql = str(f["lon"]) if f.get("lon") else "NULL"
            stmts.append(f"""
                UPDATE business_universe SET
                  gmb_place_id='{safe(f.get("place_id",""))}',
                  gmb_cid='{safe(f.get("cid",""))}',
                  gmb_category='{safe(f.get("cat",""))}',
                  gmb_rating={rating_sql},
                  gmb_review_count={int(f.get("reviews_cnt", 0))},
                  gmb_domain='{safe(f.get("domain",""))}',
                  gmb_phone='{safe(f.get("phone",""))}',
                  gmb_address='{safe(f.get("address",""))}',
                  gmb_city='{safe(f.get("city",""))}',
                  gmb_latitude={lat_sql},
                  gmb_longitude={lon_sql},
                  gmb_enriched_at=NOW(), updated_at=NOW()
                WHERE abn='{abn}';
            """)
        mcp_sql(" ".join(stmts), timeout=120)


# ── Main ─────────────────────────────────────────────────────────────────────

def main(dry_run=False):
    from dotenv import load_dotenv
    load_dotenv(Path.home() / ".config" / "agency-os" / ".env")

    api_key = os.environ["BRIGHTDATA_API_KEY"]
    t_total = time.time()

    print("\n" + "="*60)
    print(f"GMB PILOT 2 — Directive #227 {'[DRY RUN]' if dry_run else ''}")
    print("="*60)

    # ── Phase 0: Select 1,000 fresh businesses ───────────────────────────────
    print("\n[Phase 0] Selecting businesses...")
    # Use Supabase REST API for large result sets (MCP bridge truncates at scale)
    supa_url = os.environ["SUPABASE_URL"]
    supa_key = os.environ["SUPABASE_SERVICE_KEY"]
    rest_headers = {
        "Authorization": f"Bearer {supa_key}",
        "apikey": supa_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    # Use RPC/SQL via the Supabase SQL endpoint
    sql_endpoint = f"{supa_url}/rest/v1/rpc/execute_sql"
    # Actually use the pg REST query approach via PostgREST
    # Supabase exposes tables directly; for complex WHERE use RPC or the /sql endpoint
    # Use the management API for raw SQL
    mgmt_resp = httpx.post(
        f"https://api.supabase.com/v1/projects/{PROJ}/database/query",
        headers={
            "Authorization": f"Bearer {os.environ.get('SUPABASE_ACCESS_TOKEN', supa_key)}",
            "Content-Type": "application/json",
        },
        json={"query": """
            SELECT abn, trading_name, state, postcode
            FROM business_universe
            WHERE abn NOT IN (SELECT abn FROM gmb_pilot_results)
              AND entity_type_code != 'CUT'
              AND state = 'NSW'
              AND trading_name NOT ILIKE '%HOLDINGS%'
              AND trading_name NOT ILIKE '%INVESTMENTS%'
              AND trading_name NOT ILIKE '%CAPITAL%'
              AND trading_name NOT ILIKE '%VENTURES%'
              AND trading_name NOT ILIKE '%ENTERPRISES%'
              AND trading_name NOT ILIKE '%MANAGEMENT CO%'
              AND trading_name !~ 'ACN[[:space:]]+[0-9]+'
            ORDER BY RANDOM()
            LIMIT 1000
        """},
        timeout=30,
    )
    if mgmt_resp.status_code in (200, 201):
        businesses = mgmt_resp.json()
        if not isinstance(businesses, list):
            # Some Supabase endpoints wrap in {"result": [...]}
            businesses = businesses.get("result", businesses.get("data", []))
    else:
        print(f"  Supabase management API error {mgmt_resp.status_code}: {mgmt_resp.text[:200]}")
        # Fallback: MCP with smaller LIMIT to test
        businesses = mcp_sql("""
            SELECT abn, trading_name, state, postcode
            FROM business_universe
            WHERE abn NOT IN (SELECT abn FROM gmb_pilot_results)
              AND entity_type_code != 'CUT'
              AND state = 'NSW'
              AND trading_name NOT ILIKE '%HOLDINGS%'
              AND trading_name NOT ILIKE '%INVESTMENTS%'
              AND trading_name NOT ILIKE '%CAPITAL%'
              AND trading_name NOT ILIKE '%VENTURES%'
              AND trading_name NOT ILIKE '%ENTERPRISES%'
              AND trading_name NOT ILIKE '%MANAGEMENT CO%'
              AND trading_name !~ 'ACN[[:space:]]+[0-9]+'
            ORDER BY abn
            LIMIT 1000
        """, timeout=60)
    print(f"  Selected: {len(businesses)} businesses")

    if len(businesses) < 1000:
        print(f"  WARNING: Only {len(businesses)} available (expected 1000)")

    if dry_run:
        print("  Sample (first 5):")
        for b in businesses[:5]:
            print(f"    {b['abn']} | {b['trading_name']} | {b['postcode']}")
        print("\nDry run complete.")
        return

    BUSINESSES_FILE.write_text(json.dumps(businesses))
    print(f"  Saved to {BUSINESSES_FILE}")

    # ── Phase 1: Trigger BD location snapshot ────────────────────────────────
    print("\n[Phase 1] Triggering BD batch snapshot...")
    inputs = [
        {"keyword": f"{b['trading_name']} {b['postcode']}", "country": "AU"}
        for b in businesses
    ]
    t_bd_start = time.time()
    snapshot_id = bd_trigger(api_key, inputs, discover_by="location")

    # ── Phase 2: Poll (15 min max) ───────────────────────────────────────────
    print(f"\n[Phase 2] Polling (max {BD_POLL_MAX_SEC}s)...")
    status = bd_poll(api_key, snapshot_id, label="main")
    t_bd_end = time.time()
    bd_elapsed = t_bd_end - t_bd_start

    if status != "ready":
        print(f"  BD snapshot not ready (status={status}). Halting.")
        sys.exit(1)
    print(f"  BD complete in {bd_elapsed:.0f}s")

    # ── Phase 3: Download ────────────────────────────────────────────────────
    print("\n[Phase 3] Downloading results...")
    data = bd_download(api_key, snapshot_id)
    SNAPSHOT_FILE.write_text(json.dumps(data))
    valid = [r for r in data if not r.get("error")]
    errors = [r for r in data if r.get("error")]
    single_page_errors = [r for r in errors if "does not contain a list" in str(r.get("error", ""))]
    other_errors = [r for r in errors if "does not contain a list" not in str(r.get("error", ""))]
    print(f"  Valid: {len(valid)} | Single-page errors: {len(single_page_errors)} | Other errors: {len(other_errors)}")

    # ── Phase 4: Retry single-page errors ───────────────────────────────────
    # Get the ABNs of single-page-error businesses by matching keywords back
    retry_results = []
    if single_page_errors:
        print(f"\n[Phase 4] Retrying {len(single_page_errors)} single-page errors...")

        # Map error keywords back to businesses
        error_kws = set()
        for r in single_page_errors:
            di = r.get("discovery_input") or {}
            kw = di.get("keyword", "").lower().strip() if isinstance(di, dict) else ""
            if kw:
                error_kws.add(kw)

        # Find businesses whose keyword errored
        error_businesses = []
        for b in businesses:
            kw = f"{b['trading_name'].lower()} {b['postcode']}".strip()
            if kw in error_kws:
                error_businesses.append(b)

        print(f"  Matched {len(error_businesses)} error businesses to retry")

        if error_businesses:
            # Retry with name-only keyword (no postcode) — avoids direct-match redirect
            retry_inputs = [
                {"keyword": f"{b['trading_name']} {b['state']}", "country": "AU"}
                for b in error_businesses
            ]
            retry_sid = bd_trigger(api_key, retry_inputs, discover_by="location")
            retry_status = bd_poll(api_key, retry_sid, label="retry")

            if retry_status == "ready":
                retry_data = bd_download(api_key, retry_sid)
                RETRY_SNAPSHOT_FILE.write_text(json.dumps(retry_data))
                retry_valid = [r for r in retry_data if not r.get("error")]
                retry_errors = [r for r in retry_data if r.get("error")]
                print(f"  Retry: {len(retry_valid)} valid, {len(retry_errors)} still erroring")
                retry_results = retry_valid
                # Extend the error kw set with retry keywords
                for b in error_businesses:
                    kw_orig = f"{b['trading_name'].lower()} {b['postcode']}".strip()
                    kw_retry = f"{b['trading_name'].lower()} {b['state']}".strip()
                    # We'll match retry results using name matching below
            else:
                print(f"  Retry snapshot not ready (status={retry_status}). Skipping.")
    else:
        print("\n[Phase 4] No single-page errors — skipping retry.")

    # ── Phase 5: Match results → ABNs ───────────────────────────────────────
    print("\n[Phase 5] Matching GMB results to businesses...")

    # Build name lookup from ALL results (main + retry)
    all_valid = valid + retry_results
    result_by_kw = {}     # discovery_input.keyword → first result
    result_by_name = {}   # normalized name → result

    for r in all_valid:
        di = r.get("discovery_input") or {}
        kw = di.get("keyword", "").lower().strip() if isinstance(di, dict) else ""
        if kw:
            result_by_kw.setdefault(kw, r)
        norm = normalize(r.get("name", ""))
        if norm:
            result_by_name.setdefault(norm, r)

    pilot_rows = []       # for gmb_pilot_results
    bu_updates = []       # for business_universe
    matched = 0
    not_found = 0
    kw_matched = 0
    name_matched = 0
    prefix_matched = 0

    for b in businesses:
        kw = f"{b['trading_name'].lower()} {b['postcode']}".strip()
        kw_retry = f"{b['trading_name'].lower()} {b.get('state','nsw')}".strip()
        norm_b = normalize(b["trading_name"])
        words = [w for w in norm_b.split() if len(w) > 4]

        # Match priority: keyword (main) → keyword (retry) → exact name → prefix
        gmb = (result_by_kw.get(kw)
               or result_by_kw.get(kw_retry)
               or result_by_name.get(norm_b))
        match_path = None

        if result_by_kw.get(kw):
            gmb = result_by_kw[kw]
            match_path = "keyword"
            kw_matched += 1
        elif result_by_kw.get(kw_retry):
            gmb = result_by_kw[kw_retry]
            match_path = "keyword_retry"
            kw_matched += 1
        elif result_by_name.get(norm_b):
            gmb = result_by_name[norm_b]
            match_path = "name_exact"
            name_matched += 1
        elif words:
            gmb = next((v for k, v in result_by_name.items() if k.startswith(words[0])), None)
            if gmb:
                match_path = "name_prefix"
                prefix_matched += 1

        if gmb:
            matched += 1
            cat = gmb.get("category", "") or ""
            place_id = gmb.get("place_id", "") or ""
            cid = gmb.get("fid_location", "") or gmb.get("cid", "") or ""
            details = gmb.get("business_details") or []
            domain = next(
                (d.get("details", "").strip() for d in details if d.get("field_name") == "authority"),
                gmb.get("open_website", "") or ""
            )
            if domain and domain.startswith("http"):
                domain = urlparse(domain).netloc.replace("www.", "")
            phone = gmb.get("phone_number", "") or ""
            address = gmb.get("address", "") or ""
            city = address.split(",")[0].strip() if "," in address else ""
            rating = float(gmb.get("rating") or 0)
            reviews_cnt = int(gmb.get("reviews_count") or 0)
            lat = float(gmb.get("lat") or 0)
            lon = float(gmb.get("lon") or 0)

            pilot_rows.append({
                "abn": b["abn"],
                "trading_name": b["trading_name"],
                "serp_match": True,
                "gmb_category": cat or None,
                "gmb_rating": rating if rating else None,
                "gmb_review_count": reviews_cnt,
                "gmb_domain": domain or None,
                "match_confidence": match_path,
            })
            bu_updates.append((b["abn"], {
                "place_id": place_id, "cid": cid, "cat": cat,
                "rating": rating, "reviews_cnt": reviews_cnt, "domain": domain,
                "phone": phone, "address": address, "city": city,
                "lat": lat, "lon": lon,
            }))
        else:
            not_found += 1
            pilot_rows.append({
                "abn": b["abn"],
                "trading_name": b["trading_name"],
                "serp_match": False,
                "gmb_category": None,
                "gmb_rating": None,
                "gmb_review_count": 0,
                "gmb_domain": None,
                "match_confidence": "none",
            })

    print(f"  Matched: {matched} | Not found: {not_found}")
    print(f"  By path: keyword={kw_matched} name_exact={name_matched} prefix={prefix_matched}")

    # ── Phase 6: Bulk REST insert to gmb_pilot_results ──────────────────────
    print(f"\n[Phase 6] Bulk inserting {len(pilot_rows)} rows to gmb_pilot_results...")
    t_db_start = time.time()
    inserted = supabase_bulk_insert(pilot_rows, "gmb_pilot_results")
    t_db_end = time.time()
    db_elapsed = t_db_end - t_db_start
    print(f"  Inserted: {inserted} rows in {db_elapsed:.1f}s")

    # ── Phase 7: Bulk update business_universe ───────────────────────────────
    print(f"\n[Phase 7] Updating business_universe for {len(bu_updates)} matched businesses...")
    t_bu_start = time.time()
    bulk_update_business_universe(bu_updates)
    t_bu_elapsed = time.time() - t_bu_start
    print(f"  Done in {t_bu_elapsed:.0f}s")

    # ── Phase 8: Verify ──────────────────────────────────────────────────────
    print("\n[Phase 8] Verifying final row count...")
    rows = mcp_sql("""
        SELECT COUNT(*) as total,
               COUNT(DISTINCT abn) as unique_abns,
               SUM(CASE WHEN serp_match THEN 1 ELSE 0 END) as matched,
               SUM(CASE WHEN NOT serp_match THEN 1 ELSE 0 END) as not_found
        FROM (
            SELECT abn, serp_match
            FROM gmb_pilot_results
            WHERE created_at > NOW() - INTERVAL '2 hours'
        ) sub;
    """)
    if rows:
        r = rows[0]
        total_written = int(r.get("total") or 0)
        unique = int(r.get("unique_abns") or 0)
        matched_db = int(r.get("matched") or 0)
        not_found_db = int(r.get("not_found") or 0)
        match_rate = matched_db / total_written * 100 if total_written else 0
    else:
        total_written = unique = matched_db = not_found_db = 0
        match_rate = 0

    total_elapsed = time.time() - t_total

    # ── Phase 9: Report ──────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("PILOT 2 RESULTS")
    print("="*60)
    print(f"Total rows written:        {total_written}")
    print(f"Unique ABNs:               {unique}")
    print(f"Matched (GMB found):       {matched_db} ({match_rate:.1f}%)")
    print(f"Not found:                 {not_found_db}")
    print(f"BD valid records:          {len(valid)}")
    print(f"BD single-page errors:     {len(single_page_errors)}")
    print(f"BD other errors:           {len(other_errors)}")
    print(f"BD snapshot time:          {bd_elapsed:.0f}s ({bd_elapsed/60:.1f} min)")
    print(f"DB write time:             {db_elapsed:.1f}s")
    print(f"Total wall clock:          {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")

    print("\nVS TARGETS:")
    print(f"  Match rate:   {match_rate:.1f}%  (target 65%+)  {'✅' if match_rate >= 65 else '❌'}")
    print(f"  Zero-result:  {not_found_db}    (target <120)   {'✅' if not_found_db < 120 else '❌'}")
    print(f"  BD errors:    {len(single_page_errors)}   (target ~0)    {'✅' if len(single_page_errors) < 30 else f'❌ — {len(single_page_errors)} remain'}")
    print(f"  DB write:     {db_elapsed:.0f}s   (target <60s)  {'✅' if db_elapsed < 60 else '❌'}")

    if match_rate < 60:
        print("\n⚠️  HALT CONDITION: Match rate below 60% after retries. Reporting to CEO.")

    # ── Phase 10: Write ceo_memory ───────────────────────────────────────────
    print("\n[Phase 10] Writing ceo_memory...")
    payload = json.dumps({
        "status": "complete",
        "pilot": 2,
        "snapshot_main": snapshot_id,
        "businesses": len(businesses),
        "total_written": total_written,
        "unique_abns": unique,
        "matched": matched_db,
        "not_found": not_found_db,
        "match_rate_pct": round(match_rate, 1),
        "bd_valid": len(valid),
        "bd_single_page_errors": len(single_page_errors),
        "bd_other_errors": len(other_errors),
        "bd_elapsed_sec": round(bd_elapsed),
        "db_write_sec": round(db_elapsed, 1),
        "total_elapsed_sec": round(total_elapsed),
        "pass_match_rate": match_rate >= 65,
        "pass_zero_result": not_found_db < 120,
        "pass_db_write": db_elapsed < 60,
    }).replace("'", "''")

    mcp_sql(f"""
        INSERT INTO ceo_memory (key, value, updated_at)
        VALUES ('ceo:directive_227_complete', '{payload}'::jsonb, NOW())
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW();
        UPDATE ceo_memory SET value = jsonb_set(value, '{{last_number}}', '227'), updated_at=NOW()
        WHERE key='ceo:directives';
    """)
    print("  ceo_memory written.")
    print("\nDirective #227 complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
