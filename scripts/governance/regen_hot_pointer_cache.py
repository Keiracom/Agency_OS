#!/usr/bin/env python3
"""regen_hot_pointer_cache.py — Agency_OS-wk3q / KEI-wk3q.

Renders docs/governance/_hot_pointer_cache.md from the embedded MANIFEST.
The hot pointer cache is the layer-2 static fallback in the Layered
Governance Matrix v1 — when cognee_recall is unavailable (cold start,
search misfire, budget exhausted), agents fall back to this single
markdown table to look up which LAW / GOV / Rule / persona to pull.

Single source of truth for the table content lives here, in MANIFEST.
When a new rule or persona is ratified, edit MANIFEST and re-run:

    python3 scripts/governance/regen_hot_pointer_cache.py

Acceptance:
  - Output file exists at docs/governance/_hot_pointer_cache.md
  - Token count ≤2500 (per Layered Governance Matrix v1 budget)
  - Every row has all 5 columns including a non-empty recall key
  - Recall keys are kebab-case + unique
"""

from __future__ import annotations

import sys
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "governance" / "_hot_pointer_cache.md"
TOKEN_BUDGET = 2500
CHARS_PER_TOKEN = 4  # rough English heuristic; matches cognee/LLM estimates


# Manifest schema: (item_id, title, one_line, trigger, recall_key)
# Keep one_line + trigger tight — every cell counts against the 2500-token budget.

LAWS: list[tuple[str, str, str, str, str]] = [
    (
        "LAW I-A",
        "Architecture First",
        "cat ARCHITECTURE.md before any architectural decision",
        "code change, architectural decision, sub-agent task brief",
        "law-i-a-architecture-first",
    ),
    (
        "LAW II",
        "Australia First",
        "all financial outputs in $AUD (1 USD = 1.55 AUD)",
        "any pricing/cost output, vendor comparison",
        "law-ii-australia-first-aud",
    ),
    (
        "LAW III",
        "Justification Required",
        "Governance Trace on every decision",
        "any decision posted to Dave or peers",
        "law-iii-justification-trace",
    ),
    (
        "LAW IV",
        "Non-Coder Bridge",
        "no code blocks >20 lines without Conceptual Summary",
        "posting code to Dave",
        "law-iv-non-coder-bridge",
    ),
    (
        "LAW V",
        "50-Line Protection",
        "if a task requires >50 lines, spawn a sub-agent",
        "starting a build task",
        "law-v-50-line-protection",
    ),
    (
        "LAW VI",
        "Skills-First Operations",
        "skill → MCP → exec hierarchy; never call services ad-hoc",
        "before any external service call",
        "law-vi-skills-first",
    ),
    (
        "LAW VII",
        "Timeout Protection",
        "use async patterns for any task >60s",
        "long-running operations",
        "law-vii-timeout-protection",
    ),
    (
        "LAW VIII",
        "GitHub Visibility",
        "all work pushed to GitHub before reporting complete",
        "before any [SHIPPED] or completion claim",
        "law-viii-github-visibility",
    ),
    (
        "LAW IX",
        "Session Memory",
        "Supabase is the SOLE persistent memory store",
        "session start, session end, memory writes",
        "law-ix-supabase-sole-memory",
    ),
    (
        "LAW XI",
        "Orchestrate",
        "Elliottbot delegates, never executes task work directly",
        "Elliot considering executing instead of dispatching",
        "law-xi-orchestrate-delegate",
    ),
    (
        "LAW XII",
        "Skills-First Integration",
        "direct calls to src/integrations/ outside skill execution forbidden",
        "considering a non-skill integration call",
        "law-xii-skills-first-integration",
    ),
    (
        "LAW XIII",
        "Skill Currency Enforcement",
        "skill files must update in the same PR as any service-call change",
        "any PR that changes how an external service is called",
        "law-xiii-skill-currency",
    ),
    (
        "LAW XIV",
        "Raw Output Mandate",
        "paste verbatim terminal output, never summarise",
        "any 'done/verified' claim",
        "law-xiv-raw-output-mandate",
    ),
    (
        "LAW XV",
        "Four-Store Completion",
        "docs/MANUAL.md + ceo_memory + cis_directive_metrics + Drive mirror",
        "before declaring directive complete",
        "law-xv-four-store-completion",
    ),
    (
        "LAW XV-A",
        "Skills Are Mandatory",
        "cat the skill file before any matching task",
        "task that maps to an existing skill",
        "law-xv-a-skills-mandatory",
    ),
    (
        "LAW XV-B",
        "DoD Is Mandatory",
        "cat DEFINITION_OF_DONE.md before reporting complete",
        "before any completion claim",
        "law-xv-b-dod-mandatory",
    ),
    (
        "LAW XV-C",
        "Governance Docs Immutable",
        "never recreate/modify gov docs without explicit CEO directive",
        "considering editing CONSOLIDATED_RULES, ARCHITECTURE, MANUAL",
        "law-xv-c-governance-immutable",
    ),
    (
        "LAW XV-D",
        "Step 0 RESTATE",
        "mandatory RESTATE before any directive execution, no exceptions",
        "every directive received",
        "law-xv-d-step-0-restate",
    ),
]

