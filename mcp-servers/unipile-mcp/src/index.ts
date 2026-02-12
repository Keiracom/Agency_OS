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

const UNIPILE_API_URL = process.env.UNIPILE_API_URL || "https://api22.unipile.com:15268";
const UNIPILE_API_KEY = process.env.UNIPILE_API_KEY || "";

async function apiRequest(endpoint: string, method = "GET", body?: object, params?: Record<string, string | number>) {
  const url = new URL(`${UNIPILE_API_URL}/api/v1${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  }

  const response = await fetch(url.toString(), {
    method,
    headers: {
      "X-API-KEY": UNIPILE_API_KEY,
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
  { name: "unipile-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search_profiles",
      description: "Search LinkedIn profiles by query (name, title, company, keywords)",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query" },
          limit: { type: "number", description: "Max results (default 25)" },
          connection_degree: { type: "string", description: "Filter by connection (1st, 2nd, 3rd)" },
        },
        required: ["query"],
      },
    },
    {
      name: "get_profile",
      description: "Get detailed LinkedIn profile (experience, education, skills)",
      inputSchema: {
        type: "object",
        properties: {
          profile_id: { type: "string", description: "LinkedIn profile ID or vanity URL" },
        },
        required: ["profile_id"],
      },
    },
    {
      name: "send_connection",
      description: "Send a LinkedIn connection request",
      inputSchema: {
        type: "object",
        properties: {
          profile_id: { type: "string", description: "LinkedIn profile ID to connect with" },
          message: { type: "string", description: "Optional connection note (300 char limit)" },
        },
        required: ["profile_id"],
      },
    },
    {
      name: "send_message",
      description: "Send a direct message to a LinkedIn connection",
      inputSchema: {
        type: "object",
        properties: {
          profile_id: { type: "string", description: "LinkedIn profile ID (must be connected)" },
          message: { type: "string", description: "Message content" },
        },
        required: ["profile_id", "message"],
      },
    },
    {
      name: "list_connections",
      description: "List your LinkedIn connections",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Results per page (default 50)" },
          cursor: { type: "string", description: "Pagination cursor from previous response" },
        },
      },
    },
    {
      name: "get_account_status",
      description: "Get linked LinkedIn account health (status, connection count, daily limits, restrictions)",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "list_conversations",
      description: "List LinkedIn message conversations",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Results per page (default 25)" },
        },
      },
    },
    {
      name: "get_conversation",
      description: "Get messages in a specific conversation",
      inputSchema: {
        type: "object",
        properties: {
          conversation_id: { type: "string", description: "Conversation ID" },
        },
        required: ["conversation_id"],
      },
    },
    {
      name: "withdraw_invitation",
      description: "Withdraw a pending connection request",
      inputSchema: {
        type: "object",
        properties: {
          invitation_id: { type: "string", description: "Invitation ID to withdraw" },
        },
        required: ["invitation_id"],
      },
    },
    {
      name: "list_pending_invitations",
      description: "List pending connection invitations",
      inputSchema: {
        type: "object",
        properties: {
          direction: { type: "string", description: "'sent' or 'received'" },
          limit: { type: "number", description: "Results per page (default 25)" },
        },
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "search_profiles": {
        const params: Record<string, string | number> = {
          q: args?.query as string,
          limit: (args?.limit as number) || 25,
        };
        if (args?.connection_degree) params.connection_degree = args.connection_degree as string;
        const result = await apiRequest("/linkedin/search/people", "GET", undefined, params);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_profile": {
        const result = await apiRequest(`/linkedin/profile/${args?.profile_id}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "send_connection": {
        const payload: Record<string, string> = { profile_id: args?.profile_id as string };
        if (args?.message) {
          payload.message = (args.message as string).slice(0, 300);
        }
        const result = await apiRequest("/linkedin/invitation", "POST", payload);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "send_message": {
        const result = await apiRequest("/linkedin/message", "POST", {
          profile_id: args?.profile_id,
          text: args?.message,
        });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_connections": {
        const params: Record<string, string | number> = { limit: (args?.limit as number) || 50 };
        if (args?.cursor) params.cursor = args.cursor as string;
        const result = await apiRequest("/linkedin/connections", "GET", undefined, params);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_account_status": {
        const result = await apiRequest("/accounts");
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_conversations": {
        const params = { limit: (args?.limit as number) || 25 };
        const result = await apiRequest("/linkedin/conversations", "GET", undefined, params);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_conversation": {
        const result = await apiRequest(`/linkedin/conversations/${args?.conversation_id}/messages`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "withdraw_invitation": {
        const result = await apiRequest(`/linkedin/invitation/${args?.invitation_id}`, "DELETE");
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_pending_invitations": {
        const params = {
          direction: (args?.direction as string) || "sent",
          limit: (args?.limit as number) || 25,
        };
        const result = await apiRequest("/linkedin/invitations", "GET", undefined, params);
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
  console.error("Unipile MCP server running on stdio");
}

main().catch(console.error);
