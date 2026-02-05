#!/bin/bash
# Quick helper to log Elliot messages to shared Boardroom context
# Usage: ./log-to-boardroom.sh "message text"

MESSAGE="$1"
CHAT_ID="-5240078568"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "{\"ts\": \"$TS\", \"agent\": \"elliot\", \"sender\": \"Elliot\", \"text\": \"$MESSAGE\", \"chat_id\": $CHAT_ID}" >> /home/elliotbot/clawd/data/boardroom_chat.jsonl
