"""
FILE: src/memory/types.py
PURPOSE: Shared types for the agent memory layer (v1 — no embeddings).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

VALID_SOURCE_TYPES: set[str] = {
    "pattern",
    "decision",
    "test_result",
    "reasoning",
    "skill",
    "daily_log",
    "dave_confirmed",
    "verified_fact",
    "research",
}


@dataclass(frozen=True)
class Memory:
    id: uuid.UUID
    callsign: str
    source_type: str
    content: str
    typed_metadata: dict
    tags: list[str]
    valid_from: datetime
    valid_to: datetime | None
    created_at: datetime


class RateLimitExceeded(Exception):
    pass
