#!/usr/bin/env python3
"""
LISTENER-KNOWLEDGE-SEED-V1 — Ingest curated factual chunks from
docs/MANUAL.md + ARCHITECTURE.md into public.agent_memories.

Pairs with Elliot's CLAUDE.md ingest. Both target:
  source_type = 'verified_fact'
  state       = 'confirmed'
  trust       = 'dave_confirmed'
  confidence  = 1.0

Reads chunks from /tmp/seed_chunks_aiden.json (produced by extraction agent
per docs/governance_chunking.md rules).

Embeds each chunk via OpenAI text-embedding-3-small (batched) and bulk-inserts
into Supabase via REST. Logs OpenAI cost per batch.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx

CHUNK_FILE = "/tmp/seed_chunks_aiden.json"
ENV_FILE = "/home/elliotbot/.config/agency-os/.env"
EMBED_MODEL = "text-embedding-3-small"
EMBED_BATCH = 64
INSERT_BATCH = 50
DIRECTIVE_ID = "LISTENER-KNOWLEDGE-SEED-V1"


def load_env() -> None:
    if not os.path.exists(ENV_FILE):
        print(f"ERROR: env not found at {ENV_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def embed_batch(client: httpx.Client, texts: list[str]) -> tuple[list[list[float]], dict]:
    resp = client.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={"model": EMBED_MODEL, "input": texts},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    embeddings = [item["embedding"] for item in data["data"]]
    return embeddings, data.get("usage", {})


def insert_batch(client: httpx.Client, rows: list[dict]) -> None:
    url = os.environ["SUPABASE_URL"] + "/rest/v1/agent_memories"
    key = os.environ["SUPABASE_SERVICE_KEY"]
    resp = client.post(
        url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        json=rows,
        timeout=60,
    )
    if resp.status_code not in (200, 201, 204):
        print(f"INSERT FAILED {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
        resp.raise_for_status()


def main() -> None:
    load_env()

    with open(CHUNK_FILE) as f:
        chunks = json.load(f)

    print(f"Loaded {len(chunks)} chunks from {CHUNK_FILE}")

    # Skip any chunks flagged _uncertain (spec allowed reviewers to drop these)
    chunks = [c for c in chunks if not c.get("_uncertain")]
    print(f"After _uncertain filter: {len(chunks)} chunks\n")

    now_iso = datetime.now(timezone.utc).isoformat()
    total_input_tokens = 0

    # Step 1 — embed in batches
    print(f"Embedding via {EMBED_MODEL} in batches of {EMBED_BATCH}...")
    with httpx.Client() as client:
        for i in range(0, len(chunks), EMBED_BATCH):
            batch = chunks[i : i + EMBED_BATCH]
            texts = [c["content"] for c in batch]
            embeddings, usage = embed_batch(client, texts)
            total_input_tokens += usage.get("total_tokens", 0)
            for c, emb in zip(batch, embeddings):
                c["_embedding"] = emb
            print(
                f"  batch {i // EMBED_BATCH + 1}: {len(batch)} chunks, "
                f"{usage.get('total_tokens', 0)} tokens"
            )

    # Rough cost calc: text-embedding-3-small = $0.02 per 1M tokens (USD)
    cost_usd = total_input_tokens / 1_000_000 * 0.02
    cost_aud = cost_usd * 1.55
    print(
        f"\nEmbedding total: {total_input_tokens} tokens -> "
        f"~${cost_usd:.6f} USD / ~${cost_aud:.6f} AUD"
    )

    # Step 2 — build insert rows
    rows = []
    for c in chunks:
        typed_meta = {
            "source": "governance_doc",
            "section": c.get("section"),
            "origin_file": c.get("origin_file"),
            "seeded_at": now_iso,
            "seeded_by": DIRECTIVE_ID,
            "ingested_by": DIRECTIVE_ID,
        }
        if c.get("sub_section"):
            typed_meta["sub_section"] = c["sub_section"]

        rows.append(
            {
                "callsign": "system",
                "source_type": "verified_fact",
                "content": c["content"],
                "typed_metadata": typed_meta,
                "tags": c.get("tags", []),
                "state": "confirmed",
                "confidence": 1.0,
                "trust": "dave_confirmed",
                "embedding": c["_embedding"],
                "directive_id": DIRECTIVE_ID,
            }
        )

    # Step 3 — insert in batches
    print(
        f"\nInserting {len(rows)} rows into public.agent_memories in batches of {INSERT_BATCH}..."
    )
    with httpx.Client() as client:
        for i in range(0, len(rows), INSERT_BATCH):
            batch = rows[i : i + INSERT_BATCH]
            insert_batch(client, batch)
            print(f"  batch {i // INSERT_BATCH + 1}: +{len(batch)} rows")
            time.sleep(0.1)

    print(f"\nDone. Inserted {len(rows)} rows with directive_id={DIRECTIVE_ID}.")
    print(f"Embedding cost: ~${cost_aud:.6f} AUD ({total_input_tokens} tokens).")


if __name__ == "__main__":
    main()
