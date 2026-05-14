#!/usr/bin/env bash
# uninstall_bd_shim.sh — reverse install_bd_shim.sh.
#
# Removes the shim symlink at ~/.local/bin/bd and restores the real binary
# from bd-original. Idempotent.

set -euo pipefail

LOCAL_BIN="${LOCAL_BIN:-$HOME/.local/bin}"
BD="$LOCAL_BIN/bd"
BD_ORIGINAL="$LOCAL_BIN/bd-original"

if [[ ! -e "$BD_ORIGINAL" ]]; then
    echo "no bd-original to restore — shim wasn't installed?"
    exit 0
fi

# Remove the shim symlink if present.
if [[ -L "$BD" ]]; then
    rm "$BD"
fi

mv "$BD_ORIGINAL" "$BD"
echo "restored: $BD (real Beads binary)"
