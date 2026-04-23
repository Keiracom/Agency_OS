"""Tests for /update command handler (src/telegram_bot/chat_bot.py::cmd_update)."""
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Minimal import — cmd_update uses CALLSIGN, SUPABASE_URL, etc. from module scope.
# We patch those at test level to avoid env dependency.


@pytest.fixture
def mock_update():
    update = AsyncMock()
    update.effective_chat.id = 7267788033
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context_aiden():
    ctx = MagicMock()
    ctx.args = ["aiden"]
    return ctx


@pytest.fixture
def mock_context_no_args():
    ctx = MagicMock()
    ctx.args = []
    return ctx


@patch.dict(os.environ, {"CALLSIGN": "elliot", "SUPABASE_URL": "https://test.supabase.co",
                          "SUPABASE_SERVICE_KEY": "test-key", "TELEGRAM_TOKEN": "test"})
class TestCmdUpdate:
    """cmd_update handler tests."""

    def _import_cmd_update(self):
        """Import cmd_update with mocked env to avoid startup side-effects."""
        # Patch telegram.ext before import to avoid bot init
        import importlib
        with patch("src.telegram_bot.chat_bot.auth_check", new_callable=AsyncMock, return_value=True):
            from src.telegram_bot.chat_bot import cmd_update
            return cmd_update

    @pytest.mark.asyncio
    async def test_target_defaults_to_peer(self, mock_update, mock_context_no_args):
        """When no args, target defaults to the peer callsign."""
        with patch("src.telegram_bot.chat_bot.auth_check", new_callable=AsyncMock, return_value=True), \
             patch("src.telegram_bot.chat_bot.CALLSIGN", "elliot"), \
             patch("src.telegram_bot.chat_bot.SUPABASE_URL", "https://test.supabase.co"), \
             patch("src.telegram_bot.chat_bot.SUPABASE_HEADERS", {}), \
             patch("src.telegram_bot.chat_bot.WORK_DIR", "/tmp"), \
             patch("httpx.AsyncClient") as mock_client, \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            client_instance = AsyncMock()
            client_instance.get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: []))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.telegram_bot.chat_bot import cmd_update
            await cmd_update(mock_update, mock_context_no_args)

            reply_text = mock_update.message.reply_text.call_args[0][0]
            # Default peer for elliot is aiden
            assert "→AIDEN" in reply_text
            assert "TELEGRAM-ONLY" in reply_text

    @pytest.mark.asyncio
    async def test_protocol_first_in_output(self, mock_update, mock_context_aiden):
        """Protocol checklist appears BEFORE state in the output."""
        with patch("src.telegram_bot.chat_bot.auth_check", new_callable=AsyncMock, return_value=True), \
             patch("src.telegram_bot.chat_bot.CALLSIGN", "elliot"), \
             patch("src.telegram_bot.chat_bot.SUPABASE_URL", "https://test.supabase.co"), \
             patch("src.telegram_bot.chat_bot.SUPABASE_HEADERS", {}), \
             patch("src.telegram_bot.chat_bot.WORK_DIR", "/tmp"), \
             patch("httpx.AsyncClient") as mock_client, \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="abc123 test commit", stderr="", returncode=0)
            client_instance = AsyncMock()
            client_instance.get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: []))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.telegram_bot.chat_bot import cmd_update
            await cmd_update(mock_update, mock_context_aiden)

            reply_text = mock_update.message.reply_text.call_args[0][0]
            protocol_pos = reply_text.find("PROTOCOL CHECKLIST")
            state_pos = reply_text.find("CURRENT STATE")
            # Protocol must come before state (-1 means not found, still valid if state missing)
            assert protocol_pos >= 0, "Protocol checklist missing"
            assert protocol_pos < state_pos or state_pos == -1

    @pytest.mark.asyncio
    async def test_auth_rejected(self, mock_update, mock_context_aiden):
        """Unauthorized users get rejected."""
        with patch("src.telegram_bot.chat_bot.auth_check", new_callable=AsyncMock, return_value=False):
            from src.telegram_bot.chat_bot import cmd_update
            await cmd_update(mock_update, mock_context_aiden)
            # reply_text should NOT have been called (auth failed early)
            mock_update.message.reply_text.assert_not_called()
