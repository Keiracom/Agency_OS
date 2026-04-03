---
name: decomposer
description: Self-decomposition protocol — breaks high-level objectives into verified task graphs before any execution.
---

# Decomposer Skill — Objective-to-Task-Graph Protocol

When the main agent receives a directive or high-level objective, BEFORE any execution:

## Step 1 — DECOMPOSE

Break the objective into discrete numbered tasks. For each task specify:

| Field | Description |
|-------|-------------|
| Task ID | T1, T2, T3... |
| Description | One sentence max |
| Assigned Agent | research-1 / build-2 / build-3 / test-4 / review-5 / devops-6 / architect-0 |
| Dependencies | Task IDs that must complete first, or "none" |
| Verification | Specific command + expected output proving completion |
| Complexity | low / medium / high |

**Agent selection rule:**
- Haiku: research-1, test-4, devops-6 (cheap, mechanical, procedural)
- Sonnet: build-2, build-3, review-5 (code, review)
- Opus: architect-0 only (architecture decisions, complexity=high)

## Step 2 — PRESENT

Show full task graph to Dave. Format: clean markdown table.
**Do NOT begin execution until Dave responds with "go", "approved", or equivalent.**

## Step 3 — EXECUTE

Run tasks respecting dependency order. Parallel where no deps block.
Each task spawns the assigned sub-agent.

## Step 4 — VERIFY

After each task: run verification criteria.
- Pass → mark complete
- Fail → retry once
- Retry fail → pause and report to Dave with full error

## Step 5 — REPORT

Full completion report:
- Task-by-task results
- Verification evidence (verbatim output)
- PR link if applicable
- Store updates (ceo_memory, Manual)

## CRITICAL RULES

1. Never skip decomposition — even simple tasks get decomposed
2. Never execute before approval
3. Never report complete without verification evidence
4. EVO directives do NOT increment Agency OS directive counter (306)
5. Use cheapest appropriate agent per complexity
