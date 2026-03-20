#!/usr/bin/env python3
"""
scripts/gmb_pilot3.py — Directive #229: GMB Pilot 3

Pre-flight fixes vs Pilot 2:
  1. Name exclusion filter expanded: NOMINEES, CUSTODIANS, PASTORAL, FUNDS MANAGEMENT,
     SUPER FUND, FUNDRAISING, PROPERTIES, FINANCE (personal-name combos) added to SQL WHERE
  2. PTR personal-name partnership pre-filter added to SQL WHERE
  3. &/AND normalisation in name matching (& → AND before strip)
  4. Legal suffix stripping in BD keyword construction
  5. BD retry correctly reads input.keyword (not discovery_input.keyword) for error records
  6. 30s wait after BD "ready" before download (avoids assembly-lag partial downloads)

Usage:
  python3 scripts/gmb_pilot3.py [--dry-run]
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
SNAPSHOT_FILE = Path("/tmp/gmb_pilot3_snapshot.json")
RETRY_SNAPSHOT_FILE = Path("/tmp/gmb_pilot3_retry_snapshot.json")
BUSINESSES_FILE = Path("/tmp/gmb_pilot3_businesses.json")

BD_POLL_MAX_SEC = 1200  # 20 minutes
BD_POLL_INTERVAL = 10
BD_READY_WAIT_SEC = 30  # Fix #6: wait after "ready" before downloading
UPSERT_CHUNK = 500

# Legal suffixes to strip from BD keywords (Fix #4)
LEGAL_SUFFIX_RE = re.compile(
    r"\s+(?:pty\.?\s+ltd\.?|pty\.?\s+limited|pty|p\/l|limited|ltd\.?)$",
    re.IGNORECASE,
)

# Apostrophes and special chars to strip from keyword
KEYWORD_CLEAN_RE = re.compile(r"[''`]")

# PTR business indicator words (matches load_business_universe.py FILTER 8)
PTR_INDICATOR_RE = re.compile(
    r"\b(pty|ltd|services|group|agency|studio|media|digital|marketing|consulting|solutions|"
    r"advisory|associates|partners|enterprises|industries|technology|technologies|"
    r"logistics|transport|construction|engineering|training|education)\b",
    re.IGNORECASE,
)

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
    try:
        s = json.loads(raw)
        if not isinstance(s, str):
            s = json.dumps(s)
    except Exception:
        s = raw

    m = re.search(r'<untrusted-data[^>]+>\s*(.*?)\s*</untrusted-data', s, re.DOTALL)
    if m:
        content = m.group(1).strip()
        try:
            return json.loads(content)
        except Exception:
            pass

    start = s.find('[')
    end = s.rfind(']')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(s[start:end + 1])
        except Exception:
            pass
    return []


def normalize(name):
    """Normalise business name for matching. Fix #3: & → AND before stripping."""
    name = name.lower()
    # Fix #3: normalise ampersand before stripping punctuation
    name = name.replace("&", "and")
    # Strip legal suffixes
    for sfx in [" pty ltd", " pty. ltd.", " pty limited", " pty. limited", " limited", " ltd", " pty", " p/l"]:
        name = name.replace(sfx, "")
    # Strip all non-alphanumeric (except spaces)
    return re.sub(r"[^a-z0-9 ]", "", name).strip()


def strip_legal_suffix(name):
    """Strip legal entity suffixes from a business name for keyword construction (Fix #4)."""
    cleaned = KEYWORD_CLEAN_RE.sub("", name).strip()
    cleaned = LEGAL_SUFFIX_RE.sub("", cleaned).strip()
    return cleaned


def safe(s):
    return str(s).replace("'", "''").replace("\x00", "") if s else ""


