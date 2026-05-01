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

MAX_RELEVANCE_RESULTS: int = int(os.environ.get("LISTENER_TOP_K", "3"))

# Similarity threshold for semantic retrieval.
# Raised 0.35 → 0.50 (2026-04-24) to suppress low-relevance matches.
# Raised 0.50 → 0.55 (2026-05-01) after Dave flagged ~50K tokens/session of
# memory-brief noise where sim 0.50–0.55 results were topically off (Pipeline F
# audit memories, ContactOut credit model, etc. injected into governance threads).
# Override with LISTENER_SIM_THRESHOLD env var if tuning further.
SIM_THRESHOLD: float = float(os.environ.get("LISTENER_SIM_THRESHOLD", "0.55"))

# Context attachment toggles. Git + repo context averaged ~200 tokens each per
# inbound message with low cited-rate. Default off 2026-04-24; re-enable via env
# vars if needed for specific use cases.
ENABLE_GIT_CONTEXT: bool = os.environ.get("LISTENER_ENABLE_GIT_CONTEXT", "false").lower() == "true"
ENABLE_REPO_CONTEXT: bool = os.environ.get("LISTENER_ENABLE_REPO_CONTEXT", "false").lower() == "true"

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


async def _expand_query(query_text: str) -> list[str]:
    """Generate 3 alternative phrasings via GPT-4o-mini for MultiQueryRetriever.

    Returns [original_query, variation_1, variation_2, variation_3].
    Best-effort: returns [query_text] on any failure — caller falls back to original.
    Adds ~500ms latency (one GPT-4o-mini call). Temperature 0.3 for mild diversity.
    """
    if not OPENAI_API_KEY:
        return [query_text]
    prompt = (
        f"Rewrite this search query 3 ways to maximize retrieval from a knowledge base: '{query_text}'. "
        "Rules: "
        "(1) PARENT: ask about the broader product/system/business — not just the feature mentioned. "
        "(2) SIBLING: ask about related or adjacent concepts. "
        "(3) INVERSE: flip the framing (e.g. 'what remains' → 'what exists'). "
        "CRITICAL: Output SHORT keyword phrases (3-6 words), NOT full sentences. "
        "Short phrases retrieve better than long sentences. "
        'Return JSON: {"variations": ["short phrase 1", "short phrase 2", "short phrase 3"]}'
    )
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "temperature": 0.3,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                variations = parsed.get("variations", [])
                try:
                    from src.telegram_bot.openai_cost_logger import log_openai_call
                    usage = data.get("usage", {})
                    log_openai_call(
                        callsign=os.environ.get("CALLSIGN", "unknown"),
                        use_case="query_expansion",
                        model="gpt-4o-mini",
                        input_tokens=usage.get("prompt_tokens", 0),
                        output_tokens=usage.get("completion_tokens", 0),
                    )
                except Exception:
                    pass
                if isinstance(variations, list) and variations:
                    return [query_text] + [v for v in variations if isinstance(v, str)][:3]
    except Exception as exc:
        logger.warning(f"[memory-listener] query expansion failed: {exc}")
    return [query_text]


