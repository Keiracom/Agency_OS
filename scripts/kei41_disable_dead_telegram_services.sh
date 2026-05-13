#!/usr/bin/env bash
# KEI-41 Phase 2 — disable dead Telegram systemd units + patch active relay-watcher ExecStart paths.
# Operator runs ONCE post-merge. Tracked + reversible (revert via systemctl enable / git revert).
#
# Per Dave directive ts ~1778675900: "systemd service disabling → in-PR (tracked, reviewable,
# reversible — not manual operator action)". The disable + patch logic lives in this script
# rather than being executed by CI (CI shouldn't modify systemd state).
#
# Background:
# - Dead Telegram services (inactive at Phase 1 audit): telegram-chat-bot, coo-bot,
#   aiden-telegram, max-telegram, scout-telegram, agency-os-coo, enforcer-bot.
# - Active relay-watcher services: their ExecStart pointed at
#   /home/elliotbot/clawd/Agency_OS/src/telegram_bot/relay_watcher.sh — moved to
#   /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/relay_watcher.sh.

set -euo pipefail

DEAD_UNITS=(
    telegram-chat-bot.service
    coo-bot.service
    aiden-telegram.service
    max-telegram.service
    scout-telegram.service
    agency-os-coo.service
    enforcer-bot.service
)

ACTIVE_RELAY_UNITS=(
    aiden-relay-watcher.service
    max-relay-watcher.service
    scout-relay-watcher.service
    orion-relay-watcher.service
    relay-watcher.service
)

UNIT_DIR="$HOME/.config/systemd/user"
OLD_PATH="src/telegram_bot/relay_watcher.sh"
NEW_PATH="scripts/orchestrator/relay_watcher.sh"

echo "KEI-41 Phase 2 systemd remediation — dry-run summary:"
echo ""
echo "Will DISABLE (already inactive — disable just removes wants links):"
for unit in "${DEAD_UNITS[@]}"; do
    if [ -f "$UNIT_DIR/$unit" ]; then
        state=$(systemctl --user is-enabled "$unit" 2>/dev/null || echo unknown)
        echo "  $unit (current: $state)"
    fi
done
echo ""
echo "Will PATCH ExecStart paths in (sed $OLD_PATH -> $NEW_PATH):"
for unit in "${ACTIVE_RELAY_UNITS[@]}"; do
    if [ -f "$UNIT_DIR/$unit" ] && grep -q "$OLD_PATH" "$UNIT_DIR/$unit"; then
        echo "  $unit (contains old path)"
    fi
done
echo ""

if [ "${1:-}" != "--execute" ]; then
    echo "Pass --execute to perform the changes."
    exit 0
fi

echo "Executing..."
for unit in "${DEAD_UNITS[@]}"; do
    if [ -f "$UNIT_DIR/$unit" ]; then
        systemctl --user disable "$unit" 2>&1 || echo "  (already disabled): $unit"
    fi
done

for unit in "${ACTIVE_RELAY_UNITS[@]}"; do
    if [ -f "$UNIT_DIR/$unit" ] && grep -q "$OLD_PATH" "$UNIT_DIR/$unit"; then
        cp "$UNIT_DIR/$unit" "$UNIT_DIR/$unit.kei41bak"
        sed -i "s|$OLD_PATH|$NEW_PATH|g" "$UNIT_DIR/$unit"
        echo "  patched $unit (backup at $unit.kei41bak)"
    fi
done

systemctl --user daemon-reload

echo ""
echo "Done. Restart active services for the path change to take effect:"
for unit in "${ACTIVE_RELAY_UNITS[@]}"; do
    if systemctl --user is-active "$unit" >/dev/null 2>&1; then
        echo "  systemctl --user restart $unit"
    fi
done
echo ""
echo "Reversal: revert this commit + restore .kei41bak files + daemon-reload + restart units."
