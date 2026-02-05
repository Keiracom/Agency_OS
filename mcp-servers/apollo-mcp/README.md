# Apollo MCP Server

MCP server for Apollo.io lead enrichment and prospecting API.

## Tools

| Tool | Description | Credits |
|------|-------------|---------|
| `search_people` | Search contacts by title, location, company | 1/result |
| `search_companies` | Search organizations | 1/result |
| `enrich_person` | Enrich by email | 1/match |
| `enrich_company` | Enrich by domain | 1/match |
| `get_credits` | Check account status | 0 |
| `bulk_enrich` | Bulk email enrichment | 1/match |

## Setup

```bash
npm install
npm run build
```

## Environment

```
APOLLO_API_KEY=your_api_key
```

## Usage with Claude Desktop

```json
{
  "mcpServers": {
    "apollo": {
      "command": "node",
      "args": ["/path/to/apollo-mcp/dist/index.js"],
      "env": {
        "APOLLO_API_KEY": "your_key"
      }
    }
  }
}
```

## Cost Tracking

All responses include metadata with `creditsUsed` for budget tracking.
