"""Dogfood tests for proof_gate_ledger base — verify trg_01 (fn_verify_before_proven)
enforces contract Checks A/B/C on the live database.

The four named test functions BELOW are the load-bearing contract tokens
recorded in ceo:keiracom:proof_gate_ledger_design_v1 and seeded as the
gate_roadmap.proof_gate_contract.expected_output_contains list on row
gate_roadmap_id = 8ccca6bc-6478-4f8e-a173-0500474d8b41. Renaming any of them
breaks the binding_reviewer pair's ability to verify the dogfood proof_run
output substring matches — DO NOT rename without coordinating a follow-up
migration that updates the seed contract in lockstep.

ref: atlas-proof-gate-ledger-base-build
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

# Use TEST_DATABASE_URL (Agency_OS convention — tests/conftest.py overrides
# DATABASE_URL to a fake "localhost:5432/test_db" so unit tests cannot
# accidentally hit a real database; live-DB tests opt in via TEST_DATABASE_URL).
_DSN = os.environ.get("TEST_DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")

pytestmark = pytest.mark.skipif(
    not _DSN,
    reason="TEST_DATABASE_URL not set — proof_gate_ledger dogfood tests skipped",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_CONTRACT = {
    "check_id": "proof_gate_ledger_dogfood_pytest",
    "cmd": "EXACTCMD_FOR_DOGFOOD",
    "expected_output_contains": [
        "MUST_APPEAR_TOKEN_ONE",
        "MUST_APPEAR_TOKEN_TWO",
    ],
    "role_sep": {"builder": "atlas", "attester": ["aiden", "max"]},
    "negative_test_required": True,
}


def _build_run_output(*, include: list[str]) -> str:
    """Return >=32-char run_output containing the given substrings."""
    base = "dogfood proof_run output padded out to satisfy the >=32 length check — "
    return base + " ".join(include) + " — end"


def _connect() -> psycopg.Connection:
    return psycopg.connect(_DSN, autocommit=False)


def _seed_fixture(
    cur: psycopg.Cursor,
    *,
    contract: dict,
    component_suffix: str,
    session_uuid: uuid.UUID,
    attester_callsign: str = "aiden",
) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert temp gate_roadmap + tool_call_log rows. Returns (gate_id, gate_id_unused)."""
    import json

    gate_id = uuid.uuid4()
    cur.execute("SET LOCAL agency_os.callsign = 'atlas'")
    cur.execute(
        """
        INSERT INTO public.gate_roadmap (
            id, component, phase, subphase, proof_gate, proof_gate_contract,
            status, required_attestation_kind, owner
        ) VALUES (
            %s, %s, '0_foundation', 'gates',
            'dogfood pytest fixture row',
            %s::jsonb,
            'built', 'binding_reviewer', 'atlas'
        )
        """,
        (gate_id, f"proof_gate_ledger_DOGFOOD_{component_suffix}", json.dumps(contract)),
    )
    cur.execute(
        """
        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES (%s, %s, 'dogfood_pytest', now())
        """,
        (attester_callsign, session_uuid),
    )
    return gate_id, gate_id


def _insert_proof_run(
    cur: psycopg.Cursor,
    *,
    gate_id: uuid.UUID,
    run_cmd: str,
    run_output: str,
    attesting_callsign: str,
    attester_session_uuid: uuid.UUID,
) -> uuid.UUID:
    import hashlib

    # Derive a per-row sha so (gate_roadmap_id, output_sha256) stays unique
    # across multiple proof_run inserts on the same gate (e.g. aiden + max
    # for the positive-control dual-attest scenario). CEO Q2: SHA is
    # application-layer, trigger only validates length=64 + uniqueness.
    sha = hashlib.sha256(
        f"{attesting_callsign}|{attester_session_uuid}|{run_cmd}|{run_output}".encode()
    ).hexdigest()
    cur.execute(
        f"SET LOCAL agency_os.callsign = {psycopg.sql.Literal(attesting_callsign).as_string(cur)}"
    )
    cur.execute(
        """
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid
        ) VALUES (
            %s, 'binding_reviewer', %s, %s, %s, 0, %s, %s
        )
        RETURNING id
        """,
        (
            gate_id,
            run_cmd,
            run_output,
            sha,
            attesting_callsign,
            str(attester_session_uuid),
        ),
    )
    return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# Test 1 — Check B (output substring missing)
# ---------------------------------------------------------------------------


