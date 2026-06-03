#!/usr/bin/env python3
"""Mutation harness for fn_verify_before_proven Check A (cmd_mismatch).

Spike per ceo:keiracom:proof_integration_plan_v1 → spike_mutation_gate
(ref: atlas-spike-mutation-gate).

WHY A CUSTOM HARNESS (not mutmut / cosmic-ray):

  mutmut and cosmic-ray mutate Python source. The verifier we care about
  is a PL/pgSQL trigger function (fn_verify_before_proven) living in
  Postgres — mutating the Python TEST file would prove nothing about
  whether the gate itself bites. So this harness mutates the PL/pgSQL
  body in-place inside the harness's own transaction, runs targeted
  negative-path probes against the mutated trigger, then ROLLS BACK the
  entire transaction so the production fn body never changes from the
  outside world's perspective.

SAFETY MODEL:

  The harness runs in ONE long-lived transaction (autocommit=False).
  Each mutant is applied via CREATE OR REPLACE FUNCTION inside that tx.
  Postgres DDL within a transaction is visible only to the executing tx
  until commit — concurrent connections continue to see the original fn
  the entire time. The harness NEVER commits — `finally: conn.rollback()`
  discards all mutant DDL and any fixture rows. Zero production impact.

  Test fixtures (gate_roadmap row, tool_call_log row, gate_proof_runs
  row) are wrapped in SAVEPOINTs so an inner check_violation from the
  mutant doesn't break the harness's outer tx state.

ACCEPTANCE CRITERION (directive verbatim):

  "the test asserting the gate REJECTS a non-matching run_cmd must KILL
  the mutant that represents today's shape-only flip — i.e. a mutant
  that removes or weakens Check A so that a pytest-only attestation
  (run_cmd='pytest tests/db/test_proof_gate_ledger.py -v') would be
  ACCEPTED when the contract requires a different command."

  A mutant is KILLED when the negative test no longer observes
  "Check A" + "cmd_mismatch" in the error message — either the mutant
  raised something else (trg_11 dual-attest, Check B substring, etc.)
  or it didn't raise at all and the UPDATE was accepted.

USAGE:

  source /home/elliotbot/.config/agency-os/.env
  export TEST_DATABASE_URL="${DATABASE_URL//postgresql+asyncpg/postgresql}"
  PYTHONPATH=/home/elliotbot/clawd/Agency_OS \\
      python3 scripts/spike/mutation_test_check_a.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from typing import Any

import psycopg

CONTRACT = {
    "check_id": "spike_mutation_check_a",
    "cmd": "EXACTCMD_FOR_SPIKE",
    "expected_output_contains": ["SIGNAL_X", "SIGNAL_Y"],
    "role_sep": {"builder": "atlas", "attester": ["aiden", "max"]},
    "negative_test_required": True,
}

# Each scenario provides the run_cmd we will write into the proof_run.
# UNRELATED — completely different cmd; original raises, M1/M2/M3 all change behaviour.
# SUPERSET  — run_cmd CONTAINS contract.cmd as a substring; original raises (exact
#             mismatch), M_substring would accept (contains contract.cmd).
SCENARIOS: list[tuple[str, str]] = [
    ("UNRELATED_CMD", "WRONG_CMD_unrelated"),
    ("SUPERSET_CMD", CONTRACT["cmd"] + " --extra-arg suffix"),
]

# Targeted mutants of Check A. Each `old` string MUST be unique in the original
# fn body — if `mutated == original`, the harness flags the mutant as NO_APPLY
# rather than silently letting it survive.
MUTANTS: list[dict[str, str]] = [
    {
        "id": "M1_invert_distinct_from",
        "description": "Replace IS DISTINCT FROM with IS NOT DISTINCT FROM (logical inversion).",
        "old": "IF v_run_cmd IS DISTINCT FROM v_expected_cmd THEN",
        "new": "IF v_run_cmd IS NOT DISTINCT FROM v_expected_cmd THEN",
    },
    {
        "id": "M2_never_raise",
        "description": "Replace cmd-mismatch condition with false (no-op the check).",
        "old": "IF v_run_cmd IS DISTINCT FROM v_expected_cmd THEN",
        "new": "IF false THEN",
    },
    {
        "id": "M3_substring_match",
        "description": (
            "Weaken exact match to substring match — today's shape-only flip "
            "(allows a pytest-only attestation when contract.cmd happens to be "
            "a substring of the run_cmd)."
        ),
        "old": "IF v_run_cmd IS DISTINCT FROM v_expected_cmd THEN",
        "new": "IF position(v_expected_cmd IN v_run_cmd) = 0 THEN",
    },
]


def _run_output_with_signals() -> str:
    return (
        "spike mutation run_output padded for >=32 length — "
        + " ".join(CONTRACT["expected_output_contains"])
        + " — end"
    )


def _run_negative_probe(
    conn: psycopg.Connection, scenario_id: str, run_cmd: str
) -> tuple[str, str | None]:
    """Set up fixtures + attempt the proven flip — observe the outcome.

    Returns (outcome, message):
        ("RAISED_CHECK_A", msg) — original Check A behaviour preserved
        ("RAISED_OTHER",   msg) — some other trigger refused (mutant broke
                                  Check A, but downstream caught the case
                                  → still observably KILLED)
        ("DID_NOT_RAISE",  None) — mutant let the UPDATE through — KILLED
    """
    cur = conn.cursor()
    gate_id = uuid.uuid4()
    session_uuid = uuid.uuid4()
    cur.execute("SAVEPOINT spike_probe")
    try:
        cur.execute("SET LOCAL agency_os.callsign = 'atlas'")
        cur.execute(
            """
            INSERT INTO public.gate_roadmap (
                id, component, phase, subphase, proof_gate, proof_gate_contract,
                status, required_attestation_kind, owner
            ) VALUES (
                %s, %s, '0_foundation', 'gates', 'spike mutation fixture',
                %s::jsonb, 'built', 'binding_reviewer', 'atlas'
            )
            """,
            (gate_id, f"spike_mut_{scenario_id}_{uuid.uuid4().hex[:8]}", json.dumps(CONTRACT)),
        )
        cur.execute(
            """
            INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
            VALUES ('aiden', %s, 'spike_mutation', now())
            """,
            (session_uuid,),
        )
        cur.execute("SET LOCAL agency_os.callsign = 'aiden'")
        run_output = _run_output_with_signals()
        sha = hashlib.sha256(f"spike|{scenario_id}|{run_cmd}|{session_uuid}".encode()).hexdigest()
        cur.execute(
            """
            INSERT INTO public.gate_proof_runs (
                gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
                exit_code, attesting_callsign, attester_session_uuid
            ) VALUES (
                %s, 'binding_reviewer', %s, %s, %s, 0, 'aiden', %s
            )
            RETURNING id
            """,
            (gate_id, run_cmd, run_output, sha, str(session_uuid)),
        )
        run_id = cur.fetchone()[0]

        cur.execute("SET LOCAL agency_os.callsign = 'dave'")
        try:
            cur.execute(
                "UPDATE public.gate_roadmap SET status='proven', proof_run_id=%s WHERE id=%s",
                (run_id, gate_id),
            )
            return "DID_NOT_RAISE", None
        except psycopg.errors.CheckViolation as exc:
            msg = str(exc).strip()
            if "Check A" in msg and "cmd_mismatch" in msg:
                return "RAISED_CHECK_A", msg
            return "RAISED_OTHER", msg
    finally:
        cur.execute("ROLLBACK TO SAVEPOINT spike_probe")


def _fetch_original_fn(conn: psycopg.Connection) -> str:
    cur = conn.cursor()
    cur.execute("SELECT pg_get_functiondef('fn_verify_before_proven'::regproc)")
    return cur.fetchone()[0]


def main() -> int:
    dsn = os.environ.get("TEST_DATABASE_URL", "")
    if not dsn:
        sys.stderr.write("ERROR: TEST_DATABASE_URL not set.\n")
        return 2

    conn = psycopg.connect(dsn, autocommit=False)
    original = _fetch_original_fn(conn)

    print("=" * 78)
    print("MUTATION HARNESS — fn_verify_before_proven Check A (cmd_mismatch)")
    print("=" * 78)
    print(f"Original fn body length: {len(original)} chars")
    print("Tx isolation: harness runs in a single uncommitted transaction; ")
    print("              DDL mutants are visible only to this tx and are ")
    print("              discarded by the final ROLLBACK.")
    print()

    cur = conn.cursor()
    results: list[dict[str, Any]] = []

    try:
        # ── Baseline ────────────────────────────────────────────────────────
        print("--- BASELINE (original fn) ---")
        baseline_outcomes = []
        for scen, cmd in SCENARIOS:
            outcome, msg = _run_negative_probe(conn, scen, cmd)
            baseline_outcomes.append((scen, outcome, msg))
            print(f"  scenario={scen:14s}  outcome={outcome}")
            print(f"    message: {(msg or '')[:240]}")
        baseline_ok = all(o[1] == "RAISED_CHECK_A" for o in baseline_outcomes)
        print(f"\nBaseline pass (all RAISED_CHECK_A): {baseline_ok}")

        # ── Each mutant ─────────────────────────────────────────────────────
        for m in MUTANTS:
            print(f"\n--- MUTANT {m['id']} ---")
            print(f"    {m['description']}")
            mutated = original.replace(m["old"], m["new"])
            if mutated == original:
                print("    WARNING: mutant did not apply (old text not found in fn body).")
                results.append({"id": m["id"], "status": "NO_APPLY", "scenarios": []})
                continue

            cur.execute(mutated)

            scenario_outcomes: list[tuple[str, str, str | None]] = []
            for scen, cmd in SCENARIOS:
                outcome, msg = _run_negative_probe(conn, scen, cmd)
                scenario_outcomes.append((scen, outcome, msg))
                print(f"    scenario={scen:14s}  outcome={outcome}")
                print(f"      message: {(msg or '')[:240]}")

            # Mutant is KILLED iff the negative test no longer observes Check A
            # on AT LEAST ONE scenario (the test that previously detected this
            # class of weakening).
            killed = any(o[1] != "RAISED_CHECK_A" for o in scenario_outcomes)
            results.append(
                {
                    "id": m["id"],
                    "description": m["description"],
                    "status": "KILLED" if killed else "SURVIVED",
                    "scenarios": scenario_outcomes,
                }
            )

            # Restore original within the tx so the next mutant starts clean.
            cur.execute(original)

    finally:
        # Hard rollback — discard every DDL change + every fixture insert.
        conn.rollback()
        conn.close()

    # ── Report ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    print("MUTATION REPORT")
    print("=" * 78)
    print(f"{'Mutant ID':32s}  {'Status':10s}  Scenario outcomes")
    print("-" * 78)
    for r in results:
        scen_str = ", ".join(f"{s[0]}={s[1]}" for s in r.get("scenarios", []))
        print(f"{r['id']:32s}  {r['status']:10s}  {scen_str}")

    n_killed = sum(1 for r in results if r["status"] == "KILLED")
    n_survived = sum(1 for r in results if r["status"] == "SURVIVED")
    n_no_apply = sum(1 for r in results if r["status"] == "NO_APPLY")
    print(
        f"\nTotal: {n_killed} KILLED, {n_survived} SURVIVED, "
        f"{n_no_apply} NO_APPLY (out of {len(results)})."
    )
    # Exit 0 iff every applied mutant was killed (no survivors).
    return 0 if n_survived == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
