#!/usr/bin/env python3
"""scripts/campaign_sender.py — render and (dry-run) send campaign emails.

Reads a campaign sequence JSON, queries Supabase business_universe for
matching prospects with verified emails, replaces merge tags, and either
prints the rendered emails (default --dry-run) or sends via Resend MCP.

Defaults are paranoid: dry-run unless --live, require dm_email_verified,
min_confidence=70, suppression-list filtered, limit=10. Live mode requires
explicit --live AND non-zero --limit.

Usage:
    python scripts/campaign_sender.py                     # dry-run, step 1, 10 prospects
    python scripts/campaign_sender.py --step 2 --limit 5  # dry-run step 2
    python scripts/campaign_sender.py --live --limit 1    # send 1 real email
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_ENV_FILE = Path("/home/elliotbot/clawd/Agency_OS/config/.env")
DEFAULT_CAMPAIGN = Path(
    "/home/elliotbot/clawd/Agency_OS-max/campaigns/dental_sequence_v1.json"
)
MCP_BRIDGE_DIR = Path("/home/elliotbot/clawd/skills/mcp-bridge")
TAG_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def psycopg_dsn() -> str:
    url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("DATABASE_URL_MIGRATIONS")
        or ""
    )
    if not url:
        sys.exit("ERROR: DATABASE_URL not configured (looked in env + .env file)")
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://"):]
    elif url.startswith("postgres+asyncpg://"):
        url = "postgresql://" + url[len("postgres+asyncpg://"):]
    return url


def connect():  # noqa: ANN201
    import psycopg  # noqa: PLC0415

    return psycopg.connect(psycopg_dsn(), prepare_threshold=None)


@dataclass
class Prospect:
    bu_id: str
    dm_email: str
    dm_name: str | None
    display_name: str | None
    state: str | None
    suburb: str | None
    gmb_category: str | None
    confidence: int | None


def fetch_prospects(
    *,
    vertical_pattern: str,
    limit: int,
    require_verified: bool,
    min_confidence: int,
) -> list[Prospect]:
    """Fetch BU prospects matching vertical, with email + suppression filters."""
    sql = """
        SELECT bu.id::text, bu.dm_email, bu.dm_name, bu.display_name,
               bu.state, bu.suburb, bu.gmb_category, bu.dm_email_confidence
        FROM public.business_universe bu
        LEFT JOIN public.global_suppression gs
          ON LOWER(gs.email) = LOWER(bu.dm_email)
        WHERE bu.dm_email IS NOT NULL
          AND gs.email IS NULL
          AND bu.gmb_category ILIKE %s
          AND (NOT %s OR bu.dm_email_verified = TRUE)
          AND COALESCE(bu.dm_email_confidence, 0) >= %s
        ORDER BY bu.dm_email_confidence DESC NULLS LAST, bu.id
        LIMIT %s
    """
    out: list[Prospect] = []
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (vertical_pattern, require_verified, min_confidence, limit))
        for row in cur.fetchall():
            out.append(Prospect(*row))
    return out


def first_name(full: str | None) -> str:
    if not full:
        return "there"
    return full.strip().split()[0]


def render(template: str, ctx: dict[str, str]) -> str:
    return TAG_RE.sub(lambda m: ctx.get(m.group(1), m.group(0)), template)


def build_context(p: Prospect, sender_name: str) -> dict[str, str]:
    return {
        "dm_name": first_name(p.dm_name),
        "display_name": p.display_name or "your practice",
        "state": p.state or "Australia",
        "suburb": p.suburb or "your area",
        "sender_name": sender_name,
    }


def send_via_mcp(
    *, to: str, subject: str, html: str, text: str, sender: str,
) -> dict[str, Any]:
    payload = {
        "from_address": sender,
        "to": to,
        "subject": subject,
        "html": html,
        "text": text,
    }
    proc = subprocess.run(
        [
            "node", "scripts/mcp-bridge.js", "call", "resend", "send_email",
            json.dumps(payload),
        ],
        cwd=MCP_BRIDGE_DIR,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"raw": proc.stdout}


def derive_pattern(vertical: str, override: str | None) -> str:
    if override:
        return override if "%" in override else f"%{override}%"
    # 'dental' -> '%denta%' so it matches both 'Dentist' and 'Dental clinic'
    stem = vertical.rstrip("s").lower()[:5]
    return f"%{stem}%" if stem else "%"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--sender", default="Dave")
    ap.add_argument(
        "--from",
        dest="from_address",
        default=os.environ.get("RESEND_DEFAULT_FROM", "Dave <dave@agencyxos.ai>"),
    )
    ap.add_argument("--min-confidence", type=int, default=70)
    ap.add_argument(
        "--require-verified", action=argparse.BooleanOptionalAction, default=True,
    )
    ap.add_argument(
        "--vertical-match", default=None,
        help="Override gmb_category ILIKE pattern (default derived from campaign vertical)",
    )
    ap.add_argument(
        "--live", action="store_true",
        help="Actually send via Resend (default = dry-run, no network call)",
    )
    args = ap.parse_args()

    load_env(DEFAULT_ENV_FILE)

    if not args.campaign.exists():
        sys.exit(f"ERROR: campaign file not found: {args.campaign}")
    campaign = json.loads(args.campaign.read_text())
    steps = {e["step"]: e for e in campaign.get("emails", [])}
    if args.step not in steps:
        sys.exit(f"ERROR: step {args.step} not in campaign (steps={sorted(steps)})")
    template = steps[args.step]
    pattern = derive_pattern(campaign.get("vertical", ""), args.vertical_match)

    prospects = fetch_prospects(
        vertical_pattern=pattern,
        limit=args.limit,
        require_verified=args.require_verified,
        min_confidence=args.min_confidence,
    )

    mode = "LIVE" if args.live else "DRY-RUN"
    print(f"=== campaign_sender [{mode}] ===")
    print(f"campaign        : {campaign.get('campaign_name')}")
    print(f"step            : {args.step}/{len(steps)}  delay_days={template.get('delay_days')}")
    print(f"vertical pattern: {pattern}  (campaign vertical={campaign.get('vertical')})")
    print(f"filters         : verified={args.require_verified}, min_confidence={args.min_confidence}")
    print(f"prospects found : {len(prospects)} (limit={args.limit})")
    print(f"from            : {args.from_address}")
    print()

    if not prospects:
        print("No matching prospects. Exiting.")
        return 0

    if args.live:
        api_key = os.environ.get("RESEND_API_KEY", "")
        if not api_key:
            sys.exit("ERROR: --live set but RESEND_API_KEY missing")
        confirm = input(
            f"About to send {len(prospects)} REAL emails. Type 'SEND' to confirm: "
        )
        if confirm.strip() != "SEND":
            print("Aborted.")
            return 1

    sent = failed = 0
    for p in prospects:
        ctx = build_context(p, args.sender)
        subject = render(template["subject"], ctx)
        body_html = render(template["body_html"], ctx)
        body_text = render(template["body_text"], ctx)

        header = (
            f"--- {p.dm_email}  "
            f"({p.display_name or '?'} | {p.suburb or '?'}, {p.state or '?'} "
            f"| conf={p.confidence}) ---"
        )
        print(header)
        print(f"Subject: {subject}")

        if not args.live:
            print(body_text)
            print()
            continue

        try:
            res = send_via_mcp(
                to=p.dm_email,
                subject=subject,
                html=body_html,
                text=body_text,
                sender=args.from_address,
            )
            sent += 1
            print(f"  -> sent: {res}")
        except subprocess.CalledProcessError as exc:
            failed += 1
            err = (exc.stderr or "").strip()[:300]
            print(f"  -> FAILED rc={exc.returncode}: {err}")
        except subprocess.TimeoutExpired:
            failed += 1
            print("  -> FAILED: timeout")
        print()

    if args.live:
        print(f"=== summary: {sent} sent, {failed} failed ===")
    else:
        print(f"=== dry-run complete: {len(prospects)} would be sent ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