GOVS: list[tuple[str, str, str, str, str]] = [
    (
        "GOV-8",
        "Maximum Extraction Per Call",
        "capture every API response in full; write to BU; never re-fetch",
        "any vendor API call",
        "gov-8-maximum-extraction",
    ),
    (
        "GOV-9",
        "Two-Layer Directive Scrutiny",
        "Layer 2 CTO scrutiny before Step 0; report GAPS or CLEAR",
        "every directive received",
        "gov-9-directive-scrutiny",
    ),
    (
        "GOV-10",
        "Resolve-Now-Not-Later",
        "fix bounded gaps in current PR, not follow-up directives",
        "any gap found during build",
        "gov-10-resolve-now",
    ),
    (
        "GOV-11",
        "Structural Audit Before Validation",
        "stage audit within 7 days before any N>=20 validation run",
        "considering a cohort validation run",
        "gov-11-audit-before-validation",
    ),
    (
        "GOV-12",
        "Gates As Code Not Comments",
        "runtime enforcement required, not documentation-only",
        "any 'gate added' claim",
        "gov-12-gates-as-code",
    ),
]

RULES: list[tuple[str, str, str, str, str]] = [
    (
        "RULE 1",
        "VERIFY",
        "truth over speed — run verification before claiming done",
        "any completion keyword (done/merged/shipped)",
        "rule-1-verify",
    ),
    (
        "RULE 2",
        "COORDINATE",
        "no overlap, no surprise — claim before touch, peer before dispatch",
        "before editing a shared file or dispatching peers",
        "rule-2-coordinate",
    ),
    (
        "RULE 3",
        "APPROVE",
        "two checkpoints only — queue approval + merge approval",
        "before queueing work or merging PR",
        "rule-3-approve",
    ),
    (
        "RULE 4",
        "ORCHESTRATE",
        "delegate, don't execute — sub-agents build, bots verify",
        "Elliot considering direct execution",
        "rule-4-orchestrate",
    ),
    (
        "RULE 5",
        "COMMUNICATE",
        "right channel, right density — TG group, concise, always propose",
        "any Dave-facing or peer-facing post",
        "rule-5-communicate",
    ),
    (
        "RULE 6",
        "GOVERN",
        "rules are code, not comments — runtime enforcement required",
        "any new rule added to repo",
        "rule-6-govern",
    ),
    (
        "RULE 7",
        "BUSINESS",
        "Australia-first, pre-revenue honest — $AUD, no fake social proof",
        "any marketing or pricing output",
        "rule-7-business",
    ),
]

