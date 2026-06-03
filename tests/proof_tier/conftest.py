"""tests/proof_tier/conftest.py — Testcontainers Postgres for the proof tier.

Per gate_roadmap.spike_real_deps_proof: throwaway containers, no shared state,
no mocks. The Postgres container is session-scoped — one spin-up per pytest
run, all tests in the proof tier reuse it.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO / "supabase" / "migrations"


@pytest.fixture(scope="session")
def pg_container():
    """Spin a throwaway Postgres container for the session."""
    if not os.environ.get("DOCKER_HOST") and not Path("/var/run/docker.sock").exists():
        pytest.skip("Docker socket not reachable — proof tier requires Docker")
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def pg_dsn(pg_container) -> str:
    """psycopg-compatible DSN for the throwaway container."""
    return pg_container.get_connection_url().replace("postgresql+psycopg2://", "postgresql://", 1)


@pytest.fixture(scope="session")
def reasoning_records_schema(pg_dsn: str) -> str:
    """Apply the reasoning_records migration to the container.

    Returns the DSN once the schema is in place. The migration file is the
    SOURCE OF TRUTH — running it against a throwaway container proves the
    same DDL the live database runs.
    """
    sql_path = MIGRATIONS_DIR / "20260603_reasoning_records.sql"
    with sql_path.open("r", encoding="utf-8") as fh:
        sql = fh.read()
    # The migration references gate_roadmap (§3-§5) which is not present in
    # this throwaway container. Pre-stub gate_roadmap + needed extensions
    # then apply the FULL migration — table + trg_08 + atom_capture SUBSTANCE
    # check + §6 negative-path DO block all exercise their real paths.
    stub_sql = """
    CREATE TABLE IF NOT EXISTS public.gate_roadmap (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        component TEXT UNIQUE NOT NULL,
        phase TEXT,
        proof_gate TEXT,
        status TEXT,
        owner TEXT,
        notes TEXT,
        blocker_text TEXT
    );
    INSERT INTO public.gate_roadmap (component, proof_gate)
    VALUES ('atom_capture', 'placeholder containing deliberation reasoning + rejected options for the SUBSTANCE assertion')
    ON CONFLICT (component) DO NOTHING;
    INSERT INTO public.gate_roadmap (component, status)
    VALUES ('reasoning_capture', 'not_started')
    ON CONFLICT (component) DO NOTHING;
    CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """
    with psycopg.connect(pg_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(stub_sql)
        cur.execute(sql)
    return pg_dsn
