"""Tests for src/orchestration/flows/pool_population_flow.py BU-exclusion query.

BU-CLOSED-LOOP-C5 — verifies _exclude_existing_bu_domains drops candidates
already in business_universe while honouring the permanent-drop carve-out
that keeps re-discoverable rows reachable.

Hermetic — no live DB. Mocks the SQLAlchemy session returned by
get_db_session().

Coverage matrix per dispatch:
  (a) existing-domain-skipped              — active row blocks re-INSERT
  (b) new-domain-inserted                  — unmatched candidate passes
  (c) permanently-dropped-row-allowed-through — pipeline_status='dropped'
      AND filter_reason LIKE 'permanent_%' carve-out
  (d) soft-deleted/non-permanent-dropped row still excluded
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import os
from unittest.mock import AsyncMock, MagicMock

import pytest


os.environ.setdefault("DATABASE_URL", "postgresql://stub:stub@stub:5432/stub")

flow_mod = importlib.import_module("src.orchestration.flows.pool_population_flow")


# ── helpers ─────────────────────────────────────────────────────────────────


def _candidate(gmb_domain: str, abn: str = "12345678901") -> dict:
    """Build a minimal bu_gmb_rows entry mirroring the production INSERT shape."""
    return {
        "abn": abn,
        "gmb_place_id": f"place-{gmb_domain}",
        "gmb_cid": None,
        "gmb_category": None,
        "gmb_rating": None,
        "gmb_review_count": None,
        "gmb_phone": None,
        "gmb_website": f"https://{gmb_domain}",
        "gmb_domain": gmb_domain,
        "gmb_address": None,
        "gmb_city": None,
        "gmb_latitude": None,
        "gmb_longitude": None,
    }


def _patch_session(monkeypatch, fetched_rows: list[tuple[str | None, str | None]]):
    """Stub get_db_session so the SELECT returns `fetched_rows` (list of
    (domain, gmb_domain) tuples). Captures the bound :incoming param so the
    test can also assert on the candidate batch sent to SQL."""
    captured: dict[str, list] = {"incoming_calls": []}

    fake_result = MagicMock()
    fake_result.fetchall = MagicMock(return_value=fetched_rows)

    fake_session = MagicMock()

    async def _capture_execute(*args, **kwargs):
        # args[0] is the text(...) clause; args[1] is the params dict.
        if len(args) >= 2 and isinstance(args[1], dict):
            captured["incoming_calls"].append(args[1].get("incoming"))
        return fake_result

    fake_session.execute = AsyncMock(side_effect=_capture_execute)

    @contextlib.asynccontextmanager
    async def fake_get_db_session():
        yield fake_session

    monkeypatch.setattr(flow_mod, "get_db_session", fake_get_db_session)
    return captured


# ── coverage matrix ─────────────────────────────────────────────────────────


def test_a_existing_domain_skipped(monkeypatch):
    """Active BU row carrying gmb_domain='already.com.au' blocks re-INSERT."""
    captured = _patch_session(
        monkeypatch,
        fetched_rows=[(None, "already.com.au")],  # SELECT returns blocking row
    )

    candidates = [_candidate("already.com.au"), _candidate("fresh.com.au")]
    kept = asyncio.run(flow_mod._exclude_existing_bu_domains(candidates))

    assert len(kept) == 1
    assert kept[0]["gmb_domain"] == "fresh.com.au"
    # Sanity — exactly one SELECT issued, with both incoming domains bound.
    assert captured["incoming_calls"] == [["already.com.au", "fresh.com.au"]]


def test_b_new_domain_inserted(monkeypatch):
    """All candidates are new — none blocked. Helper returns the input unchanged."""
    _patch_session(monkeypatch, fetched_rows=[])  # nothing in BU yet

    candidates = [_candidate("new1.com.au"), _candidate("new2.com.au")]
    kept = asyncio.run(flow_mod._exclude_existing_bu_domains(candidates))

    assert len(kept) == 2
    assert {r["gmb_domain"] for r in kept} == {"new1.com.au", "new2.com.au"}


def test_c_permanently_dropped_row_allowed_through(monkeypatch):
    """A BU row with pipeline_status='dropped' AND filter_reason LIKE
    'permanent_%' is the future-thaw carve-out — it must NOT appear in the
    blocked set, so the candidate is allowed through. We simulate the
    SELECT returning [] for this domain (matching the SQL's NOT-permanent
    clause behavior)."""
    _patch_session(monkeypatch, fetched_rows=[])  # SQL excludes permanent_*
    candidates = [_candidate("thaw.com.au")]

    kept = asyncio.run(flow_mod._exclude_existing_bu_domains(candidates))

    assert len(kept) == 1
    assert kept[0]["gmb_domain"] == "thaw.com.au"


def test_d_soft_deleted_or_non_permanent_dropped_still_excluded(monkeypatch):
    """A BU row that is soft-deleted (deleted_at IS NOT NULL) OR dropped
    without a 'permanent_' filter_reason DOES block re-INSERT. We simulate
    by having the SELECT return the matching row (the SQL's WHERE clause
    does the soft-delete + non-permanent filtering server-side)."""
    _patch_session(
        monkeypatch,
        fetched_rows=[
            ("dropped-temp.com.au", None),  # ordinary dropped, blocks
        ],
    )
    candidates = [_candidate("dropped-temp.com.au"), _candidate("ok.com.au")]

    kept = asyncio.run(flow_mod._exclude_existing_bu_domains(candidates))

    assert len(kept) == 1
    assert kept[0]["gmb_domain"] == "ok.com.au"


# ── SQL-shape regressions (defends the carve-out clause from accidental edits) ──


def test_select_excludes_soft_deleted_rows():
    """The SELECT WHERE clause must include 'deleted_at IS NULL' so soft-
    deleted rows do not leak into the blocked set (preserving GOV-8 audit
    trail without re-suppressing future re-discovery)."""
    import inspect

    src = inspect.getsource(flow_mod._exclude_existing_bu_domains)
    assert "deleted_at IS NULL" in src


def test_select_carves_out_permanent_drop_only():
    """The SELECT must NOT block rows where pipeline_status='dropped'
    AND filter_reason LIKE 'permanent_%' — that is the thaw carve-out."""
    import inspect

    src = inspect.getsource(flow_mod._exclude_existing_bu_domains)
    assert "pipeline_status = 'dropped'" in src
    assert "filter_reason LIKE 'permanent_%%'" in src
    # The clause is wrapped in NOT(...) so 'permanent_' rows pass through.
    # A simple presence check is sufficient given the SQL is short.
    assert "NOT (" in src


def test_select_matches_either_domain_or_gmb_domain():
    """Both BU domain columns are valid blocking keys — SELECT must
    consult both."""
    import inspect

    src = inspect.getsource(flow_mod._exclude_existing_bu_domains)
    assert "domain     = ANY(:incoming::text[])" in src
    assert "gmb_domain = ANY(:incoming::text[])" in src


def test_helper_short_circuits_when_no_candidates_have_domains():
    """If every candidate has gmb_domain=None the helper returns the input
    unchanged without issuing any SELECT — saves a DB round-trip on an
    all-null batch."""
    captured = _patch_session(
        MagicMock(setattr=lambda *a, **kw: None),  # no-op patch
        fetched_rows=[],
    )

    candidates = [{"abn": "x", "gmb_domain": None}]
    # Direct call — _patch_session above won't be reached because helper returns early.
    kept = asyncio.run(flow_mod._exclude_existing_bu_domains(candidates))
    assert kept == candidates


def test_helper_logs_skip_count_and_sample(monkeypatch, caplog):
    """When candidates are skipped the helper emits a structured info line
    so the de-dup ratio is observable in run logs."""
    _patch_session(
        monkeypatch,
        fetched_rows=[("dup1.com.au", None), (None, "dup2.com.au")],
    )
    candidates = [_candidate("dup1.com.au"), _candidate("dup2.com.au"), _candidate("fresh.com.au")]

    import logging

    with caplog.at_level(logging.INFO, logger=flow_mod.logger.name):
        kept = asyncio.run(flow_mod._exclude_existing_bu_domains(candidates))

    assert len(kept) == 1
    assert kept[0]["gmb_domain"] == "fresh.com.au"
    # Structured log line must be emitted with the skip count.
    log_text = " ".join(r.getMessage() for r in caplog.records)
    assert "pool_population_skipped_existing_bus" in log_text
    assert "count=2" in log_text
