---
name: context-warning
description: Injects context usage warnings at 40/50/60% thresholds
metadata: {"clawdbot":{"emoji":"⚠️","events":["message:received"]}}
---
# Context Warning Hook

Monitors context usage and injects warnings into messages at thresholds:
- 40%: 🟡 Self-alert, prioritize remaining work
- 50%: 🟠 Alert Dave, prepare session summary  
- 60%: 🔴 Save to Supabase NOW, recommend restart
