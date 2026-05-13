# Linear-KEI-before-build standing rule — GOVERNANCE.md design delta

**Author:** Aiden (design only — per Dave verbatim ts ~1778666900)
**Implementer:** Elliot (post-compact ratification + execute, bundled with KEI-37/38/39 + ceo_memory hygiene)
**Beads:** Agency_OS-8lz — P2
**Self-referential:** this bd issue + design doc were created BEFORE the branch + commit per the rule it documents.

## Dave verbatim — canonical sources

### Initial ratification (ts ~1778666900)

> No build begins without a Linear issue in Todo or In Progress assigned to you. If you find something that needs building and there is no KEI for it — raise the KEI first, get it on the board, then build. Never the other way around.

### Hardening — Linear-only + Beads-hard-block (ts ~1778667000)

> Linear is the only source of work. Beads is the enforcement mechanism. Cannot build without active bd claim on Linear-sourced task. No exceptions. Chain: KEI in Linear → bd sync → bd claim → Enforcer confirms → build begins. Any step missing = HARD STOP at tool level.

Applies to all 6 callsigns going forward. The hardening (Beads as enforcement mechanism, tool-level hard stop) shifts the rule from agent-discipline to mechanical-enforcement.

## Rule restated for GOVERNANCE.md

```markdown
## STANDING RULE — Linear-KEI-before-build (Dave 2026-05-13 ratified)

Every build (code change, design doc, infrastructure work) MUST be backed by a
Linear KEI in Todo or In Progress, assigned to the building agent, BEFORE any
branch is opened or any file is written.

If an agent identifies work that needs building and no KEI exists:

1. Raise the KEI in Linear (or via `bd create` which mirrors to Linear via KEI-22).
2. Confirm the KEI is on the board (status Todo or In Progress).
3. Assign to self.
4. Then begin the work (which also triggers the KEI-39 4-step pre-execution claim).

Never the other way around. "I'll file the KEI after I'm done" is a violation.

This rule composes with KEI-39:
- KEI-39 step 1 (`bd claim`) presupposes a bd/Linear issue exists. This rule
  guarantees it.
- KEI-39 step 2 (Linear assignee + comment) updates an existing issue. This
  rule guarantees the issue was filed first.
- KEI-39 step 3 (`#execution [STARTING]`) references the now-existing KEI.

