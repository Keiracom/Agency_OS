# APPENDIX: machine-derived boot-dependency inventory (vault_secrets Phase 2)

Generated 80 `.env`-dependent `.service` units (`EnvironmentFile=…/agency-os/.env`).
Timers carry no `EnvironmentFile` — they activate backing services, so the conversion
target is the service set below. `vault_ord`=has a Vault systemd ordering dep today.

| unit | type | vault_ord | ExecStart (abbrev) |
|------|------|:---------:|--------------------|
| `agency-os-alert-budget-threshold.service` | timer | - | `scripts/alerts/budget_threshold_alert.py` |
| `agency-os-alert-daily-digest.service` | timer | - | `scripts/alerts/daily_digest.py` |
| `agency-os-alert-lead-quality.service` | timer | - | `scripts/alerts/lead_quality_anomaly.py` |
| `agency-os-alert-pipeline-failure.service` | timer | - | `scripts/alerts/pipeline_failure_alert.py` |
| `agency-os-alert-vendor-budget.service` | timer | - | `scripts/alerts/vendor_budget_alert.py` |
| `agency-os-artifact-freshness-monitor.service` | timer | - | `scripts/alerts/artifact_freshness_monitor.py` |
| `agency-os-coo.service` | svc | - | `scripts/coo_bot_service.py` |
| `agency-os-elliot-slack-listener.service` | svc | - | `scripts/elliot_socket_listener.py` |
| `agency-os-elliot-slack-mirror.service` | svc | - | `scripts/elliot_slack_mirror.py` |
| `agency-os-enforcer-slack-bot.service` | svc | - | `-m src.slack_bot.enforcer_bot` |
| `agency-os-hook-failure-monitor.service` | timer | - | `scripts/alerts/hook_failure_monitor.py` |
| `agency-os-llm-wiki-refresh.service` | timer | - | `scripts/compile_llm_wiki.py` |
| `agency-os-max-slack-listener.service` | svc | - | `scripts/coo_slack_listener.py` |
| `agency-os-phoenix-export.service` | svc | - | `scripts/phoenix_export_loop.py` |
| `agency-os-service-health-monitor.service` | timer | - | `scripts/alerts/service_health_monitor.py` |
| `agency-os-skill-pr-staleness-monitor.service` | timer | - | `scripts/alerts/skill_pr_staleness_monitor.py` |
| `agency-os-slack-central-listener.service` | svc | - | `-m src.slack_bot.central_listener` |
| `agent-memories-indexer.service` | svc | - | `scripts/orchestrator/agent_memories_indexer.py` |
| `agent-self-claim-loop@.service` | svc | - | `scripts/orchestrator/agent_self_claim_loop.sh` |
| `aiden-agent.service` | svc | - | `scripts/agent_keepalive.sh` |
| `aiden-nats-review-bridge.service` | svc | - | `scripts/orchestrator/nats_tmux_bridge.py` |
| `aiden-slack-mirror.service` | svc | - | `scripts/aiden_slack_mirror.py` |
| `aiden-telegram.service` | svc | - | `src/telegram_bot/chat_bot.py` |
| `atlas-agent.service` | svc | - | `scripts/agent_keepalive.sh` |
| `atlas-clone.service` | svc | - | `-m -e` |
| `atlas-nats-dispatch-bridge.service` | svc | - | `scripts/orchestrator/nats_tmux_bridge.py` |
| `bd_linear_sync.service` | timer | - | `scripts/bd_linear_sync_periodic.sh` |
| `ceo-memory-indexer.service` | svc | - | `scripts/orchestrator/ceo_memory_indexer.py` |
| `cognee.service` | svc | - | `scripts/cognee_kuzu_capped_launcher.py` |
| `completion-sync-worker.service` | svc | - | `scripts/orchestrator/completion_sync_worker.py` |
| `coo-slack-listener.service` | svc | - | `scripts/coo_slack_listener.py` |
| `deliberator-concur-router.service` | svc | - | `scripts/orchestrator/deliberator_concur_router.py` |
| `dispatcher.service` | svc | - | `src.dispatcher.main:app` |
| `drive-strategic-indexer.service` | timer | - | `scripts/orchestrator/drive_strategic_indexer.py` |
| `elliot-agent.service` | svc | - | `scripts/agent_keepalive.sh` |
| `elliot-compact-state-writer.service` | timer | - | `scripts/orchestrator/write_compact_state.py` |
| `elliot-context-watchdog.service` | timer | - | `scripts/orchestrator/context_watchdog.py` |
| `elliot-memories-indexer.service` | svc | - | `scripts/orchestrator/elliot_memories_indexer.py` |
| `elliot-nats-inbox-bridge.service` | svc | - | `scripts/orchestrator/nats_to_inbox_bridge.py` |
| `elliot-supervisor-wake.service` | timer | - | `scripts/orchestrator/supervisor_wake_publish.py` |
| `enforcer-bot.service` | svc | - | `src/telegram_bot/enforcer_bot.py` |
| `evo-callback-poller.service` | timer | - | `src/evo/callback_poller.py` |
| `evo-consumer.service` | svc | - | `src/evo/task_consumer.py` |
| `external-knowledge-ingester.service` | timer | - | `scripts/orchestrator/external_knowledge_ingester.py` |
| `fleet-liveness-checker.service` | timer | - | `scripts/orchestrator/fleet_liveness_checker.py` |
| `fleet-supervisor.service` | timer | - | `scripts/fleet_supervisor.py` |
| `git-commits-indexer.service` | svc | - | `scripts/orchestrator/git_commits_indexer.py` |
| `indexing-queue-worker.service` | svc | - | `scripts/indexing_queue_worker.py` |
| `keiracom-temporal-worker.service` | svc | - | `-m src.keiracom_system.temporal.worker` |
| `keiracom-v1-chain-consumer.service` | svc | - | `-m src.keiracom_system.chain.v1_chain_orchestrator` |
| `keiracom-work-loop-bridge.service` | svc | - | `-m src.keiracom_system.work_loop.bridge` |
| `keiracom-work-loop-consumer.service` | svc | - | `-m src.keiracom_system.work_loop` |
| `linear-oneway-push.service` | timer | - | `scripts/orchestrator/linear_oneway_push.py` |
| `linear-state-indexer.service` | svc | - | `scripts/orchestrator/linear_state_indexer.py` |
| `litellm.service` | svc | - | `/home/elliotbot/clawd/litellm-venv/bin/litellm \` |
| `max-agent.service` | svc | - | `scripts/agent_keepalive.sh` |
| `max-nats-review-bridge.service` | svc | - | `scripts/orchestrator/nats_tmux_bridge.py` |
| `max-telegram.service` | svc | - | `src/telegram_bot/chat_bot.py` |
| `memory-core-fact-probe.service` | timer | - | `scripts/orchestrator/memory_core_fact_probe.py` |
| `migration-apply-watcher.service` | timer | - | `scripts/orchestrator/migration_apply_watcher.py` |
| `nova-agent.service` | svc | - | `scripts/agent_keepalive.sh` |
| `nova-nats-dispatch-bridge.service` | svc | - | `scripts/orchestrator/nats_tmux_bridge.py` |
| `openai-cost-daily.service` | timer | - | `scripts/openai_cost_rollup.py` |
| `openai-cost-weekly.service` | timer | - | `scripts/openai_cost_weekly.py` |
| `orion-agent.service` | svc | - | `scripts/agent_keepalive.sh` |
| `orion-nats-dispatch-bridge.service` | svc | - | `scripts/orchestrator/nats_tmux_bridge.py` |
| `peer-event-ceo-relay.service` | svc | - | `scripts/orchestrator/peer_event_ceo_relay.py` |
| `postgres-dump-r2.service` | timer | - | `-m src.keiracom_system.backup.postgres_dump` |
| `reboot-test-c2xk.service` | svc | Y | `verify.py` |
| `reconcile_three_stores.service` | timer | - | `scripts/reconcile_three_stores.py` |
| `scout-agent.service` | svc | - | `scripts/agent_keepalive.sh` |
| `scout-nats-dispatch-bridge.service` | svc | - | `scripts/orchestrator/nats_tmux_bridge.py` |
| `scout-telegram.service` | svc | - | `src/telegram_bot/chat_bot.py` |
| `session-transcript-indexer.service` | svc | - | `scripts/orchestrator/session_transcript_indexer.py` |
| `sync-orchestrator.service` | svc | - | `scripts/orchestrator/sync_orchestrator.py` |
| `telegram-chat-bot.service` | svc | - | `src/telegram_bot/chat_bot.py` |
| `tool-call-log-indexer.service` | svc | - | `scripts/orchestrator/tool_call_log_indexer.py` |
| `weaviate-backup.service` | timer | - | `scripts/orchestrator/weaviate_backup.sh` |
| `weaviate-snapshot.service` | timer | - | `-m src.keiracom_system.backup.weaviate_snapshot` |
| `weaviate.service` | svc | - | `scripts/orchestrator/weaviate_capped.sh` |

**79 of 80 have NO Vault ordering dep** — each must gain
`After=/Requires=keiracom-vault-unseal.service` (+ `network-online.target`) on conversion.
Vault unseal unit on host: `keiracom-vault-unseal.service`.

Out of scope (already Vault-resolved, not wrapped): agent-spawn path
(`dispatcher.service` → `agent_cold_start`, `env -i`, precedent #1289).
