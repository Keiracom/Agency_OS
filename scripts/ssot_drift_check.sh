#!/usr/bin/env bash
# ssot_drift_check.sh — Layer 6 drift detector for SSOT-alignment.
#
# Purpose:
#   Detect when .claude/modules/_enrichment_path.md or _dead_references.md
#   drift from being bare pointers and start paraphrasing canonical state
#   from ARCHITECTURE.md. The bare-pointer shape was ratified 2026-05-07
#   (PR #603) after both bots auto-loaded stale prose ("T0 GMB → T1 ABN ...
#   T5 Leadmagic Mobile" + Direct mail as channel) and quoted it as truth.
#
# Mode: fail-WARN on first deploy. Exits 0 always; emits warning text to
#   stdout/stderr. Settings.json hook (SessionStart:clear) surfaces warning
#   to the agent before first prompt.
#
# Usage:
#   bash scripts/ssot_drift_check.sh
#   # or via settings.json hook on SessionStart:clear
#
# Author: AIDEN (Layer 6 of 2026-05-07 SSOT-alignment fix)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENRICHMENT_PATH="${REPO_ROOT}/.claude/modules/_enrichment_path.md"
DEAD_REFS_PATH="${REPO_ROOT}/.claude/modules/_dead_references.md"
ARCHITECTURE_PATH="${REPO_ROOT}/ARCHITECTURE.md"

WARNINGS=()

emit_warning() {
    WARNINGS+=("$1")
}

# ─── Check 1: _enrichment_path.md must be a bare pointer ────────────────────
# A bare pointer is short, contains "ARCHITECTURE.md", and does NOT contain
# pipeline tier names or flow descriptions.
if [[ -f "${ENRICHMENT_PATH}" ]]; then
    SIZE=$(wc -c < "${ENRICHMENT_PATH}")
    if (( SIZE > 400 )); then
        emit_warning "_enrichment_path.md is ${SIZE} bytes — bare pointer should be <400. Possible drift to paraphrase."
    fi
    if ! grep -q "ARCHITECTURE.md" "${ENRICHMENT_PATH}"; then
        emit_warning "_enrichment_path.md missing ARCHITECTURE.md pointer — file may have been overwritten."
    fi
    # Patterns that should NEVER appear in a bare-pointer module (they belong in ARCHITECTURE.md only):
    DRIFT_PATTERNS=(
        "T0 GMB"
        "T1 ABN"
        "T1.5"
        "T2.5"
        "T3 Leadmagic"
        "T5 Leadmagic"
        "FLOW A"
        "FLOW B"
        "asyncio.gather"
        "DataForSEO"
    )
    for pattern in "${DRIFT_PATTERNS[@]}"; do
        if grep -qF "${pattern}" "${ENRICHMENT_PATH}"; then
            emit_warning "_enrichment_path.md contains '${pattern}' — pipeline detail belongs in ARCHITECTURE.md only."
        fi
    done
else
    emit_warning "_enrichment_path.md missing at ${ENRICHMENT_PATH}"
fi

# ─── Check 2: _dead_references.md must be a bare pointer ────────────────────
if [[ -f "${DEAD_REFS_PATH}" ]]; then
    SIZE=$(wc -c < "${DEAD_REFS_PATH}")
    if (( SIZE > 400 )); then
        emit_warning "_dead_references.md is ${SIZE} bytes — bare pointer should be <400. Possible drift to deprecated-list paraphrase."
    fi
    if ! grep -q "ARCHITECTURE.md" "${DEAD_REFS_PATH}"; then
        emit_warning "_dead_references.md missing ARCHITECTURE.md pointer — file may have been overwritten."
    fi
    # Patterns that belong in ARCHITECTURE.md §3 only:
    DRIFT_VENDORS=(
        "Proxycurl"
        "Apollo (enrichment)"
        "Direct mail"
        "Kaspr"
        "Hunter.io"
        "ABNFirstDiscovery"
        "Lemlist"
        "SmartLead"
    )
    for vendor in "${DRIFT_VENDORS[@]}"; do
        if grep -qF "${vendor}" "${DEAD_REFS_PATH}"; then
            emit_warning "_dead_references.md contains '${vendor}' — deprecated-vendor list belongs in ARCHITECTURE.md §3 only."
        fi
    done
else
    emit_warning "_dead_references.md missing at ${DEAD_REFS_PATH}"
fi

# ─── Check 3: ARCHITECTURE.md must exist and have Last-validated header ────
if [[ ! -f "${ARCHITECTURE_PATH}" ]]; then
    emit_warning "ARCHITECTURE.md MISSING at ${ARCHITECTURE_PATH} — this is the canonical SSOT. STOP and report to Dave."
elif ! grep -q "^# Last validated:" "${ARCHITECTURE_PATH}"; then
    emit_warning "ARCHITECTURE.md missing 'Last validated' header — freshness gate not in place."
fi

# ─── Emit results ────────────────────────────────────────────────────────────
if (( ${#WARNINGS[@]} > 0 )); then
    echo "═══ SSOT DRIFT DETECTED (Layer 6 hook, fail-WARN) ═══" >&2
    echo "" >&2
    for w in "${WARNINGS[@]}"; do
        echo "  ⚠ ${w}" >&2
    done
    echo "" >&2
    echo "Action: cat ARCHITECTURE.md fresh (it is the canonical SSOT). Do NOT extract" >&2
    echo "from .claude/modules/*.md as truth — those are pointers only by design." >&2
    echo "If drift is real, open a governance PR to restore bare-pointer shape." >&2
    echo "═══════════════════════════════════════════════════" >&2
    exit 0  # WARN mode: do not block session
fi

echo "ssot_drift_check: clean (modules are bare pointers, ARCHITECTURE.md present)"
exit 0
