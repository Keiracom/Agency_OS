"""
Tests for openai_cost_logger.py — F4-PART2-SETUP.
"""

import json
import os
from pathlib import Path

import pytest


def _make_logger(log_path: str):
    """Import the module with COST_LOG_PATH patched to a temp path."""
    import importlib
    import src.telegram_bot.openai_cost_logger as mod

    original = mod.COST_LOG_PATH
    mod.COST_LOG_PATH = log_path
    yield mod
    mod.COST_LOG_PATH = original


@pytest.fixture()
def cost_logger(tmp_path):
    """Yield the cost logger module with log path pointed at tmp_path."""
    import src.telegram_bot.openai_cost_logger as mod

    log_file = str(tmp_path / "openai-cost.jsonl")
    original = mod.COST_LOG_PATH
    mod.COST_LOG_PATH = log_file
    yield mod, log_file
    mod.COST_LOG_PATH = original


def test_writes_valid_jsonl(cost_logger):
    mod, log_file = cost_logger
    mod.log_openai_call(
        callsign="elliot",
        use_case="query_expansion",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
    )
    lines = Path(log_file).read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["callsign"] == "elliot"
    assert entry["use_case"] == "query_expansion"
    assert entry["model"] == "gpt-4o-mini"
    assert entry["input_tokens"] == 100
    assert entry["output_tokens"] == 50
    assert "ts" in entry
    assert "estimated_cost_usd" in entry


def test_cost_gpt4o_mini(cost_logger):
    mod, log_file = cost_logger
    mod.log_openai_call(
        callsign="elliot",
        use_case="discernment",
        model="gpt-4o-mini",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    entry = json.loads(Path(log_file).read_text().strip())
    # $0.15/1M input + $0.60/1M output = $0.75 total
    assert abs(entry["estimated_cost_usd"] - 0.75) < 1e-6


def test_cost_embedding(cost_logger):
    mod, log_file = cost_logger
    mod.log_openai_call(
        callsign="aiden",
        use_case="embedding",
        model="text-embedding-3-small",
        input_tokens=1_000_000,
        output_tokens=0,
    )
    entry = json.loads(Path(log_file).read_text().strip())
    # $0.02/1M tokens
    assert abs(entry["estimated_cost_usd"] - 0.02) < 1e-6


def test_unknown_model_zero_cost(cost_logger):
    mod, log_file = cost_logger
    mod.log_openai_call(
        callsign="elliot",
        use_case="test",
        model="gpt-99-unknown",
        input_tokens=1000,
        output_tokens=500,
    )
    entry = json.loads(Path(log_file).read_text().strip())
    assert entry["estimated_cost_usd"] == 0.0


def test_multiple_entries_appended(cost_logger):
    mod, log_file = cost_logger
    for i in range(3):
        mod.log_openai_call(
            callsign="elliot",
            use_case=f"use_case_{i}",
            model="gpt-4o-mini",
            input_tokens=10,
            output_tokens=5,
        )
    lines = Path(log_file).read_text().strip().splitlines()
    assert len(lines) == 3


def test_does_not_raise_on_write_failure(tmp_path):
    """log_openai_call must never raise even on an unwritable path."""
    import src.telegram_bot.openai_cost_logger as mod

    original = mod.COST_LOG_PATH
    # Point to a non-existent directory — guaranteed write failure
    mod.COST_LOG_PATH = "/nonexistent_dir/openai-cost.jsonl"
    try:
        # Must not raise
        mod.log_openai_call(
            callsign="elliot",
            use_case="test",
            model="gpt-4o-mini",
            input_tokens=10,
        )
    finally:
        mod.COST_LOG_PATH = original
