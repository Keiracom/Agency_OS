#!/usr/bin/env python3
"""
Memory Search Tool for Elliot
Queries elliot_internal.memories using vector similarity search.

Usage:
    python3 tools/query_memory.py "What is the project focus?"
"""

import asyncio
import os
import sys
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

# ============================================
# CONFIG
# ============================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MATCH_THRESHOLD = 0.25  # Low threshold - text-embedding-3-small tends to have lower scores
MATCH_COUNT = 5

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL_MIGRATIONS") or os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


# ============================================
# FUNCTIONS
# ============================================

async def get_embedding(text: str) -> list[float]:
    """Generate embedding for query text."""
    
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text,
                "dimensions": EMBEDDING_DIMENSIONS,
            },
        )
        
        response.raise_for_status()
        data = response.json()
        
        return data["data"][0]["embedding"]


def search_memories(query_embedding: list[float]) -> list[dict]:
    """Search memories using vector similarity."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Convert embedding to pgvector format
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    # Direct similarity search (more flexible than RPC function)
    cur.execute("""
        SELECT 
            id, 
            content, 
            type, 
            metadata,
            1 - (embedding <=> %s::vector) as similarity
        FROM elliot_internal.memories
        WHERE embedding IS NOT NULL
          AND deleted_at IS NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (embedding_str, embedding_str, MATCH_COUNT))
    
    results = []
    for row in cur.fetchall():
        # Only include results above threshold
        similarity = row[4]
        if similarity >= MATCH_THRESHOLD:
            results.append({
                "id": str(row[0]),
                "content": row[1],
                "type": row[2],
                "metadata": row[3],
                "similarity": similarity,
            })
    
    cur.close()
    conn.close()
    
    return results


def format_results(results: list[dict], query: str) -> str:
    """Format search results as clean text."""
    
    if not results:
        return f"No memories found matching: '{query}'"
    
    output = [f"🔍 Memory Search: \"{query}\"", "=" * 50, ""]
    
    for i, result in enumerate(results, 1):
        similarity_pct = result["similarity"] * 100
        mem_type = result["type"]
        
        # Get section name from metadata if available
        metadata = result.get("metadata") or {}
        section = metadata.get("section", metadata.get("source_file", ""))
        
        # Truncate content for display
        content = result["content"]
        if len(content) > 500:
            content = content[:500] + "..."
        
        # Format entry
        output.append(f"[{i}] ({similarity_pct:.1f}% match) {mem_type}")
        if section:
            output.append(f"    Section: {section}")
        output.append(f"    {content[:200]}...")
        output.append("")
    
    return "\n".join(output)


async def main(query: str):
    """Main search function."""
    
    # Generate embedding for query
    query_embedding = await get_embedding(query)
    
    # Search memories
    results = search_memories(query_embedding)
    
    # Format and print results
    output = format_results(results, query)
    print(output)
    
    return results


# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tools/query_memory.py \"<query>\"")
        print("Example: python3 tools/query_memory.py \"What is the project focus?\"")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    asyncio.run(main(query))
