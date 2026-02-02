#!/usr/bin/env python3
"""
Memory Master Tool - Unified memory interface.

⚠️ CRITICAL TOOL - This is your brain. Handle with care.

Consolidates: memory-db, elliot-memory, memory-hygiene, second-brain

Usage:
    python3 tools/memory_master.py <action> [query/content] [options]

Actions:
    search   - Semantic search over memories (vector search)
    save     - Store new memory to database
    list     - List recent memories by type
    stats    - Show memory statistics
    audit    - Check memory health
"""

import argparse
import asyncio
import json
import os
import sys
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
from psycopg2.extras import Json, RealDictCursor

# ============================================
# CONFIG
# ============================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MATCH_THRESHOLD = 0.25
MATCH_COUNT = 5

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL_MIGRATIONS") or os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


# ============================================
# EMBEDDING
# ============================================

async def get_embedding(text: str) -> list[float]:
    """Generate embedding for text."""
    
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


# ============================================
# SEARCH
# ============================================

async def search_memories(query: str, limit: int = MATCH_COUNT, mem_type: str = None) -> list[dict]:
    """Semantic search over memories using vector similarity."""
    
    # Generate embedding for query
    query_embedding = await get_embedding(query)
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Convert embedding to pgvector format
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    # Build query with optional type filter
    sql = """
        SELECT 
            id, 
            content, 
            type, 
            metadata,
            1 - (embedding <=> %s::vector(1536)) as similarity
        FROM elliot_internal.memories
        WHERE embedding IS NOT NULL
          AND deleted_at IS NULL
    """
    params = [embedding_str]
    
    if mem_type:
        sql += " AND type = %s"
        params.append(mem_type)
    
    sql += " ORDER BY similarity DESC LIMIT %s"
    params.append(limit)
    
    cur.execute(sql, params)
    
    results = []
    for row in cur.fetchall():
        similarity = row["similarity"]
        if similarity >= MATCH_THRESHOLD:
            results.append({
                "id": str(row["id"]),
                "content": row["content"],
                "type": row["type"],
                "metadata": row["metadata"],
                "similarity": round(similarity, 4),
            })
    
    cur.close()
    conn.close()
    
    return results


# ============================================
# SAVE
# ============================================

async def save_memory(content: str, mem_type: str = "general", metadata: dict = None) -> dict:
    """Save new memory to database with embedding."""
    
    # Generate embedding
    embedding = await get_embedding(content)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO elliot_internal.memories (content, type, embedding, metadata)
            VALUES (%s, %s, %s::vector, %s)
            RETURNING id
        """, (content, mem_type, embedding_str, Json(metadata or {})))
        
        memory_id = cur.fetchone()[0]
        conn.commit()
        
        return {
            "status": "saved",
            "id": str(memory_id),
            "type": mem_type,
            "content_preview": content[:100] + "..." if len(content) > 100 else content,
        }
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()


# ============================================
# LIST
# ============================================

def list_memories(mem_type: str = None, limit: int = 20) -> list[dict]:
    """List recent memories."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    sql = """
        SELECT id, type, metadata, created_at, 
               LEFT(content, 100) as preview
        FROM elliot_internal.memories
        WHERE deleted_at IS NULL
    """
    params = []
    
    if mem_type:
        sql += " AND type = %s"
        params.append(mem_type)
    
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    
    cur.execute(sql, params)
    results = [dict(row) for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return results


# ============================================
# STATS
# ============================================

def get_stats() -> dict:
    """Get memory statistics."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    stats = {}
    
    # Total count
    cur.execute("SELECT COUNT(*) FROM elliot_internal.memories WHERE deleted_at IS NULL")
    stats["total"] = cur.fetchone()[0]
    
    # Count by type
    cur.execute("""
        SELECT type, COUNT(*) 
        FROM elliot_internal.memories 
        WHERE deleted_at IS NULL 
        GROUP BY type
    """)
    stats["by_type"] = {row[0]: row[1] for row in cur.fetchall()}
    
    # With embeddings
    cur.execute("""
        SELECT COUNT(*) 
        FROM elliot_internal.memories 
        WHERE embedding IS NOT NULL AND deleted_at IS NULL
    """)
    stats["with_embeddings"] = cur.fetchone()[0]
    
    # Without embeddings
    stats["without_embeddings"] = stats["total"] - stats["with_embeddings"]
    
    cur.close()
    conn.close()
    
    return stats


# ============================================
# AUDIT
# ============================================