PERSONAS: list[tuple[str, str, str, str, str]] = [
    (
        "PERSONA elliot",
        "Elliot",
        "deliberation layer — implementation lens",
        "PR review on implementation feasibility, dispatch routing",
        "persona-elliot",
    ),
    (
        "PERSONA aiden",
        "Aiden",
        "deliberation layer — governance + architecture lens",
        "PR review on architecture drift, dependency ordering, governance",
        "persona-aiden",
    ),
    (
        "PERSONA max",
        "Max",
        "deliberation layer — code quality + test coverage lens",
        "PR review on Sonar QG, test edge cases, hardcoded values",
        "persona-max",
    ),
    (
        "PERSONA john",
        "John",
        "face layer — Dave-facing communicator; never executes/reviews",
        "Dave-facing summary translation, single-voice presentation",
        "persona-john",
    ),
    (
        "PERSONA orion",
        "Orion",
        "worker layer — unrestricted; claims any worker-lane KEI",
        "engineer-tier build/test/fix work",
        "persona-orion",
    ),
    (
        "PERSONA atlas",
        "Atlas",
        "worker layer — unrestricted; operator-tier ops + builds",
        "Vultr deploys, systemd install scripts, infra ops",
        "persona-atlas",
    ),
    (
        "PERSONA scout",
        "Scout",
        "worker layer — unrestricted; research + build",
        "research, sourcing, data collection, frontend builds",
        "persona-scout",
    ),
    (
        "PERSONA nova",
        "Nova",
        "worker layer — unrestricted; build + verification",
        "engineer-tier build/test/fix work",
        "persona-nova",
    ),
    (
        "PERSONA worker4",
        "Worker-4",
        "worker layer — unrestricted; shared identity with orion/atlas/scout/nova",
        "any worker-lane KEI when 4 primaries saturated",
        "persona-worker4",
    ),
]


def render() -> str:
    parts: list[str] = []
    parts.append("# Hot Pointer Cache — Layered Governance Matrix v1 layer-2 fallback\n")
    parts.append(
        "> **AUTO-GENERATED — do not hand-edit.** Source manifest: `scripts/governance/regen_hot_pointer_cache.py`. Regenerate on every governance ratification.\n"
    )
    parts.append("\n")
    parts.append(
        "This file is the deterministic static fallback for `cognee_recall` — when the semantic recall layer is unavailable (cold start, search misfire, exceeded budget) agents fall back to this single markdown table to look up which LAW / GOV / Rule / persona to pull.\n"
    )
    parts.append("\n")
    parts.append(
        "Token budget per Layered Governance Matrix v1: **≤2500 tokens**. Regenerator asserts.\n"
    )

    for heading, rows in (
        ("## LAWs", LAWS),
        ("## GOV Rules", GOVS),
        ("## Consolidated Rules", RULES),
        ("## Personas", PERSONAS),
    ):
        parts.append(f"\n{heading}\n\n")
        parts.append("| Item | Title | 1-line | Trigger | Recall key |\n")
        parts.append("|------|-------|--------|---------|------------|\n")
        for item, title, one_line, trigger, recall_key in rows:
            parts.append(f"| `{item}` | {title} | {one_line} | {trigger} | `{recall_key}` |\n")

    return "".join(parts)


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def validate(text: str) -> None:
    """Fail-loud per Layered Governance Matrix v1 §FAIL-LOUD SEMANTICS."""
    tokens = estimate_tokens(text)
    if tokens > TOKEN_BUDGET:
        print(
            f"FAIL-LOUD: hot pointer cache is {tokens} tokens; budget {TOKEN_BUDGET}",
            file=sys.stderr,
        )
        sys.exit(2)

    all_rows = LAWS + GOVS + RULES + PERSONAS
    seen_keys: set[str] = set()
    for item, title, one_line, trigger, recall_key in all_rows:
        if not all((item, title, one_line, trigger, recall_key)):
            print(f"FAIL-LOUD: empty cell in row {item!r}", file=sys.stderr)
            sys.exit(2)
        if recall_key in seen_keys:
            print(f"FAIL-LOUD: duplicate recall_key {recall_key!r}", file=sys.stderr)
            sys.exit(2)
        if recall_key != recall_key.lower() or " " in recall_key or "_" in recall_key:
            print(
                f"FAIL-LOUD: recall_key {recall_key!r} must be lowercase kebab-case",
                file=sys.stderr,
            )
            sys.exit(2)
        seen_keys.add(recall_key)


def main() -> int:
    text = render()
    validate(text)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text)
    tokens = estimate_tokens(text)
    print(f"wrote {OUTPUT} ({len(text)} chars, ~{tokens} tokens, budget {TOKEN_BUDGET})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
