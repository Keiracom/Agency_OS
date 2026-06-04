#!/usr/bin/env bash
# persona_bank_reasoning_headers_live_proof.sh
#
# LIVE proof for gate_roadmap component persona_bank_reasoning_headers
# (phase 2_chain). KEI ref: orion-persona-reasoning-headers.
#
# PROOF BOUNDARY (recorded on the component; attest against THIS):
#   proven = the persona CONTRACT specifies the 5 deliberation headers AND the
#   deterministic parser ENFORCES them (real negative test). Live-LLM EMISSION
#   confirmation is DEFERRED to a post-LLM-restore chain run — out of scope here
#   (LLM excluded). This is the provable layer with the chain offline.
#
# trg_01 Check A pins gate_proof_runs.run_cmd to EXACTLY:
#     bash scripts/proof_bar/persona_bank_reasoning_headers_live_proof.sh
# so a pytest/mock run_cmd is disqualified. Zero production mutation — reads the
# persona files + runs the real parser over in-memory fixtures.
#
# Exit 0 = every assertion passed. Exit 2 = an assertion failed. Exit 3 = env.
#
# ref: orion-persona-reasoning-headers.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export PR_REPO_ROOT="$REPO_ROOT"

echo "=========================================================================="
echo "PROOF: persona_bank_reasoning_headers  (5-header deliberation contract + parser)"
echo "Generated: $(date -u +%FT%TZ)   Host: $(hostname)"
echo "=========================================================================="

# ── STATIC: all 3 reviewer personas carry the 5-header schema ───────────────
echo "─── STATIC: personas/v1_chain/{nova,orion,atlas}.md carry the 5 headers ─"
miss=0
for p in nova orion atlas; do
    f="${REPO_ROOT}/personas/v1_chain/${p}.md"
    [[ -f "$f" ]] || { echo "ERROR: $f missing" >&2; exit 3; }
    for h in DECISION CHALLENGE TRADEOFFS REJECTED ATTRIBUTION; do
        grep -qE "^${h}:" "$f" || { echo "  MISSING ${h}: in ${p}.md"; miss=1; }
    done
    echo "  ${p}.md: all 5 headers present"
done
[[ "$miss" -eq 0 ]] || { echo "PERSONA_REASONING_PROOF: FAIL — a persona is missing a header" >&2; exit 2; }
echo "PERSONA_REASONING_PROOF: personas_carry_schema OK"
echo

# ── PARSER: real extractor over fixtures (positive + negative) ──────────────
echo "─── PARSER: deterministic extract (well-formed) + reject (incomplete) ──"
python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["PR_REPO_ROOT"])
from src.keiracom_system.chain.deliberation_headers import (
    REQUIRED_HEADERS, validate, is_valid, DeliberationFormatError,
)

def die(msg):
    print(f"PERSONA_REASONING_PROOF: FAIL — {msg}", file=sys.stderr); sys.exit(2)

well_formed = """[REVIEW:reject:atlas]
DELIBERATION:
DECISION: reject — the migration drops a column with live rows.
CHALLENGE: data-loss risk: prospects.contact_emails has 1.2M non-null rows.
TRADEOFFS: blocking now vs a follow-up — chose blocking; the drop is irreversible.
REJECTED: soft-deprecate-then-drop — still loses the data this release.
ATTRIBUTION: atlas (safety lens) — PR #1402, supabase/migrations/20260604_drop_col.sql
"""
h = validate(well_formed)
if not (h.decision and h.challenge and h.tradeoffs and h.rejected and h.attribution):
    die("well-formed block did not extract all five non-empty headers")
print(f"  extracted all 5 headers from a well-formed reviewer block "
      f"(decision={h.decision[:24]!r}...)")
print("PERSONA_REASONING_PROOF: parser_extracts_wellformed OK")

# NEGATIVE: drop each required header in turn — parser MUST reject every one.
for drop in REQUIRED_HEADERS:
    bad = "\n".join(l for l in well_formed.splitlines() if not l.startswith(f"{drop}:"))
    if is_valid(bad):
        die(f"parser ACCEPTED a block missing required header {drop} — negative bar open")
    try:
        validate(bad); die(f"validate() did not raise on missing {drop}")
    except DeliberationFormatError:
        pass
# NEGATIVE: empty value
empty = well_formed.replace(
    "REJECTED: soft-deprecate-then-drop — still loses the data this release.", "REJECTED:")
if is_valid(empty):
    die("parser ACCEPTED a block with an empty REJECTED header")
print("  parser REJECTED every incomplete block (5 missing-header cases + 1 empty)")
print("PERSONA_REASONING_PROOF: parser_rejects_incomplete OK")
PY
PYRC=$?
[[ "$PYRC" -eq 0 ]] || { echo "BACKSTOP: parser assertions failed (rc=$PYRC)" >&2; exit "$PYRC"; }
echo

echo "PERSONA_REASONING_PROOF: run_nonce=$(date -u +%Y%m%dT%H%M%S.%N)"
echo "PERSONA_REASONING_PROOF: ALL PASS"
exit 0
