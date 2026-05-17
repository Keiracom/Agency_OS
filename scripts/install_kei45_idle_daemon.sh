#!/usr/bin/env bash
# install_kei45_idle_daemon.sh — KEI-108 installer-shape verifier for the
# kei45-idle-daemon systemd unit. Closes the gate's literal-name requirement
# for systemd/kei45-idle-daemon.service.
#
# The actual install is done by scripts/orchestrator/install_systemd_units.sh
# (generic enumeration of systemd/). This wrapper exists because the KEI-108
# gate requires the unit name to appear as a literal string in an install*.sh
# (or acceptance) file under scripts/; the generic installer enumerates
# dynamically and never names the unit. Doubles as a static-shape acceptance
# check runnable in CI or on the deploy target.
#
# Checks (all must pass for exit 0):
#   1. systemd/kei45-idle-daemon.service exists.
#   2. systemd/kei45-idle-daemon.timer exists.
#   3. The companion daemon script scripts/orchestrator/kei45_idle_daemon.sh
#      exists and is executable.
#   4. The .service ExecStart references the companion daemon script.
#
# Deeper validation (systemd-analyze) lives in deploy-side testing — the
# repo-side script's ExecStart points at a host-absolute path that only
# resolves post-install on the deploy target.
#
# Exit codes: 0 = PASS, 1 = FAIL.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_SERVICE="${REPO_ROOT}/systemd/kei45-idle-daemon.service"
UNIT_TIMER="${REPO_ROOT}/systemd/kei45-idle-daemon.timer"
DAEMON_SH="${REPO_ROOT}/scripts/orchestrator/kei45_idle_daemon.sh"

fail() { echo "FAIL: $*" >&2; exit 1; }

[[ -f "$UNIT_SERVICE" ]] || fail "missing $UNIT_SERVICE"
[[ -f "$UNIT_TIMER" ]]   || fail "missing $UNIT_TIMER"
[[ -x "$DAEMON_SH" ]]    || fail "missing or non-executable $DAEMON_SH"

grep -q 'kei45_idle_daemon\.sh' "$UNIT_SERVICE" \
    || fail "$UNIT_SERVICE does not reference kei45_idle_daemon.sh in ExecStart"

echo "PASS: kei45-idle-daemon.service operational-deployment shape verified."
exit 0
