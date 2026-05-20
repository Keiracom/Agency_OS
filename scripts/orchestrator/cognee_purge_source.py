#!/usr/bin/env python3
"""cognee_purge_source.py — remove specific source documents from Cognee.

Cognee accumulates ingested documents and has NO supersession concept — a
stale doc, once ingested, is never marked dead and cognee_recall returns it
flat alongside current facts (the memory-content audit proved this). When a
doc is found stale, the ONLY remedy is to DELETE it from the Cognee dataset.

This tool deletes governance-dataset data items by exact source name via the
Cognee data-delete API (/api/v1/datasets/{id}/data/{data_id}).

Usage:
    python3 scripts/orchestrator/cognee_purge_source.py --source NAME [...]          # dry-run
    python3 scripts/orchestrator/cognee_purge_source.py --source NAME [...] --apply  # delete

Exit codes:
  0  clean (dry-run, or every requested source purged)
  1  one or more sources not found / delete failed
  2  Cognee unreachable / no auth
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS/scripts")
from cognee_http_client import BASE, get_token  # noqa: E402

logger = logging.getLogger("cognee_purge_source")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_DATASET = "governance"


def _api(token: str, method: str, path: str) -> tuple[int, str]:
    req = urllib.request.Request(  # noqa: S310 — fixed Cognee endpoint
        f"{BASE}{path}", method=method, headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def _dataset_id(token: str) -> str | None:
    status, body = _api(token, "GET", "/api/v1/datasets")
    if status != 200:
        return None
    for ds in json.loads(body):
        if ds.get("name") == _DATASET:
            return ds.get("id")
    return None


def list_data(token: str, dataset_id: str) -> list[dict]:
    status, body = _api(token, "GET", f"/api/v1/datasets/{dataset_id}/data")
    if status != 200:
        raise RuntimeError(f"list data {status}: {body[:160]}")
    return json.loads(body)


def purge(sources: list[str], *, apply: bool) -> int:
    token = get_token()
    if not token:
        logger.error("no Cognee auth token")
        return 2
    dataset_id = _dataset_id(token)
    if not dataset_id:
        logger.error("Cognee dataset %r not found", _DATASET)
        return 2
    items = list_data(token, dataset_id)
    by_name = {it.get("name"): it.get("id") for it in items}

    failed = 0
    for src in sources:
        data_id = by_name.get(src)
        if not data_id:
            logger.error("source not found in %s dataset: %s", _DATASET, src)
            failed += 1
            continue
        if not apply:
            logger.info("[dry-run] would delete %s (data_id=%s)", src, data_id)
            continue
        status, body = _api(token, "DELETE", f"/api/v1/datasets/{dataset_id}/data/{data_id}")
        if status not in (200, 204):
            logger.error("delete failed for %s: %s %s", src, status, body[:120])
            failed += 1
        else:
            logger.info("purged %s from Cognee %s dataset", src, _DATASET)
    print(f"sources: {len(sources)}  failed: {failed}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", action="append", default=[], help="exact data-item name to purge"
    )
    parser.add_argument("--apply", action="store_true", help="Delete (default dry-run)")
    args = parser.parse_args(argv)
    if not args.source:
        parser.error("at least one --source required")
    return purge(args.source, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
