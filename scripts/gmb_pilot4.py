#!/usr/bin/env python3
"""
scripts/gmb_pilot4.py — Directive #230: GMB Pilot 4

New vs Pilot 3:
  - COALESCE(trading_name, legal_name) fallback: targets the previously-excluded
    NULL trading_name cohort (~810k NSW businesses, now addressable)
  - WHERE trading_name IS NULL: explicitly selects from the new cohort only
  - Name exclusion filters applied to COALESCE result (not just trading_name)
  - 60s wait after BD "ready" before download (30s was insufficient in Pilot 2 retry)
  - All Pilot 3 fixes remain: &/AND normalisation, legal suffix stripping,
    input.keyword for retry, single-page error retry

Usage:
  python3 scripts/gmb_pilot4.py [--dry-run]
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
SNAPSHOT_FILE = Path("/tmp/gmb_pilot4_snapshot.json")
RETRY_SNAPSHOT_FILE = Path("/tmp/gmb_pilot4_retry_snapshot.json")
BUSINESSES_FILE = Path("/tmp/gmb_pilot4_businesses.json")

BD_POLL_MAX_SEC = 1200   # 20 minutes
BD_POLL_INTERVAL = 10
BD_READY_WAIT_SEC = 60   # 60s — 30s was insufficient (Pilot 2 retry finding)
UPSERT_CHUNK = 500

# Legal suffixes to strip from BD keywords
LEGAL_SUFFIX_RE = re.compile(
    r"\s+(?:pty\.?\s+ltd\.?|pty\.?\s+limited|pty|p\/l"
    r"|proprietary\s+limited|proprietary\s+ltd\.?"
    r"|limited|ltd\.?)$",
    re.IGNORECASE,
)
KEYWORD_CLEAN_RE = re.compile(r"[''`]")

# ── Helpers ──────────────────────────────────────────────────────────────────

def mcp_sql(q, timeout=120):
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
        try:
            return json.loads(m.group(1).strip())
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
    """Normalise business name. &/AND normalisation applied before punctuation strip."""
    name = name.lower()
    name = name.replace("&", "and")
    for sfx in [" pty ltd", " pty. ltd.", " pty limited", " pty. limited",
                " limited", " ltd", " pty", " p/l"]:
        name = name.replace(sfx, "")
    return re.sub(r"[^a-z0-9 ]", "", name).strip()


def strip_legal_suffix(name):
    """Strip legal entity suffixes for keyword construction."""
    cleaned = KEYWORD_CLEAN_RE.sub("", name).strip()
    return LEGAL_SUFFIX_RE.sub("", cleaned).strip()


def safe(s):
    return str(s).replace("'", "''").replace("\x00", "") if s else ""


def bd_download_safe(api_key, sid):
    """Download BD snapshot — handles both JSON array and NDJSON."""
    base = "https://api.brightdata.com/datasets/v3"
    headers = {"Authorization": f"Bearer {api_key}"}
    r = httpx.get(f"{base}/snapshot/{sid}?format=json", headers=headers, timeout=180)
    r.raise_for_status()
    text = r.text.strip()
    # Parse text ONCE (do not call r.json() twice — second call fails)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
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


def bd_trigger(api_key, inputs, discover_by="location"):
    base = "https://api.brightdata.com/datasets/v3"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{base}/trigger?dataset_id={GMB_DATASET}&include_errors=true&type=discover_new&discover_by={discover_by}"
    resp = httpx.post(url, headers=headers, json=inputs, timeout=60)
    resp.raise_for_status()
    sid = resp.json()["snapshot_id"]
    print(f"  Snapshot triggered: {sid}")
    return sid


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
                return "failed", 0
        except Exception as e:
            print(f"  Poll error: {e}")
        time.sleep(BD_POLL_INTERVAL)
    return "timeout", 0


def bulk_insert(rows, table="gmb_pilot_results"):
    """Plain INSERT (gmb_pilot_results has no unique constraint on abn)."""
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
        if resp.status_code in (200, 201):
            inserted += len(chunk)
            print(f"  Batch {i // UPSERT_CHUNK + 1}: {len(chunk)} rows OK")
        else:
            print(f"  INSERT error {resp.status_code}: {resp.text[:200]}")
    return inserted


def bulk_update_business_universe(updates, batch=40):
    for i in range(0, len(updates), batch):
        chunk = updates[i:i + batch]
        stmts = []
        for (abn, f) in chunk:
            rs = str(f["rating"]) if f.get("rating") else "NULL"
            ls = str(f["lat"]) if f.get("lat") else "NULL"
            los = str(f["lon"]) if f.get("lon") else "NULL"
            stmts.append(
                f"UPDATE business_universe SET "
                f"gmb_place_id='{safe(f.get('place_id',''))}', "
                f"gmb_cid='{safe(f.get('cid',''))}', "
                f"gmb_category='{safe(f.get('cat',''))}', "
                f"gmb_rating={rs}, "
                f"gmb_review_count={int(f.get('reviews_cnt', 0))}, "
                f"gmb_domain='{safe(f.get('domain',''))}', "
                f"gmb_phone='{safe(f.get('phone',''))}', "
                f"gmb_address='{safe(f.get('address',''))}', "
                f"gmb_city='{safe(f.get('city',''))}', "
                f"gmb_latitude={ls}, gmb_longitude={los}, "
                f"gmb_enriched_at=NOW(), updated_at=NOW() "
                f"WHERE abn='{abn}';"
            )
        mcp_sql(" ".join(stmts), timeout=120)


# ── Main ─────────────────────────────────────────────────────────────────────

def main(dry_run=False):
    from dotenv import load_dotenv
    load_dotenv(Path.home() / ".config" / "agency-os" / ".env")

    api_key = os.environ["BRIGHTDATA_API_KEY"]
    supa_key = os.environ["SUPABASE_SERVICE_KEY"]
    t_total = time.time()

    print("\n" + "=" * 60)
    print(f"GMB PILOT 4 — Directive #230 {'[DRY RUN]' if dry_run else ''}")
    print("=" * 60)
    print("Cohort: NULL trading_name businesses (COALESCE fix)")

    # ── Phase 0: Select 1,000 from NULL trading_name cohort ──────────────────
    print("\n[Phase 0] Selecting businesses (COALESCE cohort)...")

    # COALESCE fix: apply all name filters to COALESCE(trading_name, legal_name)
    # WHERE trading_name IS NULL: explicitly targets the new cohort
    selection_sql = r"""
        SELECT
            abn,
            COALESCE(trading_name, legal_name) AS trading_name,
            state,
            postcode
        FROM business_universe
        WHERE abn NOT IN (SELECT abn FROM gmb_pilot_results)
          AND state = 'NSW'
          AND trading_name IS NULL
          AND legal_name IS NOT NULL
          AND entity_type_code NOT IN ('CUT')
          AND entity_type_code = 'PRV'
          -- Apply all name exclusion filters to COALESCE result (= legal_name here)
          AND legal_name NOT ILIKE '%HOLDINGS%'
          AND legal_name NOT ILIKE '%INVESTMENTS%'
          AND legal_name NOT ILIKE '%CAPITAL%'
          AND legal_name NOT ILIKE '%VENTURES%'
          AND legal_name NOT ILIKE '%ENTERPRISES%'
          AND legal_name NOT ILIKE '%MANAGEMENT CO%'
          AND legal_name NOT ILIKE '%NOMINEES%'
          AND legal_name NOT ILIKE '%CUSTODIANS%'
          AND legal_name NOT ILIKE '%PASTORAL%'
          AND legal_name NOT ILIKE '%FUNDS MANAGEMENT%'
          AND legal_name NOT ILIKE '%SUPER FUND%'
          AND legal_name NOT ILIKE '%FUNDRAISING%'
          AND legal_name NOT ILIKE '%PROPERTIES%'
          AND legal_name !~ 'ACN[[:space:]]+[0-9]+'
          -- Exclude obvious numbered/shell holding companies
          AND legal_name !~ '^[A-Z]\s+(NO\.?\s*)?[0-9]+'
          -- Require at least one word with 3+ chars (filter out pure initials)
          AND legal_name ~ '[A-Za-z]{3}'
          -- PTR personal-name filter: entity_type_code = PRV already excludes PTR
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

    print(f"  Selected: {len(businesses)} businesses (NULL trading_name cohort)")
    if len(businesses) < 1000:
        print(f"  WARNING: Only {len(businesses)} available")
        if len(businesses) < 500:
            print("  CRITICAL: Insufficient pool. Halting.")
            sys.exit(1)

    if dry_run:
        print("  Sample (first 10):")
        for b in businesses[:10]:
            print(f"    {b['abn']} | {b['trading_name']} | {b.get('postcode','?')}")
        print("\n  Keyword construction (first 10 — showing legal suffix stripping):")
        for b in businesses[:10]:
            raw = b['trading_name']
            stripped = strip_legal_suffix(raw)
            kw = f"{stripped} {b.get('postcode', '')}"
            changed = " → STRIPPED" if stripped != raw else ""
            print(f"    '{raw}'{changed} → '{kw}'")
        print("\nDry run complete.")
        return

    BUSINESSES_FILE.write_text(json.dumps(businesses))
    print(f"  Saved to {BUSINESSES_FILE}")

    # ── Phase 1: Build BD inputs with legal suffix stripping ─────────────────
    print("\n[Phase 1] Building BD inputs...")
    inputs = []
    stripped_count = 0
    for b in businesses:
        kn = strip_legal_suffix(b["trading_name"])
        if kn != b["trading_name"]:
            stripped_count += 1
        inputs.append({"keyword": f"{kn} {b['postcode']}", "country": "AU", "lat": ""})
    print(f"  Built {len(inputs)} inputs | Legal suffixes stripped: {stripped_count}/{len(inputs)}")

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
    print(f"  Waiting {BD_READY_WAIT_SEC}s before download (assembly buffer)...")
    time.sleep(BD_READY_WAIT_SEC)

    # ── Phase 4: Download ─────────────────────────────────────────────────────
    print("\n[Phase 4] Downloading results...")
    data = bd_download_safe(api_key, snapshot_id)
    SNAPSHOT_FILE.write_text(json.dumps(data))

    valid = [r for r in data if not r.get("error")]
    errors = [r for r in data if r.get("error")]
    single_page_errors = [r for r in errors if "does not contain a list" in str(r.get("error", ""))]
    other_errors = [r for r in errors if "does not contain a list" not in str(r.get("error", ""))]
    print(f"  Valid: {len(valid)} | Single-page errors: {len(single_page_errors)} | Other: {len(other_errors)}")

    # ── Phase 5: Retry single-page errors ────────────────────────────────────
    retry_results = []
    if single_page_errors:
        print(f"\n[Phase 5] Retrying {len(single_page_errors)} single-page errors...")

        # Error records: use input.keyword (not discovery_input.keyword)
        error_kws = {}
        for rec in single_page_errors:
            inp = rec.get("input") or {}
            kw = inp.get("keyword", "").lower().strip() if isinstance(inp, dict) else ""
            if kw:
                error_kws[kw] = rec

        error_businesses = []
        for b in businesses:
            kn = strip_legal_suffix(b["trading_name"])
            kw_c = f"{kn.lower()} {b['postcode']}".strip()
            if kw_c in error_kws:
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
                retry_data = bd_download_safe(api_key, retry_sid)
                RETRY_SNAPSHOT_FILE.write_text(json.dumps(retry_data))
                retry_valid = [r for r in retry_data if not r.get("error")]
                retry_err_count = len([r for r in retry_data if r.get("error")])
                print(f"  Retry: {len(retry_valid)} valid, {retry_err_count} errors")
                retry_results = retry_valid
            else:
                print(f"  Retry not ready (status={retry_status}). Skipping.")
    else:
        print("\n[Phase 5] No single-page errors — skipping retry.")

    # ── Phase 6: Match GMB results → ABNs ────────────────────────────────────
    print("\n[Phase 6] Matching GMB results to businesses...")

    all_valid = valid + retry_results
    result_by_kw = {}
    result_by_name = {}

    for rec in all_valid:
        di = rec.get("discovery_input") or {}
        kw = di.get("keyword", "").lower().strip() if isinstance(di, dict) else ""
        if kw:
            result_by_kw.setdefault(kw, rec)
        norm = normalize(rec.get("name", ""))
        if norm:
            result_by_name.setdefault(norm, rec)

    pilot_rows = []
    bu_updates = []
    matched = not_found = kw_m = name_m = prefix_m = 0

    for b in businesses:
        kn = strip_legal_suffix(b["trading_name"])
        kw_main = f"{kn.lower()} {b['postcode']}".strip()
        kw_retry = f"{kn.lower()} {b.get('state', 'nsw').lower()}".strip()
        norm_b = normalize(b["trading_name"])
        words = [w for w in norm_b.split() if len(w) > 4]

        gmb = None
        mp = None

        if result_by_kw.get(kw_main):
            gmb = result_by_kw[kw_main]; mp = "keyword"; kw_m += 1
        elif result_by_kw.get(kw_retry):
            gmb = result_by_kw[kw_retry]; mp = "keyword_retry"; kw_m += 1
        elif result_by_name.get(norm_b):
            gmb = result_by_name[norm_b]; mp = "name_exact"; name_m += 1
        elif words:
            gmb = next((v for k, v in result_by_name.items() if k.startswith(words[0])), None)
            if gmb:
                mp = "name_prefix"; prefix_m += 1

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
                "abn": b["abn"], "trading_name": b["trading_name"], "serp_match": True,
                "gmb_category": cat or None, "gmb_rating": rating if rating else None,
                "gmb_review_count": reviews_cnt, "gmb_domain": domain or None,
                "match_confidence": mp,
            })
            bu_updates.append((b["abn"], {
                "place_id": place_id, "cid": cid, "cat": cat, "rating": rating,
                "reviews_cnt": reviews_cnt, "domain": domain, "phone": phone,
                "address": address, "city": city, "lat": lat, "lon": lon,
            }))
        else:
            not_found += 1
            pilot_rows.append({
                "abn": b["abn"], "trading_name": b["trading_name"], "serp_match": False,
                "gmb_category": None, "gmb_rating": None, "gmb_review_count": 0,
                "gmb_domain": None, "match_confidence": "none",
            })

    print(f"  Matched: {matched} ({matched / 10:.1f}%) | Not found: {not_found}")
    print(f"  By path: keyword={kw_m} name_exact={name_m} prefix={prefix_m}")

    # ── Phase 7: Plain INSERT to gmb_pilot_results ────────────────────────────
    print(f"\n[Phase 7] Inserting {len(pilot_rows)} rows to gmb_pilot_results...")
    t_db = time.time()
    inserted = bulk_insert(pilot_rows)
    db_elapsed = time.time() - t_db
    print(f"  Inserted: {inserted} rows in {db_elapsed:.1f}s")

    # ── Phase 8: Update business_universe ─────────────────────────────────────
    print(f"\n[Phase 8] Updating business_universe ({len(bu_updates)} records)...")
    t_bu = time.time()
    bulk_update_business_universe(bu_updates)
    bu_elapsed = time.time() - t_bu
    print(f"  Done in {bu_elapsed:.0f}s")

    # ── Phase 9: Verify ────────────────────────────────────────────────────────
    print("\n[Phase 9] Verifying via REST count...")
    count_resp = httpx.get(
        f"{os.environ['SUPABASE_URL']}/rest/v1/gmb_pilot_results",
        params={"select": "abn,serp_match", "created_at": "gte.2026-03-20T02:50:00Z"},
        headers={
            "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}",
            "apikey": os.environ['SUPABASE_SERVICE_KEY'],
            "Prefer": "count=exact",
        },
        timeout=15,
    )
    cr = count_resp.headers.get("content-range", "")
    print(f"  Content-Range: {cr}")

    total_elapsed = time.time() - t_total
    match_rate = matched / len(pilot_rows) * 100 if pilot_rows else 0

    # ── Phase 10: Report ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("GMB PILOT 4 — FINAL RESULTS")
    print("=" * 60)
    print(f"Cohort:                    NULL trading_name (COALESCE fix)")
    print(f"Total rows:                {len(pilot_rows)}")
    print(f"Matched (GMB found):       {matched} ({match_rate:.1f}%)")
    print(f"Not found:                 {not_found}")
    print(f"BD valid:                  {len(valid)} | Errors: {len(single_page_errors)}")
    print(f"BD snapshot time:          {bd_elapsed:.0f}s ({bd_elapsed/60:.1f} min)")
    print(f"DB write time:             {db_elapsed:.1f}s")
    print(f"Total wall clock:          {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")

    print("\nVS TARGETS (Pilot 3 → Pilot 4):")
    print(f"  Match rate:   {match_rate:.1f}% (Pilot3: 73.9%, target 65%+)  {'✅' if match_rate >= 65 else '❌ HALT'}")
    print(f"  BD snapshot:  {bd_elapsed:.0f}s (target <600s)               {'✅' if bd_elapsed < 600 else '❌'}")
    print(f"  DB write:     {db_elapsed:.1f}s (target <10s)                {'✅' if db_elapsed < 10 else '❌'}")
    print(f"  Wall clock:   {total_elapsed:.0f}s (target <1200s)            {'✅' if total_elapsed < 1200 else '❌'}")

    if match_rate < 65:
        print(f"\n⚠️  HALT: Match rate {match_rate:.1f}% < 65% floor on new cohort.")
        _write_ceo_memory(snapshot_id, businesses, matched, not_found, match_rate,
                          valid, single_page_errors, other_errors, bd_elapsed, db_elapsed,
                          total_elapsed, halted=True)
        sys.exit(1)

    _write_ceo_memory(snapshot_id, businesses, matched, not_found, match_rate,
                      valid, single_page_errors, other_errors, bd_elapsed, db_elapsed,
                      total_elapsed, halted=False)
    print("\nDirective #230 complete.")


