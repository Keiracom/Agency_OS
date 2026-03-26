# FILE: src/utils/asyncpg_connection.py
# PURPOSE: asyncpg connection factory with JSONB codec registered globally.
#          Without this, asyncpg returns JSONB columns as raw strings instead
#          of parsed Python objects (dicts/lists).
# DIRECTIVE: #275 (bugfix — live test revealed codec missing)

from __future__ import annotations

import json

import asyncpg


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
