"""tests/proof_tier/test_reasoning_records_real_pg.py — REAL Postgres proof.

Per gate_roadmap.spike_real_deps_proof: prove the trg_08 write-guard on
public.reasoning_records by exercising it against a throwaway Postgres
container, NOT a Python-side mock or shim. Asserts on the verbatim PG
exception message — the proof_gate's "verbatim RAISE" requirement.
"""

from __future__ import annotations

import psycopg


def test_trigger_refuses_insert_without_session_var(reasoning_records_schema):
    """trg_08 RAISES on INSERT when agency_os.callsign is unset.

    The PostgreSQL RAISE message text is the proof. We capture the literal
    string from the live Postgres process running in the container.
    """
    dsn = reasoning_records_schema
    raised_msg = None
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        try:
            cur.execute(
                "INSERT INTO public.reasoning_records "
                "(chain_id, hop_name, callsign, source, "
                " decision, challenge, tradeoffs, rejected_options) "
                "VALUES (%s, %s, %s, 'temporal_activity', %s, %s, %s, %s)",
                ("real-pg-no-session-var", "aiden_plan", "aiden", "d", "c", "t", "r"),
            )
        except psycopg.errors.CheckViolation as exc:
            raised_msg = str(exc)
        conn.rollback()
    assert raised_msg is not None, "trg_08 did NOT raise — proof tier FAIL"
    assert "reasoning_records write-guard" in raised_msg, (
        f"verbatim RAISE missing the write-guard marker: {raised_msg!r}"
    )
    assert "agency_os.callsign" in raised_msg, (
        f"verbatim RAISE missing the session-var marker: {raised_msg!r}"
    )
    print(f"\nVERBATIM RAISE: {raised_msg!s}")


def test_trigger_admits_insert_with_session_var(reasoning_records_schema):
    """Positive control: set agency_os.callsign in a transaction → INSERT succeeds.

    Mirrors the production capture_hop_reasoning() pattern (set_config(true)
    within a transaction, then INSERT in the same transaction).
    """
    dsn = reasoning_records_schema
    inserted_id = None
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT set_config('agency_os.callsign', %s, true)", ("orion",))
        cur.execute(
            "INSERT INTO public.reasoning_records "
            "(chain_id, hop_name, callsign, source, "
            " decision, challenge, tradeoffs, rejected_options) "
            "VALUES (%s, %s, %s, 'temporal_activity', %s, %s, %s, %s) "
            "RETURNING id",
            (
                "real-pg-positive",
                "orion_spec",
                "orion",
                "Add (state, expires_at) to keiracom_handoffs; BRIN expires_at.",
                "BRIN+UPDATE breaks heap-locality.",
                "BRIN 100x smaller vs degrades under updates.",
                "BTREE — index size bottleneck at 50/s 30d.",
            ),
        )
        row = cur.fetchone()
        inserted_id = row[0] if row else None
        conn.commit()
    assert inserted_id is not None, "positive-path INSERT returned no id"


def test_source_check_constraint_refuses_unknown_value(reasoning_records_schema):
    """source CHECK ('temporal_activity') refuses any other value verbatim."""
    dsn = reasoning_records_schema
    raised_msg = None
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT set_config('agency_os.callsign', %s, true)", ("orion",))
        try:
            cur.execute(
                "INSERT INTO public.reasoning_records "
                "(chain_id, hop_name, callsign, source, "
                " decision, challenge, tradeoffs, rejected_options) "
                "VALUES (%s, %s, %s, 'manual', %s, %s, %s, %s)",
                ("real-pg-bad-source", "aiden_plan", "aiden", "d", "c", "t", "r"),
            )
        except psycopg.errors.CheckViolation as exc:
            raised_msg = str(exc)
        conn.rollback()
    assert raised_msg is not None, "source CHECK did NOT raise on value='manual'"
    assert "reasoning_records_source_check" in raised_msg or "source" in raised_msg, (
        f"verbatim RAISE missing source-check marker: {raised_msg!r}"
    )
    print(f"\nVERBATIM RAISE (source CHECK): {raised_msg!s}")
