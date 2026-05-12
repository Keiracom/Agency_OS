"""Drevon port end-to-end smoke against real Supabase.

Env-gated: skipped unless INTEGRATION=1 AND SUPABASE_URL/SUPABASE_SERVICE_KEY
are present. Default `pytest tests/integration/` collects but skips this file.
Run with:

    INTEGRATION=1 python3 -m pytest tests/integration/test_drevon_port_smoke.py -v

Scenarios:
  1. Inserts a synthetic session + turn + turn_log under a disposable callsign.
  2. resolve_session_uuid finds the synthetic session (resume path).
  3. verify_completion_claim returns True for a claim referencing the synthetic
     PR# (evidence present in the turn_logs row's tool_args_json).
  4. verify_completion_claim returns False for a claim referencing a PR# that
     has no synthetic evidence.

Cleanup: every synthetic row soft-deleted (`deleted_at = NOW()`) so production
data and the partial indexes are unaffected.
"""

from __future__ import annotations

import contextlib
import os
import random
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

DEFAULT_DOTENV = Path("/home/elliotbot/.config/agency-os/.env")

pytestmark = pytest.mark.skipif(
    os.environ.get("INTEGRATION") != "1",
    reason="Set INTEGRATION=1 to run (real-Supabase smoke).",
)


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


@pytest.fixture(autouse=True)
def _real_supabase_creds(monkeypatch):
    """tests/conftest.py overrides SUPABASE_URL/KEY to mock values for unit
    tests. This integration test needs the real prod creds — pull them from
    the .env file (or DREVON_DOTENV env override) and patch supabase_client's
    cached module-level constants. Skips cleanly if creds aren't loadable."""
    from dotenv import dotenv_values

    dotenv_path = Path(os.environ.get("DREVON_DOTENV", DEFAULT_DOTENV))
    if not dotenv_path.exists():
        pytest.skip(f"dotenv not found at {dotenv_path}; cannot load real creds")
    values = dotenv_values(dotenv_path)
    url = values.get("SUPABASE_URL")
    key = values.get("SUPABASE_SERVICE_KEY")
    if not url or not key or "test.supabase.co" in url:
        pytest.skip(f"real SUPABASE_URL/SUPABASE_SERVICE_KEY missing in {dotenv_path}")

    from src.evo import supabase_client

    monkeypatch.setattr(supabase_client, "_URL", url)
    monkeypatch.setattr(supabase_client, "_KEY", key)
    monkeypatch.setattr(
        supabase_client,
        "_HEADERS",
        {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )


@pytest.fixture
def synthetic_drevon_rows():
    """Insert sessions + turn + turn_log; yield IDs + a unique synthetic PR#;
    soft-delete on teardown so prod pollution is bounded."""
    from src.evo.supabase_client import sb_patch, sb_post

    # Disposable callsign so resolver queries can't hit a real-callsign row.
    suffix = uuid.uuid4().hex[:8]
    callsign = f"orion-int-{suffix}"
    # Bizarre 8-digit PR# unlikely to appear in real turn_logs (real PRs are
    # currently 3-digit). Random within the range so concurrent runs collide
    # at vanishing probability.
    synthetic_pr = random.randint(99_000_000, 99_999_999)
    fabricated_pr = random.randint(98_000_000, 98_999_999)
    session_uid = str(uuid.uuid4())
    session_row = sb_post(
        "sessions",
        {
            "callsign": callsign,
            "session_uuid": session_uid,
            "working_directory": f"/tmp/drevon-port-smoke-{suffix}",
            "started_at": _utc_iso(),
            "status": "active",
        },
    )[0]
    turn_row = sb_post(
        "turns",
        {
            "session_id": session_row["id"],
            "turn_index": 0,
            "started_at": _utc_iso(),
        },
    )[0]
    log_row = sb_post(
        "turn_logs",
        {
            "turn_id": turn_row["id"],
            "tool_name": "Bash",
            "tool_args_json": {
                "command": f"bash scripts/verify_pr.sh {synthetic_pr}",
                "description": "drevon-port-smoke synthetic evidence",
            },
            "tool_result_summary": f"verify_pr.sh exited 0 for PR #{synthetic_pr}",
            "exit_status": "success",
            "started_at": _utc_iso(),
        },
    )[0]
    yield {
        "callsign": callsign,
        "session_uuid": session_uid,
        "synthetic_pr": synthetic_pr,
        "fabricated_pr": fabricated_pr,
        "session_id": session_row["id"],
        "turn_id": turn_row["id"],
        "log_id": log_row["id"],
    }
    deleted_iso = _utc_iso()
    for table, row_id in (
        ("turn_logs", log_row["id"]),
        ("turns", turn_row["id"]),
        ("sessions", session_row["id"]),
    ):
        # Best-effort cleanup — never fail teardown.
        with contextlib.suppress(Exception):
            sb_patch(table, {"id": f"eq.{row_id}"}, {"deleted_at": deleted_iso})


def _import_resolver_or_skip():
    """src.session_resumption ships in PR #725 (currently OPEN). Once merged
    these tests run inline; until then they skip cleanly. Tests for the
    `.resolver` submodule explicitly — a leftover __pycache__ would let the
    namespace package import succeed but fail at the function lookup."""
    pytest.importorskip(
        "src.session_resumption.resolver",
        reason="src.session_resumption.resolver not on main yet (PR #725 pending)",
    )
    from src.session_resumption.resolver import resolve_session_uuid

    return resolve_session_uuid


def test_resolve_session_uuid_finds_synthetic_session(synthetic_drevon_rows):
    resolve_session_uuid = _import_resolver_or_skip()
    found = resolve_session_uuid(synthetic_drevon_rows["callsign"])
    assert found == synthetic_drevon_rows["session_uuid"]


def test_verify_completion_claim_returns_true_for_synthetic_evidence(
    synthetic_drevon_rows,
):
    from src.replay.claim_verifier import verify_completion_claim

    pr = synthetic_drevon_rows["synthetic_pr"]
    verified, reason = verify_completion_claim(f"Done shipping PR #{pr} to main.")
    assert verified is True, f"expected evidence-found, got reason={reason!r}"
    assert "verify_pr.sh" in reason or str(pr) in reason


def test_verify_completion_claim_handles_missing_evidence_path(synthetic_drevon_rows):
    """No-evidence path must remain safe (returns False with a reason string,
    never raises). Anchors the best-effort contract."""
    from src.replay.claim_verifier import verify_completion_claim

    pr = synthetic_drevon_rows["fabricated_pr"]
    verified, reason = verify_completion_claim(f"Done shipping PR #{pr} to main.")
    assert verified is False
    assert isinstance(reason, str) and reason


def test_soft_deleted_session_excluded_from_resolver(synthetic_drevon_rows):
    """Cleanup contract — once deleted_at is set the resolver must not see it."""
    from src.evo.supabase_client import sb_patch

    resolve_session_uuid = _import_resolver_or_skip()
    sb_patch(
        "sessions",
        {"id": f"eq.{synthetic_drevon_rows['session_id']}"},
        {"deleted_at": _utc_iso()},
    )
    found = resolve_session_uuid(synthetic_drevon_rows["callsign"])
    assert found is None
