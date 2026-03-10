---
name: mcp-bridge
description: Bridge to MCP servers - call any tool from our 12 custom MCP servers (prefect, railway, prospeo, hunter, dataforseo, vercel, salesforge, vapi, telnyx, unipile, resend, memory). Use for enrichment, infrastructure, outreach, and memory operations.
---

# MCP Bridge

Connect Clawdbot to MCP (Model Context Protocol) servers via stdio transport.

## Quick Reference

```bash
# List available servers
node scripts/mcp-bridge.js servers

# List tools from a server  
node scripts/mcp-bridge.js tools <server>

# Call a tool
node scripts/mcp-bridge.js call <server> <tool> [args_json]
```

## Available Servers

| Server | Category | Description |
|--------|----------|-------------|
| `prefect` | Infrastructure | Workflow orchestration - flows, runs, deployments |
| `railway` | Infrastructure | Deployment platform - projects, services, logs |
| `vercel` | Infrastructure | Frontend deployments - projects, domains |
| `prospeo` | Enrichment | Email finder and verification |
| `hunter` | Enrichment | Domain search, email verification |
| `dataforseo` | Enrichment | SERP, keywords, backlinks |
| `salesforge` | Outreach | Email campaigns and sequences |
| `vapi` | Outreach | Voice AI - assistants, calls |
| `telnyx` | Outreach | SMS and voice communications |
| `unipile` | Outreach | LinkedIn automation |
| `resend` | Outreach | Transactional email |
| `memory` | Memory | Semantic search and persistence |

## Examples

```bash
# List Prefect flows
node scripts/mcp-bridge.js call prefect list_flows

# Get recent flow runs
node scripts/mcp-bridge.js call prefect get_flow_runs '{"limit": 5}'

# Railway projects
node scripts/mcp-bridge.js call railway list_projects

# Memory search
node scripts/mcp-bridge.js call memory search '{"query": "enrichment pricing"}'
```

## Tool Discovery

To see what tools a server provides:

```bash
node scripts/mcp-bridge.js tools prefect
```

Output shows tool names, descriptions, and parameters (required marked with *).

## Notes

- Servers are lazy-loaded on first call
- Env vars loaded from `~/.config/agency-os/.env`
- Server crashes are handled gracefully with error messages
