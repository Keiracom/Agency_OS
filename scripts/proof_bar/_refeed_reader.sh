#!/usr/bin/env bash
# Stand-in "agent" pane for the context_watchdog re-feed live proof.
# Presents a ❯ prompt (so wait_for_prompt detects it) and, per injected line,
# invokes _refeed_agent_stub.py (which records a tool_call_log row for real work).
#   $1 = test callsign   $2 = path to _refeed_agent_stub.py
set -u
source /home/elliotbot/.config/agency-os/.env 2>/dev/null
CS="$1"
STUB="$2"
while true; do
    printf '\n❯ '
    IFS= read -r line || break
    REFED_LINE="$line" TEST_CS="$CS" python3 "$STUB"
done
