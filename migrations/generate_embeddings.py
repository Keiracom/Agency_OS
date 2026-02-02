#!/usr/bin/env python3
"""
Standalone script to generate embeddings for memories.
No Prefect dependency - runs directly.
"""

import asyncio
import os
import json
from datetime import datetime, timezone
from pathlib import Path

# ============================================
# LOAD ENV
# ============================================

def load_env():
    """Load environment variables from .env file."""
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

import httpx
import psycopg2
from psycopg2.extras import Json

# ============================================
# CONFIG
# ============================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
BATCH_LIMIT = 50
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL_MIGRATIONS") or os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# ============================================
# FUNCTIONS
# ============================================

async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Call OpenAI API to get embeddings."""
    
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
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
        
        # Extract embeddings in order
        embeddings = [item["embedding"] for item in data["data"]]
        
        # Log usage
        usage = data.get("usage", {})
        print(f"  📊 Tokens used: {usage.get('total_tokens', 'N/A')}")
        
        return embeddings


async def main():
    print("🧠 Embedding Generator for elliot_internal.memories")
    print("=" * 50)
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    print("✅ Connected")
    
    # Fetch memories without embeddings
    print(f"\n📥 Fetching memories without embeddings (limit {BATCH_LIMIT})...")
    cur.execute("""
        SELECT id, content, type 
        FROM elliot_internal.memories 
        WHERE embedding IS NULL 
          AND deleted_at IS NULL
        LIMIT %s
    """, (BATCH_LIMIT,))
    
    rows = cur.fetchall()
    print(f"✅ Found {len(rows)} memories to embed")
    
    if not rows:
        print("\n🎉 All memories already have embeddings!")
        cur.close()
        conn.close()
        return
    
    # Extract IDs and content
    memory_ids = [row[0] for row in rows]
    texts = [row[1] for row in rows]
    types = [row[2] for row in rows]
    
    # Generate embeddings
    print(f"\n🤖 Generating embeddings via OpenAI ({EMBEDDING_MODEL})...")
    embeddings = await get_embeddings(texts)
    print(f"✅ Generated {len(embeddings)} embeddings")
    
    # Update database
    print(f"\n💾 Updating database...")
    updated = 0
    for memory_id, embedding, mem_type in zip(memory_ids, embeddings, types):
        try:
            # Convert embedding to pgvector format
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            
            cur.execute("""
                UPDATE elliot_internal.memories 
                SET embedding = %s::vector,
                    updated_at = NOW()
                WHERE id = %s
            """, (embedding_str, str(memory_id)))
            
            updated += 1
            print(f"  ✅ {mem_type}: {str(memory_id)[:8]}...")
        except Exception as e:
            print(f"  ❌ Failed {memory_id}: {e}")
    
    conn.commit()
    
    # Log to prefect_logs
    print(f"\n📝 Logging run...")
    try:
        cur.execute("""
            INSERT INTO elliot_internal.prefect_logs 
            (flow_name, state, completed_at, result, tags, metadata)
            VALUES (%s, %s, NOW(), %s, %s, %s)
        """, (
            "embed_memories",
            "COMPLETED",
            Json({"records_processed": updated}),
            ["maintenance", "embeddings"],
            Json({"model": EMBEDDING_MODEL, "dimensions": EMBEDDING_DIMENSIONS}),
        ))
        conn.commit()
        print("✅ Logged to prefect_logs")
    except Exception as e:
        print(f"⚠️  Failed to log: {e}")
    
    cur.close()
    conn.close()
    
    # Summary
    print("\n" + "=" * 50)
    print(f"✅ EMBEDDING COMPLETE")
    print(f"   Records processed: {updated}/{len(rows)}")
    print(f"   Model: {EMBEDDING_MODEL}")
    print(f"   Dimensions: {EMBEDDING_DIMENSIONS}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
