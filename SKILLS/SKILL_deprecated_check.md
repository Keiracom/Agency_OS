# SKILL_deprecated_check.md
# Run before any PR. Paste all output verbatim.
# A clean result for each grep: no output.

STEP 1: confirm location
  pwd
  Expected: /home/elliotbot/clawd/Agency_OS

STEP 2: run all 7 greps against src/
  grep -r "clay" src/ --include="*.py" -il
  grep -r "hunter" src/ --include="*.py" -il
  grep -r "kaspr" src/ --include="*.py" -il
  grep -r "proxycurl" src/ --include="*.py" -il
  grep -r "apollo" src/ --include="*.py" -il
  grep -r "apify" src/ --include="*.py" -il
  grep -r "webshare" src/ --include="*.py" -il

STEP 3: interpret
  Files modified in current PR showing any hit: FAIL.
  Stop and report to CEO before continuing.
  Files NOT modified in current PR: pre-existing debt.
  List them — they do not block the PR but must be tracked.

STEP 4: report format (mandatory)
  For each grep paste the exact command and full output.
  If output is empty write: "no output — CLEAN"
  Do not summarise. Paste verbatim.
