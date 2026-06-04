#!/usr/bin/env bash
# concurrency_cap_live_proof.sh
#
# LIVE enforcement proof for gate_roadmap component concurrency_cap
# (phase 0_foundation). KEI ref: orion-concurrency-cap-live-proof.
#
# Proves the merged+enabled concurrency cap (PR #1433,
# ceo:decision:concurrency_cap_2026-06-04) actually ENFORCES — not asserted,
# RUN: the production reservation Lua (src/dispatcher/concurrency_cap.py:
# ACQUIRE_LUA / RELEASE_LUA) executed against the LIVE Redis, with the
# production caps (N_TOTAL/GATED/DELIB_CAP/REVIEW_CAP/WORKER_CAP).
#
# trg_01 Check A pins gate_proof_runs.run_cmd to EXACTLY:
#     bash scripts/proof_bar/concurrency_cap_live_proof.sh
# so a pytest/mock run_cmd is disqualified. Check B requires the
# CONCURRENCY_CAP_PROOF tokens below — each emitted ONLY after its real
# assertion passes.
#
# ISOLATION (safety): the enforcement assertions run the production Lua + caps
# against the live Redis but on an ISOLATED key namespace
# (agent:concurrency:proof:*) with namespaced test callsigns, so the live
# dispatcher counter (agent:concurrency:holders) is never touched and no real
# fleet spawn is ever refused. The reservation MATH and the Lua are production;
# only the key names differ. Proof keys are deleted on exit (clean to baseline).
#
# WHAT IT PROVES:
#   - the 2 deliberators are reserved (both acquire),
#   - the 2 reviewers co-reside (both acquire alongside),
#   - the gated ceiling holds: total == GATED (5); the overflow acquire is
#     REFUSED at N=6 (the load-bearing negative),
#   - no role starvation: a worker acquiring first cannot block the 2+2 pairs,
#   - measured worst-case peak RSS+swap stays under the RAM ceiling.
#
# Exit 0 = every assertion passed. Exit 2 = an assertion failed. Exit 3 = env.
#
# ref: orion-concurrency-cap-live-proof.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export CC_REPO_ROOT="$REPO_ROOT"
ENV_FILE="${AGENCY_OS_ENV_FILE:-/home/elliotbot/.config/agency-os/.env}"

echo "=========================================================================="
echo "PROOF: concurrency_cap  (LIVE enforcement — production Lua vs live Redis)"
echo "Generated: $(date -u +%FT%TZ)   Host: $(hostname)"
echo "=========================================================================="

[[ -f "$ENV_FILE" ]] || { echo "ERROR: env file missing $ENV_FILE" >&2; exit 3; }
set -a; # shellcheck disable=SC1090
. "$ENV_FILE"; set +a
[[ -n "${REDIS_URL:-}" ]] || { echo "ERROR: REDIS_URL not set" >&2; exit 3; }

# ── STATIC: cap wired into the live dispatcher + caps partition GATED ────────
echo "─── STATIC: cap wired into dispatcher + caps partition the band ─────────"
grep -q "ConcurrencyGate" "${REPO_ROOT}/src/dispatcher/main.py" 2>/dev/null \
  || { echo "ERROR: ConcurrencyGate not wired into src/dispatcher/main.py" >&2; exit 2; }
echo "  ConcurrencyGate wired into src/dispatcher/main.py"
echo "CONCURRENCY_CAP_PROOF: wiring OK"
echo

# ── LIVE ENFORCEMENT: production Lua + caps vs live Redis (isolated keys) ────
echo "─── LIVE ENFORCEMENT: acquire/refuse/coreside against live Redis ───────"
python3 - <<'PY'
import os, sys, time
sys.path.insert(0, os.environ["CC_REPO_ROOT"])
import redis
from src.dispatcher import concurrency_cap as cc

r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
PH, PR = "agent:concurrency:proof:holders", "agent:concurrency:proof:roles"
CAPS = {"deliberator": cc.DELIB_CAP, "reviewer": cc.REVIEW_CAP, "worker": cc.WORKER_CAP}
TTL = 60

def reset():
    r.delete(PH, PR)

def acq(cs, role):
    return int(r.eval(cc.ACQUIRE_LUA, 2, PH, PR, cs, role, CAPS[role], cc.GATED, int(time.time()), TTL))

def rel(cs):
    r.eval(cc.RELEASE_LUA, 2, PH, PR, cs)

