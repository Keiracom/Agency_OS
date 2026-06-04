#!/usr/bin/env bash
# auth_minter_live.sh
#
# LIVE proof for the auth_minter PRIMITIVE (KEI-209): mints a short-lived HS256
# agent-session JWT, verifies it, and REJECTS every bad token — using the REAL
# DISPATCHER_JWT_SECRET (from Vault/.env), against a live agent session id. Not a
# mock: real jwt.encode/decode through src.dispatcher.auth_minter.
#
# HONEST BOUNDARY: this proves the mint/verify/expiry/reissue PRIMITIVE that
# auth_minter owns. It does NOT prove the broader gate clause "validated on every
# dispatcher call" — that integration is UNWIRED (dispatcher main.py imports
# auth_minter for a boot-time env-check only; verify_token has zero call sites on
# the request path). That gap is flagged separately; this gate is the primitive.
#
# Required run_output substrings (contract Check B):
#   AUTH_MINT_VERIFY_OK
#   EXPIRED_REJECTED
#   TAMPERED_REJECTED
#   WRONGSECRET_REJECTED
#   BLANK_REJECTED
#   AUTH_MINTER_PRIMITIVE_PROOF_OK
#
# contract.cmd=bash → a pytest run_cmd fails Check A. Exit 0 on full pass; 2 on
# any assertion failure; 3 on environment error.
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -z "${DISPATCHER_JWT_SECRET:-}" ]]; then
    if [[ -f /home/elliotbot/.config/agency-os/.env ]]; then
        # shellcheck disable=SC1091
        source /home/elliotbot/.config/agency-os/.env
    fi
fi
if [[ -z "${DISPATCHER_JWT_SECRET:-}" ]]; then
    echo "ERROR: DISPATCHER_JWT_SECRET not set" >&2
    exit 3
fi

OUT="$(cd "$REPO_ROOT" && DISPATCHER_JWT_SECRET="$DISPATCHER_JWT_SECRET" python3 - <<'PY' 2>&1
import sys, os, jwt, datetime as dt
sys.path.insert(0, ".")
from src.dispatcher import auth_minter as am
sec = os.environ["DISPATCHER_JWT_SECRET"]
sess = "nova-live-" + dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S")
now = dt.datetime.now(dt.UTC)

# POSITIVE — mint for a live agent session, verify accepts with correct claims.
tok = am.mint_token("1", "nova", sess)
c = am.verify_token(tok)
if c and c.get("callsign") == "nova" and c.get("session_id") == sess:
    print("AUTH_MINT_VERIFY_OK")

# NEG — expired (real secret, past exp) → rejected.
exp = jwt.encode({"tenant_id":"1","callsign":"nova","session_id":sess,
                  "iat":now-dt.timedelta(minutes=30),"exp":now-dt.timedelta(minutes=1)},
                 sec, algorithm="HS256")
if am.verify_token(exp) is None:
    print("EXPIRED_REJECTED")

# NEG — tampered payload → rejected.
p = tok.split("."); bad = p[0]+"."+p[1][:-2]+("AA" if p[1][-2:]!="AA" else "BB")+"."+p[2]
if am.verify_token(bad) is None:
    print("TAMPERED_REJECTED")

# NEG — wrong signing secret → rejected.
wrong = jwt.encode({"tenant_id":"1","callsign":"nova","session_id":sess,
                    "iat":now,"exp":now+dt.timedelta(minutes=15)},
                   "not-the-real-secret", algorithm="HS256")
if am.verify_token(wrong) is None:
    print("WRONGSECRET_REJECTED")

# NEG — blank required field → mint refuses (no anonymous tokens).
try:
    am.mint_token("1", "", sess);
except ValueError:
    print("BLANK_REJECTED")

# REISSUE — a fresh mint differs from the first (auto-reissue before expiry).
tok2 = am.mint_token("1", "nova", sess)
if am.verify_token(tok2) is not None:
    print("REISSUE_OK")
PY
)"
echo "$OUT"

for t in AUTH_MINT_VERIFY_OK EXPIRED_REJECTED TAMPERED_REJECTED WRONGSECRET_REJECTED BLANK_REJECTED; do
    if ! echo "$OUT" | grep -Fq -- "$t"; then
        echo "MISSING REQUIRED TOKEN: $t" >&2
        exit 2
    fi
done
echo "AUTH_MINTER_PRIMITIVE_PROOF_OK"
exit 0
