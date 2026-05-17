"""KEI-68 — read API for the governance_rules table.

Agents + enforcer query this on session start to source active rules from
Supabase rather than @-importing static CLAUDE.md modules.

Public API:
    list_active_rules(category=None) -> list[dict]
    mark_deprecated(rule_id, reason, by) -> dict
    upsert_rule(rule_dict) -> dict                # seed harness call site

Caller-side caching is left to the consumer — read latency is fine for
session-start cost but enforcer hot-path callers should cache.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def list_active_rules(category: str | None = None) -> list[dict[str, Any]]:
    """Return active rules; filter by category if given."""
    with (
        psycopg.connect(
            _dsn(), prepare_threshold=None, autocommit=True, row_factory=dict_row
        ) as conn,
        conn.cursor() as cur,
    ):
        if category:
            cur.execute(
                "SELECT * FROM public.governance_rules "
                "WHERE active=TRUE AND category=%s ORDER BY id",
                (category,),
            )
        else:
            cur.execute(
                "SELECT * FROM public.governance_rules WHERE active=TRUE ORDER BY category, id"
            )
        return cur.fetchall()


def mark_deprecated(rule_id: str, reason: str, by: str) -> dict[str, Any]:
    """Flip active=FALSE + record deprecation provenance. Returns the row.

    Idempotent re-mark updates reason+by+timestamp. Raises if rule_id missing.
    """
    if not reason:
        raise ValueError("reason must be non-empty")
    with (
        psycopg.connect(
            _dsn(), prepare_threshold=None, autocommit=True, row_factory=dict_row
        ) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "UPDATE public.governance_rules "
            "SET active=FALSE, deprecated_at=NOW(), deprecated_reason=%s, deprecated_by=%s, updated_at=NOW() "
            "WHERE id=%s RETURNING *",
            (reason, by, rule_id),
        )
        row = cur.fetchone()
        if not row:
            raise LookupError(f"no governance_rule with id={rule_id!r}")
        return row


def upsert_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Insert-or-update by primary key id. Idempotent seed-harness call site.

    Required fields: id, category, rule. Optional: source_doc, active.
    """
    required = {"id", "category", "rule"}
    missing = required - rule.keys()
    if missing:
        raise ValueError(f"missing required fields: {sorted(missing)}")
    with (
        psycopg.connect(
            _dsn(), prepare_threshold=None, autocommit=True, row_factory=dict_row
        ) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "INSERT INTO public.governance_rules (id, category, rule, source_doc, active) "
            "VALUES (%(id)s, %(category)s, %(rule)s, %(source_doc)s, %(active)s) "
            "ON CONFLICT (id) DO UPDATE "
            "  SET category=EXCLUDED.category, rule=EXCLUDED.rule, "
            "      source_doc=EXCLUDED.source_doc, updated_at=NOW() "
            "RETURNING *",
            {
                "id": rule["id"],
                "category": rule["category"],
                "rule": rule["rule"],
                "source_doc": rule.get("source_doc"),
                "active": rule.get("active", True),
            },
        )
        return cur.fetchone()
