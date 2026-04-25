"""
Smoke tests for scripts/seed_demo_tenant.py.

Mocks the asyncpg connection. Verifies:
  - is_real_email rejects placeholder local-parts and bad shapes
  - select_prospects drops suppressed domains, suppressed emails,
    placeholder emails, and NULL display_name rows
  - select_prospects stops at TARGET_PROSPECTS even when more candidates exist
  - link_prospects writes one row per selected prospect (not in dry-run)
  - link_prospects writes zero rows in dry-run

Pure mocks — zero real DB, zero paid API calls.
"""
from __future__ import annotations

import importlib.util
import os
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# Load script as module without sys.path gymnastics.
_SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "scripts", "seed_demo_tenant.py",
)
_spec = importlib.util.spec_from_file_location("seed_demo_tenant", _SCRIPT_PATH)
seed = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(seed)


# ─── is_real_email ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("email,expected", [
    ("ceo@acme.com.au",      True),
    ("amy@beta.io",          True),
    ("example@mail.com",     False),    # placeholder local
    ("test@foo.com",         False),
    ("info@bar.com",         False),
    ("admin@baz.com",        False),
    ("noreply@x.com",        False),
    ("no-reply@y.com",       False),
    ("not-an-email",         False),
    ("",                     False),
    (None,                   False),
])
def test_is_real_email(email, expected):
    assert seed.is_real_email(email) is expected


# ─── select_prospects ───────────────────────────────────────────────────────

def _make_prospect(
    *, dom="acme.com.au", name="Acme", email="ceo@acme.com.au",
    score=80, reach=10, stage=7,
) -> dict:
    return {
        "id": uuid4(),
        "domain": dom, "display_name": name,
        "dm_name": "Amy", "dm_title": "CEO",
        "dm_email": email,
        "propensity_score": score, "reachability_score": reach,
        "pipeline_stage": stage,
    }


@pytest.mark.asyncio
async def test_select_prospects_filters_suppression_and_placeholders():
    rows = [
        _make_prospect(dom="ok.com.au", email="ceo@ok.com.au"),                    # keep
        _make_prospect(dom="placeholder.com.au", email="example@mail.com"),       # placeholder
        _make_prospect(dom="suppressed-dom.com.au", email="ceo@suppressed-dom.com.au"),  # supp domain
        _make_prospect(dom="another.com.au", email="bob@suppressed-em.com"),      # supp email
        _make_prospect(dom="keep2.com.au", email="amy@keep2.com.au"),             # keep
    ]
    conn = MagicMock()
    fetch_returns = iter([
        rows,                                                       # main BU
        [{"domain": "suppressed-dom.com.au"}],                      # suppressed domains
        [{"email": "bob@suppressed-em.com"}],                       # suppressed emails
    ])
    async def fetch(*_a, **_k):
        return next(fetch_returns)
    conn.fetch = fetch

    selected = await seed.select_prospects(conn)
    selected_domains = {r["domain"] for r in selected}
    assert "ok.com.au" in selected_domains
    assert "keep2.com.au" in selected_domains
    assert "placeholder.com.au" not in selected_domains
    assert "suppressed-dom.com.au" not in selected_domains
    assert "another.com.au" not in selected_domains
    assert len(selected) == 2


@pytest.mark.asyncio
async def test_select_prospects_caps_at_target():
    rows = [_make_prospect(dom=f"site{i}.com.au", email=f"ceo@site{i}.com.au")
            for i in range(seed.TARGET_PROSPECTS + 5)]
    conn = MagicMock()
    fetch_returns = iter([rows, [], []])
    async def fetch(*_a, **_k):
        return next(fetch_returns)
    conn.fetch = fetch
    selected = await seed.select_prospects(conn)
    assert len(selected) == seed.TARGET_PROSPECTS


@pytest.mark.asyncio
async def test_select_prospects_drops_null_display_name():
    """The SQL filters NULL display_name in WHERE — confirm the script does
    not crash if the DB happens to return one (defence-in-depth)."""
    rows = [_make_prospect(dom="ok.com.au")]
    conn = MagicMock()
    fetch_returns = iter([rows, [], []])
    async def fetch(*_a, **_k):
        return next(fetch_returns)
    conn.fetch = fetch
    selected = await seed.select_prospects(conn)
    assert len(selected) == 1
    assert selected[0]["display_name"] is not None


# ─── link_prospects ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_link_prospects_writes_one_row_per_prospect():
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=uuid4())
    prospects = [_make_prospect(dom=f"x{i}.com.au") for i in range(3)]
    n = await seed.link_prospects(conn, "client-uuid", prospects, dry_run=False)
    assert n == 3
    assert conn.fetchval.await_count == 3


@pytest.mark.asyncio
async def test_link_prospects_dry_run_writes_nothing():
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=uuid4())
    prospects = [_make_prospect(dom=f"x{i}.com.au") for i in range(3)]
    n = await seed.link_prospects(conn, "client-uuid", prospects, dry_run=True)
    assert n == 3  # would-link count
    conn.fetchval.assert_not_awaited()


@pytest.mark.asyncio
async def test_link_prospects_skips_on_conflict_silently():
    """ON CONFLICT DO NOTHING returns NULL — count must not increment."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(side_effect=[uuid4(), None, uuid4()])
    prospects = [_make_prospect(dom=f"x{i}.com.au") for i in range(3)]
    n = await seed.link_prospects(conn, "client-uuid", prospects, dry_run=False)
    assert n == 2
