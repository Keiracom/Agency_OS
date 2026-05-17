#!/usr/bin/env bash
# install_bd_shim.sh — KEI-22 install step.
#
# Renames the real bd binary to bd-original and installs scripts/bd as the
# new bd. Idempotent — safe to re-run. Reversible via uninstall_bd_shim.sh.
#
# Run once per agent host:
#   bash scripts/install_bd_shim.sh
#
# Dave directive 2026-05-14 (via Elliot): bd ready must return Supabase tasks
# for all agents.

set -euo pipefail

LOCAL_BIN="${LOCAL_BIN:-$HOME/.local/bin}"
BD="$LOCAL_BIN/bd"
BD_ORIGINAL="$LOCAL_BIN/bd-original"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHIM_SRC="$REPO_ROOT/scripts/bd"

if [[ ! -x "$SHIM_SRC" ]]; then
    echo "ERROR: shim source not executable: $SHIM_SRC" >&2
    exit 1
fi

if [[ ! -e "$BD" ]]; then
    echo "ERROR: no existing bd binary at $BD — nothing to wrap" >&2
    exit 1
fi

# If $BD is already our shim (symlink to repo scripts/bd OR file content
# matches), skip the rename — we're already installed.
if [[ -L "$BD" ]] && [[ "$(readlink -f "$BD")" == "$SHIM_SRC" ]]; then
    echo "shim already installed (symlink to $SHIM_SRC) — nothing to do"
    exit 0
fi

# Move the real binary aside if we haven't already.
if [[ ! -e "$BD_ORIGINAL" ]]; then
    echo "preserving real bd → bd-original"
    mv "$BD" "$BD_ORIGINAL"
elif [[ -e "$BD" && ! -L "$BD" ]]; then
    # bd-original exists but bd is also a real file → backup conflict.
    echo "ERROR: both $BD and $BD_ORIGINAL exist as real files. Resolve manually." >&2
    exit 1
fi

# Install the shim as $BD via symlink (so repo updates apply immediately).
ln -sfn "$SHIM_SRC" "$BD"
chmod +x "$SHIM_SRC"

echo "installed: $BD → $SHIM_SRC"
echo "preserved: $BD_ORIGINAL"
echo ""
echo "Smoke:"
echo "  bd ready                  # → Supabase tasks (KEI-22 SSOT)"
echo "  bd linear sync --pull     # → falls through to bd-original"
