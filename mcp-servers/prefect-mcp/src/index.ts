#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { config } from "dotenv";
import { resolve } from "path";
import { homedir } from "os";

config({ path: resolve(homedir(), ".config/agency-os/.env") });

const PREFECT_API_URL = process.env.PREFECT_API_URL || "http://localhost:4200/api";
const PREFECT_API_KEY = process.env.PREFECT_API_KEY || "";

async function apiRequest(endpoint: string, method = "GET", body?: object) {
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
    return { error: true, status_code: response.status, message: text };
  }

  try {
    return await response.json();
  } catch {
    const text = await response.text();
    return text ? { raw_response: text } : { success: true };
  }
}

const server = new Server(
  { name: "prefect-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "list_flows",
      description: "List all flows in Prefect",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Max number of flows to return (default 50)" },
          offset: { type: "number", description: "Offset for pagination" },
          name_like: { type: "string", description: "Filter flows by name pattern" },
        },
      },
    },
    {
      name: "get_flow",
      description: "Get details of a specific flow",
      inputSchema: {
        type: "object",
        properties: {
          flow_id: { type: "string", description: "Prefect flow ID" },
        },
        required: ["flow_id"],
      },
    },
    {
      name: "get_flow_runs",
      description: "Get flow runs, optionally filtered by flow",
      inputSchema: {
        type: "object",
        properties: {
          flow_id: { type: "string", description: "Filter by flow ID" },
          limit: { type: "number", description: "Max number of runs to return (default 25)" },
          offset: { type: "number", description: "Offset for pagination" },
          state_type: { type: "string", description: "Filter by state type (COMPLETED, FAILED, RUNNING, PENDING, CANCELLED, CRASHED)" },
        },
      },
    },
    {
      name: "get_flow_run",
      description: "Get details of a specific flow run",
      inputSchema: {
        type: "object",
        properties: {
          flow_run_id: { type: "string", description: "Prefect flow run ID" },
        },
        required: ["flow_run_id"],
      },
    },
    {
      name: "list_deployments",
      description: "List all deployments",
      inputSchema: {
        type: "object",
        properties: {
          flow_id: { type: "string", description: "Filter by flow ID" },
          limit: { type: "number", description: "Max number of deployments to return (default 50)" },
          offset: { type: "number", description: "Offset for pagination" },
        },
      },
    },
    {
      name: "get_deployment",
      description: "Get details of a specific deployment",
      inputSchema: {
        type: "object",
        properties: {
          deployment_id: { type: "string", description: "Prefect deployment ID" },
        },
        required: ["deployment_id"],
      },
    },
    {
      name: "trigger_deployment",
      description: "Trigger a deployment to create a new flow run",
      inputSchema: {
        type: "object",
        properties: {
          deployment_id: { type: "string", description: "Prefect deployment ID" },
          parameters: { type: "object", description: "Parameters to pass to the flow" },
          name: { type: "string", description: "Name for the flow run" },
          idempotency_key: { type: "string", description: "Idempotency key to prevent duplicate runs" },
        },
        required: ["deployment_id"],
      },
    },
    {
      name: "get_deployment_status",
      description: "Get the status and health of a deployment",
      inputSchema: {
        type: "object",
        properties: {
          deployment_id: { type: "string", description: "Prefect deployment ID" },
        },
        required: ["deployment_id"],
      },
    },
    {
      name: "pause_deployment",
      description: "Pause a deployment (stops new runs from being scheduled)",
      inputSchema: {
        type: "object",
        properties: {
          deployment_id: { type: "string", description: "Prefect deployment ID" },
        },
        required: ["deployment_id"],
      },
    },
    {
      name: "resume_deployment",
      description: "Resume a paused deployment",
      inputSchema: {
        type: "object",
        properties: {
          deployment_id: { type: "string", description: "Prefect deployment ID" },
        },
        required: ["deployment_id"],
      },
    },
    {
      name: "cancel_flow_run",
      description: "Cancel a running flow run",
      inputSchema: {
        type: "object",
        properties: {
          flow_run_id: { type: "string", description: "Prefect flow run ID" },
        },
        required: ["flow_run_id"],
      },
    },
    {
      name: "list_work_pools",
      description: "List all work pools",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Max number of pools to return (default 50)" },
          offset: { type: "number", description: "Offset for pagination" },
        },
      },
    },
    {
      name: "get_work_pool",
      description: "Get details of a specific work pool",
      inputSchema: {
        type: "object",
        properties: {
          work_pool_name: { type: "string", description: "Name of the work pool" },
        },
        required: ["work_pool_name"],
      },
    },
    {
      name: "list_task_runs",
      description: "List task runs for a flow run",
      inputSchema: {
        type: "object",
        properties: {
          flow_run_id: { type: "string", description: "Filter by flow run ID" },
          limit: { type: "number", description: "Max number of task runs (default 50)" },
        },
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "list_flows": {
        const limit = (args?.limit as number) || 50;
        const offset = (args?.offset as number) || 0;
        const body: Record<string, unknown> = {
          limit,
          offset,
          sort: "CREATED_DESC",
        };
        if (args?.name_like) {
          body.flows = { name: { like_: args.name_like } };
        }
        const result = await apiRequest("/flows/filter", "POST", body);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_flow": {
        const result = await apiRequest(`/flows/${args?.flow_id}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_flow_runs": {
        const limit = (args?.limit as number) || 25;
        const offset = (args?.offset as number) || 0;
        const body: Record<string, unknown> = {
          limit,
          offset,
          sort: "START_TIME_DESC",
        };
        const flowRuns: Record<string, unknown> = {};
        if (args?.flow_id) {
          body.flows = { id: { any_: [args.flow_id] } };
        }
        if (args?.state_type) {
          flowRuns.state = { type: { any_: [args.state_type] } };
        }
        if (Object.keys(flowRuns).length > 0) {
          body.flow_runs = flowRuns;
        }
        const result = await apiRequest("/flow_runs/filter", "POST", body);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_flow_run": {
        const result = await apiRequest(`/flow_runs/${args?.flow_run_id}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_deployments": {
        const limit = (args?.limit as number) || 50;
        const offset = (args?.offset as number) || 0;
        const body: Record<string, unknown> = {
          limit,
          offset,
          sort: "CREATED_DESC",
        };
        if (args?.flow_id) {
          body.flows = { id: { any_: [args.flow_id] } };
        }
        const result = await apiRequest("/deployments/filter", "POST", body);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_deployment": {
        const result = await apiRequest(`/deployments/${args?.deployment_id}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "trigger_deployment": {
        const body: Record<string, unknown> = {};
        if (args?.parameters) body.parameters = args.parameters;
        if (args?.name) body.name = args.name;
        if (args?.idempotency_key) body.idempotency_key = args.idempotency_key;
        const result = await apiRequest(`/deployments/${args?.deployment_id}/create_flow_run`, "POST", body);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_deployment_status": {
        // Get deployment details and recent runs to determine status
        const deployment = await apiRequest(`/deployments/${args?.deployment_id}`);
        const runsBody = {
          limit: 5,
          sort: "START_TIME_DESC",
          deployments: { id: { any_: [args?.deployment_id] } },
        };
        const recentRuns = await apiRequest("/flow_runs/filter", "POST", runsBody);
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              deployment,
              recent_runs: recentRuns,
            }, null, 2),
          }],
        };
      }

      case "pause_deployment": {
        const result = await apiRequest(`/deployments/${args?.deployment_id}/set_schedule_inactive`, "POST");
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "resume_deployment": {
        const result = await apiRequest(`/deployments/${args?.deployment_id}/set_schedule_active`, "POST");
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "cancel_flow_run": {
        const result = await apiRequest(`/flow_runs/${args?.flow_run_id}/set_state`, "POST", {
          state: { type: "CANCELLED" },
        });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_work_pools": {
        const limit = (args?.limit as number) || 50;
        const offset = (args?.offset as number) || 0;
        const result = await apiRequest("/work_pools/filter", "POST", {
          limit,
          offset,
        });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_work_pool": {
        const result = await apiRequest(`/work_pools/${args?.work_pool_name}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_task_runs": {
        const limit = (args?.limit as number) || 50;
        const body: Record<string, unknown> = {
          limit,
          sort: "START_TIME_DESC",
        };
        if (args?.flow_run_id) {
          body.task_runs = { flow_run_id: { any_: [args.flow_run_id] } };
        }
        const result = await apiRequest("/task_runs/filter", "POST", body);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
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
