"""Tests for postgres_dump credential-safety (no DSN in argv / alerts)."""

from __future__ import annotations

from unittest.mock import patch

from src.keiracom_system.backup import postgres_dump as pd

DSN = "postgresql://postgres.proj:s3cr3tP@ss!@aws-1.pooler.supabase.com:5432/postgres"


def test_redact_dsn_strips_password_url():
    msg = f"Command '['pg_dump', '-Fc', '{DSN}']' returned non-zero exit status 1."
    red = pd._redact_dsn(msg)
    assert "s3cr3tP@ss" not in red
    assert "supabase.com" not in red
    assert "[REDACTED]" in red


def test_redact_handles_asyncpg_scheme():
    red = pd._redact_dsn("err postgresql+asyncpg://u:pw@h:6543/db trailing")
    assert "pw@h" not in red
    assert "trailing" in red  # only the URL is stripped


def test_pg_dump_passes_creds_via_env_not_argv():
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["env"] = kwargs.get("env", {})

    with (
        patch.object(pd.shutil, "which", return_value="/usr/bin/pg_dump"),
        patch.object(pd.subprocess, "run", side_effect=fake_run),
    ):
        pd._pg_dump(DSN, "/tmp/x.dump")

    # The DSN (and password) must NOT appear anywhere in the command argv.
    joined = " ".join(captured["args"])
    assert DSN not in joined
    assert "s3cr3tP@ss" not in joined
    assert "supabase.com" not in joined
    # Creds delivered via libpq env vars instead.
    env = captured["env"]
    assert env["PGHOST"] == "aws-1.pooler.supabase.com"
    assert env["PGPORT"] == "5432"
    assert env["PGUSER"] == "postgres.proj"
    assert env["PGPASSWORD"] == "s3cr3tP@ss!"
    assert env["PGDATABASE"] == "postgres"
    assert captured["args"][:2] == ["pg_dump", "-Fc"]
