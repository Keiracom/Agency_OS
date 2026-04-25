"""
Seed the Demo tenant for investor-ready demos.

What it does
------------
1. Ensures a `clients` row named 'Demo Agency' exists (creates if missing).
2. Selects up to 20 best BU prospects by:
       pipeline_stage >= 6
       AND dm_email IS NOT NULL
       AND propensity_score > 60
   ordered by (propensity_score + COALESCE(reachability_score, 0)) DESC.
3. Drops any row whose dm_email or domain is in the suppression list, OR
   whose dm_email is a placeholder (example@, test@, info@, admin@, etc.),
   OR whose display_name is NULL.
4. Inserts campaign_leads junction rows linking the Demo client to each
   selected BU id (status='claimed').

If fewer than 20 prospects survive filtering it REPORTS the shortfall —
never pads with weaker prospects. The point of the demo is curated quality.

Usage:
    python3 scripts/seed_demo_tenant.py --dry-run    # default
    python3 scripts/seed_demo_tenant.py --execute    # actually write

Schema note: the clients table currently has no `is_demo` column. The
demo tenant is identified by name='Demo Agency' (idempotent lookup).
A future migration could promote this to a typed column.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, REPO_ROOT)

from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncpg  # noqa: E402

from src.config.settings import settings  # noqa: E402

DEMO_CLIENT_NAME = "Demo Agency"
DEMO_TIER = "spark"
TARGET_PROSPECTS = 20
MIN_STAGE = 6
MIN_PROPENSITY = 60

# Placeholder / non-deliverable email locals — treat the address as missing.
PLACEHOLDER_LOCALS = frozenset({
    "example", "test", "info", "admin", "noreply", "no-reply",
    "mailer-daemon", "postmaster", "sample", "dummy",
})
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def is_real_email(email: str | None) -> bool:
    if not email or not isinstance(email, str):
        return False
    e = email.strip().lower()
    if not EMAIL_RE.match(e):
        return False
    local = e.split("@", 1)[0]
    return local not in PLACEHOLDER_LOCALS


async def ensure_demo_client(conn) -> str:
    """Lookup-or-create the demo client. Returns its UUID as a string."""
    row = await conn.fetchrow(
        "SELECT id FROM clients WHERE name = $1 AND deleted_at IS NULL",
        DEMO_CLIENT_NAME,
    )
    if row:
        print(f"demo client exists — id={row['id']}")
        return str(row["id"])

    new_id = await conn.fetchval(
        """
        INSERT INTO clients (id, name, tier, subscription_status, created_at, updated_at)
        VALUES (gen_random_uuid(), $1, $2, 'active', NOW(), NOW())
        RETURNING id
        """,
        DEMO_CLIENT_NAME, DEMO_TIER,
    )
    print(f"demo client created — id={new_id}")
    return str(new_id)


async def select_prospects(conn) -> list[dict]:
    """Top-ranked BU rows that survive every filter."""
    rows = await conn.fetch(
        f"""
        SELECT id, domain, display_name, dm_name, dm_title,
               dm_email, propensity_score, reachability_score, pipeline_stage
        FROM business_universe
        WHERE pipeline_stage >= $1
          AND dm_email IS NOT NULL
          AND COALESCE(propensity_score, 0) > $2
          AND display_name IS NOT NULL
        ORDER BY (COALESCE(propensity_score, 0) + COALESCE(reachability_score, 0)) DESC
        LIMIT {TARGET_PROSPECTS * 5}
        """,
        MIN_STAGE, MIN_PROPENSITY,
    )

    # Suppression filter
    domains = list({r["domain"] for r in rows if r["domain"]})
    emails  = list({r["dm_email"].lower() for r in rows if r["dm_email"]})
    suppressed_domains: set[str] = set()
    suppressed_emails: set[str] = set()
    if domains:
        sup_dom = await conn.fetch(
            "SELECT DISTINCT domain FROM suppression_list "
            "WHERE domain = ANY($1::text[]) AND (expires_at IS NULL OR expires_at > NOW())",
            domains,
        )
        suppressed_domains = {r["domain"] for r in sup_dom}
    if emails:
        sup_em = await conn.fetch(
            "SELECT DISTINCT LOWER(email) AS email FROM suppression_list "
            "WHERE LOWER(email) = ANY($1::text[]) AND (expires_at IS NULL OR expires_at > NOW())",
            emails,
        )
        suppressed_emails = {r["email"] for r in sup_em}

    selected: list[dict] = []
    rejected = {"placeholder_email": 0, "suppressed_domain": 0, "suppressed_email": 0}
    for r in rows:
        if not is_real_email(r["dm_email"]):
            rejected["placeholder_email"] += 1
            continue
        if r["domain"] and r["domain"] in suppressed_domains:
            rejected["suppressed_domain"] += 1
            continue
        if r["dm_email"] and r["dm_email"].lower() in suppressed_emails:
            rejected["suppressed_email"] += 1
            continue
        selected.append(dict(r))
        if len(selected) >= TARGET_PROSPECTS:
            break

    print(f"  candidates returned: {len(rows)}")
    print(f"  rejected: {rejected}")
    return selected


async def link_prospects(
    conn, client_id: str, prospects: list[dict], *, dry_run: bool,
) -> int:
    """Insert (or skip-if-exists) one campaign_leads row per prospect."""
    inserted = 0
    for p in prospects:
        if dry_run:
            inserted += 1
            continue
        result = await conn.fetchval(
            """
            INSERT INTO campaign_leads (
                id, client_id, business_universe_id, status,
                claimed_at, created_at, updated_at
            ) VALUES (gen_random_uuid(), $1, $2, 'claimed', NOW(), NOW(), NOW())
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            client_id, p["id"],
        )
        if result:
            inserted += 1
    return inserted


async def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--execute", action="store_true",
                    help="Apply writes (default: dry-run)")
    args = ap.parse_args()
    dry_run = not args.execute

    print("=" * 60)
    print("Seed Demo Tenant")
    print(f"mode: {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print("=" * 60)

    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)

    try:
        client_id = await ensure_demo_client(conn) if not dry_run else "DRY-RUN-CLIENT"
        print(f"\nselecting top {TARGET_PROSPECTS} BU prospects "
              f"(stage >= {MIN_STAGE}, propensity > {MIN_PROPENSITY}, real email)…")
        prospects = await select_prospects(conn)

        print(f"\nselected: {len(prospects)} prospects")
        for p in prospects[:5]:
            score = (p["propensity_score"] or 0) + (p["reachability_score"] or 0)
            print(f"  - {p['domain']} | {p['display_name']} | "
                  f"score={score} | dm={p['dm_name']} <{p['dm_email']}>")
        if len(prospects) > 5:
            print(f"  … and {len(prospects) - 5} more")

        if len(prospects) < TARGET_PROSPECTS:
            print(f"\nWARNING — only {len(prospects)} of {TARGET_PROSPECTS} target "
                  f"prospects passed all filters. Demo will be smaller. "
                  f"Refusing to pad with weaker prospects.")

        if not prospects:
            print("\nno prospects to link — exiting")
            return

        if dry_run:
            print(f"\nDRY-RUN — would link {len(prospects)} BU rows to demo client")
            return

        linked = await link_prospects(conn, client_id, prospects, dry_run=False)
        print(f"\nlinked: {linked} new campaign_leads rows")
        print(f"demo_client_id: {client_id}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
