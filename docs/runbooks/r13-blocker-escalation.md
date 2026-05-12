# R13 Blocker Escalation — #ceo First

**Status:** Ratified by CEO Dave 2026-05-12 ts ~1778626400 (Outcome 1 of R13 directive).
**Owner:** Elliot (orchestrator protocol).
**Companion:** Outcome 2 — Aiden's R13 enforcer rule in `src/bot_common/enforcer_deterministic.py` (separate PR).

## The rule (Dave verbatim)

> Any blocker requiring CEO or Dave decision → post to #ceo immediately. Not after peer discussion. Not after review. The moment a decision outside team authority is needed — #ceo first.

## Why

CLAUDE.md Equality Guard blocker sat in #execution while the team discussed Options A/B/C/D. Dave had to surface the blocker himself instead of being notified at the moment a decision outside team authority became required. R13 closes that gap.

## Where this rule lives (KEI-12 symlink trapdoor)

The canonical operator-facing file is at:
- `~/.config/agency-os/modules/_orchestrator.md` (host-applied; symlinked into each worktree's `.claude/modules/_orchestrator.md`)

This runbook (`docs/runbooks/r13-blocker-escalation.md`) is the **repo-tracked source-of-truth** for git history. The canonical operator file is already updated host-side as part of this PR; the symlink propagates the change to all six worktrees automatically.

This dual-location pattern matches `docs/runbooks/session-start-bd-linear-sync.md` (PR #807) and is the KEI-12 symlink design's prescribed workflow for orchestrator module edits.

## What landed in the orchestrator module

A new section was inserted in `_orchestrator.md` between `### Prefect pipeline failure` and `### If I write code or open a PR directly — STOP`:

```
### Blocker escalation — #ceo first (Dave R13, ts ~1778626400)

Any blocker requiring CEO or Dave decision → post to #ceo immediately. Not after peer discussion. Not after review. The moment a decision outside team authority is needed — #ceo first.
```

Header anchors WHO ratified + WHEN per peer-review suggestion.

## How to apply

Before posting a `[PROPOSE:elliot]` or decision-needed message in `#execution`, ask:

- Does this require a CEO or Dave decision?
- If YES → post the plain-English summary in `#ceo` FIRST or simultaneously. Reference the `#execution` post for technical detail.
- If NO → `#execution`-only is fine (peer coordination, technical resolution, status update).

The orchestrator's job is to ensure Dave never has to find a blocker. Surface immediately when authority crosses the team boundary.

## Cross-callsign scope

This rule is **orchestrator-specific** (Elliot's lane). CTOs (Aiden / Max) and engineers (Atlas / Orion / Scout) escalate up the chain to Elliot; Elliot escalates to Dave. Each layer holds its own escalation discipline.

Outcome 2's R13 enforcer rule (Aiden's PR) provides the deterministic check that catches missed escalations.

## Smoke verification (post-merge)

Evidence Required item 1 from Dave: paste verbatim new line. Satisfied by the verbatim quote above + the `_orchestrator.md` diff anchor.

Evidence Required items 2+3 (simulated R13 fire / pass) gate on Aiden's enforcer-rule PR (Outcome 2). Cross-link will be added once that PR merges.
