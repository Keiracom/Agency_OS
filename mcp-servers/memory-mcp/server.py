#!/usr/bin/env python3
"""
Memory MCP Server - Semantic memory search over elliot_internal.memories.

Wraps the existing Supabase + pgvector memory system as an MCP.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ============================================
# ENV LOADING
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

# ============================================
# CONFIG
# ============================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
DEFAULT_MATCH_THRESHOLD = 0.25
DEFAULT_LIMIT = 10

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Database URL for direct psycopg2 connection
DATABASE_URL = os.getenv("DATABASE_URL_MIGRATIONS") or os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# ============================================
# DATABASE
# ============================================

import psycopg2
from psycopg2.extras import Json, RealDictCursor

def get_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)

# ============================================
# EMBEDDING
# ============================================

async def get_embedding(text: str) -> list[float]:
    """Generate embedding for text using OpenAI."""
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

def embedding_to_pgvector(embedding: list[float]) -> str:
    """Convert embedding list to pgvector format."""
    return "[" + ",".join(str(x) for x in embedding) + "]"

# ============================================
# MEMORY OPERATIONS
# ============================================

async def search_memories(query: str, limit: int = DEFAULT_LIMIT, min_score: float = DEFAULT_MATCH_THRESHOLD) -> list[dict]:
    """Semantic search over memories."""
    query_embedding = await get_embedding(query)
    embedding_str = embedding_to_pgvector(query_embedding)
    
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT 
                id, 
                content, 
                tags,
                source,
                metadata,
                created_at,
                1 - (embedding <=> %s::vector(1536)) as similarity
            FROM elliot_internal.memories
            WHERE embedding IS NOT NULL
            ORDER BY similarity DESC
            LIMIT %s
        """, (embedding_str, limit * 2))  # Fetch more to filter by min_score
        
        results = []
        for row in cur.fetchall():
            similarity = float(row["similarity"])
            if similarity >= min_score:
                results.append({
                    "id": str(row["id"]),
                    "content": row["content"],
                    "tags": row["tags"] or [],
                    "source": row["source"],
                    "metadata": row["metadata"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "similarity": round(similarity, 4),
                })
                if len(results) >= limit:
                    break
        
        return results
    finally:
        cur.close()
        conn.close()

async def save_memory(content: str, tags: list[str] = None, source: str = None, metadata: dict = None) -> dict:
    """Save a new memory with auto-embedding."""
    embedding = await get_embedding(content)
    embedding_str = embedding_to_pgvector(embedding)
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        memory_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO elliot_internal.memories (id, content, embedding, tags, source, metadata, created_at)
            VALUES (%s, %s, %s::vector, %s, %s, %s, NOW())
            RETURNING id, created_at
        """, (memory_id, content, embedding_str, tags or [], source, Json(metadata or {})))
        
        result = cur.fetchone()
        conn.commit()
        
        return {
            "status": "saved",
            "id": str(result[0]),
            "content_preview": content[:200] + "..." if len(content) > 200 else content,
            "tags": tags or [],
            "source": source,
            "created_at": result[1].isoformat() if result[1] else None,
        }
    except Exception as e:
        conn.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        cur.close()
        conn.close()

def list_recent_memories(hours: int = 24, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """List recent memories within specified hours."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cur.execute("""
            SELECT id, content, tags, source, metadata, created_at
            FROM elliot_internal.memories
            WHERE created_at >= %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (cutoff, limit))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "id": str(row["id"]),
                "content": row["content"],
                "tags": row["tags"] or [],
                "source": row["source"],
                "metadata": row["metadata"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            })
        
        return results
    finally:
        cur.close()
        conn.close()

def get_memory_by_id(memory_id: str) -> dict | None:
    """Get a specific memory by ID."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT id, content, tags, source, metadata, created_at
            FROM elliot_internal.memories
            WHERE id = %s
        """, (memory_id,))
        
        row = cur.fetchone()
        if not row:
            return None
        
        return {
            "id": str(row["id"]),
            "content": row["content"],
            "tags": row["tags"] or [],
            "source": row["source"],
            "metadata": row["metadata"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
    finally:
        cur.close()
        conn.close()

def delete_memory(memory_id: str) -> dict:
    """Delete a memory by ID."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM elliot_internal.memories
            WHERE id = %s
            RETURNING id
        """, (memory_id,))
        
        result = cur.fetchone()
        conn.commit()
        
        if result:
            return {"status": "deleted", "id": str(result[0])}
        else:
            return {"status": "not_found", "id": memory_id}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        cur.close()
        conn.close()

def get_memory_stats() -> dict:
    """Get memory statistics."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        stats = {}
        
        # Total count
        cur.execute("SELECT COUNT(*) FROM elliot_internal.memories")
        stats["total"] = cur.fetchone()[0]
        
        # With embeddings
        cur.execute("SELECT COUNT(*) FROM elliot_internal.memories WHERE embedding IS NOT NULL")
        stats["with_embeddings"] = cur.fetchone()[0]
        stats["without_embeddings"] = stats["total"] - stats["with_embeddings"]
        
        # By source
        cur.execute("""
            SELECT COALESCE(source, 'unknown') as src, COUNT(*) 
            FROM elliot_internal.memories 
            GROUP BY source
            ORDER BY COUNT(*) DESC
        """)
        stats["by_source"] = {row[0]: row[1] for row in cur.fetchall()}
        
        # By tag (unnest tags array)
        cur.execute("""
            SELECT tag, COUNT(*) 
            FROM elliot_internal.memories, UNNEST(tags) as tag
            GROUP BY tag
            ORDER BY COUNT(*) DESC
            LIMIT 20
        """)
        stats["by_tag"] = {row[0]: row[1] for row in cur.fetchall()}
        
        # Recent activity
        cur.execute("""
            SELECT COUNT(*) FROM elliot_internal.memories 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        stats["last_24h"] = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) FROM elliot_internal.memories 
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        stats["last_7d"] = cur.fetchone()[0]
        
        return stats
    finally:
        cur.close()
        conn.close()

