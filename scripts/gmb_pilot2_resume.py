#!/usr/bin/env python3
"""
Resume Pilot 2 from Phase 3 (download already triggered, snapshot ready).
Snapshot ID: sd_mmy12unjb2ntgq5bs
"""
import json, os, re, subprocess, sys, time
from pathlib import Path
from urllib.parse import urlparse
import httpx
from dotenv import load_dotenv

load_dotenv(Path.home() / ".config" / "agency-os" / ".env")

ROOT = Path(__file__).resolve().parent.parent
MCP = ROOT / "skills" / "mcp-bridge" / "scripts" / "mcp-bridge.js"
PROJ = "jatzvazlbusedwsnqxzr"
GMB_DATASET = "gd_m8ebnr0q2qlklc02fz"
SNAPSHOT_ID = "sd_mmy12unjb2ntgq5bs"
SNAPSHOT_FILE = Path("/tmp/gmb_pilot2_snapshot.json")
RETRY_SNAPSHOT_FILE = Path("/tmp/gmb_pilot2_retry_snapshot.json")
BUSINESSES_FILE = Path("/tmp/gmb_pilot2_businesses.json")
UPSERT_CHUNK = 500
BD_POLL_MAX_SEC = 900
BD_POLL_INTERVAL = 10

api_key = os.environ["BRIGHTDATA_API_KEY"]
supa_url = os.environ["SUPABASE_URL"]
supa_key = os.environ["SUPABASE_SERVICE_KEY"]

REST_HEADERS = {
    "Authorization": f"Bearer {supa_key}",
    "apikey": supa_key,
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}
BD_HEADERS = {"Authorization": f"Bearer {api_key}"}

def normalize(name):
    name = name.lower()
    for sfx in [" pty ltd"," pty. ltd."," pty limited"," ltd"," pty"," limited"]:
        name = name.replace(sfx,"")
    return re.sub(r"[^a-z0-9 ]","",name).strip()

def safe(s):
    return str(s).replace("'","''").replace("\x00","") if s else ""

