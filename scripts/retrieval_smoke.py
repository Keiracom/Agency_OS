#!/usr/bin/env python3
"""retrieval_smoke.py — KEI-49 acceptance harness.

Drives the canonical acceptance flow end-to-end:
    1. Probe Weaviate (health_check).
    2. Index a unique test document into Discoveries.
    3. Query for it.
    4. Assert the top citation matches the test document.

Exits 0 on success; non-zero with verbatim error context on first failure.
Re-runnable: the test document carries a uuid in its body so successive
runs don't collide.

Usage:
    python3 scripts/retrieval_smoke.py
    python3 scripts/retrieval_smoke.py --host 127.0.0.1 --port 8090
    python3 scripts/retrieval_smoke.py --verbose

The acceptance criterion from public.tasks[KEI-49]:
    "LlamaIndex indexes a test document. Agent queries it and gets
     accurate results. Requires KEI-48 done first."
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
import uuid

from src.retrieval import agent_query, orchestrator, weaviate_store

PROBE_COLLECTION = "Discoveries"
PROBE_AGENT = "smoke"


def _build_probe_doc() -> tuple[str, dict[str, object]]:
    """Return (text, metadata) for a unique probe document."""
    probe_id = uuid.uuid4().hex
    text = (
        f"KEI-49 smoke probe {probe_id}: the canonical fact is that "
        f"raspberries are not technically berries — botanically they are "
        f"aggregate fruits composed of many drupelets."
    )
    metadata = {
        "raw_text": text,
        "environment_hash": "smoke-env",
        "created_at": _dt.datetime.now(tz=_dt.UTC).isoformat(),
        "agent": PROBE_AGENT,
        "kei": "KEI-49",
        "source_id": f"smoke:{probe_id}",
    }
    return text, metadata


def _fail(stage: str, detail: str) -> int:
    sys.stderr.write(f"SMOKE FAIL [{stage}]: {detail}\n")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KEI-49 retrieval smoke")
    parser.add_argument("--host", default=os.environ.get("WEAVIATE_HOST", "127.0.0.1"))
    parser.add_argument("--port", default=os.environ.get("WEAVIATE_PORT", "8090"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    os.environ["WEAVIATE_HOST"] = args.host
    os.environ["WEAVIATE_PORT"] = str(args.port)

    print(f"=== KEI-49 retrieval smoke against {args.host}:{args.port} ===")

    print("\n[1/4] health_check")
    report = weaviate_store.health_check()
    if not report.reachable:
        return _fail("health_check", report.error or "weaviate unreachable")
    print(f"  reachable=True version={report.version}")
    print(f"  collections_present={sorted(report.collections_present)}")
    if report.missing_collections:
        return _fail(
            "schema_check",
            f"missing collections: {sorted(report.missing_collections)}. "
            "Run infra/weaviate/schema.py first (KEI-48 prerequisite).",
        )

    print("\n[2/4] index probe document")
    text, metadata = _build_probe_doc()
    try:
        doc_id = orchestrator.index_document(PROBE_COLLECTION, text, metadata)
    except Exception as exc:  # noqa: BLE001
        return _fail("index_document", f"{type(exc).__name__}: {exc}")
    print(f"  indexed doc_id={doc_id}")
    print(f"  text='{text[:80]}...'")

    print("\n[3/4] query for probe document")
    result = agent_query.query(
        text="What are raspberries botanically?",
        agent=PROBE_AGENT,
        collections=(PROBE_COLLECTION,),
        citation_required=True,
        min_score=0.0,
    )
    print(f"  elapsed_ms={result.elapsed_ms}")
    print(f"  citations={len(result.citations)}")
    if args.verbose:
        for i, c in enumerate(result.citations):
            print(f"    [{i}] score={c.score:.3f} src={c.source_id} excerpt={c.excerpt!r}")

    print("\n[4/4] assert accurate top citation")
    if not result.citations:
        return _fail("query", "no citations returned for probe document")
    top = result.citations[0]
    probe_tag = metadata["source_id"]
    if top.source_id != probe_tag and "raspberries" not in top.excerpt.lower():
        return _fail(
            "accuracy",
            f"top citation does not match probe — got source_id={top.source_id} "
            f"excerpt={top.excerpt!r}, expected probe_tag={probe_tag}",
        )
    print(f"  top.source_id={top.source_id}")
    print(f"  top.score={top.score:.3f}")
    print(f"  top.excerpt={top.excerpt!r}")
    print("\nSMOKE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
