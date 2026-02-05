# Railway MCP Server

MCP server for Railway deployment platform.

## Installation

```bash
npm install
npm run build
```

## Configuration

Set environment variable:
- `RAILWAY_TOKEN` - Railway API token (required)

## Usage

```bash
npm start
```

Or for development:
```bash
npm run dev
```

## Tools

| Tool | Description |
|------|-------------|
| `list_projects` | List all Railway projects |
| `list_services` | List services in a project |
| `get_deployment_status` | Get current deployment status |
| `get_logs` | Get recent service logs |
| `list_variables` | List environment variables |
| `set_variable` | Set an environment variable |
| `redeploy` | Trigger a redeploy |
| `rollback` | Rollback to previous deployment |

## MCP Config

Add to your MCP settings:

```json
{
  "mcpServers": {
    "railway": {
      "command": "node",
      "args": ["/path/to/railway-mcp/dist/index.js"],
      "env": {
        "RAILWAY_TOKEN": "your-railway-token"
      }
    }
  }
}
```
