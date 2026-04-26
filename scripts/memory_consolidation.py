"""
OC1 — Memory Consolidation (Dreaming pattern, OpenClaw research).

Sweeps the last N daily_log entries in elliot_internal.memories, scores
each on the five factors documented in the OpenClaw paper, then:
  - promotes high-scoring segments to type='core_fact' (durable knowledge)
  - prunes redundant entries (lower-scored copies of the same content)

Five-factor weighted score (weights per the OC1 spec):
  relevance      0.30   keyword density of durable-knowledge markers
                        (directive / rule / law / decision / fix / broke /
                         learned / always / never), score = min(1, hits/3)
  frequency      0.24   how many OTHER segments share ≥ 3-word overlap;
                        score = min(1, count/5)
  recency        0.15   newer = higher; (max_age_days − age) / max_age_days
  consolidation  0.10   how many times the SAME content_hash recurs;
                        score = min(1, dup_count/3)
  richness       0.06   log10(len(content)/100), clamped [0, 1]

Composite = Σ(weight × factor) / Σ(weights)   — normalised to [0, 1]

Promotion rule: composite ≥ --min-score AND type currently == 'daily_log'
                → INSERT a new core_fact row (NEVER mutates the original;
                the daily_log trail stays intact for audit).

Prune rule:     among rows sharing the same content_hash, keep the
                highest-scored one (after promotion); soft-delete the
                rest by setting deleted_at = NOW().

Usage:
    python3 scripts/memory_consolidation.py                         # dry-run preview
    python3 scripts/memory_consolidation.py --execute               # commit writes
    python3 scripts/memory_consolidation.py --lookback-days 7       # last week
    python3 scripts/memory_consolidation.py --min-score 0.7         # stricter

Exit codes: 0 OK · 3 DB unavailable.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, REPO_ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncpg  # noqa: E402

from src.config.settings import settings  # noqa: E402

# ── Scoring weights (OC1 spec) ─────────────────────────────────────────────
WEIGHTS = {
    "relevance":     0.30,
    "frequency":     0.24,
    "recency":       0.15,
    "consolidation": 0.10,
    "richness":      0.06,
}
WEIGHT_SUM = sum(WEIGHTS.values())  # 0.85 — composite is normalised by this

DURABLE_MARKERS = (
    r"\bdirective\b", r"\brule\b", r"\blaw\b", r"\bdecision\b",
    r"\bfix(?:ed)?\b", r"\bbroke\b", r"\blearned\b",
    r"\balways\b", r"\bnever\b",
)
_MARKER_RE = re.compile("|".join(DURABLE_MARKERS), re.IGNORECASE)
_WORD_RE = re.compile(r"\b[a-z][a-z0-9_-]{2,}\b")


@dataclass
class Memory:
    id: str
    content: str
    content_hash: str | None
    type: str
    created_at: datetime
    metadata: dict = field(default_factory=dict)
    # populated during scoring
    factors: dict[str, float] = field(default_factory=dict)
    composite: float = 0.0


# ── Factor calculators ─────────────────────────────────────────────────────

def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def relevance_score(m: Memory) -> float:
    hits = len(_MARKER_RE.findall(m.content or ""))
    return min(1.0, hits / 3.0)


def frequency_score(m: Memory, all_token_sets: list[set[str]]) -> float:
    """Count of OTHER memories sharing ≥ 3 distinct content tokens."""
    me = _tokens(m.content)
    if not me:
        return 0.0
    overlap_count = sum(
        1 for other in all_token_sets if other is not me and len(me & other) >= 3
    )
    return min(1.0, overlap_count / 5.0)


def recency_score(m: Memory, max_age_days: float) -> float:
    if max_age_days <= 0:
        return 1.0
    age = (datetime.now(UTC) - m.created_at).total_seconds() / 86400.0
    return max(0.0, min(1.0, (max_age_days - age) / max_age_days))


def consolidation_score(m: Memory, hash_counts: Counter) -> float:
    if not m.content_hash:
        return 0.0
    return min(1.0, hash_counts[m.content_hash] / 3.0)


def richness_score(m: Memory) -> float:
    n = len(m.content or "")
    if n <= 0:
        return 0.0
    val = math.log10(n / 100.0) if n >= 100 else 0.0
    return max(0.0, min(1.0, val))


def score(memories: list[Memory]) -> None:
    """Mutates each memory.factors + memory.composite in place."""
    if not memories:
        return
    ages = [(datetime.now(UTC) - m.created_at).total_seconds() / 86400.0 for m in memories]
    max_age = max(ages) if ages else 1.0
    token_sets = [_tokens(m.content) for m in memories]
    hash_counts: Counter = Counter(m.content_hash for m in memories if m.content_hash)

    for m, toks in zip(memories, token_sets, strict=False):
        m.factors = {
            "relevance":     relevance_score(m),
            "frequency":     frequency_score_with_tokens(m, toks, token_sets),
            "recency":       recency_score(m, max_age),
            "consolidation": consolidation_score(m, hash_counts),
            "richness":      richness_score(m),
        }
        weighted = sum(WEIGHTS[k] * v for k, v in m.factors.items())
        m.composite = round(weighted / WEIGHT_SUM, 4) if WEIGHT_SUM else 0.0


def frequency_score_with_tokens(
    m: Memory, my_tokens: set[str], all_tokens: list[set[str]],
) -> float:
    if not my_tokens:
        return 0.0
    overlap = sum(
        1 for other in all_tokens if other is not my_tokens and len(my_tokens & other) >= 3
    )
    return min(1.0, overlap / 5.0)


# ── DB I/O ─────────────────────────────────────────────────────────────────

async def fetch_recent(conn, lookback_days: int) -> list[Memory]:
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    rows = await conn.fetch(
        """
        SELECT id, content, content_hash, type, created_at, metadata
        FROM elliot_internal.memories
        WHERE deleted_at IS NULL
          AND type = 'daily_log'
          AND created_at >= $1
        ORDER BY created_at DESC
        """,
        cutoff,
    )
    return [
        Memory(
            id=str(r["id"]),
            content=r["content"] or "",
            content_hash=r["content_hash"],
            type=r["type"],
            created_at=r["created_at"],
            metadata=r["metadata"] or {},
        )
        for r in rows
    ]


async def promote_to_core_fact(conn, m: Memory, *, dry_run: bool) -> bool:
    """INSERT a new core_fact row mirroring the daily_log content. Returns True
    if an insert was made (or would be made in dry-run)."""
    if dry_run:
        return True
    metadata = dict(m.metadata or {})
    metadata.update({
        "consolidated_from": m.id,
        "consolidation_run": datetime.now(UTC).isoformat(),
        "composite_score":   m.composite,
        "factors":           m.factors,
    })
    new_hash = hashlib.sha256(m.content.encode()).hexdigest()
    await conn.execute(
        """
        INSERT INTO elliot_internal.memories
          (id, content, content_hash, type, metadata, created_at, updated_at)
        VALUES (gen_random_uuid(), $1, $2, 'core_fact', $3::jsonb, NOW(), NOW())
        """,
        m.content, new_hash,
        __import__("json").dumps(metadata),
    )
    return True


async def soft_delete(conn, memory_id: str, *, dry_run: bool) -> bool:
    if dry_run:
        return True
    await conn.execute(
        """
        UPDATE elliot_internal.memories
        SET deleted_at = NOW(), updated_at = NOW()
        WHERE id = $1 AND deleted_at IS NULL
        """,
        memory_id,
    )
    return True


# ── Pipeline ───────────────────────────────────────────────────────────────

async def consolidate(
    conn, *, lookback_days: int, min_score: float, dry_run: bool,
) -> dict:
    memories = await fetch_recent(conn, lookback_days)
    score(memories)

    promoted: list[Memory] = []
    for m in memories:
        if m.composite >= min_score:
            ok = await promote_to_core_fact(conn, m, dry_run=dry_run)
            if ok:
                promoted.append(m)

    # Pruning — among rows sharing the same content_hash, keep the highest
    # composite score; soft-delete the rest. Operates over the FULL list,
    # not just promoted ones, so duplicate noisy entries collapse.
    pruned = 0
    by_hash: dict[str, list[Memory]] = {}
    for m in memories:
        if not m.content_hash:
            continue
        by_hash.setdefault(m.content_hash, []).append(m)
    for group in by_hash.values():
        if len(group) <= 1:
            continue
        group_sorted = sorted(group, key=lambda x: x.composite, reverse=True)
        for redundant in group_sorted[1:]:
            await soft_delete(conn, redundant.id, dry_run=dry_run)
            pruned += 1

    return {
        "scanned":      len(memories),
        "promoted":     len(promoted),
        "pruned":       pruned,
        "lookback_days": lookback_days,
        "min_score":    min_score,
        "top_promotions": [
            {
                "id":        m.id,
                "composite": m.composite,
                "preview":   (m.content or "")[:120].replace("\n", " "),
            }
            for m in sorted(promoted, key=lambda x: x.composite, reverse=True)[:10]
        ],
    }


# ── CLI ────────────────────────────────────────────────────────────────────

def render_human(result: dict, *, dry_run: bool) -> str:
    lines = [
        "=" * 64,
        f"Memory Consolidation — {'DRY-RUN' if dry_run else 'EXECUTE'}",
        "=" * 64,
        f"  scanned (daily_log, last {result['lookback_days']}d):  "
        f"{result['scanned']:,}",
        f"  promoted (composite ≥ {result['min_score']}):     {result['promoted']:,}",
        f"  pruned (duplicate content_hash):                {result['pruned']:,}",
    ]
    if result["top_promotions"]:
        lines.append("")
        lines.append("  Top promotions:")
        for p in result["top_promotions"]:
            lines.append(f"    {p['composite']:>5.3f}  {p['id'][:8]}  {p['preview']}")
    return "\n".join(lines)


async def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OC1 Memory Consolidation (Dreaming).")
    ap.add_argument("--lookback-days", type=int, default=30,
                    help="Window of daily_logs to score (default 30).")
    ap.add_argument("--min-score", type=float, default=0.6,
                    help="Composite-score threshold for promotion (default 0.6).")
    ap.add_argument("--execute", action="store_true",
                    help="Apply writes. Default is dry-run.")
    args = ap.parse_args(argv)
    dry_run = not args.execute

    try:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
    except Exception as exc:  # noqa: BLE001
        print(f"DB unavailable: {exc}", file=sys.stderr)
        return 3

    try:
        result = await consolidate(
            conn,
            lookback_days=args.lookback_days,
            min_score=args.min_score,
            dry_run=dry_run,
        )
    finally:
        await conn.close()

    print(render_human(result, dry_run=dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
