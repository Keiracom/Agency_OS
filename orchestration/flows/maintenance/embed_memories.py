"""
FILE: orchestration/flows/maintenance/embed_memories.py
PURPOSE: Prefect Flow to generate embeddings for memories without vectors
CREATED: 2026-02-01
DEPENDENCIES:
  - openai
  - supabase
  - prefect
ENV VARS:
  - SUPABASE_URL
  - SUPABASE_KEY (or SUPABASE_SERVICE_KEY)
  - OPENAI_API_KEY
"""

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from openai import AsyncOpenAI
from supabase import create_client, Client

# ============================================
# CONFIGURATION
# ============================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # Default for text-embedding-3-small
BATCH_LIMIT = 50  # Max rows per run to avoid timeouts
SCHEMA = "elliot_internal"
TABLE = "memories"


# ============================================
# ENVIRONMENT SETUP
# ============================================

def load_env():
    """Load environment variables from .env file if needed."""
    env_file = Path.home() / ".config/agency-os/.env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    value = value.strip().strip('"').strip("'")
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value


# ============================================
# CLIENTS
# ============================================

def get_supabase_client() -> Client:
    """Initialize Supabase client."""
    load_env()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_KEY required")
    
    return create_client(url, key)


def get_openai_client() -> AsyncOpenAI:
    """Initialize async OpenAI client."""
    load_env()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY required")
    
    return AsyncOpenAI(api_key=api_key)


# ============================================
# TASKS
# ============================================

@task(
    name="fetch_unembedded_memories",
    description="Fetch memories without embeddings",
    retries=2,
    retry_delay_seconds=5,
)
def fetch_unembedded_memories(supabase: Client, limit: int = BATCH_LIMIT) -> list[dict]:
    """
    Fetch memories where embedding IS NULL.
    
    Args:
        supabase: Supabase client
        limit: Maximum rows to fetch
        
    Returns:
        List of memory records needing embeddings
    """
    logger = get_run_logger()
    
    # Query elliot_internal.memories where embedding is null
    response = supabase.schema(SCHEMA).table(TABLE).select(
        "id", "content", "type", "metadata"
    ).is_("embedding", "null").is_("deleted_at", "null").limit(limit).execute()
    
    records = response.data or []
    logger.info(f"Found {len(records)} memories needing embeddings")
    
    return records


