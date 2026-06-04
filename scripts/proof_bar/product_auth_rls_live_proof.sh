#!/usr/bin/env bash
# product_auth_rls_live_proof.sh
#
# LIVE proof for gate_roadmap component product_auth_rls (phase 6_product).
#
# proof_gate prose: "real signup creates tenant; cross-tenant read returns zero
# rows (RLS proven)".
#
# Exercises the REAL auth/RLS stack against the live DB — NOT a mock, NOT pytest.
# Bound as proof_gate_contract.cmd; trg_01 Check A pins run_cmd to EXACTLY:
#     bash scripts/proof_bar/product_auth_rls_live_proof.sh
# so a pytest/mock run_cmd fails Check A (cmd_mismatch) — the structural
# negative bar.
#
# NON-VACUITY (the correctness crux for an RLS proof): the connection role
# (postgres) has bypassrls, so the isolation read is performed under
# `SET ROLE authenticated` — a role with NO bypass — with auth.uid() driven from
# request.jwt.claims. A POSITIVE CONTROL (userA sees >=1 of their OWN rows)
# proves the role can read at all, so a vacuous setup (RLS silently bypassed or
# permission-denied) FAILS the positive control rather than passing green.
#
# Assertions, ZERO production mutation (all fixtures ROLLED BACK):
#   1. signup-creates-tenant — inserting auth.users fires handle_new_user, which
#      creates the user + client (tenant) + owner membership (the real signup
#      path). Two distinct tenants are created.
#   2. positive-control — under `authenticated` as userA, userA sees their OWN
#      client_customers row (>=1). Vacuity guard.
#   3. cross-tenant-zero — same session, userA sees ZERO of tenant B's rows.
#
# Exit 0 = all assertions passed. Exit 2 = an assertion failed. Exit 3 = env error.
# ref: scout-product-auth-rls-proof.

set -u

if [[ -z "${DATABASE_URL:-}" ]]; then
    if [[ -f /home/elliotbot/.config/agency-os/.env ]]; then
        # shellcheck disable=SC1091
        source /home/elliotbot/.config/agency-os/.env
    fi
fi
[[ -n "${DATABASE_URL:-}" ]] || { echo "ERROR: DATABASE_URL not set" >&2; exit 3; }
DSN="${DATABASE_URL//postgresql+asyncpg/postgresql}"
fail() { echo "PRODUCT_AUTH_RLS_PROOF: FAIL — $1" >&2; exit "${2:-2}"; }

SQL_OUT="$(psql "$DSN" -X -v ON_ERROR_STOP=1 2>&1 <<'SQL'
BEGIN;
DO $$
DECLARE
    mk        text := 'rlsprobe_' || replace(gen_random_uuid()::text, '-', '');
    uidA      uuid := gen_random_uuid();
    uidB      uuid := gen_random_uuid();
    cidA      uuid;
    cidB      uuid;
    n_tenant  int;
    n_own     int;
    n_cross   int;
BEGIN
    -- 1. Real signup (handle_new_user trigger creates user + client + membership).
    INSERT INTO auth.users (id, email)
    VALUES (uidA, mk || '_A@probe.test'), (uidB, mk || '_B@probe.test');

    SELECT client_id INTO cidA FROM public.memberships WHERE user_id = uidA LIMIT 1;
    SELECT client_id INTO cidB FROM public.memberships WHERE user_id = uidB LIMIT 1;
    IF cidA IS NULL OR cidB IS NULL OR cidA = cidB THEN
        RAISE EXCEPTION 'signup did not create two distinct tenants (cidA=% cidB=%)', cidA, cidB;
    END IF;
    SELECT count(*) INTO n_tenant FROM public.clients WHERE id IN (cidA, cidB);
    IF n_tenant <> 2 THEN RAISE EXCEPTION 'expected 2 signup tenants, got %', n_tenant; END IF;
    RAISE NOTICE 'TOK signup-creates-tenant OK';

    -- one customer per tenant.
    INSERT INTO public.client_customers (client_id, company_name, source)
    VALUES (cidA, mk || '_custA', 'manual'), (cidB, mk || '_custB', 'manual');

    -- 2 + 3. Read AS userA under the authenticated role (RLS ENFORCED — no bypass).
    PERFORM set_config('request.jwt.claims', json_build_object('sub', uidA::text)::text, true);
    SET LOCAL ROLE authenticated;
    SELECT count(*) INTO n_own   FROM public.client_customers WHERE company_name = mk || '_custA';
    SELECT count(*) INTO n_cross FROM public.client_customers WHERE company_name = mk || '_custB';
    RESET ROLE;

    IF n_own < 1 THEN
        RAISE EXCEPTION 'positive-control FAIL: userA saw % own rows (vacuous/blocked read)', n_own;
    END IF;
    RAISE NOTICE 'TOK positive-control own-rows-visible OK (own=%)', n_own;

    IF n_cross <> 0 THEN
        RAISE EXCEPTION 'isolation FAIL: userA saw % cross-tenant (clientB) rows, expected 0', n_cross;
    END IF;
    RAISE NOTICE 'TOK cross-tenant-zero OK (cross=%)', n_cross;
END
$$;
ROLLBACK;
SQL
)"
RC=$?
echo "----- live auth/RLS proof (transaction rolled back) -----"
echo "$SQL_OUT"
echo "----- end -----"
[[ $RC -eq 0 ]] || fail "psql proof transaction failed (rc=$RC)" 2
echo "$SQL_OUT" | grep -qF "TOK signup-creates-tenant OK"          || fail "signup-creates-tenant assertion missing"
echo "PRODUCT_AUTH_RLS_PROOF: signup-creates-tenant OK"
echo "$SQL_OUT" | grep -qF "TOK positive-control own-rows-visible OK" || fail "positive-control assertion missing"
echo "PRODUCT_AUTH_RLS_PROOF: positive-control own-rows-visible OK"
echo "$SQL_OUT" | grep -qF "TOK cross-tenant-zero OK"             || fail "cross-tenant-zero assertion missing"
echo "PRODUCT_AUTH_RLS_PROOF: cross-tenant-zero OK"

echo "PRODUCT_AUTH_RLS_PROOF: run_nonce=$(date -u +%Y%m%dT%H%M%S.%N)"
echo "PRODUCT_AUTH_RLS_PROOF: ALL PASS"
exit 0
