"""
Tests for DNCRClient — Australian Do Not Call Register integration.
"""

import os
from unittest.mock import patch


def test_dncr_blocks_when_not_configured():
    """DNCR hard-block: if API key not set, check_number() must block, not allow."""
    import asyncio

    from src.integrations.dncr import DNCRClient

    # Remove DNCR credentials from environment
    env_without_dncr = {
        k: v for k, v in os.environ.items() if k not in ("DNCR_API_KEY", "DNCR_ACCOUNT_ID")
    }
    with patch.dict(os.environ, env_without_dncr, clear=True):
        client = DNCRClient(api_key=None, account_id=None)
        assert not client.is_enabled, "Client should be disabled when no credentials"

        # Must not raise — must return True (blocked)
        result = asyncio.run(client.check_number("+61412345678"))
        assert result is True, f"DNCR unconfigured must return True (blocked), got: {result}"


def test_dncr_batch_blocks_when_not_configured():
    """DNCR hard-block: check_numbers_batch() must block all numbers when not configured."""
    import asyncio

    from src.integrations.dncr import DNCRClient

    env_without_dncr = {
        k: v for k, v in os.environ.items() if k not in ("DNCR_API_KEY", "DNCR_ACCOUNT_ID")
    }
    with patch.dict(os.environ, env_without_dncr, clear=True):
        client = DNCRClient(api_key=None, account_id=None)
        phones = ["+61412345678", "+61498765432"]
        results = asyncio.run(client.check_numbers_batch(phones))
        for phone in phones:
            assert results[phone] is True, (
                f"DNCR unconfigured must block {phone}, got: {results[phone]}"
            )
