# DataForSEO MCP Server

MCP server for DataForSEO SERP, keyword research, and SEO analytics.

## Tools

| Tool | Description | Est. Cost |
|------|-------------|-----------|
| `serp_google` | Google SERP results | $0.002/request |
| `keyword_data` | Search volume, CPC, competition | $0.05/keyword |
| `domain_analytics` | Domain SEO metrics | $0.01/request |
| `backlinks` | Backlink profile analysis | $0.02/request |
| `competitors` | Organic search competitors | $0.01/request |

## Setup

```bash
npm install
npm run build
```

## Environment

```
DATAFORSEO_LOGIN=your_email
DATAFORSEO_PASSWORD=your_password
```

## Usage with Claude Desktop

```json
{
  "mcpServers": {
    "dataforseo": {
      "command": "node",
      "args": ["/path/to/dataforseo-mcp/dist/index.js"],
      "env": {
        "DATAFORSEO_LOGIN": "your_email",
        "DATAFORSEO_PASSWORD": "your_password"
      }
    }
  }
}
```

## Features

- **SERP Analysis**: Organic results, featured snippets, SERP features
- **Keyword Research**: Volume, CPC, competition, trends
- **Backlink Profile**: Referring domains, anchors, link quality
- **Competitor Discovery**: Find competing domains by keyword overlap

## Cost Tracking

All responses include `estimatedCostUSD` and `estimatedCostAUD` in metadata for budget tracking.
