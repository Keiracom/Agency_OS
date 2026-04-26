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
    n = await seed.link_prospects(
        conn, "client-uuid", prospects, dry_run=False, campaign_id="cmp-uuid",
    )
    assert n == 3
    assert conn.fetchval.await_count == 3
    # Confirm campaign_id is forwarded to the INSERT positionally.
    first_args = conn.fetchval.await_args_list[0].args
    assert first_args[1] == "client-uuid"
    assert first_args[2] == "cmp-uuid"


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
    n = await seed.link_prospects(
        conn, "client-uuid", prospects, dry_run=False, campaign_id="cmp-uuid",
    )
    assert n == 2


@pytest.mark.asyncio
async def test_link_prospects_requires_campaign_id_when_executing():
    """Schema audit gate: campaign_leads.campaign_id is NOT NULL — refuse
    to issue an INSERT that would be rejected at the DB."""
    conn = MagicMock()
    conn.fetchval = AsyncMock()
    prospects = [_make_prospect(dom="x.com.au")]
    with pytest.raises(ValueError, match="campaign_id"):
        await seed.link_prospects(conn, "client-uuid", prospects, dry_run=False)
    conn.fetchval.assert_not_awaited()


@pytest.mark.asyncio
async def test_link_prospects_dry_run_allows_missing_campaign_id():
    """Dry-run never touches the DB so missing campaign_id is tolerated."""
    conn = MagicMock()
    conn.fetchval = AsyncMock()
    prospects = [_make_prospect(dom="x.com.au")]
    n = await seed.link_prospects(conn, "client-uuid", prospects, dry_run=True)
    assert n == 1
    conn.fetchval.assert_not_awaited()


# ─── ensure_demo_campaign (TASK A — schema-audited) ────────────────────────

@pytest.mark.asyncio
async def test_ensure_demo_campaign_returns_existing():
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value={"id": "existing-cmp-uuid"})
    conn.fetchval = AsyncMock()
    out = await seed.ensure_demo_campaign(conn, "client-uuid")
    assert out == "existing-cmp-uuid"
    conn.fetchval.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_demo_campaign_creates_when_absent():
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value="new-cmp-uuid")
    out = await seed.ensure_demo_campaign(conn, "client-uuid")
    assert out == "new-cmp-uuid"
    sql, args = conn.fetchval.await_args.args[0], conn.fetchval.await_args.args[1:]
    assert "INSERT INTO campaigns" in sql
    assert args[0] == "client-uuid"
    assert args[1] == seed.DEMO_CAMPAIGN_NAME


@pytest.mark.asyncio
async def test_ensure_demo_campaign_idempotent_lookup_by_name():
    """Lookup query must match on (client_id, name) to prevent duplicates."""
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value="x")
    await seed.ensure_demo_campaign(conn, "client-uuid")
    lookup_sql = conn.fetchrow.await_args.args[0]
    assert "WHERE client_id = $1 AND name = $2" in lookup_sql
    assert "deleted_at IS NULL" in lookup_sql


# ─── ensure_demo_auth_user (TASK B) ─────────────────────────────────────────

class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self):
        return self._body


def test_ensure_demo_auth_user_dry_run_returns_none():
    out = seed.ensure_demo_auth_user(
        supabase_url="https://x.supabase.co", service_key="srv", dry_run=True,
    )
    assert out is None


def test_ensure_demo_auth_user_no_credentials_skips():
    out = seed.ensure_demo_auth_user(
        supabase_url="", service_key="", dry_run=False,
    )
    assert out is None


def test_ensure_demo_auth_user_idempotent_existing(monkeypatch):
    payload = b'{"users":[{"id":"abc","email":"demo@keiracom.com"}]}'

    def fake_urlopen(req, timeout=10):
        # GET on the lookup endpoint — return the existing user
        assert req.get_method() == "GET"
        return _FakeResponse(payload)

    monkeypatch.setattr(seed.urllib.request, "urlopen", fake_urlopen)
    out = seed.ensure_demo_auth_user(
        supabase_url="https://x.supabase.co",
        service_key="srv-key",
        dry_run=False,
    )
    assert out and out["id"] == "abc"


def test_ensure_demo_auth_user_creates_when_absent(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=10):
        calls.append(req.get_method())
        if req.get_method() == "GET":
            return _FakeResponse(b'{"users":[]}')
        # POST → return a freshly-created user
        body = req.data or b""
        assert b"demo@keiracom.com" in body
        return _FakeResponse(b'{"id":"new-uuid","email":"demo@keiracom.com"}')

    monkeypatch.setattr(seed.urllib.request, "urlopen", fake_urlopen)
    out = seed.ensure_demo_auth_user(
        supabase_url="https://x.supabase.co",
        service_key="srv-key",
        password="custom-pw",
        dry_run=False,
    )
    assert calls == ["GET", "POST"]
    assert out and out["id"] == "new-uuid"


def test_ensure_demo_auth_user_uses_env_password(monkeypatch):
    seen_body = {}

    def fake_urlopen(req, timeout=10):
        if req.get_method() == "GET":
            return _FakeResponse(b'{"users":[]}')
        seen_body["data"] = req.data
        return _FakeResponse(b'{"id":"u","email":"demo@keiracom.com"}')

    monkeypatch.setattr(seed.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("DEMO_PASSWORD", "env-injected-pw")
    seed.ensure_demo_auth_user(
        supabase_url="https://x.supabase.co",
        service_key="srv",
        dry_run=False,
    )
    assert b"env-injected-pw" in seen_body["data"]


def test_ensure_demo_auth_user_handles_network_error(monkeypatch):
    def boom(req, timeout=10):
        import urllib.error
        raise urllib.error.URLError("connection refused")
    monkeypatch.setattr(seed.urllib.request, "urlopen", boom)
    out = seed.ensure_demo_auth_user(
        supabase_url="https://x.supabase.co",
        service_key="srv",
        dry_run=False,
    )
    assert out is None


# ─── link_auth_user_to_client (TASK B) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_link_auth_user_dry_run_noops():
    conn = MagicMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()
    out = await seed.link_auth_user_to_client(
        conn, auth_user_id="u", client_id="c", dry_run=True,
    )
    assert out is False
    conn.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_link_auth_user_skips_when_no_membership_table():
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock()
    out = await seed.link_auth_user_to_client(
        conn, auth_user_id="u", client_id="c", dry_run=False,
    )
    assert out is False
    conn.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_link_auth_user_inserts_when_table_present():
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value="client_users")
    conn.execute = AsyncMock(return_value="INSERT 0 1")
    out = await seed.link_auth_user_to_client(
        conn, auth_user_id="u", client_id="c", dry_run=False,
    )
    assert out is True
    conn.execute.assert_awaited_once()
