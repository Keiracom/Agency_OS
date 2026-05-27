"""LiteLLM cache_control helper unit tests — Phase A7 sub-task 3."""

from src.keiracom_system.cache.litellm_helpers import (
    ANTHROPIC_CACHE_MIN_TOKENS,
    EPHEMERAL_CACHE_CONTROL,
    inject_cache_control_markers,
)


def _long_system_prompt() -> str:
    # ~4500 chars → ~1125 estimated tokens > 1024 min
    return "x" * 4500


def _short_system_prompt() -> str:
    # ~400 chars → ~100 estimated tokens < 1024 min
    return "y" * 400


def test_injects_cache_control_on_long_system_message():
    messages = [{"role": "system", "content": _long_system_prompt()}]
    out = inject_cache_control_markers(messages)
    assert len(out) == 1
    content = out[0]["content"]
    assert isinstance(content, list)
    assert content[-1]["cache_control"] == EPHEMERAL_CACHE_CONTROL
    assert content[-1]["text"] == _long_system_prompt()


def test_skips_cache_control_on_short_system_message():
    """Anthropic >=1024 token rule — under-threshold prompts get no cache_control."""
    messages = [{"role": "system", "content": _short_system_prompt()}]
    out = inject_cache_control_markers(messages)
    # Content unchanged — still a string, no cache_control wrapping
    assert out[0]["content"] == _short_system_prompt()


def test_user_messages_never_cached_by_default():
    messages = [
        {"role": "system", "content": _long_system_prompt()},
        {"role": "user", "content": _long_system_prompt()},  # long but role=user
    ]
    out = inject_cache_control_markers(messages)
    # User content unchanged (string passthrough)
    assert out[1]["content"] == _long_system_prompt()


def test_custom_breakpoint_policy_overrides_defaults():
    """Caller can override role policy — e.g. cache user messages."""
    messages = [{"role": "user", "content": _long_system_prompt()}]
    out = inject_cache_control_markers(
        messages,
        breakpoint_policy={"system": False, "user": True, "assistant": False, "tool": False},
    )
    assert isinstance(out[0]["content"], list)
    assert out[0]["content"][-1]["cache_control"] == EPHEMERAL_CACHE_CONTROL


def test_list_content_gets_cache_control_on_last_block_only():
    """Multi-block content: cache_control marks the END of cacheable prefix."""
    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "a" * 2200},
                {"type": "text", "text": "b" * 2200},
                {"type": "text", "text": "c" * 2200},
            ],
        }
    ]
    out = inject_cache_control_markers(messages)
    blocks = out[0]["content"]
    assert "cache_control" not in blocks[0]
    assert "cache_control" not in blocks[1]
    assert blocks[2]["cache_control"] == EPHEMERAL_CACHE_CONTROL


def test_token_counter_override():
    """Caller passes a real tokeniser for accurate counts."""
    short_text = "x" * 100  # ~25 tokens by default estimator < 1024 min
    # Custom counter that always reports plenty of tokens
    out = inject_cache_control_markers(
        [{"role": "system", "content": short_text}],
        token_counter=lambda _: 5000,
    )
    # cache_control IS applied because custom counter says token_count=5000 > 1024
    assert isinstance(out[0]["content"], list)
    assert out[0]["content"][-1]["cache_control"] == EPHEMERAL_CACHE_CONTROL


def test_does_not_mutate_input_messages():
    original = [{"role": "system", "content": _long_system_prompt()}]
    snapshot = [dict(m) for m in original]
    inject_cache_control_markers(original)
    # Original list unchanged
    assert original[0]["content"] == snapshot[0]["content"]
    assert "cache_control" not in original[0]


def test_anthropic_min_tokens_constant_per_spec():
    """Anthropic API spec: minimum 1024 tokens between breakpoints."""
    assert ANTHROPIC_CACHE_MIN_TOKENS == 1024


def test_ephemeral_cache_control_payload_shape():
    """Anthropic API spec: {'type': 'ephemeral'}."""
    assert EPHEMERAL_CACHE_CONTROL == {"type": "ephemeral"}


def test_ephemeral_cache_control_is_5min_default_no_ttl_key():
    """CUTOVER GATE INFRASTRUCTURE-SIDE — "cache write TTL 5-minute" criterion
    (RATIFIED-CEO Cat 21 lever 29, Dave directive 2026-05-27).

    The Anthropic API treats `{"type": "ephemeral"}` with NO `"ttl"` key as
    the 5-minute cache write TTL default. Adding `{"ttl": "1h"}` opts INTO
    1-hour cache write — Atlas empirical 2026-05-27 measured 37% saving on
    the cache-write cost line at 5-min vs 1h on observed fleet traffic
    (~$18.75/M Opus 4.x cache_write 5m vs ~$30/M cache_write 1h published).

    This test fails if anyone adds `"ttl"` to the canonical default. Per
    LiteLLM helper docstring: if a specific caller has a justified need for
    1h-cache-write (slow-changing prompt that survives long idle windows),
    construct a one-off dict at the call-site + document the cost
    justification — do NOT change EPHEMERAL_CACHE_CONTROL.
    """
    assert "ttl" not in EPHEMERAL_CACHE_CONTROL, (
        "EPHEMERAL_CACHE_CONTROL must NOT carry a 'ttl' key — bare ephemeral "
        "= 5-minute default per Anthropic API + Cutover Readiness Gate "
        "INFRASTRUCTURE-SIDE 'cache write TTL 5-minute' criterion."
    )
    assert EPHEMERAL_CACHE_CONTROL.get("type") == "ephemeral"
    # Exactly one key. Adds beyond {"type"} should be reviewed against the
    # cutover-gate criterion + the cost-line trade-off.
    assert set(EPHEMERAL_CACHE_CONTROL.keys()) == {"type"}, (
        f"EPHEMERAL_CACHE_CONTROL has unexpected keys: "
        f"{sorted(EPHEMERAL_CACHE_CONTROL.keys())}. The locked shape is "
        f"exactly {{'type': 'ephemeral'}} per the cutover-gate discipline."
    )


def test_empty_messages_returns_empty():
    assert inject_cache_control_markers([]) == []


def test_empty_list_content_returns_empty_list():
    """Edge case — list content with zero blocks."""
    messages = [{"role": "system", "content": []}]
    out = inject_cache_control_markers(messages)
    # role=system enabled but content has no length → skips (estimated tokens 0 < 1024)
    assert out[0]["content"] == []