@task(
    name="generate_embeddings",
    description="Generate embeddings via OpenAI API",
    retries=2,
    retry_delay_seconds=10,
)
async def generate_embeddings(
    openai_client: AsyncOpenAI,
    texts: list[str]
) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts.
    
    Args:
        openai_client: Async OpenAI client
        texts: List of text strings to embed
        
    Returns:
        List of embedding vectors (1536 dimensions each)
    """
    logger = get_run_logger()
    
    if not texts:
        return []
    
    logger.info(f"Generating embeddings for {len(texts)} texts...")
    
    # Call OpenAI embeddings API
    response = await openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    
    # Extract embeddings in order
    embeddings = [item.embedding for item in response.data]
    
    logger.info(f"Generated {len(embeddings)} embeddings ({EMBEDDING_DIMENSIONS} dimensions each)")
    
    # Log token usage
    if hasattr(response, 'usage'):
        logger.info(f"Tokens used: {response.usage.total_tokens}")
    
    return embeddings


@task(
    name="update_memory_embeddings",
    description="Update memories with their embeddings",
    retries=2,
    retry_delay_seconds=5,
)
def update_memory_embeddings(
    supabase: Client,
    memory_ids: list[str],
    embeddings: list[list[float]]
) -> int:
    """
    Update memory records with their embeddings.
    
    Args:
        supabase: Supabase client
        memory_ids: List of memory UUIDs
        embeddings: Corresponding embedding vectors
        
    Returns:
        Number of successfully updated records
    """
    logger = get_run_logger()
    
    if len(memory_ids) != len(embeddings):
        raise ValueError(f"Mismatch: {len(memory_ids)} IDs vs {len(embeddings)} embeddings")
    
    updated = 0
    failed = 0
    
    for memory_id, embedding in zip(memory_ids, embeddings):
        try:
            # Update the embedding column
            # pgvector expects the embedding as a list/array
            supabase.schema(SCHEMA).table(TABLE).update({
                "embedding": embedding,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", memory_id).execute()
            
            updated += 1
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            failed += 1
    
    logger.info(f"Updated {updated} memories, {failed} failures")
    return updated


@task(
    name="log_embedding_run",
    description="Log the embedding run to prefect_logs",
)
def log_embedding_run(
    supabase: Client,
    flow_run_id: str,
    records_processed: int,
    status: str,
    error_message: str | None = None
) -> None:
    """
    Log the embedding run to elliot_internal.prefect_logs.
    
    Args:
        supabase: Supabase client
        flow_run_id: Prefect flow run ID
        records_processed: Number of records embedded
        status: 'COMPLETED' or 'FAILED'
        error_message: Error details if failed
    """
    logger = get_run_logger()
    
    try:
        supabase.schema(SCHEMA).table("prefect_logs").insert({
            "flow_run_id": flow_run_id,
            "flow_name": "embed_memories",
            "state": status,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "parameters": {"batch_limit": BATCH_LIMIT},
            "result": {"records_processed": records_processed},
            "error_message": error_message,
            "tags": ["maintenance", "embeddings"],
            "metadata": {
                "model": EMBEDDING_MODEL,
                "dimensions": EMBEDDING_DIMENSIONS,
            },
        }).execute()
        
        logger.info(f"Logged run to prefect_logs: {status}")
    except Exception as e:
        logger.warning(f"Failed to log run: {e}")


# ============================================
# MAIN FLOW
# ============================================

@flow(
    name="embed_memories",
    description="Generate embeddings for memories without vectors",
    version="1.0.0",
    retries=1,
    retry_delay_seconds=30,
)
async def embed_memories_flow(batch_limit: int = BATCH_LIMIT) -> dict[str, Any]:
    """
    Main flow to embed memories.
    
    1. Fetch memories where embedding IS NULL (limit 50)
    2. Generate embeddings via OpenAI
    3. Update records with embeddings
    4. Log run to prefect_logs
    
    Args:
        batch_limit: Maximum records to process per run
        
    Returns:
        Summary dict with counts
    """
    logger = get_run_logger()
    logger.info(f"Starting embed_memories flow (limit: {batch_limit})")
    
    # Initialize clients
    supabase = get_supabase_client()
    openai_client = get_openai_client()
    
    # Track results
    result = {
        "fetched": 0,
        "embedded": 0,
        "updated": 0,
        "status": "COMPLETED",
        "error": None,
    }
    
    try:
        # Step 1: Fetch unembedded memories
        memories = fetch_unembedded_memories(supabase, batch_limit)
        result["fetched"] = len(memories)
        
        if not memories:
            logger.info("No memories need embedding. Done!")
            return result
        
        # Step 2: Extract content and IDs
        memory_ids = [m["id"] for m in memories]
        texts = [m["content"] for m in memories]
        
        # Step 3: Generate embeddings (async)
        embeddings = await generate_embeddings(openai_client, texts)
        result["embedded"] = len(embeddings)
        
        # Step 4: Update records
        updated_count = update_memory_embeddings(supabase, memory_ids, embeddings)
        result["updated"] = updated_count
        
        logger.info(f"✅ Flow complete: {updated_count}/{len(memories)} memories embedded")
        
    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = str(e)
        logger.error(f"❌ Flow failed: {e}")
        raise
    
    finally:
        # Log run (best effort)
        try:
            from prefect.context import get_run_context
            ctx = get_run_context()
            flow_run_id = str(ctx.flow_run.id) if ctx and ctx.flow_run else "unknown"
        except Exception:
            flow_run_id = "unknown"
        
        log_embedding_run(
            supabase,
            flow_run_id,
            result["updated"],
            result["status"],
            result["error"],
        )
    
    return result


# ============================================
# CLI ENTRYPOINT
# ============================================

if __name__ == "__main__":
    # Run the flow directly for testing
    import asyncio
    
    print("🚀 Running embed_memories flow...")
    result = asyncio.run(embed_memories_flow())
    print(f"\n📊 Result: {result}")


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Uses text-embedding-3-small model
# [x] Output dimension is 1536
# [x] Fetches where embedding IS NULL
# [x] Batch limit of 50 rows
# [x] Updates elliot_internal.memories
# [x] Logs to elliot_internal.prefect_logs
# [x] Async OpenAI client
# [x] Error handling and retries
# [x] Can run standalone or via Prefect
