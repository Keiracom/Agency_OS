# SKILL_pr_verify.md
# Run before creating any PR. All steps mandatory.
# Do not skip steps. Do not reorder steps.

STEP 1: confirm location
  pwd
  Expected: /home/elliotbot/clawd/Agency_OS

STEP 2: confirm only specified files modified
  git diff --name-only
  Paste verbatim. If unlisted file appears: stop.
  Report to CEO before continuing.

STEP 3: run pytest
  pytest tests/ -q 2>&1 | tail -5
  Paste verbatim.
  Required: 797 passed, 0 failed, 22 skipped or better.
  If any test fails: stop. Report test name + traceback.

STEP 4: rebase against main
  git fetch origin
  git rebase origin/main
  Paste verbatim. If conflicts: stop and report.

STEP 5: run deprecated check
  Follow SKILLS/SKILL_deprecated_check.md all 4 steps.
  Paste all output verbatim.

STEP 6: create PR
  git push origin [branch-name]
  gh pr create \
    --title "fix: [description] (#NNN)" \
    --body "Directive #NNN | Files: [list] | \
Tests: 797 passed | Deprecated: clean"
  Paste PR URL verbatim.

STEP 7: verify PR diff
  gh pr view [N] --json files --jq ".files[].path"
  Paste verbatim. Must match STEP 2 exactly.
  If it does not match: report to CEO before merge.
