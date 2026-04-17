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

    # Strip callsign prefixes before embedding — [AIDEN]/[ELLIOT] tags add noise to cosine
    import re
    clean_text = re.sub(r'^\[(?:ELLIOT|AIDEN|SCOUT|DAVE)\]\s*', '', message_text.strip())
    clean_text = re.sub(r'^\[(?:ELLIOT|AIDEN|SCOUT|DAVE)\]\s*', '', clean_text)  # double prefix

    # Hybrid search: BM25 keyword + semantic embedding via Reciprocal Rank Fusion
    # Documents ranked high in BOTH keyword AND semantic lists bubble up.
    # Fixes same-domain corpus noise where embeddings alone match everything.
    embedding = await _embed_text(clean_text or message_text)
    if embedding is not None:
        raw_results = await _hybrid_search(clean_text or message_text, embedding, n, headers)
        if raw_results:
            results = _apply_trust_weighting(raw_results)
            await _increment_access_counts(results, headers)
        else:
            results = []
        _log_retrieval_event(message_text, raw_results, results, source="hybrid")
        return results

    # Fallback: ILIKE text search only when embedding generation FAILED
    fallback = await _search_by_text(message_text, n, headers)
    _log_retrieval_event(message_text, fallback, fallback, source="text_fallback")
    return fallback


# ---------------------------------------------------------------------------
# Telemetry — log every retrieval to a JSONL file so we can review listener
# quality offline instead of tuning blind on one-message observations.
# ---------------------------------------------------------------------------

import datetime as _dt
import json as _json

TELEMETRY_LOG = "/home/elliotbot/clawd/logs/listener-telemetry.jsonl"


def _log_retrieval_event(
    query_text: str,
    raw_results: list[dict],
    final_results: list[dict],
    source: str,
) -> None:
    """Append one retrieval event to the telemetry log. Best-effort, never raises."""
    try:
        callsign = os.environ.get("CALLSIGN", "unknown")
        raw_ids = [r.get("id") for r in (raw_results or [])]
        raw_sims = [
            round(float(r.get("similarity", 0) or 0), 4) for r in (raw_results or [])
        ]
        final_ids = [r.get("id") for r in (final_results or [])]
        event = {
            "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "callsign": callsign,
            "source": source,  # "embedding" | "text_fallback"
            "query_preview": (query_text or "")[:160],
            "query_len": len(query_text or ""),
            "raw_count": len(raw_ids),
            "raw_ids": raw_ids,
            "raw_similarities": raw_sims,
            "final_count": len(final_ids),
            "final_ids": final_ids,
            "dropped_by_overlap_filter": len(raw_ids) - len(final_ids),
        }
        with open(TELEMETRY_LOG, "a", encoding="utf-8") as fh:
            fh.write(_json.dumps(event) + "\n")
    except Exception as exc:
        logger.warning(f"[memory-listener] telemetry log failed: {exc}")


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
    # Require at least 2 matching words (or 1 if query has fewer than 3 content words)
    min_overlap = 2 if len(query_words) >= 3 else 1
    filtered: list[dict] = []
    for row in results:
        content = (row.get("content") or "").lower()
        overlap_count = sum(1 for qw in query_words if qw in content)
        if overlap_count >= min_overlap:
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


# Time decay constants — exponential decay based on row age.
# Recent memories rank higher than old ones at same similarity.
# λ values per source_type (higher = faster decay):
TIME_DECAY_LAMBDA: dict[str, float] = {
    "daily_log":     0.05,   # 14-day half-life — ephemeral
    "reasoning":     0.03,   # 23-day half-life
    "test_result":   0.02,   # 35-day half-life
    "research":      0.02,   # 35-day half-life
    "decision":      0.01,   # 69-day half-life — durable
    "pattern":       0.01,   # 69-day half-life — durable
    "skill":         0.005,  # 139-day half-life — very durable
    "dave_confirmed": 0.003, # 231-day half-life — near-permanent
    "verified_fact": 0.003,  # 231-day half-life — near-permanent
}

import math


def _apply_trust_weighting(results: list[dict]) -> list[dict]:
    """Re-rank by (similarity × source_trust × state_weight × time_decay).
    Preserves original similarity for display — adds sort-only effect.

    Time decay: e^(-λ × days_old). Old debugging notes get buried;
    recent context rises. λ varies by source_type — daily_logs decay
    fast, dave_confirmed decays very slowly."""
    now = _dt.datetime.now(_dt.timezone.utc)
    for r in results:
        base_sim = r.get("similarity", 0.0) or 0.0
        source_w = TRUST_WEIGHTS.get(r.get("source_type", ""), 1.0)
        state_w = STATE_WEIGHTS.get(r.get("state", "confirmed"), 1.0)

        # Time decay
        created = r.get("created_at", "")
        try:
            if isinstance(created, str) and created:
                row_dt = _dt.datetime.fromisoformat(created.replace("Z", "+00:00"))
                days_old = max((now - row_dt).total_seconds() / 86400, 0)
            else:
                days_old = 0
        except Exception:
            days_old = 0
        lam = TIME_DECAY_LAMBDA.get(r.get("source_type", ""), 0.01)
        decay = math.exp(-lam * days_old)

        r["_weighted_similarity"] = base_sim * source_w * state_w * decay
    results.sort(key=lambda r: r.get("_weighted_similarity", 0.0), reverse=True)
    return results


async def _hybrid_search(
    query_text: str, embedding: list[float], n: int, headers: dict
) -> list[dict]:
    """Hybrid BM25 + semantic search via Supabase RPC (Reciprocal Rank Fusion)."""
    try:
        rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/hybrid_search_agent_memories"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                rpc_url,
                headers=headers,
                json={
                    "query_text": query_text,
                    "query_embedding": embedding,
                    "match_count": n,
                    "match_threshold": 0.35,
                },
            )
            if resp.status_code == 200:
                return resp.json()
            # Fallback to embedding-only if hybrid RPC doesn't exist yet
            logger.warning(f"[memory-listener] hybrid search returned {resp.status_code}, falling back to embedding-only")
    except Exception as exc:
        logger.warning(f"[memory-listener] hybrid search failed: {exc}")

    # Fallback to embedding-only search
    return await _search_by_embedding(embedding, n, headers)


async def _search_by_embedding(
    embedding: list[float], n: int, headers: dict
) -> list[dict]:
    """Fallback: cosine similarity only via Supabase RPC (pgvector)."""
    try:
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
    """Search git commit messages — AND match (all terms must appear). Local, no cost."""
    import asyncio

    words = [w.strip(".,!?()[]\"'").lower() for w in message_text.split()]
    terms = [w for w in words if len(w) > 4 and w not in GIT_STOPWORDS][:3]
    if not terms:
        return []

    repo_dir = os.environ.get("WORK_DIR_OVERRIDE", "/home/elliotbot/clawd/Agency_OS")

    # AND-match: search for first term, then filter results that contain ALL other terms
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "log", "--all", "--oneline", f"--grep={terms[0]}", "-i",
            "--max-count=50",
            cwd=repo_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
        candidates = stdout.decode().strip().splitlines()

        # Filter: commit must contain ALL query terms (AND, not OR)
        results = []
        for line in candidates:
            lower_line = line.lower()
            if all(t in lower_line for t in terms):
                results.append(line)

        # If AND-match is too strict (0 results), fall back to first term only but cap at 3
        if not results and candidates:
            results = candidates[:3]

        return results[:n]
    except Exception:
        return []

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
