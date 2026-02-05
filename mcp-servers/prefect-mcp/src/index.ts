#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const PREFECT_API_URL = process.env.PREFECT_API_URL || "http://localhost:4200/api";
const PREFECT_API_KEY = process.env.PREFECT_API_KEY;

async function prefectRequest(endpoint: string, method = "GET", body?: object) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (PREFECT_API_KEY) {
    headers["Authorization"] = `Bearer ${PREFECT_API_KEY}`;
  }

  const response = await fetch(`${PREFECT_API_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Prefect API error: ${response.status} - ${text}`);
  }

  return response.json();
}

const server = new Server(
  { name: "prefect-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "list_flows",
      description: "List all Prefect flows",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "list_deployments",
      description: "List all Prefect deployments",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "get_flow_runs",
      description: "Get recent flow runs, optionally filtered by flow name",
      inputSchema: {
        type: "object",
        properties: {
          flow_name: { type: "string", description: "Filter by flow name (optional)" },
          limit: { type: "number", description: "Max results (default 20)", default: 20 },
        },
      },
    },
    {
      name: "trigger_run",
      description: "Trigger a flow run from a deployment",
      inputSchema: {
        type: "object",
        properties: {
          deployment_id: { type: "string", description: "Deployment ID" },
          parameters: { type: "object", description: "Flow parameters (optional)" },
        },
        required: ["deployment_id"],
      },
    },
    {
      name: "get_run_status",
      description: "Get the status of a specific flow run",
      inputSchema: {
        type: "object",
        properties: {
          run_id: { type: "string", description: "Flow run ID" },
        },
        required: ["run_id"],
      },
    },
    {
      name: "get_failed_runs",
      description: "Get failed flow runs from the last N hours",
      inputSchema: {
        type: "object",
        properties: {
          hours: { type: "number", description: "Hours to look back (default 24)", default: 24 },
        },
      },
    },
    {
      name: "cancel_run",
      description: "Cancel a running flow",
      inputSchema: {
        type: "object",
        properties: {
          run_id: { type: "string", description: "Flow run ID to cancel" },
        },
        required: ["run_id"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "list_flows": {
        const flows = await prefectRequest("/flows/filter", "POST", {
          limit: 100,
          sort: "CREATED_DESC",
        });
        return {
          content: [{ type: "text", text: JSON.stringify(flows, null, 2) }],
        };
      }

      case "list_deployments": {
        const deployments = await prefectRequest("/deployments/filter", "POST", {
          limit: 100,
          sort: "CREATED_DESC",
        });
        return {
          content: [{ type: "text", text: JSON.stringify(deployments, null, 2) }],
        };
      }

      case "get_flow_runs": {
        const limit = (args?.limit as number) || 20;
        const flowName = args?.flow_name as string | undefined;

        const filter: Record<string, unknown> = {
          limit,
          sort: "START_TIME_DESC",
        };

        if (flowName) {
          // First get the flow ID
          const flows = await prefectRequest("/flows/filter", "POST", {
            flows: { name: { any_: [flowName] } },
          });
          if (flows.length > 0) {
            filter.flow_runs = { flow_id: { any_: [flows[0].id] } };
          }
        }

        const runs = await prefectRequest("/flow_runs/filter", "POST", filter);
        return {
          content: [{ type: "text", text: JSON.stringify(runs, null, 2) }],
        };
      }

      case "trigger_run": {
        const deploymentId = args?.deployment_id as string;
        const parameters = (args?.parameters as object) || {};

        const run = await prefectRequest(
          `/deployments/${deploymentId}/create_flow_run`,
          "POST",
          { parameters }
        );
        return {
          content: [{ type: "text", text: JSON.stringify(run, null, 2) }],
        };
      }

      case "get_run_status": {
        const runId = args?.run_id as string;
        const run = await prefectRequest(`/flow_runs/${runId}`);
        return {
          content: [{ type: "text", text: JSON.stringify(run, null, 2) }],
        };
      }

      case "get_failed_runs": {
        const hours = (args?.hours as number) || 24;
        const since = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

        const runs = await prefectRequest("/flow_runs/filter", "POST", {
          flow_runs: {
            state: { type: { any_: ["FAILED", "CRASHED", "CANCELLED"] } },
            start_time: { after_: since },
          },
          limit: 100,
          sort: "START_TIME_DESC",
        });
        return {
          content: [{ type: "text", text: JSON.stringify(runs, null, 2) }],
        };
      }

      case "cancel_run": {
        const runId = args?.run_id as string;
        await prefectRequest(`/flow_runs/${runId}/set_state`, "POST", {
          state: { type: "CANCELLING" },
        });
        return {
          content: [{ type: "text", text: `Flow run ${runId} cancellation requested` }],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Prefect MCP server running on stdio");
}

main().catch(console.error);
