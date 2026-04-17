"""
src/memory/types.py
Canonical source-type constants for agent_memories writes.
Import VALID_SOURCE_TYPES wherever type validation is needed.
"""

VALID_SOURCE_TYPES: frozenset[str] = frozenset({
    "pattern",
    "decision",
    "test_result",
    "reasoning",
    "skill",
    "daily_log",
    "dave_confirmed",
    "verified_fact",
    "research",
})
