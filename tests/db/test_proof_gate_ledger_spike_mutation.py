"""Spike test: assert the gate KILLS the substring (shape-only) mutant of Check A.

Lives in its own file (NOT in tests/db/test_proof_gate_ledger.py) so the four
load-bearing dogfood function names in that file remain contract-locked. The
test below is a regression catch — without it, a future shape-only weakening
of Check A would slip past the pytest dogfood suite (the existing
test_negative_cmd_mismatch_raises uses an UNRELATED_CMD shape which a
position()-based substring check would still happen to reject).

Tested directly against the live trigger via TEST_DATABASE_URL — same opt-in
convention as the dogfood file (tests/conftest.py rewires DATABASE_URL to a
fake "test_db" for unit tests, so live-DB tests must read from
TEST_DATABASE_URL).

ref: atlas-spike-mutation-gate + ceo:keiracom:proof_integration_plan_v1
"""

from __future__ import annotations

import os

import psycopg
import pytest

# Reuse the dogfood helpers — they're the canonical fixtures for the live trigger.
from tests.db.test_proof_gate_ledger import (
    _CONTRACT,
    _build_run_output,
    _connect,
    _insert_proof_run,
    _seed_fixture,
)

_DSN = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not _DSN,
    reason="TEST_DATABASE_URL not set — spike mutation test skipped",
)


def test_negative_cmd_superset_raises():
    """run_cmd is a strict SUPERSET of contract.cmd → Check A must still raise.

    Shape-only flip the harness probes (M3_substring_match): an attacker
    submits a run_cmd that CONTAINS contract.cmd as a substring but is not
    equal — e.g. ``contract.cmd + " --extra-arg"``.

    Under exact-match Check A: the cmds are not equal → Check A raises.
    Under substring-match mutant: contract.cmd IS in run_cmd → position > 0
    → IF position(..) = 0 evaluates FALSE → no raise → downstream catches it
    via trg_11 dual-attest instead, with a message that lacks "Check A" /
    "cmd_mismatch" tokens. This test asserts the original exact-match
    behaviour by demanding those tokens in the error message — so a
    shape-only flip would make these asserts fail, killing the mutant.
    """
    import uuid

    conn = _connect()
    try:
        with conn.cursor() as cur:
            session_uuid = uuid.uuid4()
            gate_id, _ = _seed_fixture(
                cur,
                contract=_CONTRACT,
                component_suffix=f"SUPERSET_{uuid.uuid4().hex[:8]}",
                session_uuid=session_uuid,
            )
            run_id = _insert_proof_run(
                cur,
                gate_id=gate_id,
                # Strict superset — contains contract.cmd but is not equal.
                run_cmd=_CONTRACT["cmd"] + " --extra-arg suffix",
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
            assert "Check A" in str(exc_info.value), (
                "Check A (exact cmd match) did not raise on superset cmd — "
                "the verifier may have been weakened to substring/shape match. "
                f"Got: {exc_info.value!s}"
            )
            assert "cmd_mismatch" in str(exc_info.value)
    finally:
        conn.rollback()
        conn.close()
