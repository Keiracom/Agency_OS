"""
CI guard: Stage 5 dedup design contract.
Verifies the dedup path (fetchval check + early return) is present in _write_result.
"""

import inspect


def test_stage5_write_result_has_dedup_guard():
    """_write_result must call fetchval to detect duplicate linkedin_url before INSERT."""
    from src.pipeline.stage_5_dm_waterfall import Stage5DMWaterfall

    source = inspect.getsource(Stage5DMWaterfall._write_result)
    assert "fetchval" in source, (
        "_write_result must use fetchval to check for duplicate linkedin_url"
    )
    assert "stage5_dedup_skip" in source, "_write_result must log stage5_dedup_skip on duplicate"