def search_by_tag(tag: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Search memories by tag."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT id, content, tags, source, metadata, created_at
            FROM elliot_internal.memories
            WHERE %s = ANY(tags)
            ORDER BY created_at DESC
            LIMIT %s
        """, (tag, limit))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "id": str(row["id"]),
                "content": row["content"],
                "tags": row["tags"] or [],
                "source": row["source"],
                "metadata": row["metadata"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            })
        
        return results
    finally:
        cur.close()
        conn.close()

async def bulk_save_memories(memories: list[dict]) -> dict:
    """Batch save multiple memories."""
    results = []
    errors = []
    
    for i, mem in enumerate(memories):
        try:
            content = mem.get("content")
            if not content:
                errors.append({"index": i, "error": "content required"})
                continue
            
            result = await save_memory(
                content=content,
                tags=mem.get("tags"),
                source=mem.get("source"),
                metadata=mem.get("metadata"),
            )
            
            if result.get("status") == "saved":
                results.append({"index": i, "id": result["id"]})
            else:
                errors.append({"index": i, "error": result.get("error", "unknown error")})
        except Exception as e:
            errors.append({"index": i, "error": str(e)})
    
    return {
        "saved": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors if errors else None,
    }

# ============================================
# MCP SERVER
# ============================================

server = Server("memory-mcp")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available memory tools."""
    return [
        Tool(
            name="search",
            description="Semantic search over memories using vector similarity. Returns memories ranked by relevance to the query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    },
                    "min_score": {
                        "type": "number",
                        "description": "Minimum similarity score 0-1 (default: 0.25)",
                        "default": 0.25
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="save",
            description="Save a new memory with auto-generated embedding for semantic search.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Memory content to save"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for categorization"
                    },
                    "source": {
                        "type": "string",
                        "description": "Source of the memory (e.g., 'conversation', 'document', 'user')"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata JSON"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="list_recent",
            description="List recently created memories within a time window.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Look back hours (default: 24)",
                        "default": 24
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_by_id",
            description="Get a specific memory by its UUID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "UUID of the memory"
                    }
                },
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="delete",
            description="Delete a memory by its UUID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "UUID of the memory to delete"
                    }
                },
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="get_stats",
            description="Get memory statistics including counts by tag, source, and recent activity.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="search_by_tag",
            description="Find memories with a specific tag.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "Tag to search for"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                },
                "required": ["tag"]
            }
        ),
        Tool(
            name="bulk_save",
            description="Batch save multiple memories at once. Each memory should have content, and optionally tags, source, metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                                "source": {"type": "string"},
                                "metadata": {"type": "object"}
                            },
                            "required": ["content"]
                        },
                        "description": "Array of memories to save"
                    }
                },
                "required": ["memories"]
            }
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search":
            result = await search_memories(
                query=arguments["query"],
                limit=arguments.get("limit", DEFAULT_LIMIT),
                min_score=arguments.get("min_score", DEFAULT_MATCH_THRESHOLD),
            )
        elif name == "save":
            result = await save_memory(
                content=arguments["content"],
                tags=arguments.get("tags"),
                source=arguments.get("source"),
                metadata=arguments.get("metadata"),
            )
        elif name == "list_recent":
            result = list_recent_memories(
                hours=arguments.get("hours", 24),
                limit=arguments.get("limit", DEFAULT_LIMIT),
            )
        elif name == "get_by_id":
            result = get_memory_by_id(arguments["memory_id"])
            if result is None:
                result = {"status": "not_found", "id": arguments["memory_id"]}
        elif name == "delete":
            result = delete_memory(arguments["memory_id"])
        elif name == "get_stats":
            result = get_memory_stats()
        elif name == "search_by_tag":
            result = search_by_tag(
                tag=arguments["tag"],
                limit=arguments.get("limit", DEFAULT_LIMIT),
            )
        elif name == "bulk_save":
            result = await bulk_save_memories(arguments["memories"])
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]

# ============================================
# MAIN
# ============================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
