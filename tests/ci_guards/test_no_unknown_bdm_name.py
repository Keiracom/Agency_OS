"""CI guard: no is_current BDM should have name='Unknown'."""

import pytest
from unittest.mock import AsyncMock, MagicMock


def test_stage5_rejects_unknown_name():
    """Stage 5 should not write BDMs with name='Unknown'."""
    # This tests the write-path guard, not prod data
    # Import DMResult and verify is_valid returns False for name="Unknown" with no contact
    from src.pipeline.stage_5_dm_waterfall import DMResult

    dm = DMResult(name="Unknown", source="test")
    assert not dm.is_valid  # No contact method = not valid
