#!/usr/bin/env python3
"""governance_rules_seed.py — KEI-68 reproducible seed harness.

Loads the most-anchored governance rules into public.governance_rules via
upsert_rule (idempotent re-runs). One-shot, not a live sync — re-run after
ratified rule edits to migrate the new statement.

Source: docs/governance/CONSOLIDATED_RULES.md + IDENTITY.md tree + KEI-79
escalation ratify + KEI-72 Step-0 gate + KEI-78 dependency mandate. Bias
to load-bearing rules; prose-only modules excluded.
"""

from __future__ import annotations

import logging

from src.governance.rules_client import upsert_rule

logger = logging.getLogger("governance_rules_seed")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Rule rows: (id, category, rule, source_doc).
# id uses kei-79-style stable prefixes so re-runs match-by-id, not match-by-text.
SEED_RULES: tuple[dict[str, str], ...] = (
    {
        "id": "rule-r1-verify",
        "category": "concur",
        "rule": "VERIFY: truth over speed; run verification before claiming done. Verbatim output, not paraphrase.",
        "source_doc": "docs/governance/CONSOLIDATED_RULES.md",
    },
    {
        "id": "rule-r2-coordinate",
        "category": "claiming",
        "rule": "COORDINATE: no overlap, no surprise; claim before touch; peer before dispatch.",
        "source_doc": "docs/governance/CONSOLIDATED_RULES.md",
    },
    {
        "id": "rule-r3-approve",
        "category": "concur",
        "rule": "APPROVE: two checkpoints only — queue approval + merge approval.",
        "source_doc": "docs/governance/CONSOLIDATED_RULES.md",
    },
    {
        "id": "rule-r4-orchestrate",
        "category": "deliberation",
        "rule": "ORCHESTRATE: delegate, don't execute; sub-agents build, bots verify.",
        "source_doc": "docs/governance/CONSOLIDATED_RULES.md",
    },
    {
        "id": "rule-r5-communicate",
        "category": "communication",
        "rule": "COMMUNICATE: right channel, right density; concise, always propose.",
        "source_doc": "docs/governance/CONSOLIDATED_RULES.md",
    },
    {
        "id": "rule-r6-govern",
        "category": "governance-meta",
        "rule": "GOVERN: rules are code, not comments; runtime enforcement required.",
        "source_doc": "docs/governance/CONSOLIDATED_RULES.md",
    },
    {
        "id": "rule-r7-business",
        "category": "governance-meta",
        "rule": "BUSINESS: Australia-first, pre-revenue honest; $AUD, no fake social proof.",
        "source_doc": "docs/governance/CONSOLIDATED_RULES.md",
    },
    {
        "id": "rule-callsign-discipline",
        "category": "communication",
        "rule": "Every outbound message, PR title, and commit tags [ELLIOT]/[AIDEN]/[MAX]/etc. Callsign from ./IDENTITY.md. Empty = hard fail.",
        "source_doc": "IDENTITY.md",
    },
    {
        "id": "rule-step-0-restate",
        "category": "deliberation",
        "rule": "Every directive triggers Step 0 RESTATE (Objective / Scope / Success / Assumptions) before any tool call. No exceptions.",
        "source_doc": "CLAUDE.md _law_step0.md",
    },
    {
        "id": "rule-clean-tree",
        "category": "claiming",
        "rule": "Before new directive work, run git status. Uncommitted modifications from prior session → STOP and report.",
        "source_doc": "CLAUDE.md _law_clean_tree.md",
    },
    {
        "id": "rule-arch-first",
        "category": "deliberation",
        "rule": "Before any architectural decision: cat ARCHITECTURE.md from repo root. Never answer architectural questions from training data.",
        "source_doc": "CLAUDE.md _law_architecture_first.md",
    },
    {
        "id": "rule-skills-first",
        "category": "claiming",
        "rule": "LAW XII Skills-First: check skills/ before any external service call; never direct-call src/integrations/* outside skill execution.",
        "source_doc": "CLAUDE.md global",
    },
    {
        "id": "rule-skill-currency",
        "category": "governance-meta",
        "rule": "LAW XIII: when a fix changes an external service call, the corresponding skill file must update in the same PR.",
        "source_doc": "CLAUDE.md global",
    },
    {
        "id": "rule-raw-output",
        "category": "concur",
        "rule": "LAW XIV: paste verbatim terminal output, never summarise or paraphrase verification evidence.",
        "source_doc": "CLAUDE.md global",
    },
    {
        "id": "rule-four-store",
        "category": "concur",
        "rule": "LAW XV Four-Store: directive completion writes to docs/MANUAL.md + ceo_memory + cis_directive_metrics + Drive mirror. KEI-74 sync queue automates 3 of 4.",
        "source_doc": "CLAUDE.md global",
    },
    {
        "id": "rule-completion-discipline",
        "category": "concur",
        "rule": "Before posting completion language: run verify_pr.sh / git cat-file -t / systemctl status; paste verbatim. Context compaction conflates will-do with did.",
        "source_doc": "CLAUDE.md _completion_discipline.md",
    },
    {
        "id": "rule-mcp-bridge",
        "category": "claiming",
        "rule": "External service calls: (1) skill if exists, (2) MCP bridge, (3) exec last resort + write a skill. Never credential-hunt.",
        "source_doc": "CLAUDE.md _mcp_bridge.md",
    },
    {
        "id": "rule-dual-approval",
        "category": "concur",
        "rule": "Both Elliot AND Aiden (or dual-CTO subset overnight) must approve every PR before merge.",
        "source_doc": "feedback_dual_approval.md",
    },
    {
        "id": "rule-three-way-concur",
        "category": "concur",
        "rule": "Dave-facing posts need [CONCUR] from BOTH peers (Aiden+Elliot+Max), not just one.",
        "source_doc": "feedback_three_way_concur.md",
    },
    {
        "id": "rule-non-blockers-are-blockers",
        "category": "concur",
        "rule": "All issues found during PR review fix in same PR — no tiered defer.",
        "source_doc": "feedback_non_blockers_are_blockers.md",
    },
    {
        "id": "rule-wait-for-final",
        "category": "concur",
        "rule": "After [REQUEST-FINAL]: don't self-merge on green CI alone; peer may be drafting HOLD-FINAL on a Sonar issue.",
        "source_doc": "feedback_wait_for_final_response.md",
    },
    {
        "id": "rule-empirical-smoke",
        "category": "concur",
        "rule": "For external service calls: run actual binary against actual service BEFORE FINAL. Mocks lie about library shape + DB publication membership.",
        "source_doc": "feedback_empirical_test_catches_paper_concur_misses.md",
    },
    {
        "id": "rule-independent-verify",
        "category": "concur",
        "rule": "Dual verification ≠ peer echo. Run own grep/wc/diff, post raw output. 'Confirmed' without independent check is rubber-stamp.",
        "source_doc": "feedback_independent_verification_not_echo.md",
    },
    {
        "id": "rule-silence-is-status",
        "category": "communication",
        "rule": "Never emit 'Acknowledged/Aligned/Holding' pings. Step 0 → work → PR → done. Silence IS the status.",
        "source_doc": "feedback_silence_is_status.md",
    },
    {
        "id": "rule-directive-ack",
        "category": "deliberation",
        "rule": "Every directive from Dave gets explicit acknowledgement before execution.",
        "source_doc": "feedback_directive_ack.md",
    },
    {
        "id": "rule-close-loop-to-ceo",
        "category": "communication",
        "rule": "Every concurred #execution thread must produce a #ceo post within 60s. Sitting idle = governance violation.",
        "source_doc": "feedback_close_loop_to_ceo.md",
    },
    {
        "id": "rule-no-time-estimates",
        "category": "communication",
        "rule": "Never say days/weeks/tomorrow — scope by work items, not time.",
        "source_doc": "feedback_no_time_estimates.md",
    },
    {
        "id": "rule-callsign-cwd-bug",
        "category": "communication",
        "rule": "Prefix every slack_relay/tg call with CALLSIGN=<name>; relay reads IDENTITY.md from its own cwd, not caller's.",
        "source_doc": "reference_tg_callsign_cwd_bug.md",
    },
    {
        "id": "rule-task-verification-trigger",
        "category": "concur",
        "rule": "DB trigger blocks UPDATE tasks SET status='done' on tasks WITH acceptance_criteria unless task_verifications row inserted first with verbatim test_output.",
        "source_doc": "reference_task_verification_trigger.md",
    },
    {
        "id": "rule-kei-before-build",
        "category": "claiming",
        "rule": "No build starts without a Linear KEI in Todo/In Progress assigned to the agent. Raise KEI first, then build.",
        "source_doc": "feedback_kei_before_build.md",
    },
    {
        "id": "rule-kei-79-escalate",
        "category": "escalation",
        "rule": "Use `bd escalate <description> [--options A,B,C]` to escalate decisions to Dave. Writes ceo_decisions row + posts #ceo + holds claim until resolution.",
        "source_doc": "KEI-79 ratify 2026-05-16",
    },
    {
        "id": "rule-kei-72-step-0-gate",
        "category": "deliberation",
        "rule": "slack_relay auto-claim gates on a recent [STEP-0-RESTATE:<callsign>] in #execution. [ESCALATION-INITIATED:] sentinel exempts (Dave authorisation = the gate event).",
        "source_doc": "KEI-72 + KEI-79",
    },
    {
        "id": "rule-kei-78-deps-mandatory",
        "category": "claiming",
        "rule": "When filing a task that depends on another agent's work, dependencies[] array MUST be populated at creation time. Not optional.",
        "source_doc": "KEI-78 + Dave ratify 2026-05-16T11:52Z",
    },
)


def seed_all() -> dict:
    stats = {"upserted": 0, "errors": 0}
    for rule in SEED_RULES:
        try:
            upsert_rule(rule)
            stats["upserted"] += 1
        except (RuntimeError, ValueError) as exc:
            logger.warning("[seed] upsert failed for %s: %s", rule["id"], exc)
            stats["errors"] += 1
    logger.info("seed complete: %s", stats)
    return stats


def main() -> int:
    seed_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