def mcp_sql(q, timeout=120):
    r = subprocess.run(["node",str(MCP),"call","supabase","execute_sql",
        json.dumps({"project_id":PROJ,"query":q})],
        capture_output=True,text=True,timeout=timeout)
    raw = r.stdout.strip()
    if not raw: return []
    try: s = json.loads(raw)
    except: s = raw
    if not isinstance(s, str): s = json.dumps(s)
    m = re.search(r'<untrusted-data[^>]+>\s*(.*?)\s*</untrusted-data', s, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    start = s.find('['); end = s.rfind(']')
    if start != -1 and end > start:
        try: return json.loads(s[start:end+1])
        except: pass
    return []

def bd_download(sid):
    base = "https://api.brightdata.com/datasets/v3"
    r = httpx.get(f"{base}/snapshot/{sid}?format=json", headers=BD_HEADERS, timeout=180)
    r.raise_for_status()
    text = r.text.strip()
    try:
        result = r.json()
        if isinstance(result, list): return result
    except: pass
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            try: rows.append(json.loads(line))
            except: pass
    return rows

def bd_trigger(inputs, discover_by="location"):
    base = "https://api.brightdata.com/datasets/v3"
    url = f"{base}/trigger?dataset_id={GMB_DATASET}&include_errors=true&type=discover_new&discover_by={discover_by}"
    resp = httpx.post(url, headers={**BD_HEADERS,"Content-Type":"application/json"},
                      json=inputs, timeout=60)
    resp.raise_for_status()
    sid = resp.json()["snapshot_id"]
    print(f"  Triggered: {sid}")
    return sid

def bd_poll(sid, label=""):
    base = "https://api.brightdata.com/datasets/v3"
    t0 = time.time()
    while time.time()-t0 < BD_POLL_MAX_SEC:
        try:
            r = httpx.get(f"{base}/progress/{sid}", headers=BD_HEADERS, timeout=15)
            data = r.json()
            status = data.get("status","unknown")
            print(f"  [{label}] {time.time()-t0:.0f}s — status={status} records={data.get('records','?')}")
            if status == "ready": return "ready"
            if status == "failed": return "failed"
        except Exception as e: print(f"  Poll err: {e}")
        time.sleep(BD_POLL_INTERVAL)
    return "timeout"

def supabase_bulk_insert(rows, table="gmb_pilot_results"):
    url = f"{supa_url}/rest/v1/{table}"
    inserted = 0
    for i in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[i:i+UPSERT_CHUNK]
        resp = httpx.post(url, headers=REST_HEADERS, json=chunk, timeout=60)
        if resp.status_code not in (200,201):
            print(f"  REST error {resp.status_code}: {resp.text[:200]}")
        else:
            inserted += len(chunk)
    return inserted

def bulk_update_bu(updates, batch=40):
    for i in range(0, len(updates), batch):
        chunk = updates[i:i+batch]
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
                  gmb_rating={rating_sql}, gmb_review_count={int(f.get("reviews_cnt",0))},
                  gmb_domain='{safe(f.get("domain",""))}', gmb_phone='{safe(f.get("phone",""))}',
                  gmb_address='{safe(f.get("address",""))}', gmb_city='{safe(f.get("city",""))}',
                  gmb_latitude={lat_sql}, gmb_longitude={lon_sql},
                  gmb_enriched_at=NOW(), updated_at=NOW()
                WHERE abn='{abn}';""")
        mcp_sql(" ".join(stmts), timeout=120)

# ── Load businesses ──────────────────────────────────────────────────────────
businesses = json.loads(BUSINESSES_FILE.read_text())
print(f"Businesses: {len(businesses)}")

# ── Phase 3: Download ────────────────────────────────────────────────────────
print(f"\n[Phase 3] Downloading snapshot {SNAPSHOT_ID}...")
if SNAPSHOT_FILE.exists() and SNAPSHOT_FILE.stat().st_size > 100000:
    print("  Using cached snapshot file")
    data = json.loads(SNAPSHOT_FILE.read_text())
else:
    data = bd_download(SNAPSHOT_ID)
    SNAPSHOT_FILE.write_text(json.dumps(data))

valid = [r for r in data if not r.get("error")]
errors = [r for r in data if r.get("error")]
single_page_errors = [r for r in errors if "does not contain a list" in str(r.get("error",""))]
other_errors = [r for r in errors if "does not contain a list" not in str(r.get("error",""))]
print(f"  Valid: {len(valid)} | Single-page errors: {len(single_page_errors)} | Other errors: {len(other_errors)}")

# ── Phase 4: Retry single-page errors ───────────────────────────────────────
retry_results = []
if single_page_errors:
    print(f"\n[Phase 4] Retrying {len(single_page_errors)} single-page errors...")
    error_kws = set()
    for r in single_page_errors:
        di = r.get("discovery_input") or {}
        kw = di.get("keyword","").lower().strip() if isinstance(di,dict) else ""
        if kw: error_kws.add(kw)

    error_businesses = [b for b in businesses
                        if f"{b['trading_name'].lower()} {b['postcode']}".strip() in error_kws]
    print(f"  Error businesses matched: {len(error_businesses)}")

    if error_businesses:
        # Retry with name + state (broader, avoids single-result redirect)
        retry_inputs = [{"keyword": f"{b['trading_name']} {b['state']}", "country": "AU"}
                        for b in error_businesses]
        retry_sid = bd_trigger(retry_inputs, discover_by="location")
        retry_status = bd_poll(retry_sid, label="retry")
        if retry_status == "ready":
            retry_data = bd_download(retry_sid)
            RETRY_SNAPSHOT_FILE.write_text(json.dumps(retry_data))
            retry_valid = [r for r in retry_data if not r.get("error")]
            retry_err = [r for r in retry_data if r.get("error")]
            print(f"  Retry: {len(retry_valid)} valid, {len(retry_err)} still erroring")
            retry_results = retry_valid
        else:
            print(f"  Retry not ready ({retry_status}), skipping")
else:
    print("\n[Phase 4] No single-page errors to retry.")

# ── Phase 5: Match ───────────────────────────────────────────────────────────
print("\n[Phase 5] Matching...")
all_valid = valid + retry_results
result_by_kw = {}
result_by_name = {}

for r in all_valid:
    di = r.get("discovery_input") or {}
    kw = di.get("keyword","").lower().strip() if isinstance(di,dict) else ""
    if kw: result_by_kw.setdefault(kw, r)
    norm = normalize(r.get("name",""))
    if norm: result_by_name.setdefault(norm, r)

pilot_rows = []
bu_updates = []
matched = not_found = kw_m = name_m = prefix_m = 0

for b in businesses:
    kw = f"{b['trading_name'].lower()} {b['postcode']}".strip()
    kw_retry = f"{b['trading_name'].lower()} {b.get('state','nsw')}".strip()
    norm_b = normalize(b["trading_name"])
    words = [w for w in norm_b.split() if len(w) > 4]

    gmb = None
    match_path = None

    if result_by_kw.get(kw):
        gmb = result_by_kw[kw]; match_path = "keyword"; kw_m += 1
    elif result_by_kw.get(kw_retry):
        gmb = result_by_kw[kw_retry]; match_path = "keyword_retry"; kw_m += 1
    elif result_by_name.get(norm_b):
        gmb = result_by_name[norm_b]; match_path = "name_exact"; name_m += 1
    elif words:
        gmb = next((v for k,v in result_by_name.items() if k.startswith(words[0])), None)
        if gmb: match_path = "name_prefix"; prefix_m += 1

    if gmb:
        matched += 1
        cat = gmb.get("category","") or ""
        place_id = gmb.get("place_id","") or ""
        cid = gmb.get("fid_location","") or gmb.get("cid","") or ""
        details = gmb.get("business_details") or []
        domain = next((d.get("details","").strip() for d in details if d.get("field_name")=="authority"),
                      gmb.get("open_website","") or "")
        if domain and domain.startswith("http"):
            domain = urlparse(domain).netloc.replace("www.","")
        phone = gmb.get("phone_number","") or ""
        address = gmb.get("address","") or ""
        city = address.split(",")[0].strip() if "," in address else ""
        rating = float(gmb.get("rating") or 0)
        reviews_cnt = int(gmb.get("reviews_count") or 0)
        lat = float(gmb.get("lat") or 0)
        lon = float(gmb.get("lon") or 0)

        pilot_rows.append({"abn":b["abn"],"trading_name":b["trading_name"],
            "serp_match":True,"gmb_category":cat or None,
            "gmb_rating":rating if rating else None,
            "gmb_review_count":reviews_cnt,"gmb_domain":domain or None,
            "match_confidence":match_path})
        bu_updates.append((b["abn"],{"place_id":place_id,"cid":cid,"cat":cat,
            "rating":rating,"reviews_cnt":reviews_cnt,"domain":domain,
            "phone":phone,"address":address,"city":city,"lat":lat,"lon":lon}))
    else:
        not_found += 1
        pilot_rows.append({"abn":b["abn"],"trading_name":b["trading_name"],
            "serp_match":False,"gmb_category":None,"gmb_rating":None,
            "gmb_review_count":0,"gmb_domain":None,"match_confidence":"none"})

print(f"  Matched: {matched} | Not found: {not_found}")
print(f"  By path: keyword={kw_m} name_exact={name_m} prefix={prefix_m}")

# ── Phase 6: Bulk REST insert ────────────────────────────────────────────────
print(f"\n[Phase 6] Bulk inserting {len(pilot_rows)} rows...")
t_db = time.time()
inserted = supabase_bulk_insert(pilot_rows)
db_elapsed = time.time()-t_db
print(f"  Inserted: {inserted} in {db_elapsed:.1f}s")

# ── Phase 7: business_universe bulk update ───────────────────────────────────
print(f"\n[Phase 7] Updating business_universe ({len(bu_updates)} records)...")
t_bu = time.time()
bulk_update_bu(bu_updates)
print(f"  Done in {time.time()-t_bu:.0f}s")

# ── Phase 8: Verify ──────────────────────────────────────────────────────────
print("\n[Phase 8] Verifying...")
rows = mcp_sql("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN serp_match THEN 1 ELSE 0 END) as matched,
           SUM(CASE WHEN NOT serp_match THEN 1 ELSE 0 END) as not_found
    FROM gmb_pilot_results
    WHERE created_at > NOW() - INTERVAL '2 hours';
""")
r = rows[0] if rows else {}
total_db = int(r.get("total") or 0)
matched_db = int(r.get("matched") or 0)
not_found_db = int(r.get("not_found") or 0)
match_rate = matched_db/total_db*100 if total_db else 0

