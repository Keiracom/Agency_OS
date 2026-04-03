---
name: callback-poller
description: Polls evo_flow_callbacks table every 60s. Processes completed/failed Prefect flow callbacks and notifies Dave via Telegram.
---

# Callback Poller

Runs as an OpenClaw cron job every 60 seconds.

## What it does
1. Queries evo_flow_callbacks WHERE consumed_at IS NULL (up to 5 rows)
2. Atomically claims each row (UPDATE ... WHERE consumed_at IS NULL RETURNING)
3. On status=completed: sends Telegram completion report to Dave
4. On status=failed/crashed: calls send_failure_alert() from failure_alert.py
5. Stale rows (consumed_at NULL > 24h): alerts Dave, marks consumed_by='elliottbot:stale-sweep'

## Usage
Run directly: python3 src/evo/callback_poller.py
Cron: registered via OpenClaw cron, fires every 60 seconds

## Environment
Requires: SUPABASE_URL, SUPABASE_SERVICE_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
All sourced from /home/elliotbot/.config/agency-os/.env
