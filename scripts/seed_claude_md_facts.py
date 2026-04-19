"""
FILE: scripts/seed_claude_md_facts.py
PURPOSE: Seed curated factual content from CLAUDE.md into agent_memories.
         Extracts product knowledge (enrichment paths, gates, laws, stack info)
         as natural-language facts — NOT meta-instructions or session prose.

USAGE:
    python scripts/seed_claude_md_facts.py [--dry-run]

FLAGS:
    --dry-run   Print facts that would be seeded without writing to Supabase.

COST: ~$0.00002 per fact (one OpenAI text-embedding-3-small call each).
SEEDER: LISTENER-SEED-V1
"""

import os
import sys
from datetime import datetime, timezone

# --- env bootstrap ---
env_path = "/home/elliotbot/.config/agency-os/.env"
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

# --- path setup ---
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

from src.memory.store import store  # noqa: E402

SEEDED_AT = datetime.now(timezone.utc).isoformat()
SEEDER_ID = "LISTENER-SEED-V1"
ORIGIN_FILE = "CLAUDE.md"
SOURCE = "governance_doc"

# ---------------------------------------------------------------------------
# Curated facts — each is self-contained natural language.
# Grouped by section for auditability.
# ---------------------------------------------------------------------------

FACTS: list[dict] = [
    # -----------------------------------------------------------------------
    # STACK
    # -----------------------------------------------------------------------
    {
        "content": (
            "Agency OS stack: Python with FastAPI (backend), Next.js (frontend), "
            "Supabase (Postgres + auth), Railway (compute), Prefect (orchestration), "
            "Redis (queue). Repo at /home/elliotbot/clawd/Agency_OS."
        ),
        "tags": ["governance_doc", "claude_md", "stack"],
        "section": "Project",
    },

    # -----------------------------------------------------------------------
    # MCP BRIDGE
    # -----------------------------------------------------------------------
    {
        "content": (
            "MCP Bridge command: "
            "`cd /home/elliotbot/clawd/skills/mcp-bridge && node scripts/mcp-bridge.js call <server> <tool> [args_json]`. "
            "Available servers: supabase, redis, prefect, railway, prospeo, dataforseo, "
            "vercel, salesforge, vapi, telnyx, unipile, resend, memory."
        ),
        "tags": ["governance_doc", "claude_md", "mcp", "integration"],
        "section": "MCP Bridge",
    },
    {
        "content": (
            "External service call hierarchy (LAW VI): "
            "(1) skill exists in skills/ — use the skill; "
            "(2) no skill but MCP available — use MCP bridge; "
            "(3) no skill, no MCP — use exec as last resort then write a skill. "
            "Ad-hoc credential hunting is forbidden."
        ),
        "tags": ["governance_doc", "claude_md", "mcp", "law"],
        "section": "MCP Bridge",
    },

    # -----------------------------------------------------------------------
    # SUPABASE
    # -----------------------------------------------------------------------
    {
        "content": (
            "Supabase project ID for Agency OS: jatzvazlbusedwsnqxzr. "
            "This is the primary persistent memory store (LAW IX). "
            "Table elliot_internal.memories holds all agent memories. "
            "Table public.ceo_memory holds CEO SSOT state."
        ),
        "tags": ["governance_doc", "claude_md", "supabase", "infrastructure"],
        "section": "Supabase",
    },

    # -----------------------------------------------------------------------
    # ACTIVE ENRICHMENT PATH
    # -----------------------------------------------------------------------
    {
        "content": (
            "Active enrichment path: T0 GMB discovery → T1 ABN lookup → "
            "T1.5a SERP Maps → T1.5b SERP LinkedIn → T2 LinkedIn Company → "
            "ALS gate (score ≥20 to proceed) → T2.5 LinkedIn People → "
            "T3 Leadmagic Email → T5 Leadmagic Mobile."
        ),
        "tags": ["governance_doc", "claude_md", "enrichment"],
        "section": "Active Enrichment Path",
    },
    {
        "content": (
            "Decision-maker enrichment waterfall: "
            "T-DM0 DataForSEO ($0.0465 AUD per lookup) → "
            "T-DM1 Bright Data Profile ($0.0015 AUD per lookup) → "
            "T-DM2 / T-DM2b / T-DM3 / T-DM4 (only triggered when Propensity score ≥70)."
        ),
        "tags": ["governance_doc", "claude_md", "enrichment", "pricing"],
        "section": "Active Enrichment Path",
    },
    {
        "content": (
            "ALS gate constants: PRE_ALS_GATE = 20 (minimum Automated Lead Score to "
            "proceed past T2 LinkedIn Company enrichment into T2.5 People and the "
            "decision-maker waterfall — leads scoring below 20 exit the people path). "
            "HOT_THRESHOLD = 85 (leads at or above this score are classified hot)."
        ),
        "tags": ["governance_doc", "claude_md", "enrichment", "gates"],
        "section": "Active Enrichment Path",
    },

    # -----------------------------------------------------------------------
    # DEAD REFERENCES
    # -----------------------------------------------------------------------
    {
        "content": (
            "Dead reference: Proxycurl is deprecated. "
            "Replacement: Bright Data LinkedIn Profile dataset (gd_l1viktl72bvl7bjuj0)."
        ),
        "tags": ["governance_doc", "claude_md", "dead_reference", "enrichment"],
        "section": "Dead References",
    },
    {
        "content": (
            "Dead reference: Apollo (enrichment) is deprecated. "
            "Replacement: Waterfall Tiers 1–5 as defined in the active enrichment path."
        ),
        "tags": ["governance_doc", "claude_md", "dead_reference", "enrichment"],
        "section": "Dead References",
    },
    {
        "content": (
            "Dead reference: Apify for GMB scraping is deprecated. "
            "Replacement: Bright Data GMB Web Scraper (dataset gd_m8ebnr0q2qlklc02fz). "
            "EXCEPTION: Apify harvestapi/linkedin-profile-scraper remains active in "
            "Pipeline F v2.1 for L2 LinkedIn verification. "
            "Apify facebook-posts-scraper remains active for Stage 9 social enrichment."
        ),
        "tags": ["governance_doc", "claude_md", "dead_reference", "enrichment"],
        "section": "Dead References",
    },
    {
        "content": (
            "Dead reference: SDK agents for enrichment/email/voice_kb are deprecated. "
            "Replacement: Smart Prompts + sdk_brain.py."
        ),
        "tags": ["governance_doc", "claude_md", "dead_reference"],
        "section": "Dead References",
    },
    {
        "content": (
            "Dead reference: MEMORY.md (new writes) is deprecated. "
            "Replacement: Supabase table elliot_internal.memories."
        ),
        "tags": ["governance_doc", "claude_md", "dead_reference", "memory"],
        "section": "Dead References",
    },
    {
        "content": (
            "Dead reference: HANDOFF.md (new writes) is deprecated. "
            "Replacement: Supabase table elliot_internal.memories."
        ),
        "tags": ["governance_doc", "claude_md", "dead_reference", "memory"],
        "section": "Dead References",
    },
    {
        "content": (
            "Dead reference: HunterIO for email verification is deprecated. "
            "Replacement: Leadmagic at $0.015 AUD per email. "
            "EXCEPTION: Hunter email-finder remains active in Pipeline F v2.1 as "
            "L2 email fallback when score ≥70."
        ),
        "tags": ["governance_doc", "claude_md", "dead_reference", "enrichment", "pricing"],
        "section": "Dead References",
    },
    {
        "content": (
            "Dead reference: Kaspr for mobile enrichment is deprecated. "
            "Replacement: Leadmagic mobile at $0.077 AUD per lookup."
        ),
        "tags": ["governance_doc", "claude_md", "dead_reference", "enrichment", "pricing"],
        "section": "Dead References",
    },
    {
        "content": (
            "Dead reference: ABNFirstDiscovery flow is deprecated. "
            "Replacement: MapsFirstDiscovery (Waterfall v3)."
        ),
        "tags": ["governance_doc", "claude_md", "dead_reference", "enrichment"],
        "section": "Dead References",
    },

    # -----------------------------------------------------------------------
    # GOVERNANCE LAWS
    # -----------------------------------------------------------------------
    {
        "content": (
            "LAW I-A — Architecture First: read ARCHITECTURE.md from repo root before "
            "any architectural decision or code change. Query ceo_memory for current "
            "system state. Architectural questions are answered from the repo, not from training data."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW II — Australia First: all financial outputs in $AUD. "
            "Conversion rate: 1 USD = 1.55 AUD. No exceptions."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance", "pricing"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW III — Justification Required: every decision requires a Governance Trace "
            "documenting the reasoning."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW IV — Non-Coder Bridge: code blocks over 20 lines require a Conceptual Summary "
            "before the code block so the CEO can follow without reading syntax."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW V — 50-Line Protection: if a task requires more than 50 lines of new code, "
            "spawn a sub-agent to implement it rather than writing it inline."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW VI — Skills-First Operations: external service call order: "
            "(1) use existing skill in skills/; "
            "(2) use MCP bridge if no skill; "
            "(3) exec as last resort, then write a skill."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance", "integration"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW VII — Timeout Protection: tasks expected to run longer than 60 seconds "
            "use async patterns to avoid blocking."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW VIII — GitHub Visibility: all work must be pushed to GitHub "
            "before reporting a directive complete."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW IX — Session Memory: Supabase is the sole persistent memory store. "
            "MEMORY.md and HANDOFF.md are deprecated for new writes."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance", "memory"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW XI — Orchestrate: Elliottbot delegates work to sub-agents and verifies results; "
            "it does not execute task work directly."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW XII — Skills-First Integration: direct calls to src/integrations/ outside "
            "of skill execution are forbidden. Skills are the canonical interface to all integrations."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance", "integration"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW XIII — Skill Currency Enforcement: when a fix or pivot changes how an external "
            "service is called, the corresponding skill file in skills/ must be updated in the "
            "same PR as the fix. Skill changes must be noted in the Manual."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance", "integration"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW XIV — Raw Output Mandate: verbatim terminal output must be pasted in reports. "
            "Summarising or paraphrasing command output is not permitted."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW XV — Three-Store Completion: a directive is complete only when written to "
            "all three stores: docs/MANUAL.md (repo), public.ceo_memory (Supabase), "
            "and public.cis_directive_metrics (Supabase)."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW XV-A — Skills Are Mandatory: read the relevant skill file before starting "
            "any task that uses an external service."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance", "integration"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW XV-B — DoD Is Mandatory: read DEFINITION_OF_DONE.md before reporting "
            "any directive complete."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW XV-C — Governance Docs Immutable: governance documents (CLAUDE.md, "
            "ARCHITECTURE.md, DEFINITION_OF_DONE.md, etc.) are never recreated or "
            "modified without an explicit CEO directive."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "LAW XV-D — RESTATE mandate: every directive requires a RESTATE output "
            "(Objective, Scope, Success criteria, Assumptions) before any execution begins. "
            "Skipping the RESTATE is a governance violation with no exceptions."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "GOV-8 — Maximum Extraction Per Call: every API response is captured in full "
            "and written to backup/storage regardless of card eligibility. "
            "Data already received in a prior stage is not re-fetched."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance", "enrichment"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "GOV-9 — Two-Layer Directive Scrutiny: every directive triggers a Layer 2 CTO "
            "scrutiny pass prior to any execution, checking for missing capabilities, config gaps, "
            "instrumentation gaps, contradicted assumptions, and recently-merged code changes."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "GOV-10 — Resolve-Now-Not-Later: bounded gaps identified during scrutiny are "
            "fixed in the current PR, not deferred to follow-up directives."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "GOV-11 — Structural Audit Before Validation: a structural stage audit must "
            "complete within the prior 7 days before any cohort run at N≥20 domains "
            "that is intended to inform a ship/no-ship decision."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
    {
        "content": (
            "GOV-12 — Gates As Code: gates specified in directives require runtime "
            "enforcement (executable conditional logic). Gates documented only as "
            "comments are insufficient and create false confidence."
        ),
        "tags": ["governance_doc", "claude_md", "law", "compliance"],
        "section": "Governance Laws",
    },
]


def _already_seeded() -> set[str]:
    """Return a set of content snippets already in agent_memories with 'claude_md' tag.

    Best-effort: on any error, returns empty set (we'd rather seed a duplicate
    than silently skip a fact).
    """
    try:
        import httpx
        from src.memory.client import MEMORIES_ENDPOINT, _supabase_headers, _supabase_url

        url = (
            _supabase_url()
            + MEMORIES_ENDPOINT
            + "?tags=cs.{claude_md}&select=content&limit=200"
        )
        resp = httpx.get(url, headers=_supabase_headers(), timeout=10)
        if resp.status_code == 200:
            rows = resp.json()
            return {r["content"][:80] for r in rows}
    except Exception as exc:
        print(f"[warn] duplicate-check failed (will seed anyway): {exc}")
    return set()


def seed_all(dry_run: bool = False) -> None:
    already = _already_seeded() if not dry_run else set()
    seeded = 0
    skipped = 0
    failed = 0

    for fact in FACTS:
        content: str = fact["content"]
        snippet = content[:80]

        if snippet in already:
            print(f"[skip] already seeded: {snippet!r}")
            skipped += 1
            continue

        meta = {
            "source": SOURCE,
            "origin_file": ORIGIN_FILE,
            "section": fact["section"],
            "seeded_at": SEEDED_AT,
            "seeded_by": SEEDER_ID,
        }

        if dry_run:
            print(f"[dry-run] would seed ({fact['section']}): {snippet!r}")
            seeded += 1
            continue

        try:
            uid = store(
                callsign="system",
                source_type="verified_fact",
                content=content,
                typed_metadata=meta,
                tags=fact["tags"],
                state="confirmed",
                trust="dave_confirmed",
                confidence=1.0,
            )
            print(f"[seeded] {uid} | {snippet!r}")
            seeded += 1
        except Exception as exc:
            print(f"[error] failed to seed: {snippet!r} — {exc}")
            failed += 1

    print()
    print(f"=== SEED SUMMARY ===")
    print(f"Total facts defined : {len(FACTS)}")
    print(f"Seeded              : {seeded}")
    print(f"Skipped (duplicate) : {skipped}")
    print(f"Failed              : {failed}")
    if dry_run:
        print("(dry-run mode — nothing written to Supabase)")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    seed_all(dry_run=dry)