def die(msg):
    reset(); print(f"CONCURRENCY_CAP_PROOF: FAIL — {msg}", file=sys.stderr); sys.exit(2)

print(f"  caps: N_TOTAL={cc.N_TOTAL} GATED={cc.GATED} "
      f"delib={cc.DELIB_CAP} review={cc.REVIEW_CAP} worker={cc.WORKER_CAP}")
if cc.DELIB_CAP + cc.REVIEW_CAP + cc.WORKER_CAP != cc.GATED:
    die("caps do not partition the gated band")

# ── Scenario A: ceiling + overflow refusal ──────────────────────────────────
reset()
if not (acq("proof_d1", "deliberator") and acq("proof_d2", "deliberator")):
    die("deliberators not reserved (both must acquire)")
print("  2 deliberators acquired (reserved band)")
print("CONCURRENCY_CAP_PROOF: deliberators_reserved OK")

if not (acq("proof_r1", "reviewer") and acq("proof_r2", "reviewer")):
    die("reviewers cannot co-reside")
print("  2 reviewers acquired alongside the 2 deliberators")
print("CONCURRENCY_CAP_PROOF: reviewers_coreside OK")

if acq("proof_w1", "worker") != 1:
    die("first worker should acquire the last gated slot")
held = r.zcard(PH)
if held != cc.GATED:
    die(f"gated band should hold exactly {cc.GATED}, holds {held}")
print(f"  gated band full: {held} holders (2 delib + 2 review + 1 worker)")
print("CONCURRENCY_CAP_PROOF: gated_ceiling_holds OK")

# The load-bearing NEGATIVE: a 6th acquire (2nd worker) at N=6 is REFUSED.
if acq("proof_w2", "worker") != 0:
    die("overflow acquire was GRANTED — cap does NOT hold at the ceiling")
if r.zcard(PH) != cc.GATED:
    die("refused acquire must not inflate the holder count")
print("  overflow worker REFUSED at the ceiling (total stays at gated)")
print("CONCURRENCY_CAP_PROOF: overflow_refused OK")

for cs in ("proof_d1", "proof_d2", "proof_r1", "proof_r2", "proof_w1"):
    rel(cs)
if r.zcard(PH) != 0:
    die("release did not return holders to baseline")
print("  all released → baseline (0 holders)")

# ── Scenario B: no role starvation (worker first cannot block the pairs) ─────
reset()
if acq("proof_w1", "worker") != 1:
    die("worker should acquire on a clean band")
# Workers are capped at WORKER_CAP, so they can NEVER occupy a stage-pair slot.
if not (acq("proof_d1", "deliberator") and acq("proof_d2", "deliberator")
        and acq("proof_r1", "reviewer") and acq("proof_r2", "reviewer")):
    die("a worker starved the deliberator/reviewer stage-pairs")
print("  worker-first did NOT starve the 2 deliberators + 2 reviewers")
print("CONCURRENCY_CAP_PROOF: deliberator_never_starved OK")

reset()
print("  proof keyspace cleaned")
print("CONCURRENCY_CAP_PROOF: baseline_restored OK")
PY
PYRC=$?
[[ "$PYRC" -eq 0 ]] || { echo "BACKSTOP: live enforcement assertions failed (rc=$PYRC)" >&2; exit "$PYRC"; }
echo

# ── RAM CEILING: measured worst-case peak RSS+swap under the RAM ceiling ─────
echo "─── RAM CEILING: measured peak RSS+swap under the ceiling ──────────────"
if python3 "${REPO_ROOT}/scripts/measure_session_rss.py" >/tmp/cc_ram_proof.txt 2>&1; then
    grep -E "PROOF GATE|under (physical RAM|RAM\+swap)|N_TOTAL=" /tmp/cc_ram_proof.txt | sed 's/^/  /'
    echo "CONCURRENCY_CAP_PROOF: ram_ceiling OK"
else
    cat /tmp/cc_ram_proof.txt >&2
    echo "CONCURRENCY_CAP_PROOF: FAIL — RAM ceiling proof (measure_session_rss.py) exited non-zero" >&2
    exit 2
fi
rm -f /tmp/cc_ram_proof.txt
echo

# ── VERDICT ─────────────────────────────────────────────────────────────────
echo "CONCURRENCY_CAP_PROOF: run_nonce=$(date -u +%Y%m%dT%H%M%S.%N)"
echo "CONCURRENCY_CAP_PROOF: ALL PASS"
exit 0
