#!/usr/bin/env bash
# docker_runtime_live_proof.sh
#
# LIVE proof for gate_roadmap component docker_runtime
# (id = ec883620-ee1c-454b-ba31-0263fd93aaa6, phase 4_infra).
#
# Performs a REAL `docker build` + `docker run` and asserts the results FROM
# the runtime — this is NOT a mock and NOT a pytest. Bound to the gate row as
# proof_gate_contract.cmd. trg_01 fn_verify_before_proven Check A pins
# gate_proof_runs.run_cmd to EXACTLY:
#     bash scripts/proof_bar/docker_runtime_live_proof.sh
# so any pytest/mock run_cmd fails Check A (cmd_mismatch) — the structural
# negative bar. A mock also cannot produce real `docker build`/`docker run`
# stdout, which is what the assertions below grep for.
#
# Emits each DOCKER_RUNTIME_PROOF token (the contract.expected_output_contains
# substrings) ONLY after its real assertion passes.
#
# Exit 0 = every assertion passed (the runtime works, unmocked).
# Exit 2 = a required assertion/token was missing (proof failed).
# Exit 3 = environment error (no docker / daemon unreachable).
#
# Footprint: builds FROM the locally-cached postgres:16-alpine base via a
# stdin Dockerfile with an empty context (no registry pull, one tiny layer);
# removes the throwaway image on exit. hello-world is also cached locally.
#
# ref: scout-docker-runtime-live-proof.

set -u

TAG="docker-runtime-proof:scout-$$"
BAKED="DOCKER_BUILD_LAYER_MARKER_a1b2c3"

cleanup() { docker rmi -f "$TAG" >/dev/null 2>&1 || true; }
trap cleanup EXIT

fail() { echo "DOCKER_RUNTIME_PROOF: FAIL — $1" >&2; exit "${2:-2}"; }

command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not on PATH" >&2; exit 3; }
docker info >/dev/null 2>&1 || { echo "ERROR: docker daemon unreachable" >&2; exit 3; }

# ── 1. host_user assertion (proof_gate prose: "succeeds as elliotbot") ───────
HOST_USER="$(id -un)"
[[ "$HOST_USER" == "elliotbot" ]] || fail "host_user=$HOST_USER != elliotbot"
echo "DOCKER_RUNTIME_PROOF: host_user=elliotbot OK"

# ── 2. real BUILD — build-time RUN bakes a marker file into a new layer ──────
BUILD_OUT="$(printf 'FROM postgres:16-alpine\nRUN echo %s > /proof_marker.txt\n' "$BAKED" \
            | docker build -t "$TAG" - 2>&1)" \
    || { echo "$BUILD_OUT"; fail "docker build failed" 2; }
echo "$BUILD_OUT" | tail -2
IMG_ID="$(docker images --no-trunc --format '{{.ID}}' "$TAG" 2>/dev/null)"
[[ -n "$IMG_ID" ]] || fail "built image not found after build"
echo "DOCKER_RUNTIME_PROOF: build OK image=$IMG_ID"

# ── 3. real RUN — assert baked marker + runtime exec token FROM container ────
RUN_OUT="$(docker run --rm "$TAG" sh -c 'cat /proof_marker.txt; echo RUNTIME_EXEC_TOKEN; uname -s' 2>&1)" \
    || { echo "$RUN_OUT"; fail "docker run failed" 2; }
echo "--- container stdout ---"
echo "$RUN_OUT"
echo "--- end container stdout ---"
echo "$RUN_OUT" | grep -qF "$BAKED"            || fail "baked build marker absent from container stdout"
echo "$RUN_OUT" | grep -qF "RUNTIME_EXEC_TOKEN" || fail "runtime exec token absent from container stdout"
echo "$RUN_OUT" | grep -qF "Linux"             || fail "uname -s != Linux from inside container"
echo "DOCKER_RUNTIME_PROOF: run-marker asserted-from-runtime OK"

# ── 4. hello-world (proof_gate prose: "docker run hello-world succeeds") ─────
HW_OUT="$(docker run --rm hello-world 2>&1)" \
    || { echo "$HW_OUT"; fail "hello-world run failed" 2; }
echo "$HW_OUT" | grep -qF "Hello from Docker!" || fail "hello-world greeting absent"
echo "DOCKER_RUNTIME_PROOF: hello-world OK"

# ── 5. uniqueness line (distinct run_output → distinct output_sha256 so the
#       UNIQUE(gate_roadmap_id, output_sha256) constraint never collides
#       between the aiden and max attestation runs) + final token ────────────
echo "DOCKER_RUNTIME_PROOF: run_nonce=$(date -u +%Y%m%dT%H%M%S.%N)"
echo "DOCKER_RUNTIME_PROOF: server_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null)"
echo "DOCKER_RUNTIME_PROOF: ALL PASS"
exit 0
