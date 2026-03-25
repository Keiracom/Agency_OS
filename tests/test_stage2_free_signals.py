# FILE: tests/test_stage2_free_signals.py
# PURPOSE: Tests for Stage2FreeSignals — pixel audit + Yellow Pages check
# DIRECTIVE: #249

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.stage2_free_signals import Stage2FreeSignals


# ── Helpers ──────────────────────────────────────────────────────────────────


def make_mock_http_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.status_code = status_code
    return resp


def make_mock_client(side_effect=None, return_value=None) -> MagicMock:
    """Return a mock AsyncClient whose .get() is AsyncMock."""
    client = MagicMock()
    if side_effect is not None:
        client.get = AsyncMock(side_effect=side_effect)
    else:
        client.get = AsyncMock(return_value=return_value)
    return client


def make_bu_row(i: int) -> MagicMock:
    """Return a mock asyncpg-style row dict."""
    row = MagicMock()
    row_data = {
        "id": uuid.uuid4(),
        "display_name": f"Test Biz {i}",
        "website": f"https://testbiz{i}.com",
        "domain": f"testbiz{i}.com",
        "suburb": "Sydney",
        "state": "NSW",
        "postcode": "2000",
    }
    row.__getitem__ = lambda self, key: row_data[key]
    row.get = lambda key, default=None: row_data.get(key, default)
    return row


# ── Pixel audit tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pixel_audit_detects_tracking():
    """Test 1: HTML with gtag.js + fbq( + viewport → all tracking True."""
    html = (
        '<html><head>'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<script src="https://www.googletagmanager.com/gtag.js?id=G-ABC123"></script>'
        '<script>window.dataLayer = window.dataLayer || []; '
        'function gtag(){dataLayer.push(arguments);} gtag("js", new Date());</script>'
        '<script>fbq("init", "123456789");</script>'
        '</head><body></body></html>'
    )

    db = MagicMock()
    stage2 = Stage2FreeSignals(db=db)

    mock_client = make_mock_client(return_value=make_mock_http_response(html))
    with patch.object(stage2, "_get_client", new=AsyncMock(return_value=mock_client)):
        result = await stage2._pixel_audit("https://example.com")

    assert result["has_google_analytics"] is True
    assert result["has_facebook_pixel"] is True
    assert result["is_mobile_responsive"] is True
    assert result["has_conversion_tracking"] is True


@pytest.mark.asyncio
async def test_pixel_audit_no_tracking():
    """Test 2: Clean HTML with no tracking tags → all booleans False."""
    html = (
        "<html><head><title>Simple Site</title></head>"
        "<body><h1>Hello World</h1></body></html>"
    )

    db = MagicMock()
    stage2 = Stage2FreeSignals(db=db)

    mock_client = make_mock_client(return_value=make_mock_http_response(html))
    with patch.object(stage2, "_get_client", new=AsyncMock(return_value=mock_client)):
        result = await stage2._pixel_audit("https://example.com")

    assert result.get("has_google_analytics") is False
    assert result.get("has_facebook_pixel") is False
    assert result.get("has_conversion_tracking") is False


@pytest.mark.asyncio
async def test_pixel_audit_jina_fallback():
    """Test 3: Direct fetch fails, Jina fallback succeeds with gtag.js."""
    jina_html = (
        "# Test Biz\n\nSome content from Jina.\n"
        "gtag.js loaded for analytics.\n"
        + "x" * 250  # ensure len >= 200
    )

    db = MagicMock()
    stage2 = Stage2FreeSignals(db=db)

    # First call (direct) raises, second call (Jina) succeeds
    mock_client = make_mock_client(
        side_effect=[
            Exception("connection refused"),
            make_mock_http_response(jina_html, status_code=200),
        ]
    )
    with patch.object(stage2, "_get_client", new=AsyncMock(return_value=mock_client)):
        result = await stage2._pixel_audit("https://example.com")

    assert result.get("has_google_analytics") is True


@pytest.mark.asyncio
async def test_pixel_audit_both_fail_returns_empty():
    """Test 4: Both direct and Jina fail → empty-ish dict, no exception raised."""
    db = MagicMock()
    stage2 = Stage2FreeSignals(db=db)

    mock_client = make_mock_client(
        side_effect=[
            Exception("connection refused"),
            Exception("jina also down"),
        ]
    )
    with patch.object(stage2, "_get_client", new=AsyncMock(return_value=mock_client)):
        result = await stage2._pixel_audit("https://example.com")

    # Should return without raising; tracking keys should not be True
    assert result.get("has_google_analytics") is not True
    assert result.get("has_facebook_pixel") is not True
    # signal_checked_at is set to None when both fail (still a result dict)
    assert "signal_checked_at" in result


