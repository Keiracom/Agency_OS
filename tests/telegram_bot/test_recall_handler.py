"""GOV-PHASE2 Track C2 / M2 — /recall TG command handler tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.memory.types import Memory
from src.telegram_bot import recall_handler


def _mk_memory(content: str, source_type: str) -> Memory:
    return Memory(
        id="00000000-0000-0000-0000-000000000000",
        callsign="aiden",
        source_type=source_type,
        content=content,
        typed_metadata={},
        tags=[source_type],
        valid_from="2026-05-01T00:00:00Z",
        valid_to=None,
        created_at="2026-05-01T00:00:00Z",
    )


def _mk_update_context(args: list[str]):
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    ctx = MagicMock()
    ctx.args = args
    return update, ctx


@pytest.mark.asyncio
async def test_recall_no_results_with_topic():
    update, ctx = _mk_update_context(["nonexistent"])
    with patch.object(recall_handler, "recall", return_value={}):
        await recall_handler.cmd_recall(update, ctx)
    update.message.reply_text.assert_called_once()
    assert "nonexistent" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_recall_no_results_no_topic():
    update, ctx = _mk_update_context([])
    with patch.object(recall_handler, "recall", return_value={}):
        await recall_handler.cmd_recall(update, ctx)
    update.message.reply_text.assert_called_once()
    assert "No memories found" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_recall_groups_and_truncates():
    update, ctx = _mk_update_context(["test"])
    grouped = {
        "decision": [_mk_memory("decision content one", "decision")] * 5,
        "pattern": [_mk_memory("pattern long " + "x" * 200, "pattern")],
    }
    with patch.object(recall_handler, "recall", return_value=grouped):
        await recall_handler.cmd_recall(update, ctx)
    msg = update.message.reply_text.call_args[0][0]
    assert "Recall: 'test'" in msg
    assert "[decision]" in msg and "(5 total)" in msg
    assert "[pattern]" in msg and "(1 total)" in msg
    # Truncation: only 3 per type, and content >80 chars gets ellipsis
    assert msg.count("decision content one") == 3
    assert "..." in msg


@pytest.mark.asyncio
async def test_recall_handles_exception():
    update, ctx = _mk_update_context([])
    with patch.object(recall_handler, "recall", side_effect=RuntimeError("db down")):
        await recall_handler.cmd_recall(update, ctx)
    update.message.reply_text.assert_called_once()
    assert "Recall failed" in update.message.reply_text.call_args[0][0]
