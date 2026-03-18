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
    Required: 797 passed, 0 failed, 22 skipped or better.
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
