"""
Data recovery — backfill test enrichment outputs to business_universe + business_decision_makers.

Reads the Stage 5/6/7 test-cohort JSONs (300f/300g/300g_v2/300h/300i/300j) and merges them
into the live BU + DM tables using COALESCE semantics (never overwrite existing non-NULL).

Two earlier-cohort files referenced in the recovery brief — mini20_stage8.json and
cohort_run_20260415_103508/results.json — are absent from scripts/output/; they are
reported as MISSING and skipped (graceful degradation).

Defaults to --dry-run (counts only, no writes). Pass --execute to commit.

Usage:
  python scripts/backfill_test_data_to_bu.py            # dry-run
  python scripts/backfill_test_data_to_bu.py --execute  # write
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncpg
from src.config.settings import settings

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

SOURCE_FILES = {
    "300f_dm":          "300f_dm.json",
    "300g_email":       "300g_email.json",
    "300g_v2_email":    "300g_v2_email.json",
    "300h_mobile":      "300h_mobile.json",
    "300i_linkedin_co": "300i_linkedin_co.json",
    "300j_linkedin_dm": "300j_linkedin_dm.json",
}

OPTIONAL_LEGACY = [
    "mini20_stage8.json",
    "cohort_run_20260415_103508/results.json",
]

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PLACEHOLDER_LOCAL_PARTS = {"example", "admin", "info", "noreply", "no-reply", "test", "sample"}
AU_MOBILE_RE = re.compile(r"^(?:\+?614|04)\d{8}$")


def normalize_domain(d: str) -> str:
    if not d:
        return ""
    d = d.strip().lower()
    if d.startswith("www."):
        d = d[4:]
    return d


def valid_email(e):
    if not e or not isinstance(e, str):
        return False
    e = e.strip().lower()
    if not EMAIL_RE.match(e):
        return False
    local = e.split("@", 1)[0]
    if local in PLACEHOLDER_LOCAL_PARTS:
        return False
    return True


def valid_mobile(m):
    if not m or not isinstance(m, str):
        return False
    cleaned = re.sub(r"[\s\-()]", "", m)
    return bool(AU_MOBILE_RE.match(cleaned))


def normalize_mobile(m):
    cleaned = re.sub(r"[\s\-()]", "", m)
    if cleaned.startswith("04"):
        return "+61" + cleaned[1:]
    if cleaned.startswith("614"):
        return "+" + cleaned
    return cleaned


def load_sources():
    """Load each source JSON; return dict of source_name -> {domain: row}."""
    loaded = {}
    missing = []
    for name, fname in SOURCE_FILES.items():
        path = os.path.join(OUTPUT_DIR, fname)
        if not os.path.exists(path):
            missing.append(fname)
            loaded[name] = {}
            continue
        with open(path) as f:
            data = json.load(f)
        rows = data.get("domains", [])
        loaded[name] = {normalize_domain(r.get("domain", "")): r for r in rows if r.get("domain")}
    legacy_missing = [
        f for f in OPTIONAL_LEGACY
        if not os.path.exists(os.path.join(OUTPUT_DIR, f))
    ]
    return loaded, missing, legacy_missing


def merge_per_domain(sources):
    """Build a unified per-domain payload from the 6 sources."""
    all_domains = set()
    for src in sources.values():
        all_domains.update(src.keys())

    merged = {}
    for d in all_domains:
        if not d:
            continue
        f = sources["300f_dm"].get(d, {})
        g = sources["300g_email"].get(d, {})
        gv2 = sources["300g_v2_email"].get(d, {})
        h = sources["300h_mobile"].get(d, {})
        i_co = sources["300i_linkedin_co"].get(d, {})
        j_dm = sources["300j_linkedin_dm"].get(d, {})

        # Email — prefer g_v2 (later run), else g
        raw_email = (gv2.get("email") if gv2.get("email_found") else None) or \
                    (g.get("email") if g.get("email_found") else None)
        email = raw_email if valid_email(raw_email) else None
        email_verified = bool(gv2.get("email_verified") or g.get("email_verified")) if email else None
        email_source = gv2.get("email_source") or g.get("email_source") if email else None

        # Mobile — only h
        raw_mobile = h.get("mobile") if h.get("mobile_found") else None
        mobile = normalize_mobile(raw_mobile) if valid_mobile(raw_mobile or "") else None
        mobile_source = h.get("mobile_source") if mobile else None

        # DM identity — from f, supplemented by j_dm
        dm_name = f.get("dm_name") or j_dm.get("dm_name")
        dm_title = f.get("dm_title") or j_dm.get("dm_title")
        dm_linkedin = f.get("dm_linkedin_url") or j_dm.get("dm_linkedin_url")
        dm_source = f.get("dm_source")

        # LinkedIn company
        li_co_url = i_co.get("linkedin_company_url")
        li_co_data = i_co.get("data") or {}
        li_co_data = li_co_data if isinstance(li_co_data, dict) else {}

        # LinkedIn DM extra
        li_dm_data = j_dm.get("data") or {}
        li_dm_data = li_dm_data if isinstance(li_dm_data, dict) else {}

        # Skip if nothing usable
        if not any([email, mobile, dm_name, dm_linkedin, li_co_url, li_co_data, li_dm_data]):
            continue

        merged[d] = {
            "domain": d,
            "category": f.get("category") or g.get("category") or h.get("category"),
            "email": email,
            "email_verified": email_verified,
            "email_source": email_source,
            "mobile": mobile,
            "mobile_source": mobile_source,
            "dm_name": dm_name,
            "dm_title": dm_title,
            "dm_linkedin": dm_linkedin,
            "dm_source": dm_source,
            "intent_band": f.get("intent_band"),
            "intent_score": f.get("intent_score"),
            "linkedin_company_url": li_co_url,
            "company_followers": li_co_data.get("follower_count"),
            "company_about": li_co_data.get("description"),
            "company_specialties": li_co_data.get("specialties"),
            "li_dm_headline": li_dm_data.get("headline"),
            "li_dm_connections": li_dm_data.get("connections_count"),
            "li_dm_recent_posts": li_dm_data.get("recent_posts"),
        }
    return merged


async def upsert_bu(conn, p, dry_run):
    """Upsert business_universe; returns ('insert'|'update', bu_id|None)."""
    existing = await conn.fetchrow(
        "SELECT id FROM business_universe WHERE domain = $1", p["domain"]
    )
    specialties_json = json.dumps(p["company_specialties"]) if p["company_specialties"] else None

    if existing:
        if dry_run:
            return "update", existing["id"]
        await conn.execute(
            """UPDATE business_universe SET
                dm_name              = COALESCE(dm_name, $2),
                dm_title             = COALESCE(dm_title, $3),
                dm_linkedin_url      = COALESCE(dm_linkedin_url, $4),
                dm_email             = COALESCE(dm_email, $5),
                dm_email_verified    = COALESCE(dm_email_verified, $6),
                dm_mobile            = COALESCE(dm_mobile, $7),
                dm_source            = COALESCE(dm_source, $8),
                dm_found_at          = COALESCE(dm_found_at,
                                                CASE WHEN $4 IS NOT NULL OR $5 IS NOT NULL THEN NOW() END),
                linkedin_company_url = COALESCE(linkedin_company_url, $9),
                company_followers_count = COALESCE(company_followers_count, $10),
                company_about        = COALESCE(company_about, $11),
                company_specialties  = COALESCE(company_specialties, $12::jsonb),
                updated_at           = NOW()
            WHERE id = $1""",
            existing["id"],
            p["dm_name"], p["dm_title"], p["dm_linkedin"],
            p["email"], p["email_verified"], p["mobile"], p["dm_source"],
            p["linkedin_company_url"], p["company_followers"],
            p["company_about"], specialties_json,
        )
        return "update", existing["id"]

    if dry_run:
        return "insert", None
    new_id = await conn.fetchval(
        """INSERT INTO business_universe (
            domain, website, display_name,
            dm_name, dm_title, dm_linkedin_url,
            dm_email, dm_email_verified, dm_mobile, dm_source,
            dm_found_at, linkedin_company_url,
            company_followers_count, company_about, company_specialties,
            discovery_source, discovered_at, pipeline_updated_at,
            created_at, updated_at
        ) VALUES (
            $1, $2, $1,
            $3::text, $4::text, $5::text,
            $6::text, $7::bool, $8::text, $9::text,
            CASE WHEN $5 IS NOT NULL OR $6 IS NOT NULL THEN NOW() END, $10::text,
            $11::int, $12::text, $13::jsonb,
            'test_data_backfill', NOW(), NOW(),
            NOW(), NOW()
        ) RETURNING id""",
        p["domain"], f"https://{p['domain']}",
        p["dm_name"] or None, p["dm_title"] or None, p["dm_linkedin"] or None,
        p["email"] or None, p.get("email_verified") or False, p["mobile"] or None, p["dm_source"] or None,
        p["linkedin_company_url"] or None, p.get("company_followers") or None,
        p["company_about"] or None, specialties_json or '[]',
    )
    return "insert", new_id


async def upsert_dm(conn, bu_id, p, dry_run):
    """Upsert business_decision_makers (anchored on linkedin_url within a BU row)."""
    if not p["dm_linkedin"]:
        return None
    # Dry-run after a BU dry-insert has no bu_id yet — assume it would be a new DM.
    if not bu_id:
        return "insert" if dry_run else None

    existing = await conn.fetchrow(
        """SELECT id FROM business_decision_makers
           WHERE business_universe_id = $1 AND linkedin_url = $2""",
        bu_id, p["dm_linkedin"],
    )
    posts_json = json.dumps(p["li_dm_recent_posts"]) if p["li_dm_recent_posts"] else None

    if existing:
        if dry_run:
            return "update"
        await conn.execute(
            """UPDATE business_decision_makers SET
                name              = COALESCE(name, $2),
                title             = COALESCE(title, $3),
                email             = COALESCE(email, $4),
                email_verified    = COALESCE(email_verified, $5),
                email_source      = COALESCE(email_source, $6),
                mobile            = COALESCE(mobile, $7),
                mobile_source     = COALESCE(mobile_source, $8),
                headline          = COALESCE(headline, $9),
                connections_count = COALESCE(connections_count, $10),
                recent_posts      = COALESCE(recent_posts, $11::jsonb),
                profile_source    = COALESCE(profile_source, 'test_data_backfill'),
                updated_at        = NOW()
            WHERE id = $1""",
            existing["id"],
            p["dm_name"], p["dm_title"],
            p["email"], p["email_verified"], p["email_source"],
            p["mobile"], p["mobile_source"],
            p["li_dm_headline"], p["li_dm_connections"], posts_json,
        )
        return "update"

    if dry_run:
        return "insert"
    await conn.execute(
        """INSERT INTO business_decision_makers (
            business_universe_id, linkedin_url, name, title,
            email, email_verified, email_source,
            mobile, mobile_source,
            headline, connections_count, recent_posts,
            profile_source, is_current, created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4,
            $5, $6, $7,
            $8, $9,
            $10, $11, $12::jsonb,
            'test_data_backfill', TRUE, NOW(), NOW()
        )""",
        bu_id, p["dm_linkedin"], p["dm_name"], p["dm_title"],
        p["email"], p["email_verified"], p["email_source"],
        p["mobile"], p["mobile_source"],
        p["li_dm_headline"], p["li_dm_connections"], posts_json,
    )
    return "insert"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true",
                    help="Apply writes (default: dry-run, counts only)")
    args = ap.parse_args()
    dry_run = not args.execute

    print("=" * 60)
    print("Backfill test enrichment data → BU + business_decision_makers")
    print(f"Mode: {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print("=" * 60)

    sources, missing, legacy_missing = load_sources()
    if missing:
        print(f"\nWARN — required source files MISSING (skipped): {missing}")
    if legacy_missing:
        print(f"NOTE — earlier-cohort files referenced in brief but not on disk (skipped):")
        for f in legacy_missing:
            print(f"  - {f}")

    print("\nPer-source row counts:")
    for name, rows in sources.items():
        print(f"  {name:<22} {len(rows):>5} domains")

    merged = merge_per_domain(sources)
    print(f"\nMerged unique domains with usable data: {len(merged)}")

    # Pre-flight email/mobile filter stats
    n_email = sum(1 for p in merged.values() if p["email"])
    n_mobile = sum(1 for p in merged.values() if p["mobile"])
    n_dm = sum(1 for p in merged.values() if p["dm_linkedin"])
    n_company_li = sum(1 for p in merged.values() if p["linkedin_company_url"])
    print(f"  with valid email:        {n_email}")
    print(f"  with valid AU mobile:    {n_mobile}")
    print(f"  with DM LinkedIn URL:    {n_dm}")
    print(f"  with company LinkedIn:   {n_company_li}")

    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(dsn, min_size=4, max_size=12, statement_cache_size=0)
    await pool.execute("SET search_path TO public")

    bu_inserts = bu_updates = 0
    dm_inserts = dm_updates = 0
    errors = 0
    t0 = time.monotonic()

    sem = asyncio.Semaphore(10)

    async def process(p):
        nonlocal bu_inserts, bu_updates, dm_inserts, dm_updates, errors
        async with sem:
            try:
                async with pool.acquire() as conn:
                    bu_action, bu_id = await upsert_bu(conn, p, dry_run)
                    if bu_action == "insert":
                        bu_inserts += 1
                    else:
                        bu_updates += 1
                    dm_action = await upsert_dm(conn, bu_id, p, dry_run)
                    if dm_action == "insert":
                        dm_inserts += 1
                    elif dm_action == "update":
                        dm_updates += 1
            except Exception as exc:
                errors += 1
                if errors <= 5:
                    print(f"  ERROR {p['domain']}: {exc}")

    await asyncio.gather(*[process(p) for p in merged.values()])

    elapsed = time.monotonic() - t0
    print(f"\n{'=' * 60}")
    print("RESULT")
    print(f"  Mode:          {'DRY-RUN (no writes)' if dry_run else 'EXECUTED (committed)'}")
    print(f"  BU inserts:    {bu_inserts}")
    print(f"  BU updates:    {bu_updates}")
    print(f"  DM inserts:    {dm_inserts}")
    print(f"  DM updates:    {dm_updates}")
    print(f"  Errors:        {errors}")
    print(f"  Elapsed:       {elapsed:.2f}s")
    if dry_run:
        print("\nRe-run with --execute to apply.")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
