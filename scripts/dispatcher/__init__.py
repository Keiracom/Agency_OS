"""Phase A8 ephemeral-agent dispatcher package — PR #1140 §7 piece #1.

scripts/dispatcher/dispatcher_main.py is the per-callsign binary invoked by
Scout's systemd template (PR #1180) at `keiracom-dispatcher@<callsign>.service`.
The dispatcher watches /tmp/telegram-relay-<callsign>/inbox/, atomically
claims each file, composes a fresh A+B+C+D+E prompt via the composer
(src/relay/spawn_composer.py, Agency_OS-eh56), and either logs (Stage 1
DISPATCHER_MODE=noop) or spawns Claude Code (Stage 2 DISPATCHER_MODE=spawn).

bd: Agency_OS-8416
"""
