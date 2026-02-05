# Hunter MCP Server

MCP server for Hunter.io email finder and verification API.

## Tools

| Tool | Description | Credits |
|------|-------------|---------|
| `domain_search` | Find all emails at domain | 1/request |
| `email_finder` | Find email by name + domain | 1/found |
| `email_verifier` | Verify email deliverability | 1 |
| `get_account` | Account info + credits | 0 |

## Setup

```bash
npm install
npm run build
```

## Environment

```
HUNTER_API_KEY=your_api_key
```

## Usage with Claude Desktop

```json
{
  "mcpServers": {
    "hunter": {
      "command": "node",
      "args": ["/path/to/hunter-mcp/dist/index.js"],
      "env": {
        "HUNTER_API_KEY": "your_key"
      }
    }
  }
}
```

## Features

- **Domain Search**: Filter by seniority (junior/senior/executive) and department
- **Email Verification**: Returns deliverability status, risk score, and MX records
- **Credit Tracking**: All responses include `creditsUsed` in metadata

## Cost Tracking

All responses include metadata with `creditsUsed` and `creditCost` for budget tracking.
