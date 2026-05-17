## MCP Bridge

All external service calls go through MCP bridge:

```bash
cd /home/elliotbot/clawd/skills/mcp-bridge && node scripts/mcp-bridge.js call <server> <tool> [args_json]
```

Available servers: supabase, redis, prefect, railway, prospeo, dataforseo, vercel, salesforge, vapi, telnyx, unipile, resend, memory

**Decision tree (LAW VI):**
1. Skill exists in skills/ -> use the skill
2. No skill, MCP available -> use MCP bridge
3. No skill, no MCP -> use exec as last resort, then write a skill

Never call external services ad-hoc. No credential hunting.
