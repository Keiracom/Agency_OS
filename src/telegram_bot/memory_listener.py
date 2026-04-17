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
            # Post-filter: require at least one non-stopword token overlap between
            # query and row content. Embedding catches semantic vibes (produces
            # false positives on our pipeline-heavy corpus, e.g. 'check status
            # crashing' matching ContactOut schema debugging at 0.38-0.42 cosine).
            # Requiring an actual shared subject-word prunes those while keeping
            # genuinely on-topic rows.
            results = _filter_by_word_overlap(results, message_text)
            results = _apply_trust_weighting(results)
            await _increment_access_counts(results, headers)
        return results  # may be empty — that's fine

    # Fallback: ILIKE text search only when embedding generation FAILED
    return await _search_by_text(message_text, n, headers)


def _filter_by_word_overlap(results: list[dict], query_text: str) -> list[dict]:
    """Require each row to share at least one >4-char non-stopword token with
    the query. Prunes embedding false-positives on topically-unrelated content.

    Uses GIT_STOPWORDS (superset of STOPWORDS + callsigns + commit-msg verbs)
    because our callsigns ('elliot', 'aiden', 'dave', 'scout', 'claude') appear
    in nearly every memory row — if they're allowed as query terms they'll
    match everything and the filter does nothing."""
    query_words = {
        w.strip(".,!?()[]\"'").lower()
        for w in query_text.split()
        if len(w.strip(".,!?()[]\"'")) > 4
    }
    query_words -= GIT_STOPWORDS
    if not query_words:
        return results  # no content words to filter on — keep embedding result as-is
    filtered: list[dict] = []
    for row in results:
        content = (row.get("content") or "").lower()
        if any(qw in content for qw in query_words):
            filtered.append(row)
    return filtered


# Source-type trust weights — multiply similarity to reorder results.
# Higher weight = preferred at same similarity band.
# Addresses diagnostic FM-3 (no salience/trust weighting).
TRUST_WEIGHTS: dict[str, float] = {
    "dave_confirmed": 1.30,
    "verified_fact": 1.20,
    "test_result":   1.10,
    "reasoning":     1.05,
    "decision":      1.00,  # baseline
    "pattern":       0.95,
    "research":      0.90,
    "skill":         0.90,
    "daily_log":     0.85,
}

# State weights — tentative rows (auto-captured, unverified) get discounted so
# they only surface when similarity is strong enough to overcome the discount.
# Surfacing-despite-discount IS the promotion signal (access_count ticks up →
# tentative eventually flips to confirmed at PROMOTION_ACCESS_THRESHOLD).
STATE_WEIGHTS: dict[str, float] = {
    "confirmed":  1.00,
    "tentative":  0.50,  # heavy discount — bulk-extracted tentative rows only surface on very strong match
    # superseded / contradicted / archived excluded at the RPC layer
}


def _apply_trust_weighting(results: list[dict]) -> list[dict]:
    """Re-rank results by (similarity * source_trust_weight * state_weight).
    Preserves original similarity in the row for display — adds sort-only effect."""
    for r in results:
        base_sim = r.get("similarity", 0.0) or 0.0
        source_w = TRUST_WEIGHTS.get(r.get("source_type", ""), 1.0)
        state_w = STATE_WEIGHTS.get(r.get("state", "confirmed"), 1.0)
        r["_weighted_similarity"] = base_sim * source_w * state_w
    results.sort(key=lambda r: r.get("_weighted_similarity", 0.0), reverse=True)
    return results


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


# Promotion threshold — tentative rows promote to confirmed after this many retrievals.
# Addresses diagnostic FM-2: everything starts tentative (ingest gate); retrieval
# reinforcement is the natural promotion signal (memory that's actually useful gets
# surfaced, which means it's true/relevant enough to confirm).
PROMOTION_ACCESS_THRESHOLD = 3