# ── YP check tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_yp_json_format():
    """Test 5: Jina returns JSON with results + /bpp/ → listed_on_yp True."""
    import json

    content = json.dumps(
        {
            "results": [{"name": "Test Biz", "url": "https://www.yellowpages.com.au/bpp/123"}]
        }
    )
    # Also embed /bpp/ to ensure count path works
    content += "\nhttps://www.yellowpages.com.au/bpp/456/test-biz"

    db = MagicMock()
    stage2 = Stage2FreeSignals(db=db)

    mock_client = make_mock_client(return_value=make_mock_http_response(content))
    with patch.object(stage2, "_get_client", new=AsyncMock(return_value=mock_client)):
        result = await stage2._yp_check("Test Biz", "Sydney", "NSW")

    assert result["listed_on_yp"] is True


@pytest.mark.asyncio
async def test_yp_pipe_delimited_format():
    """Test 6: Pipe-delimited text with /bpp/ and Ad → listed_on_yp + yp_advertiser True."""
    content = (
        "Name | Address | Phone\n"
        "Test Biz | 123 Main St, Sydney NSW 2000 | 02 9000 0000\n"
        "https://www.yellowpages.com.au/bpp/plumbers/test-biz-12345 | Website\n"
        "Ad\n"
        "Another Biz | 456 Other St | 02 9111 1111\n"
    )

    db = MagicMock()
    stage2 = Stage2FreeSignals(db=db)

    mock_client = make_mock_client(return_value=make_mock_http_response(content))
    with patch.object(stage2, "_get_client", new=AsyncMock(return_value=mock_client)):
        result = await stage2._yp_check("Test Biz", "Sydney", "NSW")

    assert result["listed_on_yp"] is True
    assert result["yp_advertiser"] is True


@pytest.mark.asyncio
async def test_yp_not_found():
    """Test 7: No /bpp/ in response → listed_on_yp False."""
    content = "No results found for Test Biz in Sydney NSW."

    db = MagicMock()
    stage2 = Stage2FreeSignals(db=db)

    mock_client = make_mock_client(return_value=make_mock_http_response(content))
    with patch.object(stage2, "_get_client", new=AsyncMock(return_value=mock_client)):
        result = await stage2._yp_check("Test Biz", "Sydney", "NSW")

    assert result["listed_on_yp"] is False


# ── Full run tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_stage2_run_advances_rows():
    """Test 8: run() processes 3 BU rows and advances each to pipeline_stage=2."""
    db = MagicMock()
    rows = [make_bu_row(i) for i in range(3)]
    db.fetch = AsyncMock(return_value=rows)
    db.execute = AsyncMock(return_value=None)

    stage2 = Stage2FreeSignals(db=db)

    # Patch _pixel_audit and _yp_check to avoid HTTP
    minimal_audit = {
        "has_google_analytics": False,
        "has_facebook_pixel": False,
        "has_conversion_tracking": False,
        "is_mobile_responsive": False,
        "has_booking_system": False,
        "site_copyright_year": None,
        "signal_checked_at": "2026-01-01",
    }
    minimal_yp = {"listed_on_yp": False, "yp_advertiser": False, "yp_years_in_business": None}

    with (
        patch.object(stage2, "_pixel_audit", new=AsyncMock(return_value=minimal_audit)),
        patch.object(stage2, "_yp_check", new=AsyncMock(return_value=minimal_yp)),
    ):
        result = await stage2.run(batch_size=3)

    assert result["processed"] == 3

    # db.execute called once per row
    assert db.execute.call_count == 3

    # Each UPDATE should include pipeline_stage = 2
    for call in db.execute.call_args_list:
        sql_arg = call.args[0] if call.args else ""
        assert "pipeline_stage" in sql_arg, f"Expected 'pipeline_stage' in SQL: {sql_arg}"


@pytest.mark.asyncio
async def test_batch_size_respected():
    """Test 9: run() processes only as many rows as returned by the DB (batch_size=3)."""
    db = MagicMock()
    rows = [make_bu_row(i) for i in range(3)]  # DB returns exactly 3 (LIMIT enforced)
    db.fetch = AsyncMock(return_value=rows)
    db.execute = AsyncMock(return_value=None)

    stage2 = Stage2FreeSignals(db=db)

    minimal_audit = {"signal_checked_at": "2026-01-01"}
    minimal_yp = {"listed_on_yp": False, "yp_advertiser": False, "yp_years_in_business": None}

    with (
        patch.object(stage2, "_pixel_audit", new=AsyncMock(return_value=minimal_audit)),
        patch.object(stage2, "_yp_check", new=AsyncMock(return_value=minimal_yp)),
    ):
        result = await stage2.run(batch_size=3)

    assert result["processed"] == 3

    # Verify batch_size was passed to db.fetch
    fetch_call_args = db.fetch.call_args
    assert 3 in fetch_call_args.args or 3 in list(fetch_call_args.args), (
        f"Expected batch_size=3 passed to db.fetch, got: {fetch_call_args}"
    )
