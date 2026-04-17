# Agent Architecture Audit — Anthropic Framework vs Agency OS

## Core Finding
Agency OS uses static role-based workflows (Dave decomposes → agents execute in sequence). Anthropic's framework recommends dynamic routing, orchestrator-workers, and evaluator loops. Our agents are task buckets, not decision-makers.

## Classification

| Agent | Current | Should Be |
|-------|---------|-----------|
| architect-0 | Frozen to "decisions only" | Dynamic orchestrator — decomposes, delegates, monitors |
| research-1 | Research only, can't route | Should escalate to devops-6 on missing config, architect-0 on ambiguity |
| build-2/3 | Proceeds or fails, no reroute | Should callback to test-4 mid-build, escalate to devops-6 on infra gaps |
| test-4 | One-way gate | Should loop back to build-2 on failure with root cause, not just report |
| review-5 | Merge gate only | Should request changes and trigger rebuild without Dave intermediating |
| devops-6 | Deploys only | Should rollback + escalate on failure |

## Missing Patterns

1. **Routing** — No agent can redirect work to another agent. Dave is the only router.
2. **Orchestrator-Workers** — architect-0 proposes but doesn't orchestrate. Dave runs Step 1-5.
3. **Evaluator loops** — test-4 reports pass/fail but can't trigger retry.
4. **Early-abort** — No agent has defined "stop and escalate" conditions.

## Missing SOPs
No agent has a written SOP covering: trigger conditions, success criteria, failure paths, escalation rules. Each operates on implicit role description only.

## Proposed Changes (priority order)

**P0: Add routing rules to every agent prompt**
Each agent gets explicit escalation paths: "If you find X, route to Y before proceeding." Prevents the pattern where build-2 finds missing config → reports error → waits for Dave → Dave routes to devops-6 (hours). Instead: build-2 → devops-6 direct callback (minutes).

**P0: Upgrade architect-0 to persistent orchestrator**
Receives directive, auto-decomposes (<5 tasks = no Dave approval needed), spawns sub-agents with callbacks, monitors completion, auto-reroutes failures within decision authority. Dave approves architecture changes and cost increases only.

**P1: Write 1-page SOP per agent**
Trigger, success criteria, failure paths, escalation rules. Currently implicit.

**P1: Add evaluator loop to test-4**
Failed verification → categorise failure → route back to build-2 with root cause. Not "report fail and stop."

**P2: Programmatic Step 0 validation**
Script checks format before delegation. Currently Dave-eye-only.

**P2: Dry-run mode for MCP bridge**
Test orchestration without production impact.

## What This Means

Dave is currently the orchestrator, router, evaluator, AND escalation handler. That's the bottleneck. Anthropic's framework says: give agents decision authority within bounds, let them route between each other, and only escalate to the human for architecture/cost/scope decisions. Our governance (LAW XV-D, GOV-9, etc.) is strong — the gap is agent autonomy within those governance rails.
