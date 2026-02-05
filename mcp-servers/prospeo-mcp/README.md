# Prospeo MCP Server

MCP server for Prospeo email finder and verification API.

## Tools

| Tool | Description | Credits |
|------|-------------|---------|
| `find_email` | Find email by name + domain | 1 |
| `verify_email` | Verify email deliverability | 1 |
| `domain_search` | Find all emails at domain | 10 |
| `linkedin_to_email` | LinkedIn profile to email | 3 |
| `get_credits` | Check credit balance | 0 |

## Setup

```bash
npm install
npm run build
```

## Environment

```
PROSPEO_API_KEY=your_api_key
```

## Usage with Claude Desktop

```json
{
  "mcpServers": {
    "prospeo": {
      "command": "node",
      "args": ["/path/to/prospeo-mcp/dist/index.js"],
      "env": {
        "PROSPEO_API_KEY": "your_key"
      }
    }
  }
}
```

## Cost Tracking

All responses include metadata with `creditsUsed` and `creditCost` for budget tracking.
