"""Tests for Elliot Voice — system prompt, kill switch, config validation."""

from __future__ import annotations

from src.voice.kill_switch import KillSwitch, KillSwitchState
from src.voice.system_prompt import build_system_prompt

# ── System prompt tests ──────────────────────────────────────────────────────


def test_system_prompt_contains_identity():
    prompt = build_system_prompt()
    assert "You are Elliot, CTO of Agency OS" in prompt


def test_system_prompt_contains_recording_consent():
    prompt = build_system_prompt()
    assert "recorded for post-call summary" in prompt


def test_system_prompt_contains_kill_switch_keywords():
    prompt = build_system_prompt()
    assert "Elliot pause" in prompt
    assert "Elliot go ahead" in prompt


def test_system_prompt_contains_currency_rule():
    prompt = build_system_prompt()
    assert "AUD" in prompt
    assert "1.55" in prompt


def test_system_prompt_contains_sensitive_blacklist():
    prompt = build_system_prompt()
    assert "SENSITIVE-INFO BLACKLIST" in prompt


def test_system_prompt_with_briefing():
    briefing = "Investor: Jane Smith, Fund: XYZ Capital"
    prompt = build_system_prompt(investor_briefing=briefing)
    assert "Jane Smith" in prompt
    assert "XYZ Capital" in prompt


def test_system_prompt_default_briefing():
    prompt = build_system_prompt()
    assert "No investor-specific briefing" in prompt


# ── Kill switch tests ────────────────────────────────────────────────────────


def test_kill_switch_starts_active():
    ks = KillSwitch()
    assert not ks.is_muted
    assert ks.state == KillSwitchState.ACTIVE


def test_kill_switch_mutes_on_pause():
    ks = KillSwitch()
    ks.check("elliot pause")
    assert ks.is_muted


def test_kill_switch_mutes_on_stop():
    ks = KillSwitch()
    ks.check("Elliot, stop")
    assert ks.is_muted


def test_kill_switch_mutes_on_hold():
    ks = KillSwitch()
    ks.check("Elliot hold")
    assert ks.is_muted


def test_kill_switch_resumes_on_go_ahead():
    ks = KillSwitch()
    ks.check("elliot pause")
    assert ks.is_muted
    ks.check("elliot go ahead")
    assert not ks.is_muted


def test_kill_switch_resumes_on_continue():
    ks = KillSwitch()
    ks.check("Elliot, stop")
    assert ks.is_muted
    ks.check("Elliot, continue")
    assert not ks.is_muted


def test_kill_switch_ignores_unrelated_text():
    ks = KillSwitch()
    ks.check("Tell me about your unit economics")
    assert not ks.is_muted
    ks.check("What does Elliot think about the market?")
    assert not ks.is_muted


def test_kill_switch_handles_empty_text():
    ks = KillSwitch()
    ks.check("")
    assert not ks.is_muted
    ks.check("   ")
    assert not ks.is_muted


def test_kill_switch_reset():
    ks = KillSwitch()
    ks.check("elliot pause")
    assert ks.is_muted
    ks.reset()
    assert not ks.is_muted


def test_kill_switch_case_insensitive():
    ks = KillSwitch()
    ks.check("ELLIOT PAUSE")
    assert ks.is_muted
    ks.check("ELLIOT GO AHEAD")
    assert not ks.is_muted


def test_kill_switch_partial_transcript():
    """Kill switch works with surrounding conversation text."""
    ks = KillSwitch()
    ks.check("okay so I think elliot pause for a second")
    assert ks.is_muted
