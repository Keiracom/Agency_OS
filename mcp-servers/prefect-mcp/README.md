# Prefect MCP Server

MCP server for Prefect workflow orchestration.

## Installation

```bash
npm install
npm run build
```

## Configuration

Set environment variables:
- `PREFECT_API_URL` - Prefect API URL (default: http://localhost:4200/api)
- `PREFECT_API_KEY` - API key (optional for self-hosted)

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
| `list_flows` | List all Prefect flows |
| `list_deployments` | List all deployments |
| `get_flow_runs` | Get recent runs (optionally by flow name) |
| `trigger_run` | Trigger a flow run from deployment |
| `get_run_status` | Check status of a run |
| `get_failed_runs` | Get failures from last N hours |
| `cancel_run` | Cancel a running flow |

## MCP Config

Add to your MCP settings:

```json
{
  "mcpServers": {
    "prefect": {
      "command": "node",
      "args": ["/path/to/prefect-mcp/dist/index.js"],
      "env": {
        "PREFECT_API_URL": "https://prefect-server-production-f9b1.up.railway.app/api"
      }
    }
  }
}
```
