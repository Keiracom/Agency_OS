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

const VAPI_API_URL = process.env.VAPI_API_URL || "https://api.vapi.ai";
const VAPI_API_KEY = process.env.VAPI_API_KEY || "";

async function apiRequest(endpoint: string, method = "GET", body?: object, params?: Record<string, string | number>) {
  const url = new URL(`${VAPI_API_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  }

  const response = await fetch(url.toString(), {
    method,
    headers: {
      Authorization: `Bearer ${VAPI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const text = await response.text();
    return { error: true, status_code: response.status, message: text };
  }

  try {
    return await response.json();
  } catch {
    return { raw_response: await response.text() };
  }
}

const server = new Server(
  { name: "vapi-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "list_assistants",
      description: "List all Vapi voice assistants",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "create_assistant",
      description: "Create a new Vapi voice assistant",
      inputSchema: {
        type: "object",
        properties: {
          config: { type: "object", description: "Assistant config (name, model, voice, firstMessage, transcriber)" },
        },
        required: ["config"],
      },
    },
    {
      name: "get_assistant",
      description: "Get details of a specific assistant",
      inputSchema: {
        type: "object",
        properties: {
          assistant_id: { type: "string", description: "Assistant ID" },
        },
        required: ["assistant_id"],
      },
    },
    {
      name: "update_assistant",
      description: "Update an existing Vapi assistant (partial update supported)",
      inputSchema: {
        type: "object",
        properties: {
          assistant_id: { type: "string", description: "Assistant ID to update" },
          config: { type: "object", description: "Updated configuration" },
        },
        required: ["assistant_id", "config"],
      },
    },
    {
      name: "delete_assistant",
      description: "Delete a Vapi assistant",
      inputSchema: {
        type: "object",
        properties: {
          assistant_id: { type: "string", description: "Assistant ID to delete" },
        },
        required: ["assistant_id"],
      },
    },
    {
      name: "start_call",
      description: "Initiate an outbound call using a Vapi assistant",
      inputSchema: {
        type: "object",
        properties: {
          assistant_id: { type: "string", description: "Assistant to use for the call" },
          phone_number: { type: "string", description: "Destination phone number (E.164 format)" },
          phone_number_id: { type: "string", description: "Optional Vapi phone number ID to call from" },
        },
        required: ["assistant_id", "phone_number"],
      },
    },
    {
      name: "get_call",
      description: "Get call status and details (status, duration, cost, metadata)",
      inputSchema: {
        type: "object",
        properties: {
          call_id: { type: "string", description: "Call ID" },
        },
        required: ["call_id"],
      },
    },
    {
      name: "list_calls",
      description: "List call history with optional filters",
      inputSchema: {
        type: "object",
        properties: {
          assistant_id: { type: "string", description: "Filter by assistant (optional)" },
          limit: { type: "number", description: "Max results (default 100)" },
        },
      },
    },
    {
      name: "get_transcript",
      description: "Get the transcript for a completed call",
      inputSchema: {
        type: "object",
        properties: {
          call_id: { type: "string", description: "Call ID" },
        },
        required: ["call_id"],
      },
    },
    {
      name: "list_phone_numbers",
      description: "List all Vapi phone numbers",
      inputSchema: { type: "object", properties: {} },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "list_assistants": {
        const result = await apiRequest("/assistant");
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "create_assistant": {
        const result = await apiRequest("/assistant", "POST", args?.config as object);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_assistant": {
        const result = await apiRequest(`/assistant/${args?.assistant_id}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "update_assistant": {
        const result = await apiRequest(`/assistant/${args?.assistant_id}`, "PATCH", args?.config as object);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "delete_assistant": {
        const result = await apiRequest(`/assistant/${args?.assistant_id}`, "DELETE");
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "start_call": {
        const payload: Record<string, unknown> = {
          assistantId: args?.assistant_id,
          customer: { number: args?.phone_number },
        };
        if (args?.phone_number_id) {
          payload.phoneNumberId = args.phone_number_id;
        }
        const result = await apiRequest("/call/phone", "POST", payload);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_call": {
        const result = await apiRequest(`/call/${args?.call_id}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_calls": {
        const params: Record<string, string | number> = { limit: (args?.limit as number) || 100 };
        if (args?.assistant_id) params.assistantId = args.assistant_id as string;
        const result = await apiRequest("/call", "GET", undefined, params);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_transcript": {
        const callData = await apiRequest(`/call/${args?.call_id}`);
        if (callData.error) {
          return { content: [{ type: "text", text: JSON.stringify(callData, null, 2) }] };
        }
        const result = {
          call_id: args?.call_id,
          transcript: callData.transcript || [],
          messages: callData.messages || [],
          summary: callData.summary,
        };
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_phone_numbers": {
        const result = await apiRequest("/phone-number");
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
  console.error("Vapi MCP server running on stdio");
}

main().catch(console.error);
