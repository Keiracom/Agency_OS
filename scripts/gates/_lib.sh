#!/usr/bin/env bash
# _lib.sh — common helpers for gate scripts.
#
# Each gate script sources this to get _emit_pass / _emit_fail / _emit_skip
# which print JSON to stdout in the canonical shape:
#   {"gate": "<id>", "status": "pass|fail|skipped", "evidence": {...}, "ts": "..."}
#
# Constraints (per Dave directive 2026-05-30):
#   - Pure subprocess: no agent state, no filesystem session, no Claude CLI.
#   - Env-driven only.
#   - Exit 0 on pass; 1 on fail; 2 on skip (config missing).
#   - JSON to stdout; human chatter to stderr.

set -euo pipefail

GATE_LIB_VERSION="1"

_now_iso() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# _emit_pass <gate_id> <evidence_json_object>
_emit_pass() {
    local gate_id="${1:-unknown}"
    local evidence="${2-}"; : "${evidence:={}}"  # bash treats ${2:-{}} as ${2:-{} + literal }
    printf '{"gate":"%s","status":"pass","evidence":%s,"ts":"%s"}\n' \
        "$gate_id" "$evidence" "$(_now_iso)"
    exit 0
}

# _emit_fail <gate_id> <evidence_json_object>
_emit_fail() {
    local gate_id="${1:-unknown}"
    local evidence="${2-}"; : "${evidence:={}}"  # bash treats ${2:-{}} as ${2:-{} + literal }
    printf '{"gate":"%s","status":"fail","evidence":%s,"ts":"%s"}\n' \
        "$gate_id" "$evidence" "$(_now_iso)"
    exit 1
}

# _emit_skip <gate_id> <reason>
# Exit 2 — distinct from pass (0) and fail (1). Treated as not-pass by
# phase-ready / rehearsal-ready checks.
_emit_skip() {
    local gate_id="${1:-unknown}"
    local reason="${2:-no reason}"
    printf '{"gate":"%s","status":"skipped","evidence":{"reason":%s},"ts":"%s"}\n' \
        "$gate_id" "$(_json_str "$reason")" "$(_now_iso)"
    exit 2
}

# _json_str <plain-text> → "<escaped-text>"
# Minimal JSON string escaper for inline use. Not full RFC 8259 but adequate
# for backslash + double-quote + newline. For richer payloads, gates should
# build the evidence object with jq.
_json_str() {
    local s="${1:-}"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    printf '"%s"' "$s"
}

# _require_env <var-name>... — _emit_skip if any are missing.
_require_env() {
    local gate_id="${GATE_ID:-unknown}"
    local missing=()
    for var in "$@"; do
        if [[ -z "${!var:-}" ]]; then
            missing+=("$var")
        fi
    done
    if ((${#missing[@]} > 0)); then
        _emit_skip "$gate_id" "missing required env: ${missing[*]}"
    fi
}
