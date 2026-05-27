#!/usr/bin/env bash
# Composer-output-never-reaches-agent-reasoning CI guard.
#
# Enforces the load-bearing hard constraint from ceo:atomization_architecture_v1:
#   "Composer output never reaches agent reasoning input"
#
# Composer (ceo:atomization_architecture_v1 component layer #4) renders atoms
# into USER-FACING output (chat replies, emails, voice prompts). MalRetriever
# (component layer #3) is the agent-reasoning input path. The architecture
# requires these paths to be ENFORCEMENTLY SEPARATE — Composer's
# ComposedOutput must NEVER end up inside an agent's prompt.
#
# WHY THE HARD CONSTRAINT EXISTS (per dispatch failure-mode mitigations):
# "Composer non-determinism breaks multi-agent reasoning (HARD CONSTRAINT)".
# Composer can be LLM-rendered prose; if it fed agent reasoning, the
# non-determinism would propagate and break multi-agent reasoning chains.
#
# DETECTION PATTERN (import-scope):
# Composer + ComposedOutput + compose_chat_reply may ONLY be imported by:
#   1. src/keiracom_system/atomization/composer.py itself
#   2. src/keiracom_system/atomization/__init__.py (re-export)
#   3. src/keiracom_system/endpoints/ (future Endpoint Translator + Dave-
#      facing endpoint switchover — Week 2-3 dispatch per design doc §1)
#   4. Test directories
#
# Anything else importing Composer is ipso facto routing user-facing output
# into a non-endpoint code path — almost certainly into agent reasoning.
#
# COMPLEMENTS:
# - The Composer's own type-level enforcement (ComposedOutput.text is str —
#   PR #1189 test_composer_output_is_user_facing_string_only). That covers
#   intra-module discipline; this guard covers cross-module discipline.
# - Boundary-matrix-v1 guards (PR #1169) — same enforcement-via-import-scope
#   pattern; lives in the same family.
# - A7 cache-discipline (PR #1173 CB-10) — same pattern.
# - Atom-store-discipline (PR #1185 Week 1) — same pattern.

set -euo pipefail

SCOPE="src/keiracom_system"

if [ ! -d "$SCOPE" ]; then
  echo "OK (composer-isolation): $SCOPE not present — guard inactive."
  exit 0
fi

# The Composer module may not be in main yet (PR #1189 Week 2 still in
# review). The guard is preemptive — inert until the file lands.
if [ ! -f "$SCOPE/atomization/composer.py" ]; then
  echo "OK (composer-isolation): Composer not yet in tree — guard inert until PR #1189 lands."
  exit 0
fi

# Pattern: any import that pulls Composer / ComposedOutput / compose_chat_reply
# from the atomization composer module. We match both 'from ... composer import'
# and 'from src.keiracom_system.atomization import Composer' forms.
PATTERN='^[[:space:]]*(from[[:space:]]+src\.keiracom_system\.atomization\.composer[[:space:]]+import|from[[:space:]]+src\.keiracom_system\.atomization[[:space:]]+import[[:space:]]+(Composer|ComposedOutput|compose_chat_reply|select_provenance_trail))'

raw=$(grep -rnE --include='*.py' "$PATTERN" "$SCOPE" 2>/dev/null || true)

# Exempt paths:
#  - composer.py itself (self-reference impossible but defensive)
#  - __init__.py re-export
#  - endpoints/ directory (where the legitimate consumers live)
hits=$(printf '%s\n' "$raw" \
  | grep -v -E '^src/keiracom_system/atomization/composer.py' \
  | grep -v -E '^src/keiracom_system/atomization/__init__.py' \
  | grep -v -E '^src/keiracom_system/endpoints/' \
  | grep -v -E '^[[:space:]]*$' || true)

if [ -n "$hits" ]; then
  echo "FAIL (composer-isolation): Composer / ComposedOutput / compose_chat_reply"
  echo "imported outside src/keiracom_system/endpoints/. This violates the"
  echo "ceo:atomization_architecture_v1 hard constraint:"
  echo ""
  echo "  \"Composer output never reaches agent reasoning input\""
  echo ""
  echo "If you need atoms for AGENT reasoning, use MalRetriever directly —"
  echo "it's component layer #3, the canonical agent-reasoning-input path."
  echo "Composer is component layer #4, endpoint-rendering only."
  echo ""
  echo "If this is a new endpoint module, move it under"
  echo "src/keiracom_system/endpoints/ (the canonical home for the Endpoint"
  echo "Translator + Dave-facing endpoint switchover work — Week 2-3 dispatch)."
  echo ""
  echo "Offending lines:"
  echo "$hits"
  exit 1
fi

echo "OK (composer-isolation): no Composer imports outside endpoints/."
exit 0
