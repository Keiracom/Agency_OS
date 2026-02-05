# Vercel MCP Server

MCP server for Vercel deployment platform.

## Installation

```bash
npm install
npm run build
```

## Configuration

Set environment variable:
- `VERCEL_TOKEN` - Vercel API token (required)

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
| `list_projects` | List all Vercel projects |
| `list_deployments` | List deployments for a project |
| `get_deployment` | Get deployment details |
| `get_logs` | Get build logs |
| `list_env_vars` | List environment variables |
| `create_deployment` | Trigger a new deployment |
| `promote_to_production` | Promote preview to production |

## MCP Config

Add to your MCP settings:

```json
{
  "mcpServers": {
    "vercel": {
      "command": "node",
      "args": ["/path/to/vercel-mcp/dist/index.js"],
      "env": {
        "VERCEL_TOKEN": "your-vercel-token"
      }
    }
  }
}
```
