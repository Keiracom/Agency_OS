#!/usr/bin/env bash
# product_proof_enforcement_live_rejection.sh
#
# Live durable-gate rejection demonstrator. Bound to gate_roadmap
# id=8ccca6bc-6478-4f8e-a173-0500474d8b41 (product_proof_enforcement) as
# the proof_gate_contract.cmd value — running this script is what produces
# the contract-required run_output substrings:
#   - "proof_gate_contract Check A"
#   - "cmd_mismatch"
#   - "does not equal contract.cmd"
#
# Mechanism: invokes _live_rejection_probe.sql which sets up a transient
# gate_roadmap row with a known contract.cmd, inserts a non-matching
# binding_reviewer proof_run, then attempts UPDATE status='proven'.
# trg_01 fn_verify_before_proven Check A raises check_violation — the
# verbatim message contains all three required substrings. ROLLBACK
# discards every transient row.
#
# Exit code: this script exits 0 on a successful rejection demonstration
# (the trigger did its job). Exit 2 if the expected RAISE pattern was
# missing (proof failed). Exit 3 on environment errors.
#
# ref: atlas-proof-gate-trigger-fix Fix 1.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${DATABASE_URL:-}" ]]; then
    if [[ -f /home/elliotbot/.config/agency-os/.env ]]; then
        # shellcheck disable=SC1091
        source /home/elliotbot/.config/agency-os/.env
    fi
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "ERROR: DATABASE_URL is not set" >&2
    exit 3
fi

DSN="${DATABASE_URL//postgresql+asyncpg/postgresql}"

# Run the probe. psql exits non-zero when trg_01 raises — that's expected;
# we capture the output (stderr + stdout) and validate the RAISE pattern.
PROBE_OUT="$(psql "$DSN" -v ON_ERROR_STOP=0 -f "$SCRIPT_DIR/_live_rejection_probe.sql" 2>&1 || true)"

# Echo the verbatim probe output so attesters' run_output captures the RAISE.
echo "$PROBE_OUT"

REQUIRED_TOKENS=(
    "proof_gate_contract Check A"
    "cmd_mismatch"
    "does not equal contract.cmd"
)

missing=0
for token in "${REQUIRED_TOKENS[@]}"; do
    if ! echo "$PROBE_OUT" | grep -F -q -- "$token"; then
        echo "MISSING REQUIRED TOKEN: $token" >&2
        missing=1
    fi
done

if [[ "$missing" -ne 0 ]]; then
    exit 2
fi

exit 0
