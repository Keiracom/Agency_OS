"""WeaviateVectorStore adapter for the retrieval layer.

Bridges LlamaIndex's `WeaviateVectorStore` with the existing Weaviate
collections created by `infra/weaviate/schema.py` (KEI-48). The schema
contract — 5 collections (Codebase, Decisions, Discoveries, Sessions,
Keis), 5 mandatory properties per collection (raw_text, environment_hash,
created_at, agent, kei), server-side vectorizer disabled — is owned by
that module; we read from it.

Two surfaces:
    health_check()              — verbatim version + collection inventory
    get_vector_store(collection) — LlamaIndex adapter bound to one class

The agent query path uses `get_vector_store`; smoke tests call
`health_check` to confirm Weaviate is reachable before exercising any
indexing or query flow.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "127.0.0.1")
WEAVIATE_PORT_HTTP = int(os.environ.get("WEAVIATE_PORT", "8090"))
WEAVIATE_PORT_GRPC = int(os.environ.get("WEAVIATE_PORT_GRPC", "50051"))
WEAVIATE_TEXT_KEY = "raw_text"

EXPECTED_COLLECTIONS = frozenset(
    {"Codebase", "Decisions", "Discoveries", "Sessions", "Keis"}
)


@dataclass(frozen=True)
class HealthReport:
    reachable: bool
    version: str
    collections_present: frozenset[str]
    missing_collections: frozenset[str]
    error: str | None = None


def health_check() -> HealthReport:
    """Probe Weaviate and report version + collection inventory."""
    import urllib.error
    import urllib.request

    base = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT_HTTP}"  # NOSONAR python:S5332
    try:
        with urllib.request.urlopen(f"{base}/v1/meta", timeout=5.0) as resp:  # noqa: S310
            import json as _json

            meta = _json.loads(resp.read().decode("utf-8"))
        version = str(meta.get("version", "unknown"))

        with urllib.request.urlopen(f"{base}/v1/schema", timeout=5.0) as resp:  # noqa: S310
            schema = _json.loads(resp.read().decode("utf-8"))
        present = frozenset(
            c.get("class", "") for c in (schema.get("classes") or []) if c.get("class")
        )
        return HealthReport(
            reachable=True,
            version=version,
            collections_present=present,
            missing_collections=EXPECTED_COLLECTIONS - present,
        )
    except urllib.error.URLError as exc:
        return HealthReport(
            reachable=False,
            version="",
            collections_present=frozenset(),
            missing_collections=EXPECTED_COLLECTIONS,
            error=f"URLError: {exc.reason}",
        )
    except Exception as exc:  # noqa: BLE001
        return HealthReport(
            reachable=False,
            version="",
            collections_present=frozenset(),
            missing_collections=EXPECTED_COLLECTIONS,
            error=f"{type(exc).__name__}: {exc}",
        )


def _connect_client() -> Any:
    """Open a weaviate-client v4 connection. Caller closes."""
    import weaviate

    return weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=WEAVIATE_PORT_HTTP,
        grpc_port=WEAVIATE_PORT_GRPC,
    )


def get_vector_store(collection: str, *, client: Any | None = None) -> Any:
    """Return a `WeaviateVectorStore` bound to one collection.

    The text-key contract (`raw_text`) and existing schema must already
    be in place — LlamaIndex's auto-schema-create is disabled here so
    the canonical schema in `infra/weaviate/schema.py` stays authoritative.
    """
    if collection not in EXPECTED_COLLECTIONS:
        raise ValueError(
            f"unknown collection {collection!r}; expected one of "
            f"{sorted(EXPECTED_COLLECTIONS)}"
        )
    from llama_index.vector_stores.weaviate import WeaviateVectorStore

    owned = client is None
    weaviate_client = client if client is not None else _connect_client()
    try:
        return WeaviateVectorStore(
            weaviate_client=weaviate_client,
            index_name=collection,
            text_key=WEAVIATE_TEXT_KEY,
        )
    except Exception:
        if owned:
            try:
                weaviate_client.close()
            except Exception:  # noqa: BLE001
                logger.debug("failed to close weaviate client after error", exc_info=True)
        raise


def close_client(client: Any) -> None:
    """Close a weaviate-client v4 connection. No-op on already-closed."""
    try:
        client.close()
    except Exception:  # noqa: BLE001
        logger.debug("close_client swallowed exception", exc_info=True)