def supabase_bulk_upsert(rows, table="gmb_pilot_results"):
    """Bulk upsert via Supabase REST API in chunks."""
    url = f"{os.environ['SUPABASE_URL']}/rest/v1/{table}?on_conflict=abn"
    headers = {
        "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}",
        "apikey": os.environ['SUPABASE_SERVICE_KEY'],
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    inserted = 0
    for i in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[i:i + UPSERT_CHUNK]
        resp = httpx.post(url, headers=headers, json=chunk, timeout=60)
        if resp.status_code not in (200, 201):
            print(f"  REST upsert error {resp.status_code}: {resp.text[:200]}")
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
    """Poll until ready or timeout. Returns (status, records_count)."""
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
    print(f"  TIMEOUT after {BD_POLL_MAX_SEC}s — last status: {last_status}")
    return "timeout", 0


def bd_download(api_key, snapshot_id):
    """Download snapshot results. Fix #6: caller must wait 30s after 'ready' before calling."""
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
    # NDJSON fallback
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
    """Bulk UPDATE business_universe. updates = list of (abn, fields_dict)."""
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

    print("\n" + "=" * 60)
    print(f"GMB PILOT 3 — Directive #229 {'[DRY RUN]' if dry_run else ''}")
    print("=" * 60)

    # ── Phase 0: Select 1,000 fresh businesses ───────────────────────────────
    print("\n[Phase 0] Selecting businesses...")
    supa_key = os.environ["SUPABASE_SERVICE_KEY"]

    # Expanded exclusion SQL (Part A fixes #1 and #2)
    # Excludes: Pilot 1 + Pilot 2 ABNs, CUT entity, all new name patterns, PTR personal-name
    selection_sql = r"""
        SELECT abn, trading_name, state, postcode
        FROM business_universe
        WHERE abn NOT IN (SELECT abn FROM gmb_pilot_results)
          AND state = 'NSW'
          AND entity_type_code != 'CUT'
          -- Original shell filters
          AND trading_name NOT ILIKE '%HOLDINGS%'
          AND trading_name NOT ILIKE '%INVESTMENTS%'
          AND trading_name NOT ILIKE '%CAPITAL%'
          AND trading_name NOT ILIKE '%VENTURES%'
          AND trading_name NOT ILIKE '%ENTERPRISES%'
          AND trading_name NOT ILIKE '%MANAGEMENT CO%'
          AND trading_name !~ 'ACN[[:space:]]+[0-9]+'
          -- Directive #229 Part A: new name exclusions
          AND trading_name NOT ILIKE '%NOMINEES%'
          AND trading_name NOT ILIKE '%CUSTODIANS%'
          AND trading_name NOT ILIKE '%PASTORAL%'
          AND trading_name NOT ILIKE '%FUNDS MANAGEMENT%'
          AND trading_name NOT ILIKE '%SUPER FUND%'
          AND trading_name NOT ILIKE '%FUNDRAISING%'
          AND trading_name NOT ILIKE '%PROPERTIES%'
          -- FINANCE: exclude when paired with a personal name (no other business word)
          AND NOT (
            trading_name ILIKE '%FINANCE%'
            AND trading_name !~* '(services|solutions|consulting|group|partners|management|capital|advisory)'
            AND trading_name ~* '^[A-Za-z]+(\s+(and|&)\s+[A-Za-z]+)?\s+[A-Za-z]+\s+finance'
          )
          -- Directive #229 Part A: PTR personal-name partnerships
          AND NOT (
            entity_type_code = 'PTR'
            AND trading_name !~* '(pty|ltd|services|group|agency|studio|media|digital|marketing|consulting|solutions|advisory|associates|partners|enterprises|industries|technology|technologies|logistics|transport|construction|engineering|training|education)'
          )
        ORDER BY RANDOM()
        LIMIT 1000
    """

    mgmt_resp = httpx.post(
        f"https://api.supabase.com/v1/projects/{PROJ}/database/query",
        headers={
            "Authorization": f"Bearer {os.environ.get('SUPABASE_ACCESS_TOKEN', supa_key)}",
            "Content-Type": "application/json",
        },
        json={"query": selection_sql},
        timeout=30,
    )
    if mgmt_resp.status_code in (200, 201):
        businesses = mgmt_resp.json()
        if not isinstance(businesses, list):
            businesses = businesses.get("result", businesses.get("data", []))
    else:
        print(f"  Supabase management API error {mgmt_resp.status_code}: {mgmt_resp.text[:200]}")
        sys.exit(1)

    print(f"  Selected: {len(businesses)} businesses")

    if len(businesses) < 1000:
        print(f"  WARNING: Only {len(businesses)} available (expected 1000)")
        if len(businesses) < 500:
            print("  CRITICAL: Insufficient businesses. Halting.")
            sys.exit(1)

    if dry_run:
        print("  Sample (first 10):")
        for b in businesses[:10]:
            print(f"    {b['abn']} | {b['trading_name']} | {b.get('postcode','?')}")
        # Validate legal suffix stripping on the sample
        print("\n  Keyword construction check (first 10):")
        for b in businesses[:10]:
            raw = b['trading_name']
            stripped = strip_legal_suffix(raw)
            kw = f"{stripped} {b.get('postcode','')}"
            if stripped != raw:
                print(f"    '{raw}' → '{kw}'")
            else:
                print(f"    '{raw}' (no change) → '{kw}'")
        print("\nDry run complete.")
        return

    BUSINESSES_FILE.write_text(json.dumps(businesses))
    print(f"  Saved to {BUSINESSES_FILE}")

    # ── Phase 1: Build BD inputs with legal suffix stripping ─────────────────
    print("\n[Phase 1] Building BD inputs (with legal suffix stripping)...")
    # Build keyword: strip legal suffixes, clean apostrophes, append postcode
    inputs = []
    for b in businesses:
        keyword_name = strip_legal_suffix(b["trading_name"])
        inputs.append({
            "keyword": f"{keyword_name} {b['postcode']}",
            "country": "AU",
            "lat": "",
        })
    print(f"  Built {len(inputs)} inputs")
    # Show suffix-stripping stats
    stripped_count = sum(
        1 for b in businesses
        if strip_legal_suffix(b["trading_name"]) != b["trading_name"]
    )
    print(f"  Legal suffixes stripped: {stripped_count}/{len(inputs)}")

    # ── Phase 2: Trigger BD snapshot ─────────────────────────────────────────
    print("\n[Phase 2] Triggering BD batch snapshot...")
    t_bd_start = time.time()
    snapshot_id = bd_trigger(api_key, inputs, discover_by="location")

    # ── Phase 3: Poll ─────────────────────────────────────────────────────────
    print(f"\n[Phase 3] Polling (max {BD_POLL_MAX_SEC}s)...")
    status, bd_records = bd_poll(api_key, snapshot_id, label="main")
    t_bd_end = time.time()
    bd_elapsed = t_bd_end - t_bd_start

    if status != "ready":
        print(f"  BD snapshot not ready (status={status}). Halting.")
        sys.exit(1)

    print(f"  BD complete in {bd_elapsed:.0f}s ({bd_records} records)")

    # Fix #6: Wait 30s after "ready" before downloading (avoids partial assembly)
    print(f"  Waiting {BD_READY_WAIT_SEC}s before download (assembly buffer)...")
    time.sleep(BD_READY_WAIT_SEC)

    # ── Phase 4: Download ─────────────────────────────────────────────────────
    print("\n[Phase 4] Downloading results...")
    data = bd_download(api_key, snapshot_id)
    SNAPSHOT_FILE.write_text(json.dumps(data))

    valid = [r for r in data if not r.get("error")]
    errors = [r for r in data if r.get("error")]
    single_page_errors = [r for r in errors if "does not contain a list" in str(r.get("error", ""))]
    other_errors = [r for r in errors if "does not contain a list" not in str(r.get("error", ""))]
    print(f"  Valid: {len(valid)} | Single-page errors: {len(single_page_errors)} | Other errors: {len(other_errors)}")

    # ── Phase 5: Retry single-page errors ────────────────────────────────────
    retry_results = []
    if single_page_errors:
        print(f"\n[Phase 5] Retrying {len(single_page_errors)} single-page errors...")

        # Fix #5: Error records have input.keyword (not discovery_input.keyword)
        # Build set of original keywords from error records
        error_kws = {}  # original_kw_lower → error record
        for r in single_page_errors:
            inp = r.get("input") or {}
            kw = inp.get("keyword", "").lower().strip() if isinstance(inp, dict) else ""
            if kw:
                error_kws[kw] = r

        # Map error keywords back to businesses by matching constructed keyword
        error_businesses = []
        for i, b in enumerate(businesses):
            keyword_name = strip_legal_suffix(b["trading_name"])
            kw_constructed = f"{keyword_name.lower()} {b['postcode']}".strip()
            if kw_constructed in error_kws:
                error_businesses.append(b)

        print(f"  Matched {len(error_businesses)} error businesses to retry")

        if error_businesses:
            # Retry with name+state keyword (broader, avoids direct-result redirect)
            retry_inputs = [
                {
                    "keyword": f"{strip_legal_suffix(b['trading_name'])} {b.get('state', 'NSW')}",
                    "country": "AU",
                    "lat": "",
                }
                for b in error_businesses
            ]
            t_retry_start = time.time()
            retry_sid = bd_trigger(api_key, retry_inputs, discover_by="location")
            retry_status, retry_records = bd_poll(api_key, retry_sid, label="retry")

            if retry_status == "ready":
                print(f"  Waiting {BD_READY_WAIT_SEC}s before retry download...")
                time.sleep(BD_READY_WAIT_SEC)
                retry_data = bd_download(api_key, retry_sid)
                RETRY_SNAPSHOT_FILE.write_text(json.dumps(retry_data))
                retry_valid = [r for r in retry_data if not r.get("error")]
                retry_err = [r for r in retry_data if r.get("error")]
                print(f"  Retry: {len(retry_valid)} valid, {len(retry_err)} errors")
                retry_results = retry_valid
            else:
                print(f"  Retry snapshot not ready (status={retry_status}). Skipping.")
    else:
        print("\n[Phase 5] No single-page errors — skipping retry.")

    # ── Phase 6: Match GMB results → ABNs ────────────────────────────────────
    print("\n[Phase 6] Matching GMB results to businesses...")

    # Build lookup indexes from ALL results (main valid + retry)
    all_valid = valid + retry_results
    result_by_kw = {}     # constructed_keyword_lower → first result
    result_by_name = {}   # normalized_name → result

    for r in all_valid:
        # Index by discovery_input.keyword (for valid/matched records)
        di = r.get("discovery_input") or {}
        kw = di.get("keyword", "").lower().strip() if isinstance(di, dict) else ""
        if kw:
            result_by_kw.setdefault(kw, r)
        # Index by normalized GMB name (Fix #3: normalize applies &→AND)
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

    for i, b in enumerate(businesses):
        keyword_name = strip_legal_suffix(b["trading_name"])
        kw_main = f"{keyword_name.lower()} {b['postcode']}".strip()
        kw_retry = f"{keyword_name.lower()} {b.get('state', 'nsw').lower()}".strip()
        # Fix #3: normalize both sides with &→AND
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
            # Prefix match: first significant word
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
    print(f"  By path: keyword={kw_matched} name_exact={name_exact_matched} prefix={prefix_matched}")

    # ── Phase 7: Bulk REST upsert to gmb_pilot_results ───────────────────────
    print(f"\n[Phase 7] Bulk upserting {len(pilot_rows)} rows to gmb_pilot_results...")
    t_db_start = time.time()
    inserted = supabase_bulk_upsert(pilot_rows, "gmb_pilot_results")
    t_db_end = time.time()
    db_elapsed = t_db_end - t_db_start
    print(f"  Inserted: {inserted} rows in {db_elapsed:.1f}s")

    # ── Phase 8: Bulk update business_universe ────────────────────────────────
    print(f"\n[Phase 8] Updating business_universe for {len(bu_updates)} matched businesses...")
    t_bu_start = time.time()
    bulk_update_business_universe(bu_updates)
    t_bu_elapsed = time.time() - t_bu_start
    print(f"  Done in {t_bu_elapsed:.0f}s")

    # ── Phase 9: Verify via direct Supabase count ─────────────────────────────
    print("\n[Phase 9] Verifying...")
    # Direct REST count (avoids MCP truncation)
    count_url = (
        f"{os.environ['SUPABASE_URL']}/rest/v1/gmb_pilot_results"
        f"?select=abn,serp_match&abn=in.({','.join(b['abn'] for b in businesses[:50])})"
    )
    # Use MCP for the count query (small result)
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
        # Fallback to in-memory counts
        total_written = len(pilot_rows)
        unique = total_written
        matched_db = matched
        not_found_db = not_found
        match_rate = matched / total_written * 100 if total_written else 0

    total_elapsed = time.time() - t_total

    # ── Phase 10: Report ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("GMB PILOT 3 — FINAL RESULTS")
    print("=" * 60)
    print(f"Total rows written:        {total_written}")
    print(f"Unique ABNs:               {unique}")
    print(f"Matched (GMB found):       {matched_db} ({match_rate:.1f}%)")
    print(f"Not found:                 {not_found_db}")
    print(f"BD valid records:          {len(valid)}")
    print(f"BD single-page errors:     {len(single_page_errors)}")
    print(f"BD retry newly matched:    {len(retry_results)}")
    print(f"BD snapshot time:          {bd_elapsed:.0f}s ({bd_elapsed / 60:.1f} min)")
    print(f"DB write time:             {db_elapsed:.1f}s")
    print(f"Total wall clock:          {total_elapsed:.0f}s ({total_elapsed / 60:.1f} min)")

    print("\nVS TARGETS (Pilot 2 → Pilot 3):")
    tgt_match = 72.0
    tgt_zero = 280
    tgt_filter = 0
    tgt_bd = 10 * 60
    tgt_db = 10.0
    tgt_total = 20 * 60

    def row(label, actual, pilot2, target, pass_fn):
        ok = "✅" if pass_fn(actual) else "❌"
        return f"  {label:<22} {str(pilot2):<12} {str(target):<12} {str(actual):<12} {ok}"

    print(row("Match rate", f"{match_rate:.1f}%", "63.2%", f"{tgt_match}%+",
              lambda v: float(v.rstrip("%")) >= tgt_match))
    print(row("Zero-result count", not_found_db, 368, f"<{tgt_zero}",
              lambda v: v < tgt_zero))
    print(row("BD errors (single-pg)", len(single_page_errors), 259, "~0",
              lambda v: v < 30))
    print(row("BD snapshot time", f"{bd_elapsed:.0f}s", "6.1 min", f"<{tgt_bd}s",
              lambda v: float(v.rstrip("s")) < tgt_bd))
    print(row("DB write time", f"{db_elapsed:.0f}s", "3.0s", f"<{tgt_db}s",
              lambda v: float(v.rstrip("s")) < tgt_db))
    print(row("Wall-clock total", f"{total_elapsed:.0f}s", "~45 min", f"<{tgt_total}s",
              lambda v: float(v.rstrip("s")) < tgt_total))

    if match_rate < 68:
        print(f"\n⚠️  HALT CONDITION: Match rate {match_rate:.1f}% < 68% threshold. Halting.")
        # Still write ceo_memory with halt status before exiting
        _write_ceo_memory(snapshot_id, businesses, total_written, unique,
                          matched_db, not_found_db, match_rate, valid, single_page_errors,
                          other_errors, bd_elapsed, db_elapsed, total_elapsed, halted=True)
        sys.exit(1)

    # ── Phase 11: Write ceo_memory ─────────────────────────────────────────
    _write_ceo_memory(snapshot_id, businesses, total_written, unique,
                      matched_db, not_found_db, match_rate, valid, single_page_errors,
                      other_errors, bd_elapsed, db_elapsed, total_elapsed, halted=False)

    print("\nDirective #229 complete.")


def _write_ceo_memory(snapshot_id, businesses, total_written, unique,
                      matched_db, not_found_db, match_rate, valid, single_page_errors,
                      other_errors, bd_elapsed, db_elapsed, total_elapsed, halted=False):
    print("\n[Phase 11] Writing ceo_memory...")
    payload = json.dumps({
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
    }).replace("'", "''")

    mcp_sql(f"""
        INSERT INTO ceo_memory (key, value, updated_at)
        VALUES ('ceo:directive_229_complete', '{payload}'::jsonb, NOW())
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW();
        UPDATE ceo_memory SET value = jsonb_set(value, '{{last_number}}', '229'), updated_at=NOW()
        WHERE key='ceo:directives';
    """)
    print("  ceo_memory written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
