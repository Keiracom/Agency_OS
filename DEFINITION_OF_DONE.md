# DEFINITION_OF_DONE.md
# Agency OS — Directive Completion Standard
# Ratified: March 17 2026 | Authority: CEO (Claude)
# DO NOT MODIFY without an explicit CEO directive.
#
# Elliottbot — cat this file at directive end.
# Paste the completed checklist with evidence for every
# item before reporting done. No exceptions.
# CEO rejects any completion without this checklist.

---

A directive is NOT complete until Elliottbot pastes this
checklist with every item confirmed and evidence shown.
Evidence = verbatim terminal output.
Not a summary. Not a tick. Verbatim output.

---

## DUAL CONCUR RULE (KEI-206 — Ratified 2026-05-18)

PR merge eligibility requires approval from any 2 of the 3 deliberators
(Elliot / Aiden / Max). The third deliberator is the tiebreaker on splits.

### Who can approve

Authors are excluded from approving their own PRs.

| PR author | Can approve |
|-----------|-------------|
| Elliot    | Aiden + Max |
| Aiden     | Elliot + Max |
| Max       | Elliot + Aiden |

Workers (Orion / Atlas / Scout / Worker-4) are not part of the deliberation
layer and cannot contribute to dual-concur review.

### How PR review is routed

All PR reviews route to the deliberation layer (Elliot / Aiden / Max) only.
Workers do not review PRs. John (Face) does not review PRs.

Approval signal: `[REVIEW:approve:<callsign>]` in #execution from two
eligible deliberators unblocks merge. The eligible pair is determined by
the author exclusion rule above.

### Splits and tiebreaking

If two deliberators approve and the third holds, the two approvals win
(dual concur is sufficient — third is a tiebreaker only on active splits,
not a veto on a completed pair).

If all three deliberators disagree, John surfaces the 3-way split to Dave
in plain English (#ceo). Dave resolves.

### Activation gate

Dual concur (replacing triple concur) is active as of KEI-206 ratification
(2026-05-18). Author-exclusion rule is active immediately.

The broader 8-agent role structure (John / deliberators / workers) is gated
on NATS-cutover completion. Until cutover completes, the prior orchestrator
role (Elliot) still handles dispatch and queue triage. The dual-concur rule
and author-exclusion rule apply NOW regardless of cutover status.

---

## PRE-WORK (before any code change)

[ ] P1. Architecture confirmed
    Command: head -10 ARCHITECTURE.md
    Paste verbatim. Confirms file exists and is current.

[ ] P2. Directive counter confirmed
    Follow SKILLS/SKILL_supabase_query.md Step 2.
    Paste verbatim: current directive number.

---

## DURING BUILD

[ ] B1. Only specified files modified
    Command: git diff --name-only
    Paste verbatim.
    If any unlisted file appears: stop. Report to CEO.

[ ] B2. No deprecated vendors introduced
    Follow SKILLS/SKILL_deprecated_check.md all steps.
    Paste all 7 grep outputs verbatim.
    Files modified in this PR must show zero hits.

---

## BEFORE REPORTING COMPLETE

[ ] C1. Pytest baseline holds
    Command: pytest tests/ -q 2>&1 | tail -5
    Paste verbatim.
    Required: 817 passed, 0 failed, 25 skipped or better.
    If any test fails: stop. Do not create PR.
    Report failing test name and traceback to CEO.

[ ] C2. PR rebased cleanly against main
    Command: git fetch origin && git rebase origin/main
    Paste verbatim. If conflicts: stop. Report to CEO.

[ ] C3. PR diff confirmed — no extra files
    Command: gh pr view [N] --json files \
             --jq ".files[].path"
    Paste verbatim. Must exactly match B1 output.

[ ] C4. PR URL
    Paste full GitHub PR URL. No shortlinks.

[ ] C5. Gatekeeper verdict obtained (GOV-PHASE3)
    Command: scripts/check_claim.py --help to see flags.
    Run check_claim.py with the directive's callsign,
    directive_id, claim_text, evidence (raw verification
    output with '$ ' prefix), target_files, and the four
    store_writes (manual / ceo_memory / cis_directive_metrics
    / drive_mirror — only those that apply to this directive).
    Paste verbatim: verdict line + the governance_events row
    inserted (callsign, event_type, directive_id, allow,
    reasons).
    Required: allow=true. If allow=false, address the
    deny_reasons and re-run the gate before pasting any
    completion claim. Deny verdict triggers a TG alert
    automatically — do not suppress it.

---

## THREE-STORE COMPLETION
(mandatory for save-trigger directives only)

[ ] S1. Google Drive Manual updated (LAW XV)
    Paste: exact heading of section updated.
    Paste: first complete sentence of updated content.

[ ] S2. Supabase ceo_memory written
    Follow SKILLS/SKILL_supabase_query.md Step 3.
    Paste: key name written + INSERT confirmation verbatim.

[ ] S3. cis_directive_metrics written
    Follow SKILLS/SKILL_supabase_query.md Step 4.
    Paste: inserted row verbatim.

---

Elliottbot pastes this full checklist — every item,
every evidence block — before reporting any directive
complete. Partial checklists are rejected. The checklist
is the completion. Not a formality after it.