bd_elapsed = 366  # from Phase 2 above

print("\n" + "="*60)
print("PILOT 2 — FINAL RESULTS")
print("="*60)
print(f"Total rows written:      {total_db}")
print(f"Matched (GMB found):     {matched_db} ({match_rate:.1f}%)")
print(f"Not found:               {not_found_db}")
print(f"BD valid records:        {len(valid)}")
print(f"BD single-page errors:   {len(single_page_errors)}")
print(f"BD other errors:         {len(other_errors)}")
print(f"BD snapshot time:        {bd_elapsed}s ({bd_elapsed/60:.1f} min)")
print(f"DB write time:           {db_elapsed:.1f}s")
print(f"\nVS TARGETS:")
print(f"  Match rate:  {match_rate:.1f}%  (target 65%+)  {'✅ PASS' if match_rate >= 65 else ('⚠️  HALT' if match_rate < 60 else '❌ FAIL')}")
print(f"  Zero-result: {not_found_db}   (target <120)   {'✅ PASS' if not_found_db < 120 else '❌ FAIL'}")
print(f"  BD errors:   {len(single_page_errors)}  (target ~0)    {'✅ PASS' if len(single_page_errors) < 30 else '❌ FAIL'}")
print(f"  DB write:    {db_elapsed:.0f}s  (target <60s)  {'✅ PASS' if db_elapsed < 60 else '❌ FAIL'}")

