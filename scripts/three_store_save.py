#!/usr/bin/env python3
"""
three_store_save.py — Canonical 3-store save for directive completion (LAW XV).

Stores:
  1. docs/MANUAL.md  — append entry under target SECTION
  2. public.ceo_memory — upsert key ceo:directive_{directive}_complete
  3. public.cis_directive_metrics — insert execution metrics row
  4. Google Drive mirror via write_manual_mirror.py (best-effort)

Usage:
    python scripts/three_store_save.py --directive D1.8 --pr-number 329 --summary "..."
    echo "my summary" | python scripts/three_store_save.py --directive D1.8 --pr-number 329 --summary -
    python scripts/three_store_save.py --directive D1.8 --pr-number 329 --summary "..." --dry-run
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# DSN resolver — prefer DATABASE_URL, fall back to settings.database_url
# ---------------------------------------------------------------------------

def _resolve_dsn() -> str | None:
    """Return a postgres DSN suitable for asyncpg, or None when unconfigured.

    Prefers DATABASE_URL (Railway / generic), then SUPABASE_DB_URL, then
    src.config.settings.database_url. Strips any 'postgresql+asyncpg://'
    prefix because asyncpg.connect rejects the SQLAlchemy variant.
    """
    raw = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("SUPABASE_DB_URL")
        or ""
    )
    if not raw:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from src.config.settings import settings  # type: ignore[import-not-found]
            raw = settings.database_url or ""
        except Exception:  # noqa: BLE001
            raw = ""
    raw = raw.strip()
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://")


# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------

def load_env():
    env_path = Path("/home/elliotbot/.config/agency-os/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


# ---------------------------------------------------------------------------
# CALLSIGN — LAW XVII enforcement (GOV-12: gate as code, not comment)
# ---------------------------------------------------------------------------

def get_callsign() -> str:
    """Return CALLSIGN env var (default 'elliot'). Raise SystemExit if empty string.

    LAW XVII: every save tagged with the session callsign. Empty CALLSIGN is a
    governance violation — refuse to save rather than write ambiguous identity.
    """
    callsign = os.environ.get("CALLSIGN", "elliot")
    if callsign == "":
        raise SystemExit("LAW XVII: CALLSIGN is empty string — refusing to save")
    return callsign


# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Canonical 3-store save for directive completion (LAW XV)."
    )
    parser.add_argument("--directive", required=True,
                        help='Directive label, e.g. "D1.8", "309", "A"')
    parser.add_argument("--pr-number", required=True, type=int,
                        help="GitHub PR number")
    parser.add_argument("--summary", required=True,
                        help='Completion summary text, or "-" to read from stdin')
    parser.add_argument("--manual-section", type=int, default=13,
                        help="Manual section number to append entry under (default: 13)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without writing anything")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# STORE 1 — MANUAL.md
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent


def manual_entry(directive: str, pr_number: int, summary: str, callsign: str) -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tag = f"[{callsign.upper()}] " if callsign else ""
    return (
        f"\n### {tag}Directive {directive} (PR #{pr_number}, {date_str})\n"
        f"{summary}\n"
    )


def save_manual(directive: str, pr_number: int, summary: str, section: int, dry_run: bool, callsign: str = "elliot") -> bool:
    manual_path = REPO_ROOT / "docs" / "MANUAL.md"
    if not manual_path.exists():
        print(f"[STORE 1/4] Manual: FAILED — docs/MANUAL.md not found at {manual_path}")
        return False

    content = manual_path.read_text()
    lines = content.splitlines(keepends=True)

    target_marker = f"## SECTION {section}"
    target_idx = None
    next_idx = None

    for i, line in enumerate(lines):
        if line.strip() == target_marker or line.strip().startswith(f"{target_marker} "):
            target_idx = i
        elif target_idx is not None and re.match(r"^## SECTION \d+", line.strip()):
            next_idx = i
            break

    if target_idx is None:
        print(f"[STORE 1/4] Manual: FAILED — marker '{target_marker}' not found in docs/MANUAL.md")
        return False

    entry = manual_entry(directive, pr_number, summary, callsign)

    if dry_run:
        insert_before = next_idx if next_idx is not None else len(lines)
        print(f"[DRY-RUN][STORE 1/4] Would insert before line {insert_before + 1} in docs/MANUAL.md:")
        print("---")
        print(entry.strip())
        print("---")
        return True

    insert_at = next_idx if next_idx is not None else len(lines)
    lines.insert(insert_at, entry)
    try:
        manual_path.write_text("".join(lines))
        print(f"[STORE 1/4] Manual: OK — entry inserted under SECTION {section}")
        return True
    except Exception as exc:
        print(f"[STORE 1/4] Manual: FAILED — {exc}")
        return False


# ---------------------------------------------------------------------------
# STORE 2 — ceo_memory
# ---------------------------------------------------------------------------

def save_ceo_memory(directive: str, pr_number: int, summary: str, dry_run: bool, callsign: str = "elliot") -> bool:
    """Upsert public.ceo_memory via asyncpg (no REST, no PostgREST).

    statement_cache_size=0 so the connection works through Supabase's
    pgbouncer transaction-mode pooler. Function stays sync — async
    work is wrapped in asyncio.run so callers don't change.
    """
    key = f"ceo:directive_{directive}_complete"
    value = {
        "directive": directive,
        "pr": pr_number,
        "summary": summary,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "source": callsign,  # LAW XVII: tag write with callsign
    }

    if dry_run:
        print(f"[DRY-RUN][STORE 2/4] Would upsert ceo_memory key={key!r}")
        print(f"  value={json.dumps(value)}")
        return True

    dsn = _resolve_dsn()
    if not dsn:
        print("[STORE 2/4] ceo_memory: FAILED — DATABASE_URL / SUPABASE_DB_URL not set")
        return False

    async def _upsert() -> None:
        import asyncpg
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
        try:
            await conn.execute(
                """
                INSERT INTO ceo_memory (key, value, updated_at)
                VALUES ($1, $2::jsonb, NOW())
                ON CONFLICT (key) DO UPDATE
                  SET value = EXCLUDED.value, updated_at = NOW()
                """,
                key, json.dumps(value),
            )
        finally:
            await conn.close()

    try:
        asyncio.run(_upsert())
        print(f"[STORE 2/4] ceo_memory: OK — key={key!r}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[STORE 2/4] ceo_memory: FAILED — {exc}")
        return False


# ---------------------------------------------------------------------------
# STORE 3 — cis_directive_metrics
# ---------------------------------------------------------------------------

def save_metrics(directive: str, pr_number: int, summary: str, dry_run: bool, callsign: str = "elliot") -> bool:
    """Insert into public.cis_directive_metrics via asyncpg (no REST)."""
    # Determine directive_id vs directive_ref
    if re.fullmatch(r"\d+", directive):
        directive_id = int(directive)
        directive_ref = None
    else:
        directive_id = 0
        directive_ref = directive

    now = datetime.now(timezone.utc)
    row_preview = {
        "directive_id": directive_id,
        "directive_ref": directive_ref,
        "issued_date": now.isoformat(),
        "completed_date": now.isoformat(),
        "execution_rounds": 1,
        "scope_creep": False,
        "verification_first_pass": True,
        "save_completed": True,
        "agents_used": ["build-2", "build-3"],
        "notes": summary,
        "callsign": callsign,
        "created_at": now.isoformat(),
    }

    if dry_run:
        print("[DRY-RUN][STORE 3/4] Would insert cis_directive_metrics row:")
        print(f"  {json.dumps(row_preview)}")
        return True

    dsn = _resolve_dsn()
    if not dsn:
        print("[STORE 3/4] cis_directive_metrics: FAILED — DATABASE_URL / SUPABASE_DB_URL not set")
        return False

    async def _insert() -> None:
        import asyncpg
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
        try:
            await conn.execute(
                """
                INSERT INTO cis_directive_metrics (
                  directive_id, directive_ref, issued_date, completed_date,
                  execution_rounds, scope_creep, verification_first_pass,
                  save_completed, agents_used, notes, callsign, created_at
                ) VALUES (
                  $1, $2, $3, $4,
                  $5, $6, $7,
                  $8, $9, $10, $11, $12
                )
                """,
                directive_id, directive_ref, now, now,
                1, False, True,
                True, ["build-2", "build-3"], summary, callsign, now,
            )
        finally:
            await conn.close()

    try:
        asyncio.run(_insert())
        print(f"[STORE 3/4] cis_directive_metrics: OK — directive_ref={directive_ref!r}, directive_id={directive_id}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[STORE 3/4] cis_directive_metrics: FAILED — {exc}")
        return False


# ---------------------------------------------------------------------------
# STORE 4 — Drive mirror (best-effort)
# ---------------------------------------------------------------------------

def run_drive_mirror(dry_run: bool) -> None:
    mirror_script = REPO_ROOT / "scripts" / "write_manual_mirror.py"
    if dry_run:
        print(f"[DRY-RUN][STORE 4/4] Would run: {sys.executable} {mirror_script}")
        return
    result = subprocess.run(
        [sys.executable, str(mirror_script)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[STORE 4/4] Drive mirror: OK")
    else:
        print(f"[STORE 4/4] Drive mirror: WARNING — exit {result.returncode}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()[:200]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    load_env()
    args = parse_args()

    summary = args.summary
    if summary == "-":
        summary = sys.stdin.read().strip()

    directive = args.directive
    pr_number = args.pr_number
    section = args.manual_section
    dry_run = args.dry_run
    callsign = get_callsign()  # LAW XVII: fail loud on empty CALLSIGN

    if dry_run:
        print(f"[DRY-RUN] directive={directive!r} pr={pr_number} section={section} callsign={callsign!r}")
        print()

    succeeded = []

    # Store 1
    ok1 = save_manual(directive, pr_number, summary, section, dry_run, callsign)
    if ok1:
        succeeded.append("Manual")
    else:
        print(f"Succeeded before failure: {succeeded or 'none'}")
        sys.exit(1)

    # Store 2
    ok2 = save_ceo_memory(directive, pr_number, summary, dry_run, callsign)
    if ok2:
        succeeded.append("ceo_memory")
    else:
        print(f"Succeeded before failure: {succeeded}")
        sys.exit(1)

    # Store 3
    ok3 = save_metrics(directive, pr_number, summary, dry_run, callsign)
    if ok3:
        succeeded.append("cis_directive_metrics")
    else:
        print(f"Succeeded before failure: {succeeded}")
        sys.exit(1)

    # Store 4 — best-effort
    run_drive_mirror(dry_run)

    print()
    print(f"All 3 stores saved. Directive {directive!r} PR #{pr_number} complete.")


if __name__ == "__main__":
    main()