def _merge_variation_results(variation_results: list[list[dict]]) -> list[dict]:
    """Merge results from multiple query variations.

    Dedup by row ID. Rows found by 2+ variations get similarity * 1.2.
    Rows found by 3+ variations get similarity * 1.5.
    Returns merged list sorted by (boosted) similarity descending.
    """
    hit_counts: dict[str, int] = {}
    rows_by_id: dict[str, dict] = {}

    for result_set in variation_results:
        seen_in_this_variation: set[str] = set()
        for row in result_set:
            row_id = row.get("id")
            if not row_id:
                continue
            if row_id not in seen_in_this_variation:
                seen_in_this_variation.add(row_id)
                hit_counts[row_id] = hit_counts.get(row_id, 0) + 1
                if row_id not in rows_by_id:
                    rows_by_id[row_id] = dict(row)

    merged: list[dict] = []
    for row_id, row in rows_by_id.items():
        count = hit_counts.get(row_id, 1)
        if count >= 3:
            boost = 1.5
        elif count >= 2:
            boost = 1.2
        else:
            boost = 1.0
        row = dict(row)
        base_sim = float(row.get("similarity", 0.0) or 0.0)
        row["similarity"] = base_sim * boost
        row["_variation_hits"] = count
        merged.append(row)

    merged.sort(key=lambda r: r.get("similarity", 0.0), reverse=True)
    return merged


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
                emb_data = resp.json()
                try:
                    from src.telegram_bot.openai_cost_logger import log_openai_call
                    usage = emb_data.get("usage", {})
                    log_openai_call(
                        callsign=os.environ.get("CALLSIGN", "unknown"),
                        use_case="embedding",
                        model="text-embedding-3-small",
                        input_tokens=usage.get("total_tokens", 0),
                    )
                except Exception:
                    pass
                return emb_data["data"][0]["embedding"]
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
    import asyncio as _asyncio
    clean_text = re.sub(r'^\[(?:ELLIOT|AIDEN|SCOUT|DAVE)\]\s*', '', message_text.strip())
    clean_text = re.sub(r'^\[(?:ELLIOT|AIDEN|SCOUT|DAVE)\]\s*', '', clean_text)  # double prefix
    query = clean_text or message_text

    # MultiQueryRetriever: expand query into variations, search each in parallel
    variations = await _expand_query(query)
    logger.info(f"[memory-listener] query expanded to {len(variations)} variations")

    # Embed all variations in parallel
    embeddings: list[list[float] | None] = await _asyncio.gather(
        *[_embed_text(v) for v in variations]
    )

    # Only proceed with variations that have valid embeddings
    valid_pairs = [(v, emb) for v, emb in zip(variations, embeddings) if emb is not None]

    if valid_pairs:
        # Search hybrid for every variation in parallel (20 candidates each)
        variation_results: list[list[dict]] = await _asyncio.gather(
            *[_hybrid_search(v, emb, 20, headers) for v, emb in valid_pairs]
        )

        # Merge: dedup + boost rows found by multiple variations
        raw_results = _merge_variation_results(list(variation_results))

        if raw_results:
            results = _apply_trust_weighting(raw_results)
            # L2: LLM discernment — pick best N and summarise
            from src.telegram_bot.listener_discernment import discern_and_summarise
            discerned = await discern_and_summarise(query, results)
            if discerned is not None and discerned.get("selected_ids"):
                # Map discernment's selected_ids → actual row dicts for callers
                rows_by_id = {r.get("id"): r for r in results}
                selected_rows = [rows_by_id[sid] for sid in discerned["selected_ids"] if sid in rows_by_id]
                await _increment_access_counts(selected_rows, headers)
                source_tag = "multiquery+hybrid+discern" if len(valid_pairs) > 1 else "hybrid+discern"
                _log_retrieval_event(message_text, raw_results, selected_rows, source=source_tag)
                return {
                    "summary": discerned.get("brief", ""),
                    "selected_rows": selected_rows,
                    "citations": discerned.get("citations", {}),
                    "provenance_ok": discerned.get("provenance_ok", True),
                }
            # Fallback if discernment fails: return top-N from trust weighting
            results = results[:n]
            await _increment_access_counts(results, headers)
        else:
            results = []
        source_tag = "multiquery+hybrid" if len(valid_pairs) > 1 else "hybrid"
        _log_retrieval_event(message_text, raw_results, results, source=source_tag)
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
        # Capture content previews of final rows — needed for retrospective
        # relevance scoring (Dave pushback 2026-04-17: 'stable enough' was
        # a hedge because we never measured utility of surfaced rows).
        # Previews let us score events offline against the query_preview.
        final_previews = [
            {
                "id": r.get("id"),
                "source_type": r.get("source_type"),
                "state": r.get("state"),
                "content_100": (r.get("content") or "")[:100],
            }
            for r in (final_results or [])
        ]
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
            "final_previews": final_previews,  # for offline relevance scoring
            "dropped_by_overlap_filter": len(raw_ids) - len(final_ids),
            "relevance_ratings": None,  # populated later by scoring pass (null = unscored)
        }
        with open(TELEMETRY_LOG, "a", encoding="utf-8") as fh:
            fh.write(_json.dumps(event) + "\n")
    except Exception as exc:
        logger.warning(f"[memory-listener] telemetry log failed: {exc}")


