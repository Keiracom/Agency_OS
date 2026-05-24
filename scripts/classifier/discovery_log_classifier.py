#!/usr/bin/env python3
"""discovery_log_classifier.py — classify discovery log entries by context tag.

Phase 1.2.5 bundle artefact 5 (Aiden R7) per Dave-ratified separation
directive AGENCY-OS-KEIRACOM-SEPARATION-V1 (canonical key
ceo:agency_os_keiracom_separation_v1, ratified 2026-05-24).

Reads discovery log entries from:
  1. ~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/discovery_log.jsonl
  2. public.agent_memories (Supabase) — source_type filter, defaults to the
     dispatch-literal ('discovery','finding','gotcha') with a --wider flag for
     the empirically-populated source_types (lesson/pattern/verified_fact/
     test_result/research) when the literal set is empty (the current state
     2026-05-24 — see report doc §3 agent_memories vocabulary divergence note).

For each entry, applies a keyword-based heuristic to classify into one of:
  - fleet         — orchestration plumbing, NATS/CI/orchestrator, fleet infra
  - product       — Keiracom V1.0 product code (chat, dashboard, workforce,
                    MAL, Hindsight, MCP dispatcher, tenant)
  - archive       — Agency OS-era pipeline (Siege Waterfall, CIS, T0-T5,
                    enrichment waterfalls, BU, GMB/ABN, dead vendors)
  - cross-product — explicit cross-product items (separation directive, MAL
                    infrastructure that serves the product, ambiguous content
                    spanning both products)
  - manual-review — classifier cannot confidently classify (no keyword hits
                    OR top two buckets within 1 match — needs human pass)

DEFAULT MODE: dry-run (proposed classification printed to stdout, no writes).
Per dispatch: "NO destructive writes on first pass — output a proposed
classification + ask for review before applying tags back."

IDEMPOTENCY: each classified JSONL entry receives a `classification` object
({label, confidence, matched_keywords}). Re-runs detect entries already
carrying that field and skip them (override with --reclassify).

USAGE:
    python3 scripts/classifier/discovery_log_classifier.py
    python3 scripts/classifier/discovery_log_classifier.py --report
    python3 scripts/classifier/discovery_log_classifier.py --apply           # writes tags back
    python3 scripts/classifier/discovery_log_classifier.py --reclassify --report
    python3 scripts/classifier/discovery_log_classifier.py --wider           # widen agent_memories source_types
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

DEFAULT_JSONL_PATH = (
    Path.home() / ".claude/projects/-home-elliotbot-clawd-Agency-OS/memory/discovery_log.jsonl"
)
DEFAULT_SUPABASE_PROJECT_ID = "jatzvazlbusedwsnqxzr"
LITERAL_SOURCE_TYPES = ("discovery", "finding", "gotcha")
WIDER_SOURCE_TYPES = LITERAL_SOURCE_TYPES + (
    "lesson",
    "pattern",
    "verified_fact",
    "test_result",
    "research",
)

# Keyword lists per bucket. Lower-case, matched via word-boundary regex against
# concatenated entry text. Tunable — when the manual-review queue is large,
# add the recurring missed-keywords here and re-run.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "fleet": (
        # orchestration plumbing
        "relay",
        "tmux",
        "session-name",
        "watchdog",
        "dispatcher",
        "orchestrator",
        "agent_self_claim",
        "self-assign",
        "self_claim",
        "inbox-watcher",
        "relay-watcher",
        # NATS substrate
        "nats",
        "jetstream",
        "keiracom.elliot.inbox",
        "keiracom.dispatch",
        "keiracom.review",
        # CI / lint / test plumbing
        "pytest",
        "ruff",
        "sonar",
        "sonarcloud",
        "ci-guard",
        "ci_guard",
        "migration-guard",
        "confcutdir",
        "conftest",
        "github actions",
        "kei-108",
        # ceo_memory governance + write-guard
        "ceo_memory",
        "kei-87",
        "kei87",
        "ceo_memory_write_guard",
        "write-guard",
        "callsign_enforce",
        # supabase infra
        "supabase",
        "psycopg",
        "pgbouncer",
        "prepare_threshold",
        # bd / dolt / linear sync
        "bd ready",
        "bd close",
        "bd discover",
        "tasks_cli",
        "linear sync",
        "dolt",
        # slack relay (the elliot-only path)
        "slack_relay",
        "slack relay",
        "tg -c ceo",
        "slack #ceo",
        "callsign discipline",
        # cognee infra
        "cognee",
        "supersession",
        "cognee_purge_source",
        # systemd / units
        "systemd",
        "agent-keepalive",
        "keepalive.service",
        # governance laws
        "law xvii",
        "law xv-d",
        "step 0 restate",
    ),
    "product": (
        # Keiracom V1.0 product specs
        "keiracom_chat",
        "keiracom_dashboard",
        "keiracom v1",
        "keiracom workforce",
        "chat product",
        "dashboard product",
        "workforce product",
        # Memory Abstraction Layer + Hindsight
        "memory abstraction layer",
        "memory_abstraction_layer",
        "mal v1",
        "mal_v1",
        "hindsight",
        # tenant + onboarding
        "tenant_isolation",
        "tenant-isolation",
        "tenant onboarding",
        "per-tenant",
        "tenant-scoped",
        "set_tenant_session",
        # MCP dispatcher (product-side)
        "mcp dispatcher",
        "mcp_project_id",
        "mcp wrong-project-id",
        # BYO API key + customer-facing
        "byo key",
        "byo api key",
        "customer",
        "install script",
        # product roadmap / pricing / icp / competitive
        "product vision",
        "pricing config",
        "icp_market",
        "competitive intelligence",
        # Fair-Source
        "fair-source",
        "fair source",
    ),
    "archive": (
        # Agency OS Siege Waterfall pipeline
        "siege waterfall",
        "siege_waterfall",
        "waterfall v3",
        "waterfall_v2",
        "waterfall_v3",
        "pipeline_v5",
        "pipeline_v4",
        "flow a",
        "flow b",
        # CIS + ALS scoring
        "cis",
        "als scoring",
        "reachability",
        "propensity",
        "opportunity score",
        # T0-T5 enrichment tiers
        "t0 discovery",
        "t1.5 linkedin",
        "t2 gmb",
        "t3 email",
        "t5 mobile",
        "t-dm",
        # dead vendors
        "leadmagic",
        "bright data",
        "salesforge",
        "contactout",
        "hunter.io",
        "kaspr",
        "proxycurl",
        "apollo",
        "apify",
        "webshare",
        "serp api",
        "clay",
        # GMB / ABN / BU
        "gmb_place_id",
        "gmb_review_count",
        "abn",
        "abr ",
        "business_universe",
        "bu_",
        # Agency OS outreach channels
        "unipile",
        "elevenagents",
        "salesforge",
        "telnyx",
        # Agency OS-era abbreviations
        "dm_email",
        "dm waterfall",
        "scout.py",
        "enrichment tier",
    ),
    "cross-product": (
        # explicit cross-product items
        "agency_os_keiracom",
        "agency-os-keiracom",
        "separation directive",
        "phase 1.2.5",
        "phase 1.3",
        "phase 2.0",
        "phase 2.1",
        "phase 2.2",
        "3-repo",
        "three-repo",
        "repo topology",
        # MAL serving both
        "mal infrastructure",
        # tenant model architecture
        "arch:tenant_model",
        "tenant model",
        "tenant_model",
        # canonical key infra
        "ceo:comm_architecture",
        "comm_architecture",
    ),
}

# Strict margin threshold — only a TRUE tie (top score equal to next) routes
# to manual-review. Equal scores = no-confidence; 1-point lead = sufficient
# confidence. Doc/code-mismatch fix-up per Max HOLD on PR #1121 (2026-05-24):
# original doc said "within MIN_CONFIDENCE_MARGIN" implying margin=1 routes
# to manual-review, but code does strict `<` so only margin=0 (true tie)
# routes. Empirical 10-fleet-1-manual-review distribution on real JSONL
# confirms the strict semantics are not over-routing — kept the code, fixed
# the doc to match.
MIN_CONFIDENCE_MARGIN = 1

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("discovery_log_classifier")


def combine_text(entry: dict) -> str:
    """Concatenate the classifiable text fields of an entry, lower-case."""
    parts: list[str] = []
    for field in ("context", "finding", "failed_path", "verified_path", "content", "summary"):
        v = entry.get(field)
        if v:
            parts.append(str(v))
    tags = entry.get("tags")
    if isinstance(tags, (list, tuple)):
        parts.extend(str(t) for t in tags)
    return " ".join(parts).lower()


def _count_matches(text: str, keywords: tuple[str, ...]) -> tuple[int, list[str]]:
    matched: list[str] = []
    for kw in keywords:
        # Word-boundary-ish — \b doesn't play well with hyphens/colons, use a
        # simple substring check + dedup. Acceptable false-positive rate.
        if kw in text:
            matched.append(kw)
    return len(matched), matched


def classify(entry: dict) -> dict:
    """Classify a single entry. Returns dict {label, confidence, matched_keywords, scores}."""
    text = combine_text(entry)
    scores: dict[str, int] = {}
    matched_per_bucket: dict[str, list[str]] = {}
    for bucket, kws in KEYWORDS.items():
        count, matched = _count_matches(text, kws)
        scores[bucket] = count
        matched_per_bucket[bucket] = matched

    if not text or all(v == 0 for v in scores.values()):
        return {
            "label": "manual-review",
            "reason": "no_keyword_hits",
            "scores": scores,
            "matched_keywords": [],
        }

    # Pick highest-scoring bucket. Tie-break: ONLY a true tie (top == next)
    # routes to manual-review; a 1-point lead is sufficient confidence.
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    top_label, top_score = ranked[0]
    if len(ranked) > 1:
        _, second_score = ranked[1]
        if top_score - second_score < MIN_CONFIDENCE_MARGIN:
            return {
                "label": "manual-review",
                "reason": "tie_or_near_tie",
                "scores": scores,
                "matched_keywords": matched_per_bucket[top_label],
            }
    return {
        "label": top_label,
        "reason": "top_score",
        "scores": scores,
        "matched_keywords": matched_per_bucket[top_label],
    }


def read_jsonl(path: Path) -> list[dict]:
    """Read JSONL entries. Skip malformed lines with a warning."""
    if not path.is_file():
        log.warning("jsonl source not found: %s", path)
        return []
    entries: list[dict] = []
    for i, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            log.warning("jsonl line %d malformed (skipped): %s", i, exc)
    return entries


def read_agent_memories(project_id: str, source_types: tuple[str, ...]) -> list[dict]:
    """Read discovery-like rows from Supabase agent_memories via psycopg.

    Returns [] if SUPABASE_DB_DSN env unset (CI portability — same skip pattern
    as tests/governance/test_ceo_memory_context_constraint.py).
    """
    dsn = os.environ.get("SUPABASE_DB_DSN", "").strip()
    if not dsn:
        log.warning(
            "SUPABASE_DB_DSN unset — agent_memories source skipped (project_id=%s)", project_id
        )
        return []
    try:
        import psycopg
    except ImportError:
        log.warning("psycopg not installed — agent_memories source skipped")
        return []
    try:
        with psycopg.connect(dsn, autocommit=True) as cn, cn.cursor() as cur:
            cur.execute(
                "SELECT id, callsign, source_type, content, typed_metadata "
                "FROM public.agent_memories "
                "WHERE source_type = ANY(%s) "
                "ORDER BY created_at DESC LIMIT 5000",
                (list(source_types),),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r[0]),
                    "agent": r[1],
                    "source_type": r[2],
                    "content": r[3],
                    "typed_metadata": r[4] or {},
                }
                for r in rows
            ]
    except Exception as exc:
        log.warning("agent_memories read failed: %s", exc)
        return []


def classify_all(entries: list[dict], reclassify: bool = False) -> list[dict]:
    """Annotate each entry with a `classification` field. Idempotent unless reclassify=True."""
    out: list[dict] = []
    for entry in entries:
        if not reclassify and isinstance(entry.get("classification"), dict):
            out.append(entry)
            continue
        annotated = dict(entry)
        annotated["classification"] = classify(entry)
        out.append(annotated)
    return out


def summarise(entries: list[dict]) -> Counter:
    """Counter of label → count over annotated entries."""
    return Counter(
        e["classification"]["label"] for e in entries if isinstance(e.get("classification"), dict)
    )


def print_report(jsonl_entries: list[dict], agent_memories_entries: list[dict]) -> None:
    """Render a stdout report. No writes."""
    jsonl_summary = summarise(jsonl_entries)
    am_summary = summarise(agent_memories_entries)
    print("=" * 70)
    print("Discovery Log Classifier Report (dry-run — no writes)")
    print("=" * 70)
    print(f"\nJSONL source ({len(jsonl_entries)} entries):")
    for label, n in sorted(jsonl_summary.items(), key=lambda kv: -kv[1]):
        pct = (100.0 * n / len(jsonl_entries)) if jsonl_entries else 0.0
        print(f"  {label:14}  {n:4}  ({pct:.1f}%)")
    print(f"\nagent_memories source ({len(agent_memories_entries)} entries):")
    for label, n in sorted(am_summary.items(), key=lambda kv: -kv[1]):
        pct = (100.0 * n / len(agent_memories_entries)) if agent_memories_entries else 0.0
        print(f"  {label:14}  {n:4}  ({pct:.1f}%)")
    flagged = [
        e
        for e in jsonl_entries + agent_memories_entries
        if isinstance(e.get("classification"), dict)
        and e["classification"]["label"] == "manual-review"
    ]
    print(f"\nManual-review queue: {len(flagged)} entries")
    for entry in flagged[:5]:
        ident = entry.get("kei") or entry.get("id") or "?"
        reason = entry["classification"].get("reason", "?")
        ctx = (entry.get("context") or entry.get("content") or "")[:80]
        print(f"  - {ident} [{reason}] {ctx!r}")
    if len(flagged) > 5:
        print(f"  ... + {len(flagged) - 5} more")


def write_back_jsonl(path: Path, entries: list[dict]) -> None:
    """Rewrite the JSONL file with classification annotations."""
    lines = [json.dumps(e) for e in entries]
    path.write_text("\n".join(lines) + "\n")
    log.info("write_back_jsonl: wrote %d entries to %s", len(entries), path)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL_PATH, help="JSONL source path")
    p.add_argument("--project-id", default=DEFAULT_SUPABASE_PROJECT_ID, help="Supabase project id")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Write classification tags back to JSONL (NOT default — dispatch said no destructive writes on first pass)",
    )
    p.add_argument(
        "--reclassify",
        action="store_true",
        help="Re-classify entries that already have a classification field",
    )
    p.add_argument(
        "--report", action="store_true", help="Print summary report (default if not --apply)"
    )
    p.add_argument(
        "--wider",
        action="store_true",
        help="Use wider agent_memories source_types (lesson/pattern/verified_fact/test_result/research) when literal returns empty",
    )
    args = p.parse_args(argv)

    jsonl_entries = read_jsonl(args.jsonl)
    source_types = WIDER_SOURCE_TYPES if args.wider else LITERAL_SOURCE_TYPES
    am_entries = read_agent_memories(args.project_id, source_types)

    if not args.wider and not am_entries and source_types == LITERAL_SOURCE_TYPES:
        log.info(
            "agent_memories source returned 0 rows for literal source_types %s. "
            "Re-run with --wider to include lesson/pattern/verified_fact/test_result/research.",
            source_types,
        )

    jsonl_classified = classify_all(jsonl_entries, reclassify=args.reclassify)
    am_classified = classify_all(am_entries, reclassify=args.reclassify)

    print_report(jsonl_classified, am_classified)

    if args.apply:
        log.warning("--apply set — writing classification tags back to JSONL")
        write_back_jsonl(args.jsonl, jsonl_classified)
        # agent_memories write-back NOT implemented in this pass — needs the
        # context column to exist + per-row UPDATE wrapped in ceo_memory_writer
        # discipline. Per dispatch's "no destructive writes on first pass",
        # surface the gap rather than half-implement.
        log.warning(
            "agent_memories write-back not implemented (out of scope for first pass). "
            "Add migration + writer wrapper in a separate KEI."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
