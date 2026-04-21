"""Lock test: Stage 10 enhanced_vr system prompt constants must NOT contain {{agency_name}} tokens.

Rationale: F21-CRITICAL fix replaced {{agency_name}} with the literal "Agency OS"
in the system prompts used for Gemini calls. These tests lock that fix so it
cannot be silently reverted.

Note: The module docstring at line 9 legitimately mentions {{agency_name}} as a
negative example ("Do NOT use..."). Tests scope to prompt constants only.
"""
from __future__ import annotations

import src.intelligence.enhanced_vr as _vr_mod


def _prompt_constants() -> list[tuple[str, str]]:
    """Return (name, value) for module-level string constants that are prompts."""
    return [
        (name, val)
        for name, val in vars(_vr_mod).items()
        if isinstance(val, str) and name.endswith("_PROMPT")
    ]


def test_no_agency_name_token_in_system_prompts():
    """No *_PROMPT constant may contain {{agency_name}}."""
    prompts = _prompt_constants()
    assert prompts, "No *_PROMPT constants found in enhanced_vr — check naming"
    for name, text in prompts:
        assert "{{agency_name}}" not in text, (
            f"Found unfilled {{{{agency_name}}}} token in {name} — revert detected"
        )


def test_agency_os_literal_present_in_prompts():
    """The literal 'Agency OS' must appear in at least one *_PROMPT constant."""
    combined = " ".join(text for _, text in _prompt_constants())
    assert "Agency OS" in combined, (
        "'Agency OS' not found in any *_PROMPT constant in enhanced_vr"
    )


def test_no_double_brace_tokens_in_system_prompts():
    """No {{ ... }} placeholder tokens should appear in the system prompts."""
    for name, text in _prompt_constants():
        assert "{{" not in text, (
            f"Unfilled template token found in {name}: ...{text[:80]}..."
        )
