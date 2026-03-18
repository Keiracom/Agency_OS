#!/usr/bin/env python3
"""
ABR Trading Names Loader — Directive #222
Downloads ABR bulk XML extract from data.gov.au, stream-parses,
bulk-inserts into trading_names table, updates business_universe.

Usage:
  python3 -u scripts/load_abr_names.py                 # Full load (both parts)
  python3 -u scripts/load_abr_names.py --dry-run        # First 1000 records, no DB writes
  python3 -u scripts/load_abr_names.py --part1-only     # Only Part 1
"""

import argparse
import os
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PART1_URL = (
    "https://data.gov.au/data/dataset/5bd7fcab-e315-42cb-8daf-50b7efc2027e"
    "/resource/0ae4d427-6fa8-4d40-8e76-c6909b5a071b/download/public_split_1_10.zip"
)
PART2_URL = (
    "https://data.gov.au/data/dataset/5bd7fcab-e315-42cb-8daf-50b7efc2027e"
    "/resource/635fcb95-7864-4509-9fa7-a62a6e32b62d/download/public_split_11_20.zip"
)

TMP_DIR = "/tmp/abr_names"
PART1_ZIP = "/tmp/abr_part1.zip"
PART2_ZIP = "/tmp/abr_part2.zip"

BATCH_SIZE = 10_000
PROGRESS_EVERY = 100_000
DRY_RUN_LIMIT = 1_000

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_connection():
    db_url = os.environ["DATABASE_URL"]
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(db_url)


INSERT_SQL = """
INSERT INTO trading_names (abn, name, name_type, state, postcode, is_active, registration_date)
VALUES %s
ON CONFLICT (abn, name, name_type) DO NOTHING
"""

# Bulk update business_universe.trading_name where NULL, using first TRD from trading_names
BU_UPDATE_TRADING_NAME_SQL = """
UPDATE business_universe bu
SET trading_name = tn.name
FROM (
    SELECT DISTINCT ON (abn) abn, name
    FROM trading_names
    WHERE name_type = 'TRD'
    ORDER BY abn, created_at
) tn
WHERE bu.abn = tn.abn
  AND bu.trading_name IS NULL
"""

# Bulk update business_universe.abr_business_names as array of all BN names per ABN
BU_UPDATE_BN_NAMES_SQL = """
UPDATE business_universe bu
SET abr_business_names = tn.names
FROM (
    SELECT abn, array_agg(name ORDER BY name) AS names
    FROM trading_names
    WHERE name_type = 'BN'
    GROUP BY abn
) tn
WHERE bu.abn = tn.abn
"""

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_zip(url: str, dest: str):
    print(f"[download] {url}", flush=True)
    print(f"           → {dest}", flush=True)
    os.makedirs(TMP_DIR, exist_ok=True)

    if os.path.exists(dest):
        size_mb = os.path.getsize(dest) / 1_048_576
        print(f"           Already exists ({size_mb:.1f} MB), skipping download.", flush=True)
        return

    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        last_print = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1_048_576):  # 1 MB chunks
                f.write(chunk)
                downloaded += len(chunk)
                if total and downloaded - last_print >= 50 * 1_048_576:
                    pct = downloaded / total * 100
                    print(f"           {downloaded/1_048_576:.0f} MB / {total/1_048_576:.0f} MB ({pct:.0f}%)", flush=True)
                    last_print = downloaded
    print(f"           Done. {downloaded/1_048_576:.1f} MB saved.", flush=True)


# ---------------------------------------------------------------------------
# XML parsing — streaming iterparse
# ---------------------------------------------------------------------------

