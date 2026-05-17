#!/usr/bin/env bash
# Install LiteLLM governance gateway per Linear KEI-73 / bd KEI-100 T0.2.
# Idempotent. User systemd unit on 127.0.0.1:4000. Installs litellm.service.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="/home/elliotbot/clawd/litellm-venv"
CFG_SRC="$REPO_ROOT/infra/litellm/config.yaml"
CFG_DST="$HOME/.config/litellm/config.yaml"
UNIT_SRC="$REPO_ROOT/infra/litellm/litellm.service"
UNIT_DST="$HOME/.config/systemd/user/litellm.service"

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet 'litellm==1.85.0' anthropic openai google-generativeai 'psycopg[binary]'

install -d -m 0755 "$(dirname "$CFG_DST")" "$(dirname "$UNIT_DST")"
install -m 0644 "$CFG_SRC" "$CFG_DST"
install -m 0644 "$UNIT_SRC" "$UNIT_DST"

systemctl --user daemon-reload
systemctl --user enable litellm.service >/dev/null

echo "--- post-install state ---"
systemctl --user is-enabled litellm.service
systemd-analyze --user verify "$UNIT_DST"
"$VENV/bin/python" "$REPO_ROOT/scripts/litellm_boot_check.py" --mode pre || \
  echo "(boot pre-check exit non-zero — expected if ANTHROPIC_API_KEY missing/throttled)"