def audit_memories() -> dict:
    """Audit memory health."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    audit = {"issues": [], "ok": []}
    
    # Check for memories without embeddings
    cur.execute("""
        SELECT COUNT(*) 
        FROM elliot_internal.memories 
        WHERE embedding IS NULL AND deleted_at IS NULL
    """)
    unembedded = cur.fetchone()[0]
    if unembedded > 0:
        audit["issues"].append(f"{unembedded} memories without embeddings")
    else:
        audit["ok"].append("All memories have embeddings")
    
    # Check for duplicates (same content hash)
    cur.execute("""
        SELECT content_hash, COUNT(*) 
        FROM elliot_internal.memories 
        WHERE deleted_at IS NULL 
        GROUP BY content_hash 
        HAVING COUNT(*) > 1
    """)
    duplicates = cur.fetchall()
    if duplicates:
        audit["issues"].append(f"{len(duplicates)} duplicate content hashes")
    else:
        audit["ok"].append("No duplicate content")
    
    # Check embedding dimensions
    cur.execute("""
        SELECT DISTINCT vector_dims(embedding) 
        FROM elliot_internal.memories 
        WHERE embedding IS NOT NULL
    """)
    dims = [row[0] for row in cur.fetchall()]
    if len(dims) > 1:
        audit["issues"].append(f"Mixed embedding dimensions: {dims}")
    elif dims and dims[0] != EMBEDDING_DIMENSIONS:
        audit["issues"].append(f"Wrong dimensions: {dims[0]} (expected {EMBEDDING_DIMENSIONS})")
    else:
        audit["ok"].append(f"Embedding dimensions correct ({EMBEDDING_DIMENSIONS})")
    
    cur.close()
    conn.close()
    
    audit["healthy"] = len(audit["issues"]) == 0
    return audit


# ============================================
# ROUTER
# ============================================

async def route(action: str, **kwargs) -> dict | list[dict]:
    """Route to appropriate memory action."""
    
    query = kwargs.get("query")
    content = kwargs.get("content")
    mem_type = kwargs.get("type")
    limit = kwargs.get("limit", MATCH_COUNT)
    metadata = kwargs.get("metadata")
    
    if action == "search":
        if not query:
            return [{"error": "query required for search"}]
        return await search_memories(query, limit, mem_type)
    
    elif action == "save":
        if not content:
            return {"error": "content required for save"}
        return await save_memory(content, mem_type or "general", metadata)
    
    elif action == "list":
        return list_memories(mem_type, limit)
    
    elif action == "stats":
        return get_stats()
    
    elif action == "audit":
        return audit_memories()
    
    else:
        return {"error": f"Unknown action: {action}"}


# ============================================
# FORMATTING
# ============================================

def format_results(results, action: str) -> str:
    """Format results for display."""
    
    if isinstance(results, dict):
        if "error" in results:
            return f"❌ Error: {results['error']}"
        
        if action == "stats":
            output = ["🧠 Memory Statistics", "=" * 50]
            output.append(f"Total memories: {results.get('total')}")
            output.append(f"With embeddings: {results.get('with_embeddings')}")
            output.append(f"Without embeddings: {results.get('without_embeddings')}")
            output.append("\nBy type:")
            for t, count in results.get("by_type", {}).items():
                output.append(f"  {t}: {count}")
            return "\n".join(output)
        
        elif action == "audit":
            output = ["🔍 Memory Audit", "=" * 50]
            if results.get("healthy"):
                output.append("✅ Memory system healthy")
            else:
                output.append("⚠️ Issues found:")
            for issue in results.get("issues", []):
                output.append(f"  ❌ {issue}")
            for ok in results.get("ok", []):
                output.append(f"  ✅ {ok}")
            return "\n".join(output)
        
        elif action == "save":
            return f"✅ Saved: {results.get('id')} ({results.get('type')})\n   {results.get('content_preview')}"
    
    if isinstance(results, list):
        if not results:
            return "No results found."
        
        if "error" in results[0]:
            return f"❌ Error: {results[0]['error']}"
        
        output = [f"🔍 Memory Search Results ({len(results)} matches)", "=" * 50, ""]
        
        for i, item in enumerate(results, 1):
            similarity_pct = item.get("similarity", 0) * 100
            mem_type = item.get("type", "?")
            metadata = item.get("metadata") or {}
            section = metadata.get("section", metadata.get("skill_name", ""))
            
            content = item.get("content", "")[:200].replace("\n", " ")
            
            output.append(f"[{i}] ({similarity_pct:.1f}% match) {mem_type}")
            if section:
                output.append(f"    Section: {section}")
            output.append(f"    {content}...")
            output.append("")
        
        return "\n".join(output)
    
    return json.dumps(results, indent=2, default=str)


# ============================================
# CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Memory Master Tool - Your brain interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument("action", choices=["search", "save", "list", "stats", "audit"],
                        help="Action to perform")
    parser.add_argument("query", nargs="?", default=None,
                        help="Search query or content to save")
    parser.add_argument("--type", "-t", dest="mem_type",
                        help="Memory type filter (core_fact, rule, daily_log, etc.)")
    parser.add_argument("--limit", "-n", type=int, default=5,
                        help="Number of results")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON")
    
    args = parser.parse_args()
    
    # Run async
    results = asyncio.run(route(
        action=args.action,
        query=args.query,
        content=args.query,  # For save action
        type=args.mem_type,
        limit=args.limit,
    ))
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_results(results, args.action))


if __name__ == "__main__":
    main()
