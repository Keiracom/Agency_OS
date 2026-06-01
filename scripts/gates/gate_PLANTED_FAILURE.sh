#!/usr/bin/env bash
# gate_PLANTED_FAILURE.sh — DELIBERATE FAILURE GATE (gate zero proof).
#
# This gate ALWAYS exits 1. It exists to prove the verification-gate mechanism
# catches a failing gate end-to-end in CI. Remove from .gates/manifest.json
# once the proof is recorded in .gates/GATE_ZERO_PROOF.md.
#
# Do NOT add real content here. The whole point is a known-bad signal.

set -euo pipefail
GATE_ID="gate_PLANTED_FAILURE"
# shellcheck source=./_lib.sh
. "$(dirname "$0")/_lib.sh"

evidence='{"reason":"this gate is the deliberate-failure proof of the verification-gate mechanism; it must exit 1 unconditionally"}'
_emit_fail "$GATE_ID" "$evidence"