def parse_text(element, tag):
    """Safely get text from child element."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def iter_abr_records(xml_fileobj):
    """
    Stream-parse ABR XML. Yields dicts:
      abn, is_active, reg_date, state, postcode,
      trd_names: [str, ...], bn_names: [str, ...]
    """
    context = ET.iterparse(xml_fileobj, events=("end",))
    for event, elem in context:
        if elem.tag != "ABR":
            continue

        abn_el = elem.find("ABN")
        if abn_el is None or not abn_el.text:
            elem.clear()
            continue
        abn = abn_el.text.strip().replace(" ", "")
        is_active = abn_el.get("status", "").upper() == "ACT"
        reg_date_str = abn_el.get("registrationDate", None)
        reg_date = None
        if reg_date_str:
            try:
                reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        addr = elem.find("MainBusinessPhysicalAddress")
        state = None
        postcode = None
        if addr is not None:
            state = parse_text(addr, "StateCode")
            postcode = parse_text(addr, "Postcode")

        trd_names = []
        bn_names = []

        for entity_tag in ("MainEntity", "OtherEntity"):
            for entity in elem.findall(entity_tag):
                for nin in entity.findall("NonIndividualName"):
                    name_type = nin.get("type", "").upper()
                    name_text = parse_text(nin, "NonIndividualNameText")
                    if not name_text:
                        continue
                    if name_type == "TRD":
                        trd_names.append(name_text)
                    elif name_type == "BN":
                        bn_names.append(name_text)

        if trd_names or bn_names:
            yield {
                "abn": abn,
                "is_active": is_active,
                "reg_date": reg_date,
                "state": state,
                "postcode": postcode,
                "trd_names": trd_names,
                "bn_names": bn_names,
            }

        elem.clear()


# ---------------------------------------------------------------------------
# Process one zip file — inserts trading_names only (no per-row BU updates)
# ---------------------------------------------------------------------------

def process_zip(zip_path: str, conn, dry_run: bool, dry_run_limit: int,
                counters: dict, sample_printed: int) -> int:
    """
    Process one zip file. Returns updated sample_printed count.
    counters keys: abns, trd, bn
    Business_universe is updated in a separate bulk pass after all inserts.
    """
    print(f"\n[process] Opening {zip_path}", flush=True)
    cur = conn.cursor() if conn else None

    batch = []

    def flush_batch():
        nonlocal batch
        if not batch or not conn:
            batch = []
            return
        psycopg2.extras.execute_values(cur, INSERT_SQL, batch, page_size=BATCH_SIZE)
        conn.commit()
        batch = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        print(f"           Files in zip: {len(zf.namelist())} total, {len(xml_names)} XML", flush=True)

        for xml_name in xml_names:
            print(f"\n[parse]    {xml_name}", flush=True)
            with zf.open(xml_name) as xml_file:
                for rec in iter_abr_records(xml_file):
                    counters["abns"] += 1

                    if dry_run and counters["abns"] > dry_run_limit:
                        print(f"\n[dry-run]  Limit of {dry_run_limit} records reached — stopping.", flush=True)
                        flush_batch()
                        return sample_printed

                    abn = rec["abn"]
                    is_active = rec["is_active"]
                    reg_date = rec["reg_date"]
                    state = rec["state"]
                    postcode = rec["postcode"]

                    if dry_run and sample_printed < 10:
                        print(f"  ABN={abn} active={is_active} state={state} "
                              f"TRD={rec['trd_names'][:2]} BN={rec['bn_names'][:3]}", flush=True)
                        sample_printed += 1

                    for name in rec["trd_names"]:
                        batch.append((abn, name, "TRD", state, postcode, is_active, reg_date))
                        counters["trd"] += 1

                    for name in rec["bn_names"]:
                        batch.append((abn, name, "BN", state, postcode, is_active, reg_date))
                        counters["bn"] += 1

                    if counters["abns"] % PROGRESS_EVERY == 0:
                        flush_batch()  # commit current batch first
                        print(f"[progress] {counters['abns']:,} ABNs | "
                              f"TRD: {counters['trd']:,} | BN: {counters['bn']:,}", flush=True)

                    if len(batch) >= BATCH_SIZE:
                        flush_batch()
                        print(f"[batch]    {counters['abns']:,} ABNs processed | "
                              f"TRD: {counters['trd']:,} | BN: {counters['bn']:,}", flush=True)

    flush_batch()
    return sample_printed


# ---------------------------------------------------------------------------
# Bulk update business_universe after all inserts
# ---------------------------------------------------------------------------

def update_business_universe(conn):
    cur = conn.cursor()

    print("\n[bu-update] Updating business_universe.trading_name (NULL rows only)...", flush=True)
    t0 = time.time()
    cur.execute(BU_UPDATE_TRADING_NAME_SQL)
    trd_updated = cur.rowcount
    conn.commit()
    print(f"            trading_name updated: {trd_updated:,} rows ({time.time()-t0:.1f}s)", flush=True)

    print("[bu-update] Updating business_universe.abr_business_names...", flush=True)
    t0 = time.time()
    cur.execute(BU_UPDATE_BN_NAMES_SQL)
    bn_updated = cur.rowcount
    conn.commit()
    print(f"            abr_business_names updated: {bn_updated:,} rows ({time.time()-t0:.1f}s)", flush=True)

    cur.close()
    return trd_updated, bn_updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Load ABR trading names into Supabase")
    parser.add_argument("--dry-run", action="store_true",
                        help=f"Process first {DRY_RUN_LIMIT} records only, no DB writes")
    parser.add_argument("--part1-only", action="store_true",
                        help="Only process Part 1 of the ABR extract")
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60, flush=True)
        print("DRY RUN MODE — no database writes", flush=True)
        print("=" * 60, flush=True)

    parts = [(PART1_URL, PART1_ZIP)]
    if not args.part1_only:
        parts.append((PART2_URL, PART2_ZIP))

    # Download phase
    for url, dest in parts:
        download_zip(url, dest)

    # Connect
    conn = None
    if not args.dry_run:
        print("\n[db] Connecting to database...", flush=True)
        conn = get_connection()
        print("[db] Connected.", flush=True)

    counters = {"abns": 0, "trd": 0, "bn": 0}
    sample_printed = 0
    t0 = time.time()

    for _url, zip_path in parts:
        sample_printed = process_zip(
            zip_path, conn, args.dry_run, DRY_RUN_LIMIT,
            counters, sample_printed
        )
        if args.dry_run and counters["abns"] >= DRY_RUN_LIMIT:
            break

    # Bulk BU update after all trading_names are loaded
    bu_trd = 0
    bu_bn = 0
    if conn and not args.dry_run:
        bu_trd, bu_bn = update_business_universe(conn)

    if conn:
        conn.close()

    elapsed = time.time() - t0
    print("\n" + "=" * 60, flush=True)
    print("SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print(f"  ABNs processed:          {counters['abns']:>12,}", flush=True)
    print(f"  TRD names found:         {counters['trd']:>12,}", flush=True)
    print(f"  BN names found:          {counters['bn']:>12,}", flush=True)
    print(f"  Total rows queued:       {counters['trd'] + counters['bn']:>12,}", flush=True)
    print(f"  BU trading_name updated: {bu_trd:>12,}", flush=True)
    print(f"  BU bn_names updated:     {bu_bn:>12,}", flush=True)
    print(f"  Elapsed:                 {elapsed:.1f}s ({elapsed/60:.1f} min)", flush=True)
    if args.dry_run:
        print("\n  [DRY RUN] No data written to database.", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
