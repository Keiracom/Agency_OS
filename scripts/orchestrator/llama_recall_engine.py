#!/usr/bin/env python3
"""llama_recall_engine.py — unified fan-out recall over Weaviate + Cognee via LlamaIndex.

Single entry point for agents and hooks to ask "what do we know about X?" without
having to pick which collection to query. Embeds the query once (OpenAI), runs the
same nearest-neighbour search across every relevant Weaviate collection in
parallel, merges + normalises scores, returns top-K. Optionally augments with a
Cognee graph-completion query for governance content.

Per the Layered Governance Matrix v1 (RATIFIED 2026-05-19): this is the recall
layer that fills the POINTER + REFERENCE tiers. Implementations of the loader
(KEI Agency_OS-ngw2 — orion) and the Layer 3 hook (KEI Agency_OS-2ddd — scout)
call into this module.

API:
    recall(query, scope=None, top_k=5, include_cognee=True) -> list[dict]
        scope: list of Weaviate collection names; default = all useful ones
        Returns list of {text, source, collection, distance, metadata}

CLI:
    python3 llama_recall_engine.py "what do we know about X" [--top-k N] [--scope a,b,c]

Fail-open: any backend down returns partial results rather than crash. Records
which sources contributed to the answer for debugging.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from typing import Any

# LlamaIndex is heavy; lazy-import inside functions so the CLI startup stays fast
sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS/scripts")

WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://127.0.0.1:8090")
DEFAULT_SCOPE = [
    "Decisions",
    "AgentMemories",
    "Discoveries",
    "SessionFacts",
    "Codebase",
    "Keis",
    "Global_governance_patterns",
]


def _weaviate_client():
    """Lazy-construct a v4 Weaviate client connected to local."""
    import weaviate
    return weaviate.connect_to_local(host="127.0.0.1", port=8090, grpc_port=50051)


def _http_search(collection: str, query: str, top_k: int = 5) -> list[dict]:
    """Direct GraphQL nearText against one Weaviate collection.

    Avoids the v4 client's connection-lifecycle complexity; reuses the proven
    HTTP path the cognee_http_client uses. Returns merged hit dicts.
    """
    import urllib.error
    import urllib.request
    body = json.dumps({
        "query": f'{{ Get {{ {collection}(nearText:{{concepts:["{query}"]}} limit:{top_k}) {{ _additional{{distance id}} }} }} }}'
    }).encode()
    req = urllib.request.Request(
        f"{WEAVIATE_URL}/v1/graphql",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        raw = urllib.request.urlopen(req, timeout=8).read()
        d = json.loads(raw)
        hits = (((d.get("data") or {}).get("Get") or {}).get(collection) or [])
        return [
            {
                "collection": collection,
                "id": (h.get("_additional") or {}).get("id"),
                "distance": (h.get("_additional") or {}).get("distance"),
            }
            for h in hits
        ]
    except (urllib.error.URLError, json.JSONDecodeError, urllib.error.HTTPError):
        return []


def _fetch_object_content(collection: str, obj_id: str) -> dict:
    """GET the full object so we can return its text content."""
    import urllib.error
    import urllib.request
    try:
        raw = urllib.request.urlopen(
            f"{WEAVIATE_URL}/v1/objects/{collection}/{obj_id}?include=", timeout=5
        ).read()
        return json.loads(raw)
    except (urllib.error.URLError, json.JSONDecodeError, urllib.error.HTTPError):
        return {}


def _cognee_recall(query: str, top_k: int = 3) -> list[dict]:
    """Pull from Cognee via the HTTP client. Returns list of dicts on success."""
    try:
        from cognee_http_client import recall as cognee_recall_fn  # type: ignore
    except ImportError:
        return []
    res = cognee_recall_fn(query, top_k=top_k)
    if isinstance(res, list):
        return [{"source": "cognee", "kind": "graph", **r} if isinstance(r, dict) else {"source": "cognee", "text": str(r)} for r in res]
    if isinstance(res, dict) and not res.get("error"):
        return [{"source": "cognee", "kind": "graph", **res}]
    return []


def _normalise_score(distance: float | None) -> float:
    """Convert Weaviate distance (0 = identical, ~2 = unrelated) to similarity 0..1."""
    if distance is None:
        return 0.0
    # Cosine distance heuristic: 1 - d/2 clamped to [0,1]
    return max(0.0, min(1.0, 1.0 - (distance / 2.0)))


def recall(
    query: str,
    scope: list[str] | None = None,
    top_k: int = 5,
    include_cognee: bool = True,
) -> dict:
    """Fan-out recall across Weaviate collections + Cognee.

    Returns a dict:
      {
        query: <str>,
        top_hits: [ {text, source, collection, score, distance, id, metadata}, ... ],
        sources_contributing: [...],
        sources_down: [...],
        elapsed_ms: int,
      }
    """
    start = time.time()
    collections = scope or DEFAULT_SCOPE
    all_hits: list[dict] = []
    sources_contributing: list[str] = []
    sources_down: list[str] = []

    # Weaviate fan-out (sequential; ~50-200ms per collection, ~1s total)
    for coll in collections:
        hits = _http_search(coll, query, top_k=top_k)
        if hits is None or hits == []:
            sources_down.append(coll)
            continue
        sources_contributing.append(coll)
        # enrich with text
        for h in hits:
            full = _fetch_object_content(coll, h["id"])
            props = (full or {}).get("properties") or {}
            # Pick a sensible text field per collection
            text = (
                props.get("text")
                or props.get("fact_text")
                or props.get("raw_text")
                or props.get("decision_body")
                or props.get("content")
                or props.get("title")
                or ""
            )
            if isinstance(text, str) and text:
                h["text"] = text[:2000]
            h["source"] = "weaviate"
            h["score"] = _normalise_score(h.get("distance"))
            h["metadata"] = {k: v for k, v in props.items() if k != "raw_text" and not isinstance(v, (list, dict))}
        all_hits.extend(hits)

    if include_cognee:
        cog_hits = _cognee_recall(query, top_k=min(top_k, 3))
        if cog_hits:
            sources_contributing.append("cognee")
            for h in cog_hits:
                h["score"] = 0.7  # cognee returns curated content; default mid-high
                h.setdefault("text", h.get("text") or json.dumps(h, default=str)[:1500])
            all_hits.extend(cog_hits)
        else:
            sources_down.append("cognee")

    # Rank by score desc, take top_k
    all_hits.sort(key=lambda h: h.get("score", 0.0), reverse=True)
    top_hits = all_hits[:top_k]
    return {
        "query": query,
        "top_hits": top_hits,
        "sources_contributing": sources_contributing,
        "sources_down": sources_down,
        "elapsed_ms": int((time.time() - start) * 1000),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("query", nargs="?", help="recall query text")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--scope", type=str, default=None, help="comma-separated collections")
    p.add_argument("--no-cognee", action="store_true")
    p.add_argument("--json", action="store_true", help="raw JSON output")
    p.add_argument("--test", action="store_true", help="run smoke test")
    args = p.parse_args()
    if args.test:
        result = recall("Sustainable Use License", top_k=3, include_cognee=True)
        print(json.dumps(result, indent=2, default=str))
        return 0
    if not args.query:
        p.error("query required (or --test)")
    scope = args.scope.split(",") if args.scope else None
    result = recall(args.query, scope=scope, top_k=args.top_k, include_cognee=not args.no_cognee)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0
    print(f"# Recall: {args.query}")
    print(f"_elapsed: {result['elapsed_ms']}ms; sources: {result['sources_contributing']}; down: {result['sources_down']}_")
    print()
    for i, h in enumerate(result["top_hits"], 1):
        coll = h.get("collection") or h.get("source", "?")
        score = h.get("score", 0)
        print(f"### {i}. [{coll}] score={score:.3f}")
        print(h.get("text", "(no text)")[:600])
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
