"""
scripts/re_embed_corpus.py
--------------------------
Migration script: re-embed a Weaviate corpus when the embedding model changes.
Written pre-deployment as the insurance policy Dave specified in KEI-60.

Usage:
    python scripts/re_embed_corpus.py \\
        --old-model gemini-embedding-001 \\
        --new-model gemini-embedding-002 \\
        --collections AgentMemory,LeadCorpus \\
        [--dry-run]          # default True — MUST pass --dry-run=False to mutate
        [--weaviate-url http://localhost:8080]
        [--batch-size 100]

Exit codes:
    0 — success (or dry-run completed)
    2 — bad arguments
    3 — Weaviate connection failure
    4 — partial failure (some objects failed — manual reconciliation required)

KEI: KEI-60 (Linear: https://linear.app/keiracom/issue/KEI-62)
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import sys
from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Weaviate — graceful ImportError so the script can be loaded without the lib
# ---------------------------------------------------------------------------
try:
    import weaviate  # type: ignore[import-untyped]

    _WEAVIATE_AVAILABLE = True
except ImportError:
    _WEAVIATE_AVAILABLE = False
    weaviate = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding model abstraction
# ---------------------------------------------------------------------------

#: Map model-name-prefix → provider module path (lazily imported)
_MODEL_PROVIDERS: dict[str, str] = {
    "gemini-": "src.memory.re_embed_provider_gemini",
    "text-embedding-": "src.memory.re_embed_provider_openai",
}


def embed(text: str, model: str) -> list[float]:
    """
    Embed *text* using *model*.

    Resolves provider from ``_MODEL_PROVIDERS`` by prefix match, then delegates
    to ``<provider_module>.embed(text, model)``.

    Raises:
        ValueError: if no provider matches *model*.
        ImportError: if the provider module is not installed.
    """
    for prefix, module_path in _MODEL_PROVIDERS.items():
        if model.startswith(prefix):
            import importlib

            provider = importlib.import_module(module_path)
            return provider.embed(text, model)  # type: ignore[no-any-return]
    raise ValueError(f"No embedding provider found for model '{model}'. Known prefixes: {list(_MODEL_PROVIDERS)}")


# ---------------------------------------------------------------------------
# Weaviate client Protocol (testable without live Weaviate)
# ---------------------------------------------------------------------------


@runtime_checkable
class _WeaviateClient(Protocol):
    """Minimal interface used by re-embed logic — makes unit tests straightforward."""

    def get_all_objects(self, collection: str) -> list[dict[str, Any]]:
        """Return all objects in *collection* as dicts with at least 'id' and 'properties'."""
        ...

    def update_vector(self, collection: str, object_id: str, vector: list[float]) -> None:
        """Overwrite the vector for *object_id* in *collection*."""
        ...

    def query_objects(self, collection: str, query_vector: list[float], limit: int) -> list[dict[str, Any]]:
        """Return up to *limit* objects nearest to *query_vector*."""
        ...


# ---------------------------------------------------------------------------
# Real Weaviate client wrapper
# ---------------------------------------------------------------------------


def _build_real_client(weaviate_url: str) -> _WeaviateClient:
    """Connect to Weaviate and return a thin wrapper that satisfies _WeaviateClient."""
    if not _WEAVIATE_AVAILABLE:
        raise ImportError(
            "weaviate-client is not installed. Run: pip install weaviate-client"
        )

    class _RealClient:
        def __init__(self, url: str) -> None:
            self._client = weaviate.connect_to_local(host=url)  # type: ignore[union-attr]

        def get_all_objects(self, collection: str) -> list[dict[str, Any]]:
            col = self._client.collections.get(collection)
            results = []
            for obj in col.iterator(include_vector=False):
                results.append({"id": str(obj.uuid), "properties": obj.properties})
            return results

        def update_vector(self, collection: str, object_id: str, vector: list[float]) -> None:
            col = self._client.collections.get(collection)
            col.data.update(uuid=object_id, vector=vector)

        def query_objects(self, collection: str, query_vector: list[float], limit: int) -> list[dict[str, Any]]:
            col = self._client.collections.get(collection)
            response = col.query.near_vector(near_vector=query_vector, limit=limit)
            return [{"id": str(o.uuid), "properties": o.properties} for o in response.objects]

    return _RealClient(weaviate_url)


# ---------------------------------------------------------------------------
# Core re-embed logic
# ---------------------------------------------------------------------------


def _re_embed_collection(
    client: _WeaviateClient,
    collection: str,
    new_model: str,
    dry_run: bool,
    batch_size: int,
) -> tuple[int, list[str]]:
    """
    Re-embed all objects in *collection*.

    Returns:
        (n_succeeded, failed_ids)
    """
    objects = client.get_all_objects(collection)
    total = len(objects)
    log.info("Collection '%s': %d objects found", collection, total)

    succeeded = 0
    failed_ids: list[str] = []

    for i in range(0, total, batch_size):
        batch = objects[i : i + batch_size]
        for obj in batch:
            obj_id: str = obj["id"]
            raw_text: str = obj.get("properties", {}).get("raw_text", "")
            if not raw_text:
                log.warning("Object %s in '%s' has no raw_text — skipping", obj_id, collection)
                failed_ids.append(obj_id)
                continue
            try:
                vector = embed(raw_text, new_model)
                if not dry_run:
                    client.update_vector(collection, obj_id, vector)
                succeeded += 1
            except Exception as exc:
                log.error("Failed to re-embed object %s: %s", obj_id, exc)
                failed_ids.append(obj_id)

        log.info(
            "Collection '%s': processed %d/%d (dry_run=%s)",
            collection,
            min(i + batch_size, total),
            total,
            dry_run,
        )

    return succeeded, failed_ids


def _verify_spot_check(
    client: _WeaviateClient,
    collection: str,
    new_model: str,
    n_queries: int = 10,
) -> bool:
    """
    Run *n_queries* spot-check queries against the re-embedded collection.

    For each query we use a synthetic probe text; success means Weaviate returns
    at least one result per query (i.e. the vector index is queryable).
    """
    probe_texts = [
        f"spot-check probe query number {i}" for i in range(n_queries)
    ]
    passed = 0
    for probe in probe_texts:
        try:
            vector = embed(probe, new_model)
            results = client.query_objects(collection, vector, limit=1)
            if results:
                passed += 1
            else:
                log.warning("Spot-check query returned 0 results: %r", probe)
        except Exception as exc:
            log.error("Spot-check query error: %s", exc)

    log.info("Spot-check: %d/%d queries returned results", passed, n_queries)
    return passed == n_queries


def _write_audit_log(
    *,
    old_model: str,
    new_model: str,
    collections: list[str],
    n_objects: int,
    failed_ids: list[str],
    dry_run: bool,
) -> dict[str, Any]:
    """Build and log the audit record. Returns the dict (callers may persist it)."""
    record: dict[str, Any] = {
        "event": "re_embed_complete",
        "source": "scripts/re_embed_corpus.py",
        "agent": "elliot",
        "kei": "KEI-60",
        "model_from": old_model,
        "model_to": new_model,
        "collections": collections,
        "n_objects": n_objects,
        "n_failed": len(failed_ids),
        "failed_ids": failed_ids,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
        "dry_run": dry_run,
    }
    log.info("AUDIT LOG: %s", json.dumps(record, indent=2))
    return record


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-embed Weaviate corpus after an embedding model change.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--old-model", required=True, help="Previous embedding model name (e.g. gemini-embedding-001)")
    parser.add_argument("--new-model", required=True, help="New embedding model name (e.g. gemini-embedding-002)")
    parser.add_argument(
        "--collections",
        required=True,
        help="Comma-separated list of Weaviate collection names to re-embed",
    )
    parser.add_argument(
        "--dry-run",
        type=lambda v: v.lower() not in ("false", "0", "no"),
        default=True,
        metavar="BOOL",
        help="Set to False to actually mutate the corpus (default: True)",
    )
    parser.add_argument(
        "--weaviate-url",
        default="http://localhost:8080",
        help="Weaviate server URL (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Objects per batch (default: 100)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, client: _WeaviateClient | None = None) -> int:
    """
    Entry point.  Returns exit code (0, 2, 3, or 4).

    *client* is injectable for testing — if None, a real Weaviate connection is built.
    """
    try:
        args = _parse_args(argv)
    except SystemExit:
        return 2

    collections = [c.strip() for c in args.collections.split(",") if c.strip()]
    if not collections:
        log.error("--collections must contain at least one collection name")
        return 2

    if args.dry_run:
        log.info("DRY-RUN mode — corpus will NOT be mutated")
    else:
        log.warning("LIVE mode — corpus WILL be mutated")

    # Build client
    if client is None:
        try:
            client = _build_real_client(args.weaviate_url)
        except ImportError as exc:
            log.error("Cannot connect: %s", exc)
            return 3
        except Exception as exc:
            log.error("Weaviate connection failure: %s", exc)
            return 3

    # Re-embed all collections
    total_succeeded = 0
    all_failed: list[str] = []

    for collection in collections:
        succeeded, failed = _re_embed_collection(
            client, collection, args.new_model, args.dry_run, args.batch_size
        )
        total_succeeded += succeeded
        all_failed.extend(failed)

    # Spot-check (only if not dry-run — corpus unchanged in dry-run)
    if not args.dry_run and client is not None:
        for collection in collections:
            if not _verify_spot_check(client, collection, args.new_model):
                log.error("Spot-check FAILED for collection '%s'", collection)

    _write_audit_log(
        old_model=args.old_model,
        new_model=args.new_model,
        collections=collections,
        n_objects=total_succeeded + len(all_failed),
        failed_ids=all_failed,
        dry_run=args.dry_run,
    )

    if all_failed:
        log.error(
            "%d object(s) failed — manual reconciliation required. IDs: %s",
            len(all_failed),
            all_failed,
        )
        return 4

    log.info("Re-embed complete: %d objects, model %s → %s", total_succeeded, args.old_model, args.new_model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
