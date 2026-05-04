#!/usr/bin/env bash
# coo_inbox_cleanup.sh — Remove coo-inbox files older than 7 days.
# Run via cron: 0 3 * * * /home/elliotbot/clawd/Agency_OS/scripts/coo_inbox_cleanup.sh
set -euo pipefail

COO_INBOX="/tmp/coo-inbox"
MAX_AGE_DAYS=7

if [ ! -d "$COO_INBOX" ]; then
    exit 0
fi

count=$(find "$COO_INBOX" -name "*.json" -mtime +${MAX_AGE_DAYS} -type f | wc -l)
if [ "$count" -gt 0 ]; then
    find "$COO_INBOX" -name "*.json" -mtime +${MAX_AGE_DAYS} -type f -delete
    echo "[coo-cleanup] Removed $count files older than ${MAX_AGE_DAYS} days from $COO_INBOX"
fi
