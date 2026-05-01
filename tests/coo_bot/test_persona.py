"""Tests for src/coo_bot/persona.py — system prompts for Opus calls."""
from __future__ import annotations

from src.coo_bot.persona import (
    DM_SYSTEM_PROMPT,
    GROUP_POST_SYSTEM_PROMPT,
    get_system_prompt,
)


def test_dm_prompt_is_dm_voice():
    assert "DM" in DM_SYSTEM_PROMPT or "Dave" in DM_SYSTEM_PROMPT
    assert "COO" in DM_SYSTEM_PROMPT
    # No banned phrases in the prompt about banned phrases (meta)
    assert "yes-man" in DM_SYSTEM_PROMPT


def test_group_post_prompt_includes_MAX_prefix_instruction():
    assert "[MAX]" in GROUP_POST_SYSTEM_PROMPT
    assert "Dave" in GROUP_POST_SYSTEM_PROMPT


def test_group_post_prompt_is_tier_0_strict():
    # Tier 0 = 1:1 dictation, no paraphrasing
    assert "1:1" in GROUP_POST_SYSTEM_PROMPT or "paraphrase" in GROUP_POST_SYSTEM_PROMPT


def test_get_system_prompt_dm_channel():
    assert get_system_prompt("dm") == DM_SYSTEM_PROMPT


def test_get_system_prompt_group_channel():
    assert get_system_prompt("group") == GROUP_POST_SYSTEM_PROMPT


def test_get_system_prompt_unknown_falls_back_to_dm():
    assert get_system_prompt("unknown") == DM_SYSTEM_PROMPT
    assert get_system_prompt("") == DM_SYSTEM_PROMPT