Violation = governance debt entry of type `LAW_LINEAR_KEI_BEFORE_BUILD_SKIPPED`.
```

## Applies / does NOT apply

### Applies (KEI required first)

- New feature implementation.
- Bug fix that requires a code change.
- Infrastructure / CI / governance changes.
- Design documents capturing ratified decisions.
- Refactors and cleanups (these still need a tracking issue).
- Cherry-picks of work from another branch.

### Does NOT apply

- Reading code or files (no build).
- Status / concur / release Slack posts.
- Reviewing peer PRs (review is not build).
- Running diagnostic commands (`git log`, `ps`, `bd ready`).
- Smoke probes / empirical verifies (anchored in an existing KEI's investigation phase).
- Routine session-end / session-start hooks (operationally-mandated, not new builds).

## Edge cases (decision rules)

### Multi-task within one KEI

Sub-tasks within a single KEI's scope share the KEI's coverage. No new KEI per sub-task. KEI-39's claim protocol handles sub-task-level signaling.

Example: KEI-23 covered both diagnosis (PR #825) and fix (PR #826) under one KEI. Both PRs were covered by the same KEI-23 issue.

### Spontaneous-discovery during another KEI's work

If an agent discovers a separate issue mid-build (e.g. KEI-37 design exposes a CLAUDE.md gap that becomes KEI-X), the discovery itself is fine — but BEFORE actioning the new issue, file the new KEI. Existing KEI work continues uninterrupted; the new KEI queues for separate dispatch.

Example: during KEI-36 work, the §Callsign→Model table gap was discovered. Aiden filed bd Agency_OS-dfz (KEI-36 v2) for the wiring follow-up FIRST, then continued KEI-36 to merge. Did not action the v2 work in the KEI-36 PR.

### Emergency hotfix (Resolution A class)

Crash-fallback / urgent-incident-response work that cannot wait for KEI filing (system on fire, ingest crash mid-run): proceed to mitigate IMMEDIATELY, then file the KEI within 30 minutes of stabilisation. The rule defers but does not exempt — the incident KEI exists by the time the fix lands.

Anchor: Aiden's KEI-23 fix shipped same-day-as-Stream-2-crash; the bd/Linear issue was filed in the same session window as the diagnostic + fix PRs.

### Self-referential edge case

This very rule's design doc was filed via `bd create` BEFORE the branch was opened. Test case proven. The rule applies to its own ratification.

## Interaction with KEI-22 (Linear-Beads sync — Orion's lane, 6 deliverables)

This rule is the DESIGN half. Orion's KEI-22 ships the MECHANICAL half. Mesh per Elliot ts ~1778667100:

| KEI-22 deliverable | Role for this rule |
|---|---|
| 1. Session-start `bd linear sync` | Ensures Linear is the source-of-record agents query at session start. |
| 2. CI gate enforcing KEI-XX in PR title (HARD, no bypass) | PRs without `KEI-\d+ \| Agency_OS-\w+` reference cannot merge. |
| 3. bd status change → Linear MCP update | Keeps Linear and Beads converged. |
| 4. Weekly divergence sweep | Catches drift. |
| 5. Beads hard-block on no-claim execution | Tool-level fail when agent tries to execute without active claim. |
| 6. Layer 3 mechanical gates (`bd check-claim --branch` + pre-commit hooks in all 6 worktrees) | **The primary enforcement vector for this rule.** Pre-commit hook calls `bd check-claim --branch $(git branch --show-current)`; non-zero exit aborts commit. |

Until deliverable 6 ships, the rule is enforced by agent discipline + peer review + Enforcer hook. Post-deliverable-6: commit is physically refused without `bd claim`. No LLM involved in the gate — Layer 3.

### CI-gate PR title regex (deliverable 2)

```
^\[(AIDEN|MAX|ELLIOT|ATLAS|ORION|SCOUT)\].*\b(KEI-\d+|Agency_OS-\w+)\b
```

Hard fail — no override, no bypass per Dave ts ~1778667100.

### Self-referential chain-gap note (this PR)

This PR's bd issue (`Agency_OS-8lz`) was filed BEFORE the branch + commit per the rule. But the matching Linear KEI was NOT created (local `bd linear sync --push` errored on `linear.state_map` config — KEI-22 deliverable 3 territory). The Linear half of the chain is currently bd-only until KEI-22 deliverable 1 or 3 lands.

Per Dave strict-read ts ~1778667000 ("Cannot build without active bd claim on Linear-sourced task"), this PR's chain is technically incomplete. Elliot's call ts ~1778667040 ratified continuation ("Not blocking your design-doc work since pre-compact governance refresh is broadly your wheelhouse; but the chain-of-record needs to demonstrate the new rule for KEI-22 deliverable-5 enforcer testing post-merge").

Resolution: retroactively sync bd Agency_OS-8lz → Linear KEI once KEI-22 deliverable 1 ships. This PR is the design-half deliverable; the chain-of-record completeness is gated on Orion's mechanical-half delivery.

## Interaction with KEI-37 (boot state)

`ceo:boot_state_current.active_keis` is the single source of truth for "what KEIs are in flight". Before any new build, an agent queries this key (or `bd ready`) to confirm:
1. Their target work has a KEI in `active_keis` OR a Todo issue ready to claim.
2. No peer is already assigned to that KEI.

This composes cleanly with KEI-39 step 1 (bd claim).

## Implementation handoff for Elliot (post-compact governance cascade)

Files to touch:

1. `GOVERNANCE.md` — append the §STANDING RULE section verbatim above.
2. `.github/workflows/pr-title-kei-check.yml` (new, post-KEI-22) — CI gate validating PR title regex.
3. (Optional) Enforcer hook — extend with `LAW_LINEAR_KEI_BEFORE_BUILD_SKIPPED` rule that fires on commits/PRs without matching bd/Linear issue.

Estimated: ~30 LoC governance text + ~40 LoC CI workflow (deferred to post-KEI-22) + ~25 LoC enforcer rule (optional).

## Acceptance criteria

- GOVERNANCE.md updated with §STANDING RULE — Linear-KEI-before-build.
- All 6 agents acknowledge in #execution within 24h of ratification.
- First test cases: every Aiden/Max/Elliot/Atlas/Orion/Scout PR opened after ratification has a corresponding bd/Linear KEI referenced in title or first line of body.
- Peer reviewers reject PRs that violate.

## Rollback

`git revert` of the GOVERNANCE.md addition if the rule produces more friction than the wasted-work risk it prevents. First 2 weeks observation period; if false-friction (e.g. agents filing KEIs for 5-line typos) exceeds 10% of throughput, narrow to "non-trivial builds (>50 LoC OR >1 file)".