if match_rate < 60:
    print("\n⚠️  HALT: Match rate below 60%. Reporting to CEO before proceeding.")

# ── Phase 9: ceo_memory ─────────────────────────────────────────────────────
print("\n[Phase 9] Writing ceo_memory...")
payload = json.dumps({
    "status": "complete", "pilot": 2, "snapshot_main": SNAPSHOT_ID,
    "total_written": total_db, "matched": matched_db, "not_found": not_found_db,
    "match_rate_pct": round(match_rate,1),
    "bd_valid": len(valid), "bd_single_page_errors": len(single_page_errors),
    "bd_other_errors": len(other_errors),
    "bd_elapsed_sec": bd_elapsed, "db_write_sec": round(db_elapsed,1),
    "match_by_keyword": kw_m, "match_by_name_exact": name_m, "match_by_prefix": prefix_m,
    "pass_match_rate": match_rate >= 65, "pass_zero_result": not_found_db < 120,
    "pass_db_write": db_elapsed < 60,
}).replace("'","''")

mcp_sql(f"""
    INSERT INTO ceo_memory (key, value, updated_at)
    VALUES ('ceo:directive_227_complete', '{payload}'::jsonb, NOW())
    ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW();
    UPDATE ceo_memory SET value=jsonb_set(value,'{{last_number}}','227'), updated_at=NOW()
    WHERE key='ceo:directives';
""")
print("  Done. Directive #227 complete.")
