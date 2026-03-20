#!/usr/bin/env python3
"""
scripts/gmb_process_snapshot.py
Process pre-downloaded GMB snapshot into DB.

Usage: python scripts/gmb_process_snapshot.py

Expects:
  /tmp/gmb_snapshot.json     — BD snapshot download (2,235 records)
  /tmp/pilot_businesses.json — 1,000 NSW businesses

Writes:
  gmb_pilot_results (1,000 rows)
  business_universe (UPDATE matched rows)
"""
import json, subprocess, re, time
from pathlib import Path

ROOT = Path("/home/elliotbot/clawd")
MCP = ROOT / "skills/mcp-bridge/scripts/mcp-bridge.js"
PROJ = "jatzvazlbusedwsnqxzr"

def mcp_sql(q):
    r = subprocess.run(
        ["node", str(MCP), "call", "supabase", "execute_sql",
         json.dumps({"project_id": PROJ, "query": q})],
        capture_output=True, text=True, timeout=30
    )
    return r.stdout

def safe(s):
    return str(s).replace("'","''").replace("\x00","") if s else ""

def normalize(name):
    name = name.lower()
    for sfx in [" pty ltd"," pty. ltd."," pty limited"," ltd"," pty"," limited"]:
        name = name.replace(sfx, "")
    return re.sub(r"[^a-z0-9 ]", "", name).strip()

# Apply migration
print("Applying migration...")
mcp_sql("""
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
""")
print("Done.")

# Load data
businesses = json.loads(Path("/tmp/pilot_businesses.json").read_text())
data = json.load(open("/tmp/gmb_snapshot.json"))
valid = [r for r in data if not r.get("error")]
errors = [r for r in data if r.get("error")]
print(f"Businesses: {len(businesses)} | GMB valid: {len(valid)} | Errors: {len(errors)}")

# Build lookup
result_by_kw = {}
result_by_name = {}
for r in valid:
    kw = (r.get("input") or r.get("discovery_input") or {}).get("keyword","").lower().strip()
    if kw:
        result_by_kw.setdefault(kw, r)
    norm = normalize(r.get("name",""))
    if norm:
        result_by_name.setdefault(norm, r)

matched, not_found = 0, 0
t0 = time.time()

for idx, b in enumerate(businesses):
    kw = f"{b['trading_name'].lower()} {b['postcode']}".strip()
    norm = normalize(b["trading_name"])

    gmb = result_by_kw.get(kw) or result_by_name.get(norm)
    if not gmb:
        words = [w for w in norm.split() if len(w) > 4]
        if words:
            gmb = next((v for k,v in result_by_name.items() if k.startswith(words[0])), None)

    serp_found = gmb is not None
    reviews_cnt = int(gmb.get("reviews_count") or 0) if gmb else 0

    if serp_found:
        matched += 1
        cat = gmb.get("category","") or ""
        place_id = gmb.get("place_id","") or ""
        fid = gmb.get("fid_location","") or gmb.get("cid","") or ""
        details = gmb.get("business_details") or []
        domain = next((d.get("details","").strip() for d in details if d.get("field_name")=="authority"), gmb.get("open_website","") or "")
        if domain and domain.startswith("http"):
            from urllib.parse import urlparse
            domain = urlparse(domain).netloc.replace("www.","")
        phone = gmb.get("phone_number","") or ""
        address = gmb.get("address","") or ""
        city = address.split(",")[0].strip() if "," in address else ""
        rating = float(gmb.get("rating") or 0)
        lat = float(gmb.get("lat") or 0)
        lon = float(gmb.get("lon") or 0)

        mcp_sql(f"""
            UPDATE business_universe SET
              gmb_place_id='{safe(place_id)}', gmb_cid='{safe(fid)}',
              gmb_category='{safe(cat)}',
              gmb_rating={rating if rating else 'NULL'},
              gmb_review_count={reviews_cnt},
              gmb_domain='{safe(domain)}', gmb_phone='{safe(phone)}',
              gmb_address='{safe(address)}', gmb_city='{safe(city)}',
              gmb_latitude={lat if lat else 'NULL'},
              gmb_longitude={lon if lon else 'NULL'},
              gmb_enriched_at=NOW(), updated_at=NOW()
            WHERE abn='{b["abn"]}';
        """)
        mcp_sql(f"""
            INSERT INTO gmb_pilot_results
              (abn, trading_name, serp_match, gmb_category, gmb_rating, gmb_review_count, gmb_domain, match_confidence)
            VALUES ('{b["abn"]}','{safe(b["trading_name"])}',true,
              {("'"+safe(cat)+"'") if cat else 'NULL'},
              {rating if rating else 'NULL'},{reviews_cnt},
              {("'"+safe(domain)+"'") if domain else 'NULL'},'high');
        """)
    else:
        not_found += 1
        mcp_sql(f"""
            INSERT INTO gmb_pilot_results
              (abn, trading_name, serp_match, gmb_review_count, match_confidence)
            VALUES ('{b["abn"]}','{safe(b["trading_name"])}',false,0,'none');
        """)

    if (idx+1) % 100 == 0:
        print(f"[{idx+1}/1000] matched={matched} not_found={not_found} ({time.time()-t0:.0f}s)")

elapsed = time.time() - t0
cost_aud = (1000*0.0015 + matched*0.001) * 1.55
print(f"\n{'='*50}")
print(f"Total:          1000")
print(f"Matched:        {matched} ({matched/10:.1f}%)")
print(f"Not found:      {not_found}")
print(f"BD errors:      {len(errors)}")
print(f"Processing:     {elapsed:.1f}s")
print(f"BD snapshot:    427s (7.1 min) — single batch")
print(f"Est. cost:      ${cost_aud:.2f} AUD")

# Save ceo_memory
mcp_sql(f"""INSERT INTO ceo_memory (key, value, updated_at)
VALUES ('ceo:directive_225_complete', '{{"status":"complete","snapshot":"sd_mmxcph0hucllcqzlm","records_returned":{len(valid)},"matched":{matched},"not_found":{not_found},"bd_errors":{len(errors)},"cost_aud":{round(cost_aud,2)},"wall_clock_bd_sec":427}}'::jsonb, NOW())
ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW();""")

print("ceo_memory written. Done.")
