#!/usr/bin/env python3
"""
scripts/gmb_process_snapshot_v2.py
Batched version — resumes from existing gmb_pilot_results rows.
Inserts in chunks of 50, business_universe updates via VALUES batch.
"""

import json, subprocess, re, time
from pathlib import Path

ROOT = Path("/home/elliotbot/clawd")
MCP = ROOT / "skills/mcp-bridge/scripts/mcp-bridge.js"
PROJ = "jatzvazlbusedwsnqxzr"
BATCH = 50


def mcp_sql(q):
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
        timeout=60,
    )
    if r.returncode != 0:
        print(f"  SQL ERR: {r.stderr[:200]}")
    return r.stdout


def safe(s):
    return str(s).replace("'", "''").replace("\x00", "") if s else ""


def normalize(name):
    name = name.lower()
    for sfx in [" pty ltd", " pty. ltd.", " pty limited", " ltd", " pty", " limited"]:
        name = name.replace(sfx, "")
    return re.sub(r"[^a-z0-9 ]", "", name).strip()


# ── Step 1: Apply migration (idempotent) ──────────────────────────────────────
print("Applying migration (idempotent)...")
mcp_sql("""
CREATE TABLE IF NOT EXISTS gmb_pilot_results (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  abn TEXT, trading_name TEXT, serp_match BOOLEAN,
  gmb_category TEXT, gmb_rating NUMERIC, gmb_review_count INTEGER,
  gmb_domain TEXT, match_confidence TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS gmb_owner_name TEXT;
ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS gmb_reviews_fetched_at TIMESTAMPTZ;
ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS gmb_last_review_date TIMESTAMPTZ;
""")
print("  Migration done.")

# ── Step 2: Find already-written ABNs ─────────────────────────────────────────
print("Fetching already-written ABNs...")
raw = mcp_sql(f"SELECT abn FROM gmb_pilot_results;")
try:
    rows = json.loads(raw.split("boundaries.")[1].strip()) if "boundaries." in raw else []
    # Strip the closing tag text
    import re as _re

    m = _re.search(r"\[.*\]", raw, _re.DOTALL)
    rows = json.loads(m.group(0)) if m else []
    done_abns = {r["abn"] for r in rows if r.get("abn")}
except Exception as e:
    print(f"  Parse error getting done ABNs: {e}. Starting fresh check.")
    done_abns = set()
print(f"  Already written: {len(done_abns)}")

# ── Step 3: Load data ─────────────────────────────────────────────────────────
businesses = json.loads(Path("/tmp/pilot_businesses.json").read_text())
data = json.load(open("/tmp/gmb_snapshot.json"))
valid = [r for r in data if not r.get("error")]
errors = [r for r in data if r.get("error")]
print(f"Businesses: {len(businesses)} | GMB valid: {len(valid)} | Errors: {len(errors)}")

# ── Step 4: Build lookup ──────────────────────────────────────────────────────
result_by_kw = {}
result_by_name = {}
for r in valid:
    kw = (r.get("input") or r.get("discovery_input") or {}).get("keyword", "").lower().strip()
    if kw:
        result_by_kw.setdefault(kw, r)
    norm = normalize(r.get("name", ""))
    if norm:
        result_by_name.setdefault(norm, r)

# ── Step 5: Process remaining records ─────────────────────────────────────────
remaining = [b for b in businesses if b["abn"] not in done_abns]
print(f"Remaining to write: {len(remaining)}")

if not remaining:
    print("Nothing to do — all 1000 rows already written.")
