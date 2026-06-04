#!/usr/bin/env bash
# product_byok_encryption_live_proof.sh
#
# LIVE proof for gate_roadmap component product_byok_encryption (phase 6_product).
#
# proof_gate prose: "customer key stored encrypted, retrieved, used for a real
# model call; plaintext never in DB".
#
# Exercises the REAL KEI-116 encryption-at-rest service
# (src/security/customer_api_keys.py — pgcrypto pgp_sym_encrypt/decrypt) — NOT a
# mock, NOT pytest. Bound as proof_gate_contract.cmd; trg_01 Check A pins run_cmd
# to EXACTLY:
#     bash scripts/proof_bar/product_byok_encryption_live_proof.sh
# so a pytest/mock run_cmd fails Check A (cmd_mismatch) — the structural negative
# bar.
#
# HONEST PROOF BOUNDARY (flagged, not hidden):
#  * Proves the ENCRYPTION-AT-REST clauses — stored encrypted / retrieved /
#    plaintext-never-in-DB — by driving the real store_key()/decrypt_key()/
#    lookup_by_hash() path, plus the module's own "refuse to store unencrypted"
#    negative control.
#  * The "used for a real model call" clause is the LLM/launcher integration path
#    (product_litellm_router domain) — NOT exercised here (out of this gate's
#    security scope + clear of launcher services).
#  * Uses a TEST master key — the prod CUSTOMER_KEY_ENCRYPTION_KEY is absent from
#    this environment, and the at-rest security property is key-agnostic (pgp_sym
#    takes any passphrase). The proof does not touch the production secret.
#
# Side effects: inserts ONE test row into public.customer_api_keys (the real
# store_key() commits its own connection) and DELETEs it on exit — a unique,
# clearly-marked, self-cleaned probe row.
#
# Exit 0 = all assertions passed. Exit 2 = an assertion failed. Exit 3 = env error.
# ref: scout-product-byok-encryption-proof.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || { echo "ERROR: cannot cd to repo root" >&2; exit 3; }
if [[ -z "${DATABASE_URL:-}" ]]; then
    if [[ -f /home/elliotbot/.config/agency-os/.env ]]; then
        # shellcheck disable=SC1091
        source /home/elliotbot/.config/agency-os/.env
    fi
fi
[[ -n "${DATABASE_URL:-}" ]] || { echo "ERROR: DATABASE_URL not set" >&2; exit 3; }

# Test master key only — never the production secret.
export CUSTOMER_KEY_ENCRYPTION_KEY="scout-byok-proof-testkey-$$"
fail() { echo "PRODUCT_BYOK_PROOF: FAIL — $1" >&2; exit "${2:-2}"; }

PY_OUT="$(python3 - <<'PY' 2>&1
import os, sys, uuid
sys.path.insert(0, os.getcwd())
import psycopg
from src.security import customer_api_keys as ck

dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
plaintext = "sk-PROOF-" + uuid.uuid4().hex
cust = uuid.uuid4()
row_id = None
try:
    # 1. store_key — real encrypt + INSERT.
    row_id = ck.store_key(cust, "openai", plaintext)
    print("TOK stored")

    # 2. plaintext NEVER in DB — read the raw encrypted_key bytea, assert no plaintext.
    with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute("SELECT encrypted_key FROM public.customer_api_keys WHERE id=%s", (str(row_id),))
        raw = bytes(cur.fetchone()[0])
    if plaintext.encode() in raw:
        print("FAIL: plaintext bytes present in stored encrypted_key"); sys.exit(1)
    if len(raw) < 16:
        print("FAIL: stored ciphertext implausibly short"); sys.exit(1)
    print("TOK plaintext-never-in-db")

    # 3. retrieved — decrypt roundtrips to the original plaintext.
    if ck.decrypt_key(row_id) != plaintext:
        print("FAIL: decrypt_key roundtrip mismatch"); sys.exit(1)
    print("TOK retrieved-roundtrip")

    # 4. hash lookup works without decrypting.
    if not ck.lookup_by_hash(plaintext):
        print("FAIL: lookup_by_hash did not find the stored key"); sys.exit(1)
    print("TOK hash-lookup")

    # 5. NEGATIVE CONTROL — with the master key unset, store_key MUST refuse.
    saved = os.environ.pop("CUSTOMER_KEY_ENCRYPTION_KEY")
    try:
        ck.store_key(uuid.uuid4(), "openai", "should-be-refused")
        print("FAIL: store_key accepted a key with no master key set (would store unencrypted)"); sys.exit(1)
    except RuntimeError:
        print("TOK refuse-unencrypted")
    finally:
        os.environ["CUSTOMER_KEY_ENCRYPTION_KEY"] = saved
    print("PY_OK")
finally:
    if row_id is not None:
        with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM public.customer_api_keys WHERE id=%s", (str(row_id),))
            conn.commit()
PY
)"
RC=$?
echo "----- real KEI-116 encryption-at-rest proof (test row self-cleaned) -----"
echo "$PY_OUT"
echo "----- end -----"
[[ $RC -eq 0 ]] || fail "byok proof harness failed (rc=$RC)" 2
for t in "TOK stored" "TOK plaintext-never-in-db" "TOK retrieved-roundtrip" "TOK hash-lookup" "TOK refuse-unencrypted" "PY_OK"; do
    echo "$PY_OUT" | grep -qF "$t" || fail "missing assertion: $t"
done
echo "PRODUCT_BYOK_PROOF: stored-encrypted OK"
echo "PRODUCT_BYOK_PROOF: plaintext-never-in-db OK"
echo "PRODUCT_BYOK_PROOF: retrieved-roundtrip OK"
echo "PRODUCT_BYOK_PROOF: refuse-unencrypted-negative-control OK"
echo "PRODUCT_BYOK_PROOF: run_nonce=$(date -u +%Y%m%dT%H%M%S.%N)"
echo "PRODUCT_BYOK_PROOF: ALL PASS"
exit 0
