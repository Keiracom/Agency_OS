#!/usr/bin/env python3
"""
Embed Memories - Crash-proof embedding with incremental processing.

STABILITY PATCH (2026-02-02):
- Batch size reduced to 10
- Incremental fetch (while loop, not bulk load)
- Explicit garbage collection between batches
- 1 second throttle between batches

Usage:
    python3 tools/embed_memories.py
"""

import gc
import os
import sys
import time
from pathlib import Path

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================
# CONFIG
# ============================================

BATCH_SIZE = 10  # Reduced from 50
THROTTLE_SECONDS = 1  # Sleep between batches
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Load env
def load_env():
    env_file = Path.home() / ".config/agency-os/.env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    value = value.strip().strip('"').strip("'")
                    os.environ[key.strip()] = value

load_env()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL_MIGRATIONS") or os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


# ============================================
# EMBEDDING (Synchronous for stability)
# ============================================

def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a batch of texts (synchronous)."""
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": texts,
                "dimensions": EMBEDDING_DIMENSIONS,
            },
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Sort by index to maintain order
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]


# ============================================
# DATABASE (Fresh connection per batch)
# ============================================

def get_batch_without_embeddings() -> list[dict]:
    """Fetch ONE batch of memories without embeddings."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT id, content
        FROM elliot_internal.memories
        WHERE embedding IS NULL AND deleted_at IS NULL
        ORDER BY created_at ASC
        LIMIT %s
    """, (BATCH_SIZE,))
    
    results = [dict(row) for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return results


def count_without_embeddings() -> int:
    """Count memories without embeddings."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COUNT(*)
        FROM elliot_internal.memories
        WHERE embedding IS NULL AND deleted_at IS NULL
    """)
    
    count = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return count


def update_embeddings(updates: list[tuple[str, list[float]]]):
    """Update multiple memories with their embeddings."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    for memory_id, embedding in updates:
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        cur.execute("""
            UPDATE elliot_internal.memories
            SET embedding = %s::vector
            WHERE id = %s
        """, (embedding_str, memory_id))
    
    conn.commit()
    cur.close()
    conn.close()


# ============================================
# MAIN LOOP (Crash-proof)
# ============================================

def main():
    print("🧠 Embedding Memories (Crash-Proof Mode)", flush=True)
    print(f"   Batch size: {BATCH_SIZE}", flush=True)
    print(f"   Throttle: {THROTTLE_SECONDS}s between batches", flush=True)
    print("=" * 60, flush=True)
    
    total_embedded = 0
    
    while True:
        # Get count of remaining
        remaining = count_without_embeddings()
        
        if remaining == 0:
            print("", flush=True)
            print("=" * 60, flush=True)
            print(f"✅ COMPLETE: {total_embedded} memories embedded", flush=True)
            break
        
        # Fetch ONE batch
        batch = get_batch_without_embeddings()
        
        if not batch:
            print("✅ No more memories to embed.", flush=True)
            break
        
        # Truncate content for embedding (8000 chars max)
        texts = [m["content"][:8000] for m in batch]
        ids = [m["id"] for m in batch]
        
        try:
            # Get embeddings
            embeddings = get_embeddings_batch(texts)
            
            # Update database
            updates = list(zip(ids, embeddings))
            update_embeddings(updates)
            
            total_embedded += len(batch)
            print(f"   ✓ {total_embedded} embedded ({remaining - len(batch)} remaining)", flush=True)
            
        except Exception as e:
            print(f"   ⚠️ Batch error: {e}", flush=True)
            # Continue to next batch instead of crashing
        
        # CRITICAL: Clear memory
        del batch
        del texts
        del ids
        gc.collect()
        
        # Throttle
        time.sleep(THROTTLE_SECONDS)
    
    print("🏁 Embedding process finished.", flush=True)


if __name__ == "__main__":
    main()