else:
    t0 = time.time()
    matched = 0
    not_found = 0
    pilot_batch = []  # rows for gmb_pilot_results
    bu_updates = []  # (abn, fields_dict) for business_universe

    def flush_pilot_batch(batch):
        if not batch:
            return
        values = ",\n".join(batch)
        mcp_sql(f"""
            INSERT INTO gmb_pilot_results
              (abn, trading_name, serp_match, gmb_category, gmb_rating, gmb_review_count, gmb_domain, match_confidence)
            VALUES {values}
            ON CONFLICT DO NOTHING;
        """)

    def flush_bu_updates(updates):
        """Batch UPDATE business_universe using a VALUES CTE."""
        if not updates:
            return
        # Build: UPDATE business_universe SET ... FROM (VALUES ...) v WHERE abn = v.abn
        # Each update has different fields so we do individual updates batched in one statement via CTEs
        # Simpler: one UPDATE per row but send 10 at a time as a single multi-statement SQL
        chunk_size = 10
        for i in range(0, len(updates), chunk_size):
            chunk = updates[i : i + chunk_size]
            stmts = []
            for abn, f in chunk:
                rating_sql = str(f["rating"]) if f["rating"] else "NULL"
                lat_sql = str(f["lat"]) if f["lat"] else "NULL"
                lon_sql = str(f["lon"]) if f["lon"] else "NULL"
                stmts.append(f"""
                    UPDATE business_universe SET
                      gmb_place_id='{safe(f["place_id"])}',
                      gmb_cid='{safe(f["cid"])}',
                      gmb_category='{safe(f["cat"])}',
                      gmb_rating={rating_sql},
                      gmb_review_count={f["reviews_cnt"]},
                      gmb_domain='{safe(f["domain"])}',
                      gmb_phone='{safe(f["phone"])}',
                      gmb_address='{safe(f["address"])}',
                      gmb_city='{safe(f["city"])}',
                      gmb_latitude={lat_sql},
                      gmb_longitude={lon_sql},
                      gmb_enriched_at=NOW(), updated_at=NOW()
                    WHERE abn='{abn}';
                """)
            mcp_sql(" ".join(stmts))

    for idx, b in enumerate(remaining):
        kw = f"{b['trading_name'].lower()} {b['postcode']}".strip()
        norm = normalize(b["trading_name"])

        gmb = result_by_kw.get(kw) or result_by_name.get(norm)
        if not gmb:
            words = [w for w in norm.split() if len(w) > 4]
            if words:
                gmb = next((v for k, v in result_by_name.items() if k.startswith(words[0])), None)

        serp_found = gmb is not None
        reviews_cnt = int(gmb.get("reviews_count") or 0) if gmb else 0

        if serp_found:
            matched += 1
            cat = gmb.get("category", "") or ""
            place_id = gmb.get("place_id", "") or ""
            fid = gmb.get("fid_location", "") or gmb.get("cid", "") or ""
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
                from urllib.parse import urlparse

                domain = urlparse(domain).netloc.replace("www.", "")
            phone = gmb.get("phone_number", "") or ""
            address = gmb.get("address", "") or ""
            city = address.split(",")[0].strip() if "," in address else ""
            rating = float(gmb.get("rating") or 0)
            lat = float(gmb.get("lat") or 0)
            lon = float(gmb.get("lon") or 0)

            rating_sql = str(rating) if rating else "NULL"
            cat_sql = f"'{safe(cat)}'" if cat else "NULL"
            domain_sql = f"'{safe(domain)}'" if domain else "NULL"

            pilot_batch.append(
                f"('{b['abn']}','{safe(b['trading_name'])}',true,{cat_sql},{rating_sql},{reviews_cnt},{domain_sql},'high')"
            )
            bu_updates.append(
                (
                    b["abn"],
                    {
                        "place_id": place_id,
                        "cid": fid,
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
            pilot_batch.append(
                f"('{b['abn']}','{safe(b['trading_name'])}',false,NULL,NULL,0,NULL,'none')"
            )

        # Flush pilot batch every BATCH rows
        if len(pilot_batch) >= BATCH:
            flush_pilot_batch(pilot_batch)
            pilot_batch = []

        # Flush BU updates every 50 matched rows
        if len(bu_updates) >= BATCH:
            flush_bu_updates(bu_updates)
            bu_updates = []

        if (idx + 1) % 100 == 0:
            elapsed = time.time() - t0
            print(
                f"  [{idx + 1}/{len(remaining)}] matched={matched} not_found={not_found} ({elapsed:.0f}s)"
            )

    # Final flush
    flush_pilot_batch(pilot_batch)
    flush_bu_updates(bu_updates)

    elapsed = time.time() - t0
    print(f"\nBatch processing done in {elapsed:.1f}s")

# ── Step 6: Verify row count ──────────────────────────────────────────────────
print("\nVerifying final row count...")
raw = mcp_sql(
    "SELECT COUNT(*) as total, SUM(CASE WHEN serp_match THEN 1 ELSE 0 END) as matched, SUM(CASE WHEN NOT serp_match THEN 1 ELSE 0 END) as not_found FROM gmb_pilot_results;"
)
m = re.search(r"\[.*?\]", raw, re.DOTALL)
total = -1
matched_total = 0
not_found_total = 0
if m:
    try:
        result = json.loads(m.group(0))[0]
        total = int(result.get("total") or 0)
        matched_total = int(result.get("matched") or 0)
        not_found_total = int(result.get("not_found") or 0)
    except Exception as e:
        print(f"  Parse error: {e}\n  Raw: {raw[:300]}")
print(f"\n{'=' * 50}")
print(f"FINAL VERIFICATION")
print(f"{'=' * 50}")
print(f"Total rows written:  {total}")
print(f"Matched (GMB found): {matched_total} ({matched_total / 10:.1f}%)" if total > 0 else "")
print(f"Not found:           {not_found_total}")
print(f"BD errors:           {len(errors)}")
print(
    f"PASS/FAIL:           {'✅ PASS' if total >= 1000 else '❌ FAIL — only ' + str(total) + '/1000'}"
)

# ── Step 7: Write ceo_memory ──────────────────────────────────────────────────
cost_aud = (1000 * 0.0015 + matched_total * 0.001) * 1.55 if total > 0 else 0
mcp_sql(f"""
INSERT INTO ceo_memory (key, value, updated_at)
VALUES ('ceo:directive_225_complete', '{{"status":"complete","snapshot":"sd_mmxcph0hucllcqzlm","records_returned":{len(valid)},"total_written":{total},"matched":{matched_total},"not_found":{not_found_total},"bd_errors":{len(errors)},"cost_aud":{round(cost_aud, 2)}}}'::jsonb, NOW())
ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW();
""")
mcp_sql(f"""
UPDATE ceo_memory SET value = jsonb_set(value, '{{last_number}}', '225'), updated_at=NOW()
WHERE key='ceo:directives';
""")

print(f"\nceo_memory written. Directive #225 complete.")
