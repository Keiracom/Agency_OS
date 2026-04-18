#!/usr/bin/env python3
"""
SCHEMA-F1 Step 1 — One-time backfill of supersedes_id for 17 superseded rows.

For each row WHERE state='superseded' AND supersedes_id IS NULL:
  - Find best candidate superseder: same callsign + same source_type
    + created_at > superseded_row.created_at + nearest in time
  - Use match_agent_memories RPC to confirm content similarity > 0.85
  - If match found: UPDATE supersedes_id = superseder.id
                    + set typed_metadata.backfill_inferred = true
  - If no match:    set typed_metadata.backfill_failed = true
                    leave supersedes_id NULL

DO NOT run without Dave's review. Reads env from /home/elliotbot/.config/agency-os/.env
"""

import json
import os
import sys
from datetime import datetime, timezone

import httpx


def load_env() -> None:
    env_file = "/home/elliotbot/.config/agency-os/.env"
    if not os.path.exists(env_file):
        print(f"ERROR: env file not found at {env_file}", file=sys.stderr)
        sys.exit(1)
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), val)


def supabase_headers() -> dict:
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def supabase_url() -> str:
    return os.environ["SUPABASE_URL"]


SIMILARITY_THRESHOLD = 0.85


def fetch_superseded_nulls(client: httpx.Client) -> list[dict]:
    """Fetch all superseded rows with supersedes_id IS NULL."""
    url = (
        supabase_url()
        + "/rest/v1/agent_memories"
        "?state=eq.superseded"
        "&supersedes_id=is.null"
        "&select=id,callsign,source_type,content,typed_metadata,created_at,embedding"
    )
    resp = client.get(url, headers=supabase_headers())
    resp.raise_for_status()
    return resp.json()


def fetch_candidate_superseders(
    client: httpx.Client, callsign: str, source_type: str, after_ts: str
) -> list[dict]:
    """Fetch rows with same callsign + source_type created after the superseded row."""
    url = (
        supabase_url()
        + "/rest/v1/agent_memories"
        f"?callsign=eq.{callsign}"
        f"&source_type=eq.{source_type}"
        f"&created_at=gt.{after_ts}"
        "&state=neq.superseded"
        "&select=id,created_at,embedding"
        "&order=created_at.asc"
        "&limit=10"
    )
    resp = client.get(url, headers=supabase_headers())
    resp.raise_for_status()
    return resp.json()


def check_similarity_via_rpc(
    client: httpx.Client, embedding: list[float], candidate_id: str
) -> float | None:
    """
    Use match_agent_memories RPC to get similarity score for a candidate.
    Returns float similarity or None if not found / error.
    """
    rpc_url = supabase_url() + "/rest/v1/rpc/match_agent_memories_include_tentative"
    payload = {
        "query_embedding": embedding,
        "match_count": 10,
        "match_threshold": 0.0,
    }
    resp = client.post(rpc_url, headers=supabase_headers(), json=payload)
    if resp.status_code != 200:
        return None
    rows = resp.json() or []
    for row in rows:
        if row.get("id") == candidate_id:
            return row.get("similarity")
    return None


def patch_row(
    client: httpx.Client, row_id: str, patch_payload: dict
) -> bool:
    url = supabase_url() + f"/rest/v1/agent_memories?id=eq.{row_id}"
    headers = {**supabase_headers(), "Prefer": "return=minimal"}
    resp = client.patch(url, headers=headers, json=patch_payload)
    return resp.status_code in (200, 204)


def merge_typed_metadata(existing: dict | None, new_keys: dict) -> dict:
    base = existing if isinstance(existing, dict) else {}
    return {**base, **new_keys}


def main() -> None:
    load_env()

    print("SCHEMA-F1 Step 1 — Backfill supersedes_id")
    print("=" * 50)

    matched = 0
    failed = 0
    skipped_no_embedding = 0

    with httpx.Client(timeout=15) as client:
        orphans = fetch_superseded_nulls(client)
        print(f"Found {len(orphans)} superseded rows with supersedes_id=NULL\n")

        for row in orphans:
            row_id = row["id"]
            callsign = row.get("callsign") or ""
            source_type = row.get("source_type") or ""
            created_at = row.get("created_at") or ""
            embedding = row.get("embedding")
            current_meta = row.get("typed_metadata") or {}

            print(f"Processing {row_id} (callsign={callsign}, source_type={source_type})")

            if not embedding:
                print(f"  SKIP — no embedding, cannot compute similarity")
                skipped_no_embedding += 1
                continue

            candidates = fetch_candidate_superseders(
                client, callsign, source_type, created_at
            )

            if not candidates:
                print(f"  NO CANDIDATES — marking backfill_failed")
                meta = merge_typed_metadata(current_meta, {"backfill_failed": True})
                patch_row(client, row_id, {"typed_metadata": meta})
                failed += 1
                continue

            # Check similarity for each candidate (nearest in time = first)
            best_id = None
            best_similarity = 0.0
            for cand in candidates:
                cand_id = cand["id"]
                sim = check_similarity_via_rpc(client, embedding, cand_id)
                if sim is not None and sim > best_similarity:
                    best_similarity = sim
                    best_id = cand_id
                if best_similarity >= SIMILARITY_THRESHOLD:
                    break

            if best_id and best_similarity >= SIMILARITY_THRESHOLD:
                print(
                    f"  MATCH found: superseder={best_id} similarity={best_similarity:.4f}"
                )
                meta = merge_typed_metadata(
                    current_meta,
                    {
                        "backfill_inferred": True,
                        "backfill_similarity": round(best_similarity, 4),
                        "backfill_ts": datetime.now(timezone.utc).isoformat(),
                    },
                )
                ok = patch_row(
                    client,
                    row_id,
                    {"supersedes_id": best_id, "typed_metadata": meta},
                )
                if ok:
                    print(f"  PATCHED OK")
                    matched += 1
                else:
                    print(f"  PATCH FAILED — manual review needed")
                    failed += 1
            else:
                print(
                    f"  NO MATCH (best_similarity={best_similarity:.4f}) — marking backfill_failed"
                )
                meta = merge_typed_metadata(
                    current_meta,
                    {
                        "backfill_failed": True,
                        "backfill_best_similarity": round(best_similarity, 4),
                        "backfill_ts": datetime.now(timezone.utc).isoformat(),
                    },
                )
                patch_row(client, row_id, {"typed_metadata": meta})
                failed += 1

    print("\n" + "=" * 50)
    print("SUMMARY")
    print(f"  Matched + patched:   {matched}")
    print(f"  No match (failed):   {failed}")
    print(f"  Skipped (no embed):  {skipped_no_embedding}")
    print(f"  Total processed:     {len(orphans)}")


if __name__ == "__main__":
    main()
