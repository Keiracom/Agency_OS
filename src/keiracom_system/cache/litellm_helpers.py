"""LiteLLM helpers — Phase A7 sub-task 3.

`cache_control` marker injection at the caller layer per CB-4 verification:
LiteLLM has no global `cache_control_enabled: true` YAML option — markers
are set per content block at message-construction time, matching the
Anthropic API spec (`cache_control: {"type": "ephemeral"}`).

CANONICAL DESIGN — docs/architecture/design/a7_cache_architecture.md §3 + §13
CB-4 (helper-not-flag) + CB-5 (Anthropic cache-rate metric naming).

REPO PRECEDENT — src/pipeline/intelligence.py uses this exact per-block
cache_control pattern; this helper consolidates it into a reusable form for
the cache layer's callers.

DEFERRED to follow-up: Dave's tenant LiteLLM virtual_key YAML stanza
(design §5). Reason — adding anthropic/* deployments to infra/litellm/config.yaml
crosses Dave's 2026-05-20 internal-governance-never-Anthropic policy without
explicit re-ratify. The virtual key only activates against a deployed Anthropic
model group; deployment + key ship together at V1 customer onboarding gate
(Phase C5). Bd follow-up filed in PR description.

ANTHROPIC CACHE BREAKPOINT THRESHOLD: Anthropic requires >=1024 tokens between
breakpoint markers (per Anthropic API spec). Per-tier system prompts smaller
than this get no Layer 1 benefit. The helper exposes a minimum-tokens parameter
so callers can short-circuit cache_control injection for under-threshold
prompts (per design §3 edge case).
"""

from __future__ import annotations

from typing import Any

# Anthropic API spec: minimum input tokens between cache breakpoints.
# Below this threshold, Anthropic refuses to populate a cache breakpoint.
# Source: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
ANTHROPIC_CACHE_MIN_TOKENS: int = 1024

# Default cache_control marker payload (ephemeral type per Anthropic API).
EPHEMERAL_CACHE_CONTROL: dict[str, str] = {"type": "ephemeral"}


def _estimate_tokens(content: str | list[Any]) -> int:
    """Rough token estimator: ~4 chars per token for English text.

    Conservative — under-estimates somewhat (tokens are sometimes longer for
    rare words / code), which is the safe direction (we'd rather skip
    cache_control injection on a borderline prompt than fail the Anthropic
    >=1024 check at runtime).

    Caller can pass a real token counter via `token_counter` to
    `inject_cache_control_markers()` for higher accuracy.
    """
    if isinstance(content, str):
        return len(content) // 4
    if isinstance(content, list):
        # Anthropic content blocks: [{"type": "text", "text": "..."}, ...]
        total = 0
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                total += len(block["text"]) // 4
        return total
    return 0


def inject_cache_control_markers(
    messages: list[dict[str, Any]],
    *,
    breakpoint_policy: dict[str, bool] | None = None,
    min_tokens: int = ANTHROPIC_CACHE_MIN_TOKENS,
    token_counter: Any = None,
) -> list[dict[str, Any]]:
    """Inject Anthropic `cache_control` markers on stable-prefix message blocks.

    Returns a new list; does not mutate input.

    Per design §3 default policy (V1):
        - system prompt → cache YES (if over min_tokens)
        - tools/list → cache YES (if over min_tokens, configured at tool-list build time)
        - per-domain knowledge → cache YES (if >1024 tokens)
        - user input → cache NO
        - tool result → cache NO

    `breakpoint_policy` overrides defaults per role:
        {"system": True, "user": False, "assistant": False, "tool": False}

    `min_tokens` is the lower bound; messages estimating below this skip
    cache_control entirely (the Anthropic API would reject the breakpoint
    otherwise).

    `token_counter` (optional) is a callable taking (content) -> int for more
    accurate counting; default is the 4-chars-per-token estimator.
    """
    if breakpoint_policy is None:
        breakpoint_policy = {
            "system": True,
            "user": False,
            "assistant": False,
            "tool": False,
        }
    counter = token_counter if token_counter is not None else _estimate_tokens

    out: list[dict[str, Any]] = []
    for msg in messages:
        new_msg = dict(msg)
        role = msg.get("role", "")
        if not breakpoint_policy.get(role, False):
            out.append(new_msg)
            continue
        content = msg.get("content")
        if content is None:
            out.append(new_msg)
            continue
        token_count = counter(content)
        if token_count < min_tokens:
            out.append(new_msg)
            continue
        new_msg["content"] = _apply_cache_control(content)
        out.append(new_msg)
    return out


def _apply_cache_control(content: str | list[Any]) -> list[dict[str, Any]]:
    """Wrap content in Anthropic content-block list with cache_control on the LAST block.

    Anthropic's cache_control marker on a single content block marks the END of
    a cacheable prefix; subsequent blocks (after this one) are NOT in the cache
    breakpoint. Putting cache_control on the LAST block of role=system marks
    the entire system prompt as cacheable.

    String content is converted to a single text block with cache_control.
    List content gets cache_control on its last text block.
    """
    if isinstance(content, str):
        return [
            {
                "type": "text",
                "text": content,
                "cache_control": EPHEMERAL_CACHE_CONTROL,
            }
        ]
    if isinstance(content, list):
        if not content:
            return []
        new_blocks: list[dict[str, Any]] = []
        for block in content[:-1]:
            new_blocks.append(dict(block) if isinstance(block, dict) else block)
        last = content[-1]
        if isinstance(last, dict):
            last_with_cc = dict(last)
            last_with_cc["cache_control"] = EPHEMERAL_CACHE_CONTROL
            new_blocks.append(last_with_cc)
        else:
            new_blocks.append(last)
        return new_blocks
    return []
