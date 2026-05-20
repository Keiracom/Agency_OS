#!/usr/bin/env bash
# install_agent_memories_indexer.sh — Agency_OS-lsyd install entry-point.
#
# KEI-108 CI-gate requirement: per-unit named install script anchors the
# literal unit name `agent-memories-indexer.service` for the grep gate.
#
# Companion to install_elliot_memories_indexer.sh — same Weaviate target
# class (AgentMemories), different source schema (public.agent_memories
# vs elliot_internal.memories).
#
# Usage:
#   scripts/install_agent_memories_indexer.sh

set -euo pipefail

UNIT="agent-memories-indexer"
exec /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/install_indexer.sh "${UNIT}"

# Anchored unit: agent-memories-indexer.service