def _write_ceo_memory(snapshot_id, businesses, matched, not_found, match_rate,
                      valid, single_page_errors, other_errors, bd_elapsed, db_elapsed,
                      total_elapsed, halted=False):
    print("\n[Phase 11] Writing ceo_memory...")
    payload = json.dumps({
        "status": "halted" if halted else "complete",
        "pilot": 4,
        "cohort": "null_trading_name_coalesce",
        "snapshot_main": snapshot_id,
        "businesses": len(businesses),
        "matched": matched,
        "not_found": not_found,
        "match_rate_pct": round(match_rate, 1),
        "pass_match_rate": match_rate >= 65,
        "bd_valid": len(valid),
        "bd_single_page_errors": len(single_page_errors),
        "bd_elapsed_sec": round(bd_elapsed),
        "db_write_sec": round(db_elapsed, 1),
        "total_elapsed_sec": round(total_elapsed),
        "coalesce_fix_applied": True,
        "halted": halted,
    }).replace("'", "''")

    mcp_sql(f"""
        INSERT INTO ceo_memory (key, value, updated_at)
        VALUES ('ceo:directive_230_complete', '{payload}'::jsonb, NOW())
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW();
        UPDATE ceo_memory SET value=jsonb_set(value,'{{last_number}}','230'), updated_at=NOW()
        WHERE key='ceo:directives';
        INSERT INTO ceo_memory (key, value, updated_at)
        VALUES ('session_handoff_current', '{json.dumps({"updated": "2026-03-20", "last_directive": 230, "status": "complete" if not halted else "halted", "pilot_4_match_rate": round(match_rate,1), "coalesce_fix_validated": match_rate >= 65}).replace("'","''")}' ::jsonb, NOW())
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW();
    """)
    print("  ceo_memory written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