async def _increment_access_counts(rows: list[dict], headers: dict) -> None:
    """Best-effort access_count bump + tentative→confirmed promotion. Never raises."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            for row in rows:
                update_url = f"{SUPABASE_URL}/rest/v1/agent_memories?id=eq.{row['id']}"
                new_count = row.get("access_count", 0) + 1
                # Promote tentative → confirmed once the row has been retrieved
                # enough times to demonstrate real signal value. Doesn't demote
                # anything — only upgrades.
                payload: dict = {"access_count": new_count}
                current_state = row.get("state", "tentative")
                if current_state == "tentative" and new_count >= PROMOTION_ACCESS_THRESHOLD:
                    payload["state"] = "confirmed"
                    logger.info(
                        f"[memory-listener] promoting id={row['id']} tentative→confirmed "
                        f"(access_count={new_count})"
                    )
                try:
                    await client.patch(
                        update_url,
                        headers={**headers, "Prefer": "return=minimal"},
                        json=payload,
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


# ---------------------------------------------------------------------------
# Write side — auto-capture from conversations (bidirectional)
# ---------------------------------------------------------------------------

# Rule-based heuristics for source_type classification (no LLM needed)
_DECISION_SIGNALS = {"decided", "decision", "chose", "approved", "ratified", "agreed", "confirmed", "rejected", "moving to", "switching to"}
_DIRECTIVE_SIGNALS = {"directive", "scope:", "success criteria:", "objective:"}
_BLOCKER_SIGNALS = {"blocked", "blocker", "waiting on", "can't proceed", "stuck"}
_REMEMBER_SIGNALS = {"remember", "save this", "note this", "important:"}


def _classify_source_type(text: str) -> str:
    """Rule-based classification — no LLM call. ~80% accuracy on structured messages."""
    lower = text.lower()
    if any(s in lower for s in _DIRECTIVE_SIGNALS):
        return "decision"
    if any(s in lower for s in _REMEMBER_SIGNALS):
        return "dave_confirmed"
    if any(s in lower for s in _BLOCKER_SIGNALS):
        return "reasoning"
    if any(s in lower for s in _DECISION_SIGNALS):
        return "decision"
    return "daily_log"


async def auto_capture_message(
    message_text: str,
    sender: str,
    chat_id: int,
    callsign: str,
) -> None:
    """Auto-capture a Dave message as tentative memory. Best-effort, never blocks.

    - Only captures Dave messages (not peer bots, not self)
    - Skips commands (/tag, /save, /recall, etc.)
    - Skips very short messages (< 20 chars)
    - Classifies via rule-based heuristics (no LLM cost)
    - Generates embedding at write time (immediate searchability)
    - state='tentative' — doesn't surface in default retrieval until promoted
    """
    if sender not in ("dave", "peer"):
        return
    if not message_text or len(message_text) < 20:
        return
    if message_text.strip().startswith("/"):
        return

    source_type = _classify_source_type(message_text)

    # Generate embedding for immediate semantic searchability
    embedding = await _embed_text(message_text)

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    import uuid as _uuid
    from datetime import datetime as _dt, timezone as _tz

    payload = {
        "callsign": callsign,
        "source_type": source_type,
        "content": message_text[:5000],
        "typed_metadata": json.dumps({
            "source": "auto_capture",
            "chat_id": str(chat_id),
            "captured_by": callsign,
        }),
        "tags": [source_type, "auto_capture"],
        "state": "tentative",
        "trust": "dave_observed",
        "confidence": 0.5,
        "valid_from": _dt.now(_tz.utc).isoformat(),
    }

    if embedding:
        payload["embedding"] = embedding

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/agent_memories",
                headers=headers,
                json=payload,
            )
            if resp.status_code in (200, 201):
                logger.info(f"[auto-capture] saved {source_type} ({len(message_text)} chars)")
            else:
                logger.warning(f"[auto-capture] write failed: {resp.status_code}")
    except Exception as exc:
        logger.warning(f"[auto-capture] error: {exc}")


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
