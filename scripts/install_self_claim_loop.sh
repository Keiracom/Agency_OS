#!/usr/bin/env bash
# Install + enable the agent self-claim loop (KEI-92 / Linear KEI-130) as
# per-callsign systemd instances. Idempotent. Six callsigns: elliot, aiden,
# max, atlas, orion, scout. Each runs agent-self-claim-loop@.service with
# CALLSIGN=%i.
#
# Names the template unit explicitly so the KEI-108 anti-false-complete gate
# (grep for agent-self-claim-loop@.service in this file) matches.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE_SRC="$REPO_ROOT/infra/systemd/agents/agent-self-claim-loop@.service"
UNIT_DIR="$HOME/.config/systemd/user"
TEMPLATE_DST="$UNIT_DIR/agent-self-claim-loop@.service"

CALLSIGNS=("elliot" "aiden" "max" "atlas" "orion" "scout")

install -d -m 0755 "$UNIT_DIR"
install -m 0644 "$TEMPLATE_SRC" "$TEMPLATE_DST"

systemctl --user daemon-reload

for cs in "${CALLSIGNS[@]}"; do
  systemctl --user enable "agent-self-claim-loop@${cs}.service" >/dev/null
  systemctl --user restart "agent-self-claim-loop@${cs}.service"
  echo "[install] agent-self-claim-loop@${cs}.service installed + active"
done

echo "--- post-install state ---"
for cs in "${CALLSIGNS[@]}"; do
  systemctl --user is-active "agent-self-claim-loop@${cs}.service" || true
done
