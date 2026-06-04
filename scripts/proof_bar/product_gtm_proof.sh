#!/usr/bin/env bash
# product_gtm_proof.sh
#
# Proof for gate_roadmap component product_gtm
# (id = f3f42557-40f5-4602-8239-ca09fa1da9e3, phase 6_product).
#
# proof_gate prose: "1-pager + launch comms approved and ready".
#
# product_gtm is a DOCS/ARTIFACT-readiness gate, not a runtime service. This
# proof asserts the READY half — the launch kit artifact exists at the deployed
# (committed) repo_sha and contains the complete 1-pager + launch-comms
# structure. The APPROVED half is the Aiden+Max dual-attest itself (a human
# governance signal a script cannot assert). Interpretation surfaced to Elliot
# before the PR — same shape as the three_store_sync scope note.
#
# Bound as proof_gate_contract.cmd; trg_01 Check A pins run_cmd to EXACTLY:
#     bash scripts/proof_bar/product_gtm_proof.sh
# so a pytest/mock run_cmd fails Check A (cmd_mismatch) — the structural
# negative bar.
#
# Emits each PRODUCT_GTM_PROOF token only after its assertion passes.
# Exit 0 = ready. Exit 2 = a required section/artifact missing. Exit 3 = env error.
# ref: scout-product-gtm-proof.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || { echo "ERROR: cannot cd to repo root" >&2; exit 3; }

KIT="docs/launch/KEI-131_gtm_launch_kit.md"
fail() { echo "PRODUCT_GTM_PROOF: FAIL — $1" >&2; exit "${2:-2}"; }

[[ -f "$KIT" ]] || fail "launch kit artifact missing: $KIT" 2
[[ -s "$KIT" ]] || fail "launch kit artifact is empty: $KIT" 2

# ── 1. The 1-pager (positioning doc) with its load-bearing subsections ───────
grep -qF "## §1 — One-Pager (positioning doc)" "$KIT" || fail "§1 One-Pager section missing"
grep -qF "### Pricing"                          "$KIT" || fail "§1 Pricing subsection missing"
grep -qF "### Call-to-action"                   "$KIT" || fail "§1 Call-to-action subsection missing"
echo "PRODUCT_GTM_PROOF: one-pager complete OK"

# ── 2. Launch comms — email template + social posts ──────────────────────────
grep -qF "## §2 — Launch Email Template" "$KIT" || fail "§2 Launch Email Template missing"
grep -qF "## §3 — Social Launch Posts"   "$KIT" || fail "§3 Social Launch Posts missing"
echo "PRODUCT_GTM_PROOF: launch-comms complete OK"

# ── 3. repo_sha against deployed (committed) code ────────────────────────────
REPO_SHA="$(git rev-parse HEAD 2>/dev/null)"
[[ -n "$REPO_SHA" ]] || fail "could not resolve repo_sha" 3
# Confirm the artifact is committed at this sha (deployed, not a dirty work-tree).
git cat-file -e "HEAD:$KIT" 2>/dev/null || fail "launch kit not committed at HEAD ($KIT)" 2
echo "PRODUCT_GTM_PROOF: artifact committed repo_sha=$REPO_SHA OK"

# ── uniqueness line (distinct run_output → distinct output_sha256, so the
#    UNIQUE(gate_roadmap_id, output_sha256) never collides between the aiden
#    and max attestation runs) + final token ─────────────────────────────────
echo "PRODUCT_GTM_PROOF: run_nonce=$(date -u +%Y%m%dT%H%M%S.%N)"
echo "PRODUCT_GTM_PROOF: ALL PASS"
exit 0
