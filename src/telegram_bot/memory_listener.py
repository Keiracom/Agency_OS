"""
memory_listener.py — searches agent_memories for relevant context on every message.

Runs as part of handle_message flow (not a separate service).
Uses embedding cosine similarity (pgvector) for semantic search.
Falls back to ILIKE text search if embedding generation fails.
"""
import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = (
    os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
)
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")

MAX_RELEVANCE_RESULTS: int = 5

# Stopwords — common words that match too broadly
STOPWORDS: set[str] = {
    "about", "after", "again", "because", "before", "being", "between",
    "could", "doing", "during", "every", "going", "having", "maybe",
    "other", "should", "something", "their", "there", "these", "thing",
    "things", "think", "those", "through", "where", "which", "while",
    "would", "already", "really", "still",
}

# Git commit message prefixes that match too broadly
GIT_STOPWORDS: set[str] = STOPWORDS | {
    "feat", "feature", "merge", "request", "branch",
    "docs", "chore", "refactor", "style", "build",
    "elliot", "aiden", "scout", "claude",
    "pull", "commit", "pushed", "merged",
}


async def _embed_text(text: str) -> list[float] | None:
    """Generate embedding via OpenAI text-embedding-3-small. Returns None on failure."""
    if not OPENAI_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": "text-embedding-3-small", "input": text[:8000]},
            )
            if resp.status_code == 200:
                return resp.json()["data"][0]["embedding"]
    except Exception as exc:
        logger.warning(f"[memory-listener] embedding failed: {exc}")
    return None


async def find_relevant_memories(
    message_text: str,
    n: int = MAX_RELEVANCE_RESULTS,
) -> list[dict]:
    """Search agent_memories for rows relevant to message_text.

    Primary: cosine similarity on embeddings (pgvector).
    Fallback: ILIKE text search if embedding fails.
    Returns list of dicts sorted by relevance.
    Silently returns [] on any error — never blocks the message flow.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    if not message_text or len(message_text) < 10:
        return []

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    # Try embedding-based semantic search first
    embedding = await _embed_text(message_text)
    if embedding is not None:
        results = await _search_by_embedding(embedding, n, headers)
        # If embedding call succeeded (even with zero matches), don't fall through
        # to text search — zero semantic matches means nothing is relevant
        if results:
            await _increment_access_counts(results, headers)
        return results  # may be empty — that's fine

    # Fallback: ILIKE text search only when embedding generation FAILED
    return await _search_by_text(message_text, n, headers)


async def _search_by_embedding(
    embedding: list[float], n: int, headers: dict
) -> list[dict]:
    """Cosine similarity search via Supabase RPC (pgvector)."""
    try:
        # Use Supabase RPC to call a similarity search function
        # Since we may not have an RPC function, use PostgREST with order by embedding
        # pgvector supports ordering by <=> (cosine distance) via PostgREST
        rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_agent_memories"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                rpc_url,
                headers=headers,
                json={
                    "query_embedding": embedding,
                    "match_count": n,
                    "match_threshold": 0.35,
                },
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning(f"[memory-listener] embedding search failed: {exc}")
    return []


async def _search_by_text(
    message_text: str, n: int, headers: dict
) -> list[dict]:
    """Fallback ILIKE text search with stopword filtering."""
    words = [w.strip(".,!?()[]\"'").lower() for w in message_text.split()]
    terms = [w for w in words if len(w) > 4 and w not in STOPWORDS][:5]
    if not terms:
        return []

    seen_ids: set[str] = set()
    results: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            for term in terms:
                url = (
                    f"{SUPABASE_URL}/rest/v1/agent_memories"
                    f"?content=ilike.*{term}*"
                    f"&state=eq.confirmed"
                    f"&select=id,source_type,content,tags,created_at,callsign,access_count"
                    f"&order=created_at.desc"
                    f"&limit={n}"
                )
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    for row in resp.json():
                        if row["id"] not in seen_ids:
                            seen_ids.add(row["id"])
                            results.append(row)

        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        results = results[:n]
        await _increment_access_counts(results, headers)
        return results

    except Exception as exc:
        logger.warning(f"[memory-listener] text search failed: {exc}")
        return []


async def _increment_access_counts(rows: list[dict], headers: dict) -> None:
    """Best-effort access_count bump — never raises."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            for row in rows:
                update_url = f"{SUPABASE_URL}/rest/v1/agent_memories?id=eq.{row['id']}"
                try:
                    await client.patch(
                        update_url,
                        headers={**headers, "Prefer": "return=minimal"},
                        json={"access_count": row.get("access_count", 0) + 1},
                    )
                except Exception:
                    pass
    except Exception:
        pass


async def find_matching_commits(message_text: str, n: int = 5) -> list[str]:
    """Search git commit messages for terms from the message. Local, no cost."""
    import asyncio

    words = [w.strip(".,!?()[]\"'").lower() for w in message_text.split()]
    terms = [w for w in words if len(w) > 4 and w not in GIT_STOPWORDS][:3]
    if not terms:
        return []

    results: list[str] = []
    seen: set[str] = set()
    repo_dir = os.environ.get("WORK_DIR_OVERRIDE", "/home/elliotbot/clawd/Agency_OS")

    for term in terms:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "log", "--all", "--oneline", f"--grep={term}", "-i",
                "--max-count=5",
                cwd=repo_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
            for line in stdout.decode().strip().splitlines():
                if line and line not in seen:
                    seen.add(line)
                    results.append(line)
        except Exception:
            pass

    return results[:n]


def format_memory_context(memories: list[dict], commits: list[str] | None = None) -> str:
    """Format retrieved memories + git commits into context blocks for injection."""
    if not memories and not commits:
        return ""

    lines = []
    if memories:
        lines.append("[MEMORY CONTEXT — relevant past knowledge:]")
        for m in memories:
            source = m.get("source_type", "?")
            content = (m.get("content") or "")[:500]
            date = (m.get("created_at") or "")[:10]
            sim = m.get("similarity", "?")
            sim_str = f" sim={sim:.2f}" if isinstance(sim, (int, float)) else ""
            lines.append(f"  [{source}] ({date}){sim_str} {content}")
        lines.append("[END MEMORY CONTEXT]")

    if commits:
        lines.append("[GIT CONTEXT — matching commits:]")
        for c in commits:
            lines.append(f"  {c}")
        lines.append("[END GIT CONTEXT]")

    return "\n".join(lines)
