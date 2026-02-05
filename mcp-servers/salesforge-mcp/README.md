# Salesforge MCP Server

MCP server for Salesforge email campaign management, including WarmForge (email warmup) and InfraForge (domain management).

## Installation

```bash
cd salesforge-mcp
pip install -e .
```

## Environment Variables

```bash
SALESFORGE_API_KEY=your_key_here
SALESFORGE_API_URL=https://api.salesforge.ai/public/v2
WARMFORGE_API_KEY=your_key_here
WARMFORGE_API_URL=https://api.warmforge.ai/public/v1
INFRAFORGE_API_KEY=your_key_here
INFRAFORGE_API_URL=https://api.infraforge.ai/public
```

## Tools

| Tool | Description |
|------|-------------|
| `list_campaigns()` | List all campaigns |
| `create_campaign(name, config)` | Create new campaign |
| `get_campaign_stats(campaign_id)` | Get campaign metrics |
| `add_leads(campaign_id, leads[])` | Add leads to campaign |
| `pause_campaign(campaign_id)` | Pause campaign |
| `resume_campaign(campaign_id)` | Resume campaign |
| `get_warmup_status()` | WarmForge mailbox status |
| `list_domains()` | InfraForge domains |

## Usage with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "salesforge": {
      "command": "salesforge-mcp",
      "env": {
        "SALESFORGE_API_KEY": "your_key"
      }
    }
  }
}
```
