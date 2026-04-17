"""
FILE: tests/telegram_bot/test_tag_handler.py
PURPOSE: Pytest suite for the /tag command handler (lead_tags Wave 1).
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure env is set before importing handler (mirrors conftest.py pattern)
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("CALLSIGN", "aiden")
os.environ.setdefault("DAVE_USER_ID", "7267788033")

from src.telegram_bot import tag_handler  # noqa: E402  (env must be set first)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_update(text: str, user_id: int = 7267788033, is_bot: bool = False, chat_id: int = 9999) -> MagicMock:
    """Build a minimal mock Update that tag_handler inspects."""
    user = MagicMock()
    user.id = user_id
    user.is_bot = is_bot
    user.username = "dave" if not is_bot else "somebot"
    user.first_name = "Dave" if not is_bot else "Bot"

    chat = MagicMock()
    chat.id = chat_id

    message = MagicMock()
    message.text = text
    message.message_id = 42
    message.reply_text = AsyncMock()

    update = MagicMock()
    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    return update


def _make_context(args: list[str] | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.args = args or []
    return ctx


def _haiku_response(domain: str, stage: str, reason_category: str, detail: str, criteria=None) -> MagicMock:
    """Build a mock anthropic messages.create response."""
    payload = {"domain": domain, "stage": stage, "reason_category": reason_category, "detail": detail}
    if criteria is not None:
        payload["criteria"] = criteria

    content_block = MagicMock()
    content_block.text = json.dumps(payload)

    response = MagicMock()
    response.content = [content_block]
    return response


def _supabase_ok() -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=[{"id": "fake-uuid"}])
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_pending():
    """Clear pending tags before/after each test."""
    tag_handler._pending_tags.clear()
    yield
    tag_handler._pending_tags.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parses_daves_example():
    """Haiku returns expected dict; bot replies with confirmation containing all fields."""
    update = _make_update("plumbermate.com.au dropped from stage 2 enterprise 200+ employees")
    ctx = _make_context(["plumbermate.com.au", "dropped", "from", "stage", "2", "enterprise", "200+", "employees"])

    mock_response = _haiku_response(
        domain="plumbermate.com.au",
        stage="stage2_abn",
        reason_category="enterprise",
        detail="200+ employees",
    )

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
        "domain": "plumbermate.com.au",
        "stage": "stage2_abn",
        "reason_category": "enterprise",
        "detail": "200+ employees",
    })):
        await tag_handler.handle_tag(update, ctx)

    update.message.reply_text.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "plumbermate.com.au" in reply
    assert "stage2_abn" in reply
    assert "enterprise" in reply
    assert "200+ employees" in reply
    assert "yes/no" in reply.lower()


@pytest.mark.asyncio
async def test_invalid_stage_from_llm():
    """Bad stage from Haiku → error message, no row written."""
    update = _make_update("example.com.au bad stage")
    ctx = _make_context(["example.com.au", "bad", "stage"])

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
        "domain": "example.com.au",
        "stage": "stage99_nonexistent",
        "reason_category": "other",
        "detail": "some detail",
    })):
        await tag_handler.handle_tag(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "invalid stage" in reply.lower() or "stage99_nonexistent" in reply
    assert update.effective_chat.id not in tag_handler._pending_tags


@pytest.mark.asyncio
async def test_invalid_category_from_llm():
    """Bad reason_category from Haiku → error message, no row written."""
    update = _make_update("example.com.au bad cat")
    ctx = _make_context(["example.com.au", "bad", "cat"])

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
        "domain": "example.com.au",
        "stage": "stage1_discovery",
        "reason_category": "nonexistent_cat",
        "detail": "some detail",
    })):
        await tag_handler.handle_tag(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "invalid reason_category" in reply.lower() or "nonexistent_cat" in reply
    assert update.effective_chat.id not in tag_handler._pending_tags


@pytest.mark.asyncio
async def test_yes_persists_row():
    """yes reply → Supabase POST called with expected payload, reply says Tagged."""
    chat_id = 1001
    update_tag = _make_update("plumbermate.com.au enterprise", chat_id=chat_id)
    ctx = _make_context(["plumbermate.com.au", "enterprise"])

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
        "domain": "plumbermate.com.au",
        "stage": "stage2_abn",
        "reason_category": "enterprise",
        "detail": "200+ employees",
    })):
        await tag_handler.handle_tag(update_tag, ctx)

    assert chat_id in tag_handler._pending_tags

    update_yes = _make_update("yes", chat_id=chat_id)
    ctx2 = _make_context()

    mock_resp = _supabase_ok()
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        consumed = await tag_handler.handle_tag_confirmation(update_yes, ctx2)

    assert consumed is True
    assert chat_id not in tag_handler._pending_tags
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs.get("json", {})
    assert payload["domain"] == "plumbermate.com.au"
    assert payload["stage"] == "stage2_abn"
    assert payload["reason_category"] == "enterprise"

    reply = update_yes.message.reply_text.call_args[0][0]
    assert "tagged" in reply.lower()


@pytest.mark.asyncio
async def test_no_cancels():
    """no reply → no Supabase call, reply says Cancelled."""
    chat_id = 1002
    update_tag = _make_update("example.com.au sole trader", chat_id=chat_id)
    ctx = _make_context(["example.com.au", "sole", "trader"])

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
        "domain": "example.com.au",
        "stage": "stage1_discovery",
        "reason_category": "sole_trader",
        "detail": "sole trader operation",
    })):
        await tag_handler.handle_tag(update_tag, ctx)

    update_no = _make_update("no", chat_id=chat_id)
    ctx2 = _make_context()

    with patch("httpx.AsyncClient") as mock_client_cls:
        consumed = await tag_handler.handle_tag_confirmation(update_no, ctx2)
        mock_client_cls.assert_not_called()

    assert consumed is True
    assert chat_id not in tag_handler._pending_tags
    reply = update_no.message.reply_text.call_args[0][0]
    assert "cancelled" in reply.lower()


@pytest.mark.asyncio
async def test_duplicate_tag_pending_rejected():
    """Second /tag while one is pending → 'finish your previous tag first'."""
    chat_id = 1003
    update1 = _make_update("example.com.au chain", chat_id=chat_id)
    ctx1 = _make_context(["example.com.au", "chain"])

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
        "domain": "example.com.au",
        "stage": "stage1_discovery",
        "reason_category": "chain",
        "detail": "national chain",
    })):
        await tag_handler.handle_tag(update1, ctx1)

    # Second /tag before confirming
    update2 = _make_update("other.com.au franchise", chat_id=chat_id)
    ctx2 = _make_context(["other.com.au", "franchise"])

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock()) as mock_extract:
        await tag_handler.handle_tag(update2, ctx2)
        mock_extract.assert_not_called()

    reply = update2.message.reply_text.call_args[0][0]
    assert "finish your previous tag" in reply.lower()


@pytest.mark.asyncio
async def test_timeout_clears_pending():
    """After timeout elapses, pending tag is cleared silently."""
    chat_id = 1004
    update_tag = _make_update("example.com.au enterprise", chat_id=chat_id)
    ctx = _make_context(["example.com.au", "enterprise"])

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
        "domain": "example.com.au",
        "stage": "stage1_discovery",
        "reason_category": "enterprise",
        "detail": "big corp",
    })), patch.object(tag_handler, "TAG_TIMEOUT_SECONDS", 0.05):
        await tag_handler.handle_tag(update_tag, ctx)
        assert chat_id in tag_handler._pending_tags
        # Allow timeout coroutine to fire
        await asyncio.sleep(0.15)

    assert chat_id not in tag_handler._pending_tags


@pytest.mark.asyncio
async def test_orphan_domain_still_writes():
    """Domain not in leads table → row still written to lead_tags (no FK)."""
    chat_id = 1005
    update_tag = _make_update("newdomain.com.au government", chat_id=chat_id)
    ctx = _make_context(["newdomain.com.au", "government"])

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
        "domain": "newdomain.com.au",
        "stage": "manual",
        "reason_category": "government",
        "detail": "local council",
    })):
        await tag_handler.handle_tag(update_tag, ctx)

    update_yes = _make_update("yes", chat_id=chat_id)
    ctx2 = _make_context()

    mock_resp = _supabase_ok()
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        consumed = await tag_handler.handle_tag_confirmation(update_yes, ctx2)

    assert consumed is True
    mock_client.post.assert_called_once()
    payload = mock_client.post.call_args[1]["json"]
    assert payload["domain"] == "newdomain.com.au"


@pytest.mark.asyncio
async def test_append_on_duplicate():
    """Two /tag + yes for the same domain → two Supabase POST calls."""
    chat_id = 1006

    for i, detail in enumerate(["first tag", "second tag"]):
        update_tag = _make_update(f"sameDomain.com.au {detail}", chat_id=chat_id)
        ctx = _make_context([f"sameDomain.com.au", detail])

        with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
            "domain": "sameDomain.com.au",
            "stage": "stage1_discovery",
            "reason_category": "duplicate",
            "detail": detail,
        })):
            await tag_handler.handle_tag(update_tag, ctx)

        update_yes = _make_update("yes", chat_id=chat_id)
        ctx2 = _make_context()

        mock_resp = _supabase_ok()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            consumed = await tag_handler.handle_tag_confirmation(update_yes, ctx2)

        assert consumed is True
        # Both iterations should POST without error
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_tagged_by_defaults_dave():
    """Sender classified as Dave → tagged_by = 'dave'."""
    chat_id = 1007
    update_tag = _make_update("example.com.au not_au_based", user_id=7267788033, is_bot=False, chat_id=chat_id)
    ctx = _make_context(["example.com.au", "not_au_based"])

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
        "domain": "example.com.au",
        "stage": "stage1_discovery",
        "reason_category": "not_au_based",
        "detail": "US company",
    })):
        await tag_handler.handle_tag(update_tag, ctx)

    assert tag_handler._pending_tags[chat_id]["tagged_by"] == "dave"


@pytest.mark.asyncio
async def test_tagged_by_callsign_for_agent():
    """Sender is a peer bot / unknown human → tagged_by = CALLSIGN."""
    chat_id = 1008
    # Non-Dave user_id
    update_tag = _make_update("example.com.au bad_data", user_id=9999999, is_bot=False, chat_id=chat_id)
    ctx = _make_context(["example.com.au", "bad_data"])

    with patch("src.telegram_bot.tag_handler._haiku_extract", new=AsyncMock(return_value={
        "domain": "example.com.au",
        "stage": "stage1_discovery",
        "reason_category": "bad_data",
        "detail": "corrupted data",
    })):
        await tag_handler.handle_tag(update_tag, ctx)

    callsign = os.environ.get("CALLSIGN", "elliot")
    assert tag_handler._pending_tags[chat_id]["tagged_by"] == callsign


@pytest.mark.asyncio
async def test_non_yes_no_does_not_consume():
    """A random text message when pending tag exists is not consumed (returns False)."""
    chat_id = 1009
    # Seed a pending tag manually
    tag_handler._pending_tags[chat_id] = {
        "domain": "test.com.au",
        "stage": "manual",
        "reason_category": "other",
        "detail": "test",
        "tagged_by": "dave",
        "message_id": 1,
    }

    update = _make_update("hello there", chat_id=chat_id)
    ctx = _make_context()
    consumed = await tag_handler.handle_tag_confirmation(update, ctx)
    assert consumed is False
    # Pending should still be there
    assert chat_id in tag_handler._pending_tags