# _filter_by_word_overlap REMOVED — L2 discernment replaces it as the sole
# intelligent filter. Word-overlap was a cheap heuristic that pre-empted L2
# on typo/synonym queries (e.g. 'repi' killed all 5 embedding matches).
# L2 handles both precision AND typo tolerance. Removed per architectural
# decision during listener tuning session.


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
                    "match_threshold": SIM_THRESHOLD,
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
                    "match_threshold": SIM_THRESHOLD,
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
                    payload["promoted_from_id"] = row["id"]
                    current_meta = row.get("typed_metadata") or {}
                    payload["typed_metadata"] = {
                        **current_meta,
                        "promoted_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                        "promoted_from_state": "tentative",
                    }
                    logger.info(
                        f"[memory-listener] PROMOTION FIRED id={row['id']} tentative→confirmed "
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


async def recall_via_mem0(
    query: str,
    callsign: str,
    limit: int = 5,
) -> list[dict]:
    """Retrieve memories from Mem0 for cross-session relationship-aware recall.

    Controlled by MEMORY_RECALL_BACKEND env var (mem0|supabase|hybrid).
    Hybrid: queries both stores, merges by score, dedupes by content prefix.
    Returns [] on any error — never blocks the message flow.
    """
    backend = os.environ.get("MEMORY_RECALL_BACKEND", "supabase").lower()
    if backend == "supabase":
        return []

    mem0_results: list[dict] = []
    try:
        from src.governance.mem0_adapter import Mem0Adapter
        adapter = Mem0Adapter()
        raw = adapter.search(query, limit=limit, callsign=callsign)
        mem0_results = [
            {
                "id": r.get("id", ""),
                "content": r.get("memory", r.get("content", "")),
                "source_type": (r.get("metadata") or {}).get("source_type", "research"),
                "similarity": r.get("score", 0.0),
                "_source": "mem0",
            }
            for r in raw
        ]
    except Exception as exc:
        logger.warning(f"[memory-listener] Mem0 recall failed: {exc}")

    if backend == "mem0":
        return mem0_results

    # Hybrid: merge mem0 results with Supabase find_relevant_memories
    supabase_raw = await find_relevant_memories(query, n=limit)
    supabase_rows: list[dict] = []
    if isinstance(supabase_raw, dict):
        supabase_rows = supabase_raw.get("selected_rows", [])
    elif isinstance(supabase_raw, list):
        supabase_rows = supabase_raw

    seen_prefixes: set[str] = set()
    merged: list[dict] = []
    for row in mem0_results + supabase_rows:
        prefix = (row.get("content") or "")[:80]
        if prefix not in seen_prefixes:
            seen_prefixes.add(prefix)
            merged.append(row)

    merged.sort(key=lambda r: float(r.get("similarity") or 0.0), reverse=True)
    return merged[:limit]


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


async def find_repo_mentions(message_text: str, n: int = 5) -> list[str]:
    """Search repo file contents for terms (git grep). Catches codebase facts
    invisible to agent_memories — deploy names, constants, file paths, config."""
    import asyncio

    words = [w.strip(".,!?()[]\"'").lower() for w in message_text.split()]
    terms = [w for w in words if len(w) > 2 and w not in GIT_STOPWORDS][:3]
    if not terms:
        return []

    repo_dir = os.environ.get("WORK_DIR_OVERRIDE", "/home/elliotbot/clawd/Agency_OS")
    results: list[str] = []
    seen: set[str] = set()

    for term in terms:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "grep", "-i", "-l", term,
                cwd=repo_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
            files = stdout.decode().strip().splitlines()
            for f in files[:3]:
                if f and f not in seen and not f.startswith("node_modules") and not f.startswith("frontend/node_modules"):
                    seen.add(f)
                    # Get matching line for context
                    try:
                        proc2 = await asyncio.create_subprocess_exec(
                            "git", "grep", "-i", "-m", "1", term, "--", f,
                            cwd=repo_dir,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.DEVNULL,
                        )
                        stdout2, _ = await asyncio.wait_for(proc2.communicate(), timeout=2)
                        line = stdout2.decode().strip()[:120]
                        results.append(line)
                    except Exception:
                        results.append(f)
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


def format_memory_context(memories, commits: list[str] | None = None, repo_hits: list[str] | None = None) -> str:
    """Format retrieved memories + git commits into context blocks for injection.

    memories can be:
    - list[dict]: raw memory rows (L1 mode)
    - dict with 'summary' + 'selected_rows': L2 discernment result
    """
    # Handle L2 discernment result
    if isinstance(memories, dict) and "summary" in memories:
        summary = memories.get("summary", "")
        rows = memories.get("selected_rows", [])
        if not summary and not rows:
            return ""
        lines = []
        if summary:
            lines.append(f"[MEMORY BRIEF — AI-synthesised from {len(rows)} relevant memories:]")
            lines.append(f"  {summary}")
            lines.append("[END MEMORY BRIEF]")
        if commits and ENABLE_GIT_CONTEXT:
            lines.append("[GIT CONTEXT — matching commits:]")
            for c in commits:
                lines.append(f"  {c}")
            lines.append("[END GIT CONTEXT]")
        return "\n".join(lines)

    # Handle L1 raw rows (list of dicts)
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

    if commits and ENABLE_GIT_CONTEXT:
        lines.append("[GIT CONTEXT — matching commits:]")
        for c in commits:
            lines.append(f"  {c}")
        lines.append("[END GIT CONTEXT]")

    if repo_hits and ENABLE_REPO_CONTEXT:
        lines.append("[REPO CONTEXT — matching code/docs:]")
        for r in repo_hits:
            lines.append(f"  {r}")
        lines.append("[END REPO CONTEXT]")

    return "\n".join(lines)
