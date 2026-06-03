#!/usr/bin/env bash
# weaviate_offsite_backup_live_proof.sh
#
# LIVE round-trip proof for gate_roadmap component weaviate_offsite_backup
# (phase 4_infra). KEI ref: orion-weaviate-offsite-r2.
#
# Closes the ratified HARD GATE (ceo:vultr_infrastructure_ratified:
# weaviate_snapshot offsite = Cloudflare R2, hard gate before ceo_memory
# decommission). The offsite pipeline existed (KEI-242) but was NEVER WIRED —
# 0 snapshots had ever reached R2, so there was NO offsite memory-store backup.
#
# trg_01 Check A pins gate_proof_runs.run_cmd to EXACTLY:
#     bash scripts/proof_bar/weaviate_offsite_backup_live_proof.sh
# so a pytest/mock run_cmd is disqualified. Check B requires the
# WEAVIATE_OFFSITE_PROOF tokens — each emitted only after its real assertion.
#
# REAL round-trip (no mocks): snapshot the live Weaviate data dir → upload to
# Cloudflare R2 (the production weaviate_snapshot module) → confirm the object
# lands in R2 → download it back → STRUCTURAL restore-verify (every collection
# survives with real object segments + schema; no on-host boot — Weaviate
# recovery is node-replacement, not a parallel boot). Plus the systemd timer
# wiring assertion and a negative test (the too-small-snapshot guard refuses).
#
# Exit 0 = every assertion passed. Exit 2 = an assertion failed. Exit 3 = env.
#
# ref: orion-weaviate-offsite-r2.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export CC_REPO_ROOT="$REPO_ROOT"
ENV_FILE="${AGENCY_OS_ENV_FILE:-/home/elliotbot/.config/agency-os/.env}"

echo "=========================================================================="
echo "PROOF: weaviate_offsite_backup  (snapshot → R2 → fetch-back → restore-verify)"
echo "Generated: $(date -u +%FT%TZ)   Host: $(hostname)"
echo "=========================================================================="

[[ -f "$ENV_FILE" ]] || { echo "ERROR: env file missing $ENV_FILE" >&2; exit 3; }
set -a; # shellcheck disable=SC1090
. "$ENV_FILE"; set +a
[[ -n "${R2_BACKUP_BUCKET:-}" ]] || { echo "ERROR: R2_BACKUP_BUCKET not set" >&2; exit 3; }

# ── STATIC: pipeline modules present ────────────────────────────────────────
echo "─── STATIC: offsite pipeline modules present ───────────────────────────"
for m in r2.py pipeline.py weaviate_snapshot.py restore_verify.py; do
    [[ -f "${REPO_ROOT}/src/keiracom_system/backup/${m}" ]] || { echo "ERROR: backup/${m} missing" >&2; exit 2; }
done
echo "  r2 / pipeline / weaviate_snapshot / restore_verify present"
echo "WEAVIATE_OFFSITE_PROOF: modules_present OK"
echo

# ── WIRING: the daily offsite snapshot timer is enabled ─────────────────────
echo "─── WIRING: weaviate-snapshot.timer enabled ───────────────────────────"
if systemctl --user is-enabled weaviate-snapshot.timer >/dev/null 2>&1; then
    NEXT=$(systemctl --user list-timers weaviate-snapshot.timer --no-legend 2>/dev/null | awk '{print $1, $2}')
    echo "  weaviate-snapshot.timer enabled (next: ${NEXT:-scheduled})"
    echo "WEAVIATE_OFFSITE_PROOF: timer_wired OK"
else
    echo "ERROR: weaviate-snapshot.timer not enabled — offsite backup not wired" >&2
    exit 2
fi
echo

# ── LIVE ROUND-TRIP: snapshot → R2 → fetch-back → structural verify ─────────
echo "─── LIVE ROUND-TRIP: real snapshot → R2 → fetch-back → restore-verify ──"
python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["CC_REPO_ROOT"])
from src.keiracom_system.backup import weaviate_snapshot, restore_verify
from src.keiracom_system.backup.r2 import R2Client
from src.keiracom_system.backup.pipeline import upload_and_prune

def die(msg):
    print(f"WEAVIATE_OFFSITE_PROOF: FAIL — {msg}", file=sys.stderr); sys.exit(2)

# 1. Real snapshot of the live Weaviate data dir → R2 upload (production path).
try:
    key = weaviate_snapshot.run()
except Exception as exc:  # noqa: BLE001
    die(f"weaviate_snapshot.run() raised: {exc}")
print(f"  snapshot uploaded to R2: {key}")
print("WEAVIATE_OFFSITE_PROOF: snapshot_uploaded_to_r2 OK")

# 2. Confirm the object actually landed in R2 (independent list).
r2 = R2Client()
keys = {o.key for o in r2.list_objects(os.environ.get("WEAVIATE_R2_PREFIX", "weaviate/"))}
if key not in keys:
    die(f"uploaded key {key} not found in R2 listing")
print(f"  R2 now holds {len(keys)} weaviate snapshot(s); uploaded key confirmed present")
print("WEAVIATE_OFFSITE_PROOF: r2_object_confirmed OK")

# 3. Fetch-back from R2 + STRUCTURAL restore-verify (downloads the latest key).
try:
    n_collections = restore_verify.run()
except Exception as exc:  # noqa: BLE001
    die(f"restore_verify.run() raised — snapshot not restorable: {exc}")
if n_collections < 1:
    die("restore_verify recovered 0 collections")
print(f"  fetched back from R2 + structurally verified: {n_collections} collections recoverable")
print("WEAVIATE_OFFSITE_PROOF: restore_verify_recoverable OK")

# 4. NEGATIVE: the pipeline guard must REFUSE a too-small (broken) snapshot,
#    so a half-written dump can never overwrite good backups.
import tempfile
with tempfile.NamedTemporaryFile(suffix=".tar.gz") as tiny:
    tiny.write(b"x"); tiny.flush()
    try:
        upload_and_prune(r2, tiny.name, prefix="weaviate-proof-neg/",
                         key_name="should-never-upload.tar.gz", keep_recent=7)
        die("too-small snapshot was NOT refused — broken-backup guard is open")
    except RuntimeError:
        pass  # expected — the guard raised
print("  too-small snapshot refused by the upload guard (expected)")
print("WEAVIATE_OFFSITE_PROOF: negative_small_snapshot_refused OK")
PY
PYRC=$?
[[ "$PYRC" -eq 0 ]] || { echo "BACKSTOP: round-trip assertions failed (rc=$PYRC)" >&2; exit "$PYRC"; }
echo

# ── VERDICT ─────────────────────────────────────────────────────────────────
echo "WEAVIATE_OFFSITE_PROOF: run_nonce=$(date -u +%Y%m%dT%H%M%S.%N)"
echo "WEAVIATE_OFFSITE_PROOF: ALL PASS"
exit 0
