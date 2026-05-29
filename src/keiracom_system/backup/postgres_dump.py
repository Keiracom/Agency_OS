"""postgres_dump.py — hourly Postgres dump → Cloudflare R2 (KEI-243).

pg_dump -Fc of the Vultr Postgres → upload to R2 under postgres/ → prune to 24
hourly + 7 daily anchors. Shares the R2 infra with the Weaviate snapshot
pipeline (separate prefix). Any failure writes ceo:backup_alert:{date} and
exits non-zero.

DSN resolution: BACKUP_PG_DSN, else DATABASE_URL_MIGRATIONS, else
SUPABASE_DB_DSN/DATABASE_URL. Point BACKUP_PG_DSN at the Vultr Postgres once it
is provisioned (it does not exist on the fleet host yet — pre-cutover).

Run: python3 -m src.keiracom_system.backup.postgres_dump [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

from src.keiracom_system.backup.alerting import write_backup_alert
from src.keiracom_system.backup.pipeline import timestamp, upload_and_prune
from src.keiracom_system.backup.r2 import R2Client

logger = logging.getLogger(__name__)

PREFIX = os.environ.get("POSTGRES_R2_PREFIX", "postgres/")
KEEP_HOURLY = int(os.environ.get("POSTGRES_R2_KEEP_HOURLY", "24"))
KEEP_DAILY = int(os.environ.get("POSTGRES_R2_KEEP_DAILY", "7"))


def _resolve_dsn() -> str:
    dsn = (
        os.environ.get("BACKUP_PG_DSN")
        or os.environ.get("DATABASE_URL_MIGRATIONS")
        or os.environ.get("SUPABASE_DB_DSN")
        or os.environ.get("DATABASE_URL")
    )
    if not dsn:
        raise RuntimeError("no Postgres DSN (set BACKUP_PG_DSN / DATABASE_URL_MIGRATIONS)")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def _redact_dsn(text: str) -> str:
    """Strip any postgres connection string (with embedded password) from a
    message before it is logged or written to a ceo:backup_alert row."""
    return re.sub(r"postgres(?:ql)?(?:\+\w+)?://[^\s'\"]+", "postgresql://[REDACTED]", text)


def _pg_dump(dsn: str, dest: str) -> None:
    if shutil.which("pg_dump") is None:
        raise RuntimeError("pg_dump not installed on host (need postgresql-client)")
    # Pass connection via libpq env vars, NOT in argv — keeps the DB password out
    # of the command line / process listing / CalledProcessError. A DSN in argv
    # leaked into both the log and the ceo:backup_alert row on the first failure
    # (server-version mismatch, 2026-05-29).
    p = urllib.parse.urlparse(dsn)
    env = {
        **os.environ,
        "PGHOST": p.hostname or "",
        "PGPORT": str(p.port or 5432),
        "PGUSER": urllib.parse.unquote(p.username or ""),
        "PGPASSWORD": urllib.parse.unquote(p.password or ""),
        "PGDATABASE": (p.path or "/postgres").lstrip("/") or "postgres",
    }
    # -Fc custom format (compressed, parallel-restore); --no-owner/--no-acl so it
    # restores into a fresh DB without role-permission errors.
    subprocess.run(
        ["pg_dump", "-Fc", "--no-owner", "--no-acl", "--file", dest],
        check=True,
        env=env,
    )


def run(*, dry_run: bool = False) -> str:
    ts = timestamp()
    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.join(tmp, f"postgres-dump-{ts}.dump")
        _pg_dump(_resolve_dsn(), dump)
        r2 = R2Client()
        return upload_and_prune(
            r2,
            dump,
            prefix=PREFIX,
            key_name=f"postgres-dump-{ts}.dump",
            keep_recent=KEEP_HOURLY,
            keep_daily=KEEP_DAILY,
            dry_run=dry_run,
        )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        key = run(dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001 — any failure → alert + non-zero exit
        # Redact any DSN before it reaches the alert row or the log.
        write_backup_alert("postgres_dump", _redact_dsn(str(exc)))
        logger.error("postgres dump failed: %s", _redact_dsn(str(exc)))
        return 1
    logger.info("postgres dump complete: %s", key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