def test_negative_mismatched_output_raises():
    """Mismatched run_output (missing required substring) → Check B raises."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            session_uuid = uuid.uuid4()
            gate_id, _ = _seed_fixture(
                cur,
                contract=_CONTRACT,
                component_suffix=f"OUTPUT_{uuid.uuid4().hex[:8]}",
                session_uuid=session_uuid,
            )
            run_id = _insert_proof_run(
                cur,
                gate_id=gate_id,
                run_cmd=_CONTRACT["cmd"],  # cmd MATCHES — only output is wrong
                run_output=_build_run_output(include=["MUST_APPEAR_TOKEN_ONE"]),  # missing TWO
                attesting_callsign="aiden",
                attester_session_uuid=session_uuid,
            )
            cur.execute("SET LOCAL agency_os.callsign = 'dave'")
            with pytest.raises(psycopg.errors.CheckViolation) as exc_info:
                cur.execute(
                    "UPDATE public.gate_roadmap SET status='proven', proof_run_id=%s WHERE id=%s",
                    (run_id, gate_id),
                )
            assert "Check B" in str(exc_info.value)
            assert "output_substring_missing" in str(exc_info.value)
            assert "MUST_APPEAR_TOKEN_TWO" in str(exc_info.value)
    finally:
        conn.rollback()
        conn.close()


# ---------------------------------------------------------------------------
# Test 2 — Check A (cmd mismatch)
# ---------------------------------------------------------------------------


def test_negative_cmd_mismatch_raises():
    """run_cmd != contract.cmd → Check A raises."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            session_uuid = uuid.uuid4()
            gate_id, _ = _seed_fixture(
                cur,
                contract=_CONTRACT,
                component_suffix=f"CMD_{uuid.uuid4().hex[:8]}",
                session_uuid=session_uuid,
            )
            run_id = _insert_proof_run(
                cur,
                gate_id=gate_id,
                run_cmd="WRONG_CMD",
                run_output=_build_run_output(include=_CONTRACT["expected_output_contains"]),
                attesting_callsign="aiden",
                attester_session_uuid=session_uuid,
            )
            cur.execute("SET LOCAL agency_os.callsign = 'dave'")
            with pytest.raises(psycopg.errors.CheckViolation) as exc_info:
                cur.execute(
                    "UPDATE public.gate_roadmap SET status='proven', proof_run_id=%s WHERE id=%s",
                    (run_id, gate_id),
                )
            assert "Check A" in str(exc_info.value)
            assert "cmd_mismatch" in str(exc_info.value)
    finally:
        conn.rollback()
        conn.close()


# ---------------------------------------------------------------------------
# Test 3 — Check C (attester == builder)
# ---------------------------------------------------------------------------


def test_negative_attester_ne_builder_raises():
    """attesting_callsign == contract.role_sep.builder → Check C raises.

    Builder is 'atlas' in our contract. We must attempt to attest as 'atlas'.
    trg_04 (no-self-attest) will raise at INSERT before our trigger sees the
    flip — so this test exercises Check C via a contract whose builder
    differs from gate_roadmap.built_by_callsign, isolating Check C as the
    sole gate the trigger runs.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            session_uuid = uuid.uuid4()
            # Override contract.role_sep.builder to 'aiden' so the attester
            # (aiden) collides with contract.role_sep.builder but NOT with
            # gate_roadmap.built_by_callsign (atlas) — trg_04 passes, only
            # the new Check C raises.
            contract = {
                **_CONTRACT,
                "role_sep": {"builder": "aiden", "attester": ["max"]},
            }
            gate_id, _ = _seed_fixture(
                cur,
                contract=contract,
                component_suffix=f"ATT_{uuid.uuid4().hex[:8]}",
                session_uuid=session_uuid,
                attester_callsign="aiden",
            )
            run_id = _insert_proof_run(
                cur,
                gate_id=gate_id,
                run_cmd=contract["cmd"],
                run_output=_build_run_output(include=contract["expected_output_contains"]),
                attesting_callsign="aiden",  # == contract.role_sep.builder
                attester_session_uuid=session_uuid,
            )
            cur.execute("SET LOCAL agency_os.callsign = 'dave'")
            with pytest.raises(psycopg.errors.CheckViolation) as exc_info:
                cur.execute(
                    "UPDATE public.gate_roadmap SET status='proven', proof_run_id=%s WHERE id=%s",
                    (run_id, gate_id),
                )
            assert "Check C" in str(exc_info.value)
            assert "attester_eq_builder" in str(exc_info.value)
    finally:
        conn.rollback()
        conn.close()


# ---------------------------------------------------------------------------
# Test 4 — positive control (Checks A + B + C all pass)
# ---------------------------------------------------------------------------


def test_positive_control_accepted():
    """run_cmd == contract.cmd AND run_output contains all expected_output_contains
    AND attester != builder → trigger ACCEPTS the proven flip.

    Note: trg_11 (dual_attest) requires BOTH aiden AND max binding_reviewer
    proof_runs. We insert both, point proof_run_id at aiden's, and verify
    the UPDATE succeeds.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            session_aiden = uuid.uuid4()
            session_max = uuid.uuid4()
            gate_id, _ = _seed_fixture(
                cur,
                contract=_CONTRACT,
                component_suffix=f"POS_{uuid.uuid4().hex[:8]}",
                session_uuid=session_aiden,
            )
            # tool_call_log row for max so trg_06 passes for max's proof_run.
            cur.execute(
                """
                INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
                VALUES ('max', %s, 'dogfood_pytest', now())
                """,
                (session_max,),
            )

            aiden_run_id = _insert_proof_run(
                cur,
                gate_id=gate_id,
                run_cmd=_CONTRACT["cmd"],
                run_output=_build_run_output(include=_CONTRACT["expected_output_contains"]),
                attesting_callsign="aiden",
                attester_session_uuid=session_aiden,
            )
            _insert_proof_run(
                cur,
                gate_id=gate_id,
                run_cmd=_CONTRACT["cmd"],
                run_output=_build_run_output(include=_CONTRACT["expected_output_contains"]),
                attesting_callsign="max",
                attester_session_uuid=session_max,
            )

            cur.execute("SET LOCAL agency_os.callsign = 'dave'")
            cur.execute(
                "UPDATE public.gate_roadmap SET status='proven', proof_run_id=%s WHERE id=%s",
                (aiden_run_id, gate_id),
            )
            # Verify the flip landed (still inside the transaction).
            cur.execute("SELECT status FROM public.gate_roadmap WHERE id=%s", (gate_id,))
            assert cur.fetchone()[0] == "proven"
    finally:
        conn.rollback()
        conn.close()
