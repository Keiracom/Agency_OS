#!/usr/bin/env bash
# env_schema_validate.sh — fail-fast guard for the 5 critical env vars
# (Agency_OS-9erxio P1).
#
# Registered FIRST in the SessionStart hook chain so a misconfigured agent
# environment surfaces with a clear, actionable error instead of failing
# obscurely several hooks later (or, worse, succeeding through the hook
# chain and then crashing inside Claude on the first MCP call).
#
# Critical-5 (per Elliot dispatch 2026-05-18):
#   1. SUPABASE_DB_URL  OR  DATABASE_URL   (postgres DSN — either name OK)
#   2. SLACK_BOT_TOKEN                     (inbound/outbound relay auth)
#   3. ANTHROPIC_API_KEY                   (Claude API for sub-agents)
#   4. OPENAI_API_KEY                      (Cognee embeddings + secondary models)
#   5. CALLSIGN                            (identity discipline — LAW XVII)
#
# Behaviour:
#   - Sources the canonical .env (path overridable via AGENCY_OS_ENV) if the
#     env isn't already populated. Many hook chains start with a near-empty
#     env; the .env file is the source of truth.
#   - If any critical var is unset OR empty, print a list of missing vars +
#     a remediation pointer to stderr, then exit 1. SessionStart treats a
#     non-zero exit as a hook failure surfaced to the user.
#   - Exit 0 silently when all 5 are present.
#
# Env (optional):
#   AGENCY_OS_ENV — path to the .env file (default $HOME/.config/agency-os/.env)
#   ENV_VALIDATE_DRY=1 — print which vars would be checked + exit 0 (test mode)
#   ENV_VALIDATE_SKIP_SOURCE=1 — don't auto-source .env (test mode)

set -u

# `set -u` is in effect — guard $HOME so a stripped-env caller (tests, some
# systemd contexts) doesn't trip "HOME: unbound variable".
AGENCY_OS_ENV="${AGENCY_OS_ENV:-${HOME:-/nonexistent}/.config/agency-os/.env}"

if [[ "${ENV_VALIDATE_DRY:-}" == "1" ]]; then
    cat <<'EOF'
env_schema_validate.sh — critical-5 vars:
  - DATABASE_URL or SUPABASE_DB_URL
  - SLACK_BOT_TOKEN
  - ANTHROPIC_API_KEY
  - OPENAI_API_KEY
  - CALLSIGN
EOF
    exit 0
fi

# Auto-load .env when the calling shell hasn't already exported the critical
# vars. SessionStart hooks tend to inherit a minimal env; the .env file is the
# canonical source of truth for the Vultr deploy.
if [[ "${ENV_VALIDATE_SKIP_SOURCE:-}" != "1" ]] \
    && [[ -r "$AGENCY_OS_ENV" ]] \
    && [[ -z "${SUPABASE_DB_URL:-}${DATABASE_URL:-}" \
        || -z "${SLACK_BOT_TOKEN:-}" \
        || -z "${ANTHROPIC_API_KEY:-}" \
        || -z "${OPENAI_API_KEY:-}" \
        || -z "${CALLSIGN:-}" ]]; then
    # shellcheck disable=SC1090
    set -a; source "$AGENCY_OS_ENV"; set +a
fi

missing=()

# (1) Database — accept either canonical name. CALLSIGN-validated workers all
# read DATABASE_URL; some legacy code paths still query SUPABASE_DB_URL.
if [[ -z "${SUPABASE_DB_URL:-}" && -z "${DATABASE_URL:-}" ]]; then
    missing+=("DATABASE_URL (or SUPABASE_DB_URL)")
fi

# (2) Slack relay token — without it tg + inbox watchers misfire silently.
if [[ -z "${SLACK_BOT_TOKEN:-}" ]]; then
    missing+=("SLACK_BOT_TOKEN")
fi

# (3) Anthropic — primary model auth.
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    missing+=("ANTHROPIC_API_KEY")
fi

# (4) OpenAI — embeddings + secondary models.
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    missing+=("OPENAI_API_KEY")
fi

# (5) Callsign — identity discipline. Worktrees that don't set CALLSIGN
# mis-tag posts as the relay default and corrupt the audit trail.
if [[ -z "${CALLSIGN:-}" ]]; then
    missing+=("CALLSIGN")
fi

if (( ${#missing[@]} > 0 )); then
    {
        echo "ERROR: env_schema_validate.sh — ${#missing[@]} critical env var(s) missing:"
        for v in "${missing[@]}"; do
            echo "  - $v"
        done
        echo ""
        echo "Remediation: populate $AGENCY_OS_ENV (or override AGENCY_OS_ENV)."
        echo "             The session is blocked until the above are set."
    } >&2
    exit 1
fi

exit 0
