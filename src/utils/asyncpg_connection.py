# FILE: src/utils/asyncpg_connection.py
# PURPOSE: asyncpg connection factory with JSONB codec registered globally.
#          Without this, asyncpg returns JSONB columns as raw strings instead
#          of parsed Python objects (dicts/lists).
# DIRECTIVE: #275 (bugfix — live test revealed codec missing)

from __future__ import annotations

import json

import asyncpg


async def get_asyncpg_pool(
    dsn: str,
    min_size: int = 1,
    max_size: int = 50,
) -> asyncpg.Pool:
    """
    Create an asyncpg connection pool with JSON/JSONB codecs registered.

    Use this instead of get_asyncpg_connection() for concurrent pipeline stages.
    Supabase Pro supports 200+ connections; max_size=50 leaves headroom.

    Usage:
        pool = await get_asyncpg_pool(DATABASE_URL)
        fe = FreeEnrichment(pool)
        ...
        await pool.close()

    Note: min_size=1 (not 5) avoids Supabase pooler connection-init hang.
    Pool grows on demand up to max_size=50.

    Or as context manager:
        async with await get_asyncpg_pool(DATABASE_URL) as pool:
            fe = FreeEnrichment(pool)
    """

    async def _init_conn(conn: asyncpg.Connection) -> None:
        await conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )
        await conn.set_type_codec(
            "json",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )

    pool = await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        init=_init_conn,
    )
    return pool


async def get_asyncpg_connection(dsn: str) -> asyncpg.Connection:
    """
    Create an asyncpg connection with JSON/JSONB codecs registered.

    asyncpg does not register JSONB codecs by default — JSONB columns are
    returned as raw JSON strings. This factory registers both 'json' and
    'jsonb' codecs so all JSONB columns automatically return parsed Python
    objects (dicts/lists) without any json.loads() calls in callers.

    Use this instead of asyncpg.connect() everywhere in the pipeline layer.
    """
    conn = await asyncpg.connect(dsn)
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    return conn
