#!/usr/bin/env python3
"""repair_untracked_migrations.py — track functional-but-untracked migrations.

Sweep tool (Elliot-authorized 2026-06-04, off the #1454 watcher discovery).
Finds migrations that are FUNCTIONALLY APPLIED (present in information_schema)
but NOT recorded in supabase_migrations.schema_migrations, and marks ONLY those
as applied via `supabase migration repair --status applied <version>` — which
records migration history WITHOUT re-running any SQL.

Discipline (per dispatch), enforced per version:
  1. VERIFY functionally-applied BEFORE marking — never false-track.
  2. repair --status applied <version> (no SQL re-run).
  3. confirm tracked count +1, the version now present, others untouched.
Any untracked file NOT confirmed functionally-applied is SKIPPED + flagged
(real not-applied = a different problem; undeterminable = parser can't tell).

The Supabase CLI globs <14-digit-version>_*.sql to resolve a migration name,
but this repo names files <date>_name.sql. We supply a TEMP copy named
<version>_<original_basename>.sql purely for name resolution (repair reads the
name; --status applied does not execute the file), then delete it. The
committed file is never renamed — consistent with existing tracked rows whose
version (a timestamp) already differs from their filename prefix.

Usage:
  python3 scripts/orchestrator/repair_untracked_migrations.py --dry-run
  python3 scripts/orchestrator/repair_untracked_migrations.py --apply [--limit N]
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import urllib.parse as _u
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent))
import migration_apply_watcher as maw  # noqa: E402

logger = logging.getLogger("repair_untracked_migrations")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MIGRATIONS_DIR = maw.MIGRATIONS_DIR


def enc_migrations_dsn() -> str:
    """Percent-encoded direct (session) migrations DSN the Supabase CLI needs."""
    raw = os.environ.get("DATABASE_URL_MIGRATIONS") or os.environ.get("DATABASE_URL")
    if not raw:
        raise SystemExit("DATABASE_URL_MIGRATIONS or DATABASE_URL must be set")
    p = _u.urlparse(raw.replace("postgresql+asyncpg", "postgresql"))
    netloc = (
        f"{_u.quote(p.username or '', safe='')}:{_u.quote(p.password or '', safe='')}"
        f"@{p.hostname}:{p.port}"
    )
    return _u.urlunparse((p.scheme, netloc, p.path, p.params, p.query, p.fragment))


def _plain_dsn() -> str:
    return (os.environ.get("DATABASE_URL") or "").replace("postgresql+asyncpg", "postgresql")


def derive_version(basename: str, used: set[str]) -> str:
    """A unique 14-digit version from the file's main commit timestamp.

    Collisions (same commit, or already-tracked) bump by one second until free.
    Falls back to a date-prefix-derived stamp if git has no record.
    """
    base = ""
    with __import__("contextlib").suppress(subprocess.SubprocessError, OSError):
        base = subprocess.check_output(
            [
                "git",
                "log",
                "-1",
                "--format=%cd",
                "--date=format:%Y%m%d%H%M%S",
                "origin/main",
                "--",
                f"supabase/migrations/{basename}.sql",
            ],
            text=True,
        ).strip()
    if len(base) != 14 or not base.isdigit():
        # Fallback: leading 8-digit date token + 000000, else epoch-free constant.
        digits = "".join(c for c in basename[:8] if c.isdigit())
        base = (digits + "000000")[:14].ljust(14, "0") if digits else "20260101000000"
    v = int(base)
    while str(v) in used:
        v += 1
    used.add(str(v))
    return str(v)


def _tracked_count(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM supabase_migrations.schema_migrations")
        return cur.fetchone()[0]


def _version_present(conn: psycopg.Connection, version: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM supabase_migrations.schema_migrations WHERE version = %s",
            (version,),
        )
        return cur.fetchone() is not None


def repair_one(basename: str, version: str, enc_dsn: str) -> tuple[bool, str]:
    """Temp-name trick + `migration repair --status applied`. Returns (ok, output)."""
    tmp = MIGRATIONS_DIR / f"{version}_{basename}.sql"
    src = MIGRATIONS_DIR / f"{basename}.sql"
    try:
        tmp.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as exc:
        return False, f"temp-copy failed: {exc}"
    try:
        proc = subprocess.run(
            [
                "npx",
                "--yes",
                "supabase",
                "migration",
                "repair",
                "--status",
                "applied",
                version,
                "--db-url",
                enc_dsn,
                "--yes",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        out = (proc.stdout + proc.stderr).strip()
        return proc.returncode == 0 and "=> applied" in out, out
    except (subprocess.SubprocessError, OSError) as exc:
        return False, f"repair invocation failed: {exc}"
    finally:
        tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually repair (default is dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="list classification only (default)")
    ap.add_argument("--limit", type=int, default=0, help="cap repairs this run (0 = no cap)")
    args = ap.parse_args(argv)
    do_apply = args.apply and not args.dry_run

    enc_dsn = enc_migrations_dsn()
    with psycopg.connect(_plain_dsn(), autocommit=True, prepare_threshold=None) as conn:
        tracked = maw.fetch_tracked_names(conn)
        if not tracked:
            raise SystemExit("schema_migrations empty/absent — refusing to sweep")
        untracked = maw.compute_untracked(maw.list_migration_basenames(), tracked)

        eligible, not_applied, undeterminable = [], [], []
        for b in untracked:
            status = maw._file_functionally_applied(conn, b)
            (
                eligible if status is True else not_applied if status is False else undeterminable
            ).append(b)

        logger.info(
            "untracked=%d | eligible(functional)=%d not_applied=%d undeterminable=%d",
            len(untracked),
            len(eligible),
            len(not_applied),
            len(undeterminable),
        )
        if not_applied:
            logger.warning("SKIP not-applied (real gap, different problem): %s", not_applied)
        if undeterminable:
            logger.info(
                "SKIP undeterminable (parser can't confirm; not auto-tracked): %s", undeterminable
            )

        with conn.cursor() as cur:
            cur.execute("SELECT version FROM supabase_migrations.schema_migrations")
            used = {r[0] for r in cur.fetchall()}

        repaired, failed = [], []
        targets = eligible[: args.limit] if args.limit > 0 else eligible
        for b in targets:
            version = derive_version(b, used)
            if not do_apply:
                logger.info("DRY-RUN would repair: %s -> version %s", b, version)
                continue
            # Discipline (1): re-verify functionally-applied immediately before marking.
            if maw._file_functionally_applied(conn, b) is not True:
                logger.warning("re-verify failed (no longer confirmed applied) — skipping %s", b)
                not_applied.append(b)
                continue
            before = _tracked_count(conn)
            ok, out = repair_one(b, version, enc_dsn)
            after = _tracked_count(conn)
            if ok and _version_present(conn, version) and after == before + 1:
                logger.info("repaired %s -> %s (tracked %d->%d)", b, version, before, after)
                repaired.append((b, version))
            else:
                logger.error(
                    "repair FAILED for %s: ok=%s before=%d after=%d out=%s",
                    b,
                    ok,
                    before,
                    after,
                    out,
                )
                failed.append((b, out))

        print("\n===== SWEEP SUMMARY =====")
        print(f"eligible(functional-but-untracked): {len(eligible)}")
        print(f"repaired: {len(repaired)}")
        print(f"failed:   {len(failed)}")
        print(f"skipped not-applied (flagged): {len(not_applied)} -> {not_applied}")
        print(f"skipped undeterminable:        {len(undeterminable)} -> {undeterminable}")
        if not do_apply:
            print("(dry-run — no repairs performed; re-run with --apply)")


if __name__ == "__main__":
    main()
