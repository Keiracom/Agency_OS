#!/usr/bin/env python3
"""
gmb_pilot3_resume.py — Resume Pilot 3 from existing BD snapshot.

Called when the main pilot3.py process was SIGTERM'd after triggering the
BD snapshot but before polling/downloading. Reads businesses from the saved
file and picks up from polling.

Usage:
  python3 scripts/gmb_pilot3_resume.py --snapshot sd_mmy98ml8wv4vsf04o
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parent.parent
MCP = ROOT / "skills" / "mcp-bridge" / "scripts" / "mcp-bridge.js"
PROJ = "jatzvazlbusedwsnqxzr"
GMB_DATASET = "gd_m8ebnr0q2qlklc02fz"
BUSINESSES_FILE = Path("/tmp/gmb_pilot3_businesses.json")
SNAPSHOT_FILE = Path("/tmp/gmb_pilot3_snapshot.json")
RETRY_SNAPSHOT_FILE = Path("/tmp/gmb_pilot3_retry_snapshot.json")

BD_POLL_MAX_SEC = 1200
BD_POLL_INTERVAL = 10
BD_READY_WAIT_SEC = 30
UPSERT_CHUNK = 500

LEGAL_SUFFIX_RE = re.compile(
    r"\s+(?:pty\.?\s+ltd\.?|pty\.?\s+limited|pty|p\/l|limited|ltd\.?)$",
    re.IGNORECASE,
)
KEYWORD_CLEAN_RE = re.compile(r"[''`]")


def mcp_sql(q, timeout=60):
    r = subprocess.run(
        [
            "node",
            str(MCP),
            "call",
            "supabase",
            "execute_sql",
            json.dumps({"project_id": PROJ, "query": q}),
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    raw = r.stdout.strip()
    if not raw:
        return []
    try:
        s = json.loads(raw)
        if not isinstance(s, str):
            s = json.dumps(s)
    except Exception:
        s = raw
    m = re.search(r"<untrusted-data[^>]+>\s*(.*?)\s*</untrusted-data", s, re.DOTALL)
    if m:
        content = m.group(1).strip()
        try:
            return json.loads(content)
        except Exception:
            pass
    start = s.find("[")
    end = s.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(s[start : end + 1])
        except Exception:
            pass
    return []


def normalize(name):
    name = name.lower()
    name = name.replace("&", "and")
    for sfx in [
        " pty ltd",
        " pty. ltd.",
        " pty limited",
        " pty. limited",
        " limited",
        " ltd",
        " pty",
        " p/l",
    ]:
        name = name.replace(sfx, "")
    return re.sub(r"[^a-z0-9 ]", "", name).strip()


def strip_legal_suffix(name):
    cleaned = KEYWORD_CLEAN_RE.sub("", name).strip()
    return LEGAL_SUFFIX_RE.sub("", cleaned).strip()


def safe(s):
    return str(s).replace("'", "''").replace("\x00", "") if s else ""


def supabase_bulk_upsert(rows, table="gmb_pilot_results"):
    url = f"{os.environ['SUPABASE_URL']}/rest/v1/{table}?on_conflict=abn"
    headers = {
        "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}",
        "apikey": os.environ["SUPABASE_SERVICE_KEY"],
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    inserted = 0
    for i in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[i : i + UPSERT_CHUNK]
        resp = httpx.post(url, headers=headers, json=chunk, timeout=60)
        if resp.status_code not in (200, 201):
            print(f"  REST upsert error {resp.status_code}: {resp.text[:200]}")
        else:
            inserted += len(chunk)
    return inserted


def bd_poll(api_key, snapshot_id, label=""):
    base = "https://api.brightdata.com/datasets/v3"
    headers = {"Authorization": f"Bearer {api_key}"}
    t0 = time.time()
    last_status = "unknown"
    last_records = 0
    while time.time() - t0 < BD_POLL_MAX_SEC:
        elapsed = time.time() - t0
        try:
            r = httpx.get(f"{base}/progress/{snapshot_id}", headers=headers, timeout=15)
            data = r.json()
            last_status = data.get("status", "unknown")
            last_records = data.get("records", 0) or 0
            print(f"  [{label}] {elapsed:.0f}s — status={last_status} records={last_records}")
            if last_status == "ready":
                return "ready", last_records
            if last_status == "failed":
                print(f"  BD job failed: {data}")
                return "failed", 0
        except Exception as e:
            print(f"  Poll error: {e}")
        time.sleep(BD_POLL_INTERVAL)
    print(f"  TIMEOUT — last status: {last_status}")
    return "timeout", 0


def bd_trigger(api_key, inputs, discover_by="location"):
    base = "https://api.brightdata.com/datasets/v3"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{base}/trigger?dataset_id={GMB_DATASET}&include_errors=true&type=discover_new&discover_by={discover_by}"
    resp = httpx.post(url, headers=headers, json=inputs, timeout=60)
    resp.raise_for_status()
    sid = resp.json()["snapshot_id"]
    print(f"  Snapshot triggered: {sid}")
    return sid


def bd_download(api_key, snapshot_id):
    base = "https://api.brightdata.com/datasets/v3"
    headers = {"Authorization": f"Bearer {api_key}"}
    r = httpx.get(f"{base}/snapshot/{snapshot_id}?format=json", headers=headers, timeout=180)
    r.raise_for_status()
    text = r.text.strip()
    try:
        result = r.json()
        if isinstance(result, list):
            return result
    except Exception:
        pass
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
    for i in range(0, len(updates), batch):
        chunk = updates[i : i + batch]
        stmts = []
        for abn, f in chunk:
            rating_sql = str(f["rating"]) if f.get("rating") else "NULL"
            lat_sql = str(f["lat"]) if f.get("lat") else "NULL"
            lon_sql = str(f["lon"]) if f.get("lon") else "NULL"
            stmts.append(f"""
                UPDATE business_universe SET
                  gmb_place_id='{safe(f.get("place_id", ""))}',
                  gmb_cid='{safe(f.get("cid", ""))}',
                  gmb_category='{safe(f.get("cat", ""))}',
                  gmb_rating={rating_sql},
                  gmb_review_count={int(f.get("reviews_cnt", 0))},
                  gmb_domain='{safe(f.get("domain", ""))}',
                  gmb_phone='{safe(f.get("phone", ""))}',
                  gmb_address='{safe(f.get("address", ""))}',
                  gmb_city='{safe(f.get("city", ""))}',
                  gmb_latitude={lat_sql},
                  gmb_longitude={lon_sql},
                  gmb_enriched_at=NOW(), updated_at=NOW()
                WHERE abn='{abn}';
            """)
        mcp_sql(" ".join(stmts), timeout=120)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, help="BD snapshot ID to resume from")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(Path.home() / ".config" / "agency-os" / ".env")

    api_key = os.environ["BRIGHTDATA_API_KEY"]
    snapshot_id = args.snapshot
    t_total = time.time()

    print("\n" + "=" * 60)
    print(f"GMB PILOT 3 RESUME — snapshot {snapshot_id}")
    print("=" * 60)

    # Load businesses
    if not BUSINESSES_FILE.exists():
        print("ERROR: Businesses file not found. Cannot resume.")
        sys.exit(1)

    businesses = json.loads(BUSINESSES_FILE.read_text())
    print(f"\n[Step 0] Loaded {len(businesses)} businesses from {BUSINESSES_FILE}")

    # Poll until ready
    print(f"\n[Step 1] Polling snapshot {snapshot_id}...")
    t_bd_start = time.time()
    status, bd_records = bd_poll(api_key, snapshot_id, label="main")
    t_bd_end = time.time()
    bd_elapsed = t_bd_end - t_bd_start

    if status != "ready":
        print(f"  BD snapshot not ready (status={status}). Halting.")
        sys.exit(1)

    print(f"  BD complete in {bd_elapsed:.0f}s ({bd_records} records)")
    print(f"  Waiting {BD_READY_WAIT_SEC}s before download (assembly buffer)...")
    time.sleep(BD_READY_WAIT_SEC)

    # Download
    print("\n[Step 2] Downloading results...")
    data = bd_download(api_key, snapshot_id)
    SNAPSHOT_FILE.write_text(json.dumps(data))

    valid = [r for r in data if not r.get("error")]
    errors = [r for r in data if r.get("error")]
    single_page_errors = [r for r in errors if "does not contain a list" in str(r.get("error", ""))]
    other_errors = [r for r in errors if "does not contain a list" not in str(r.get("error", ""))]
    print(
        f"  Valid: {len(valid)} | Single-page errors: {len(single_page_errors)} | Other errors: {len(other_errors)}"
    )

    # Retry single-page errors
    retry_results = []
    if single_page_errors:
        print(f"\n[Step 3] Retrying {len(single_page_errors)} single-page errors...")

        # Fix: read input.keyword for error records
        error_kws = {}
        for r in single_page_errors:
            inp = r.get("input") or {}
            kw = inp.get("keyword", "").lower().strip() if isinstance(inp, dict) else ""
            if kw:
                error_kws[kw] = r

        error_businesses = []
        for b in businesses:
            keyword_name = strip_legal_suffix(b["trading_name"])
            kw_constructed = f"{keyword_name.lower()} {b['postcode']}".strip()
            if kw_constructed in error_kws:
                error_businesses.append(b)

        print(f"  Matched {len(error_businesses)} error businesses to retry")

        if error_businesses:
            retry_inputs = [
                {
                    "keyword": f"{strip_legal_suffix(b['trading_name'])} {b.get('state', 'NSW')}",
                    "country": "AU",
                    "lat": "",
                }
                for b in error_businesses
            ]
            retry_sid = bd_trigger(api_key, retry_inputs, discover_by="location")
            retry_status, _ = bd_poll(api_key, retry_sid, label="retry")

            if retry_status == "ready":
                print(f"  Waiting {BD_READY_WAIT_SEC}s before retry download...")
                time.sleep(BD_READY_WAIT_SEC)
                retry_data = bd_download(api_key, retry_sid)
                RETRY_SNAPSHOT_FILE.write_text(json.dumps(retry_data))
                retry_valid = [r for r in retry_data if not r.get("error")]
                retry_err_count = len([r for r in retry_data if r.get("error")])
                print(f"  Retry: {len(retry_valid)} valid, {retry_err_count} errors")
                retry_results = retry_valid
            else:
                print(f"  Retry snapshot not ready (status={retry_status}). Skipping.")
    else:
        print("\n[Step 3] No single-page errors — skipping retry.")

    # Match results → ABNs
    print("\n[Step 4] Matching GMB results to businesses...")

    all_valid = valid + retry_results
    result_by_kw = {}
    result_by_name = {}

    for r in all_valid:
        di = r.get("discovery_input") or {}
        kw = di.get("keyword", "").lower().strip() if isinstance(di, dict) else ""
        if kw:
            result_by_kw.setdefault(kw, r)
        norm = normalize(r.get("name", ""))
        if norm:
            result_by_name.setdefault(norm, r)

    pilot_rows = []
    bu_updates = []
    matched = 0
    not_found = 0
    kw_matched = 0
    name_exact_matched = 0
    prefix_matched = 0

    for b in businesses:
        keyword_name = strip_legal_suffix(b["trading_name"])
        kw_main = f"{keyword_name.lower()} {b['postcode']}".strip()
        kw_retry = f"{keyword_name.lower()} {b.get('state', 'nsw').lower()}".strip()
        norm_b = normalize(b["trading_name"])
        words = [w for w in norm_b.split() if len(w) > 4]

        gmb = None
        match_path = None

        if result_by_kw.get(kw_main):
            gmb = result_by_kw[kw_main]
            match_path = "keyword"
            kw_matched += 1
        elif result_by_kw.get(kw_retry):
            gmb = result_by_kw[kw_retry]
            match_path = "keyword_retry"
            kw_matched += 1
        elif result_by_name.get(norm_b):
            gmb = result_by_name[norm_b]
            match_path = "name_exact"
            name_exact_matched += 1
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
                (
                    d.get("details", "").strip()
                    for d in details
                    if d.get("field_name") == "authority"
                ),
                gmb.get("open_website", "") or "",
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

            pilot_rows.append(
                {
                    "abn": b["abn"],
                    "trading_name": b["trading_name"],
                    "serp_match": True,
                    "gmb_category": cat or None,
                    "gmb_rating": rating if rating else None,
                    "gmb_review_count": reviews_cnt,
                    "gmb_domain": domain or None,
                    "match_confidence": match_path,
                }
            )
            bu_updates.append(
                (
                    b["abn"],
                    {
                        "place_id": place_id,
                        "cid": cid,
                        "cat": cat,
                        "rating": rating,
                        "reviews_cnt": reviews_cnt,
                        "domain": domain,
                        "phone": phone,
                        "address": address,
                        "city": city,
                        "lat": lat,
                        "lon": lon,
                    },
                )
            )
        else:
            not_found += 1
            pilot_rows.append(
                {
                    "abn": b["abn"],
                    "trading_name": b["trading_name"],
                    "serp_match": False,
                    "gmb_category": None,
                    "gmb_rating": None,
                    "gmb_review_count": 0,
                    "gmb_domain": None,
                    "match_confidence": "none",
                }
            )

    print(f"  Matched: {matched} | Not found: {not_found}")
    print(
        f"  By path: keyword={kw_matched} name_exact={name_exact_matched} prefix={prefix_matched}"
    )

    # Bulk upsert to gmb_pilot_results
    print(f"\n[Step 5] Bulk upserting {len(pilot_rows)} rows to gmb_pilot_results...")
    t_db_start = time.time()
    inserted = supabase_bulk_upsert(pilot_rows, "gmb_pilot_results")
    t_db_end = time.time()
    db_elapsed = t_db_end - t_db_start
    print(f"  Inserted: {inserted} rows in {db_elapsed:.1f}s")

    # Update business_universe
    print(f"\n[Step 6] Updating business_universe for {len(bu_updates)} matched businesses...")
    t_bu_start = time.time()
    bulk_update_business_universe(bu_updates)
    t_bu_elapsed = time.time() - t_bu_start
    print(f"  Done in {t_bu_elapsed:.0f}s")

    # Verify
    print("\n[Step 7] Verifying...")
    rows = mcp_sql("""
        SELECT
          COUNT(*) AS total,
          COUNT(DISTINCT abn) AS unique_abns,
          SUM(CASE WHEN serp_match THEN 1 ELSE 0 END) AS matched,
          SUM(CASE WHEN NOT serp_match THEN 1 ELSE 0 END) AS not_found
        FROM gmb_pilot_results
        WHERE created_at > NOW() - INTERVAL '3 hours';
    """)
    if rows:
        r0 = rows[0]
        total_written = int(r0.get("total") or 0)
        unique = int(r0.get("unique_abns") or 0)
        matched_db = int(r0.get("matched") or 0)
        not_found_db = int(r0.get("not_found") or 0)
        match_rate = matched_db / total_written * 100 if total_written else 0
    else:
        total_written = len(pilot_rows)
        unique = total_written
        matched_db = matched
        not_found_db = not_found
        match_rate = matched / total_written * 100 if total_written else 0

    total_elapsed = time.time() - t_total

    # Report
    print("\n" + "=" * 60)
    print("GMB PILOT 3 — FINAL RESULTS")
    print("=" * 60)
    print(f"Total rows written:        {total_written}")
    print(f"Unique ABNs:               {unique}")
    print(f"Matched (GMB found):       {matched_db} ({match_rate:.1f}%)")
    print(f"Not found:                 {not_found_db}")
    print(f"BD valid records:          {len(valid)}")
    print(f"BD single-page errors:     {len(single_page_errors)}")
    print(f"BD retry matched:          {len(retry_results)}")
    print(f"BD snapshot time:          {bd_elapsed:.0f}s ({bd_elapsed / 60:.1f} min)")
    print(f"DB write time:             {db_elapsed:.1f}s")
    print(f"Total wall clock:          {total_elapsed:.0f}s ({total_elapsed / 60:.1f} min)")

    print("\nVS TARGETS (Pilot 2 → Pilot 3):")
    print(
        f"  Match rate:   {match_rate:.1f}%  (Pilot2: 63.2%, target 72%+)  {'✅' if match_rate >= 72 else '❌'}"
    )
    print(
        f"  Zero-result:  {not_found_db}    (Pilot2: 368, target <280)     {'✅' if not_found_db < 280 else '❌'}"
    )
    print(
        f"  BD errors:    {len(single_page_errors)}   (Pilot2: 259, target ~0)      {'✅' if len(single_page_errors) < 30 else '❌'}"
    )
    print(
        f"  DB write:     {db_elapsed:.0f}s   (target <10s)                {'✅' if db_elapsed < 10 else '❌'}"
    )
    print(
        f"  Wall clock:   {total_elapsed:.0f}s  (target <1200s)             {'✅' if total_elapsed < 1200 else '❌'}"
    )

    if match_rate < 68:
        print(f"\n⚠️  HALT: Match rate {match_rate:.1f}% < 68% threshold.")
        _write_ceo_memory(
            snapshot_id,
            businesses,
            total_written,
            unique,
            matched_db,
            not_found_db,
            match_rate,
            valid,
            single_page_errors,
            other_errors,
            bd_elapsed,
            db_elapsed,
            total_elapsed,
            halted=True,
        )
        sys.exit(1)

    _write_ceo_memory(
        snapshot_id,
        businesses,
        total_written,
        unique,
        matched_db,
        not_found_db,
        match_rate,
        valid,
        single_page_errors,
        other_errors,
        bd_elapsed,
        db_elapsed,
        total_elapsed,
        halted=False,
    )

    print("\nDirective #229 complete.")


def _write_ceo_memory(
    snapshot_id,
    businesses,
    total_written,
    unique,
    matched_db,
    not_found_db,
    match_rate,
    valid,
    single_page_errors,
    other_errors,
    bd_elapsed,
    db_elapsed,
    total_elapsed,
    halted=False,
):
    print("\n[Phase 11] Writing ceo_memory...")
    payload = json.dumps(
        {
            "status": "halted" if halted else "complete",
            "pilot": 3,
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
            "pass_match_rate": match_rate >= 72,
            "pass_zero_result": not_found_db < 280,
            "pass_db_write": db_elapsed < 10,
            "fixes_applied": [
                "name_exclusion_expanded",
                "ptr_personal_name_filter",
                "ampersand_and_normalisation",
                "legal_suffix_stripping",
                "retry_reads_input_keyword",
                "30s_ready_wait_before_download",
            ],
        }
    ).replace("'", "''")

    mcp_sql(f"""
        INSERT INTO ceo_memory (key, value, updated_at)
        VALUES ('ceo:directive_229_complete', '{payload}'::jsonb, NOW())
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW();
        UPDATE ceo_memory SET value = jsonb_set(value, '{{last_number}}', '229'), updated_at=NOW()
        WHERE key='ceo:directives';
    """)
    print("  ceo_memory written.")


if __name__ == "__main__":
    main()
