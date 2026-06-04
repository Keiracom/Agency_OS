#!/usr/bin/env bash
# install_vault_envwrap_shim.sh — install the stable ~/.local/bin/vault-envwrap
# shim that fronts the in-repo launcher (split-resilient: units reference the
# shim by a host path + ${AGENCY_OS_REPO}, never the repo tree directly).
#
# Idempotent. Host-side infra (admin-bypass acceptable per orchestrator-merge
# scope) — the launcher itself (scripts/vault_envwrap.py) is the reviewed repo code.
set -euo pipefail

BIN="$HOME/.local/bin"
SHIM="$BIN/vault-envwrap"
mkdir -p "$BIN"

cat > "$SHIM" <<'EOF'
#!/usr/bin/env bash
# vault-envwrap shim → in-repo launcher. Repo location via ${AGENCY_OS_REPO}
# (split-resilient: the repo-split re-points this one value, all units follow).
set -u
AGENCY_OS_REPO="${AGENCY_OS_REPO:-/home/elliotbot/clawd/Agency_OS}"
PY="$AGENCY_OS_REPO/.venv/bin/python3"
[[ -x "$PY" ]] || PY="$(command -v python3)"
exec "$PY" "$AGENCY_OS_REPO/scripts/vault_envwrap.py" "$@"
EOF

chmod +x "$SHIM"
echo "installed: $SHIM"
"$SHIM" --verify >/dev/null 2>&1 && echo "shim --verify: OK" || echo "shim --verify: (check VAULT env)"
