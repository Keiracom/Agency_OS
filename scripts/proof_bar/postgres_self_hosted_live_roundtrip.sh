#!/usr/bin/env bash
# postgres_self_hosted_live_roundtrip.sh
#
# LIVE proof for gate_roadmap id=5cb0d0de-6aae-4e85-92e0-8fadddc1d7f3
# (component=postgres_self_hosted). Bound as the proof_gate_contract.cmd
# value — running this script against the self-hosted (Vultr VPS) Postgres
# produces the contract-required run_output substrings:
#   - "LIVE_HOST_CONFIRMED="        (host is the VPS, NOT *.supabase.co)
#   - "sentinel_readback_match=true" (durable write read back from live DB)
#   - "LIVE_ROUNDTRIP_OK"           (full connect->write->read->assert passed)
#
# Mechanism: connects to VULTR_POSTGRES_DSN (the self-hosted instance — NOT
# DATABASE_URL, which still points at Supabase), then runs
# _live_roundtrip_probe.sql which performs a REAL durable write of a unique
# sentinel token, reads it back, asserts equality from the live server, and
# deletes the sentinel (idempotent). This is a live R/W proof — not a mock,
# not pytest. A Supabase DSN is refused so the managed DB cannot masquerade
# as the self-hosted proof.
#
# Exit code: 0 on a verified live roundtrip; 2 if a required token is
# missing (proof failed); 3 on environment errors (no/invalid DSN).
#
# ref: NOVA postgres_self_hosted built->proven (gate 5cb0d0de).

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The self-hosted DSN must come from VULTR_POSTGRES_DSN. We deliberately do
# NOT fall back to DATABASE_URL — that is Supabase and would prove the wrong
# instance.
if [[ -z "${VULTR_POSTGRES_DSN:-}" ]]; then
    if [[ -f /home/elliotbot/.config/agency-os/.env ]]; then
        # shellcheck disable=SC1091
        source /home/elliotbot/.config/agency-os/.env
    fi
fi

if [[ -z "${VULTR_POSTGRES_DSN:-}" ]]; then
    echo "ERROR: VULTR_POSTGRES_DSN is not set — cannot prove the self-hosted Postgres" >&2
    exit 3
fi

DSN="${VULTR_POSTGRES_DSN//postgresql+asyncpg/postgresql}"

# Extract host; refuse Supabase so the proof can only pass against self-hosted.
HOST="$(python3 - "$DSN" <<'PY'
import sys, urllib.parse as u
print((u.urlparse(sys.argv[1]).hostname or ""))
PY
)"

if [[ -z "$HOST" ]]; then
    echo "ERROR: could not parse host from VULTR_POSTGRES_DSN" >&2
    exit 3
fi
if [[ "$HOST" == *supabase* ]]; then
    echo "ERROR: VULTR_POSTGRES_DSN host is Supabase ($HOST) — refusing; this proof requires the self-hosted instance" >&2
    exit 3
fi

echo "LIVE_HOST_CONFIRMED=$HOST"

# Unique sentinel token for this run (no Date/random in SQL — generated here).
TOKEN="nova-pgproof-$(date -u +%Y%m%dT%H%M%SZ)-$$-${RANDOM}"

PROBE_OUT="$(psql "$DSN" -v ON_ERROR_STOP=1 -v token="$TOKEN" \
    -f "$SCRIPT_DIR/_live_roundtrip_probe.sql" 2>&1)"
PROBE_RC=$?

echo "$PROBE_OUT"

if [[ "$PROBE_RC" -ne 0 ]]; then
    echo "ERROR: live probe exited non-zero ($PROBE_RC)" >&2
    exit 2
fi

if ! echo "$PROBE_OUT" | grep -F -q -- "sentinel_readback_match=true"; then
    echo "MISSING REQUIRED TOKEN: sentinel_readback_match=true" >&2
    exit 2
fi

# Gated on a real readback against the live host.
echo "LIVE_ROUNDTRIP_OK"
exit 0
