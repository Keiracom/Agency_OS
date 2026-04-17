"""
Package: src/memory
Purpose: Agent memory layer — text + tag + type filtered persistence.
         v1: no embeddings, no pgvector, no OpenAI. PostgREST only.
"""

from .store import store
from .types import VALID_SOURCE_TYPES, Memory, RateLimitExceeded

__all__ = [
    "store",
    "Memory",
    "VALID_SOURCE_TYPES",
    "RateLimitExceeded",
]
