"""Keiracom System — reranker client package.

Wave 2 dispatch Agency_OS-0thg. Thin Python client for the cross-encoder
reranker sidecar (BAAI/bge-reranker-base via TEI). Hindsight's recall path
returns top-50 candidates; this client reranks them so the LLM sees the 5-10
that actually answer the query.
"""

from src.keiracom_system.reranker.reranker_client import (
    DEFAULT_BASE_URL,
    EXPECTED_MODEL_ID,
    RerankClientError,
    RerankerClient,
    RerankHit,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "EXPECTED_MODEL_ID",
    "RerankClientError",
    "RerankerClient",
    "RerankHit",
]
