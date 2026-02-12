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

const TELNYX_API_URL = process.env.TELNYX_API_URL || "https://api.telnyx.com/v2";
const TELNYX_API_KEY = process.env.TELNYX_API_KEY || "";

async function apiRequest(endpoint: string, method = "GET", body?: object, params?: Record<string, string | number>) {
  const url = new URL(`${TELNYX_API_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  }

  const response = await fetch(url.toString(), {
    method,
    headers: {
      Authorization: `Bearer ${TELNYX_API_KEY}`,
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
  { name: "telnyx-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "send_sms",
      description: "Send an SMS message via Telnyx",
      inputSchema: {
        type: "object",
        properties: {
          from_number: { type: "string", description: "Sender phone number (Telnyx number, E.164 format)" },
          to_number: { type: "string", description: "Recipient phone number (E.164 format)" },
          text: { type: "string", description: "Message content" },
        },
        required: ["from_number", "to_number", "text"],
      },
    },
    {
      name: "list_phone_numbers",
      description: "List all Telnyx phone numbers (DIDs)",
      inputSchema: {
        type: "object",
        properties: {
          page_size: { type: "number", description: "Results per page (default 25)" },
        },
      },
    },
    {
      name: "search_available_numbers",
      description: "Search for available phone numbers to purchase",
      inputSchema: {
        type: "object",
        properties: {
          country_code: { type: "string", description: "ISO country code (default US)" },
          area_code: { type: "string", description: "Filter by area code (optional)" },
          limit: { type: "number", description: "Max results (default 10)" },
        },
      },
    },
    {
      name: "buy_number",
      description: "Purchase a phone number",
      inputSchema: {
        type: "object",
        properties: {
          phone_number: { type: "string", description: "Phone number to purchase (from search results)" },
          connection_id: { type: "string", description: "Optional connection/app ID to assign" },
        },
        required: ["phone_number"],
      },
    },
    {
      name: "make_call",
      description: "Initiate an outbound voice call",
      inputSchema: {
        type: "object",
        properties: {
          from_number: { type: "string", description: "Caller ID (must be Telnyx number)" },
          to_number: { type: "string", description: "Destination number (E.164 format)" },
          connection_id: { type: "string", description: "Telnyx connection/app ID for call control" },
        },
        required: ["from_number", "to_number", "connection_id"],
      },
    },
    {
      name: "list_calls",
      description: "List recent calls",
      inputSchema: {
        type: "object",
        properties: {
          page_size: { type: "number", description: "Results per page (default 25)" },
        },
      },
    },
    {
      name: "get_call",
      description: "Get details of a specific call",
      inputSchema: {
        type: "object",
        properties: {
          call_control_id: { type: "string", description: "Call control ID" },
        },
        required: ["call_control_id"],
      },
    },
    {
      name: "get_message",
      description: "Get details of a sent/received message",
      inputSchema: {
        type: "object",
        properties: {
          message_id: { type: "string", description: "Message ID" },
        },
        required: ["message_id"],
      },
    },
    {
      name: "get_usage",
      description: "Get account usage statistics",
      inputSchema: {
        type: "object",
        properties: {
          start_date: { type: "string", description: "Start date (YYYY-MM-DD format)" },
          end_date: { type: "string", description: "End date (YYYY-MM-DD format)" },
        },
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "send_sms": {
        const result = await apiRequest("/messages", "POST", {
          from: args?.from_number,
          to: args?.to_number,
          text: args?.text,
        });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_phone_numbers": {
        const params: Record<string, number> = { "page[size]": (args?.page_size as number) || 25 };
        const result = await apiRequest("/phone_numbers", "GET", undefined, params);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "search_available_numbers": {
        const params: Record<string, string | number> = {
          "filter[country_code]": (args?.country_code as string) || "US",
          "filter[limit]": (args?.limit as number) || 10,
        };
        if (args?.area_code) {
          params["filter[national_destination_code]"] = args.area_code as string;
        }
        const result = await apiRequest("/available_phone_numbers", "GET", undefined, params);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "buy_number": {
        const payload: Record<string, unknown> = {
          phone_numbers: [{ phone_number: args?.phone_number }],
        };
        if (args?.connection_id) {
          payload.connection_id = args.connection_id;
        }
        const result = await apiRequest("/number_orders", "POST", payload);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "make_call": {
        const result = await apiRequest("/calls", "POST", {
          from: args?.from_number,
          to: args?.to_number,
          connection_id: args?.connection_id,
        });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_calls": {
        const params: Record<string, number> = { "page[size]": (args?.page_size as number) || 25 };
        const result = await apiRequest("/calls", "GET", undefined, params);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_call": {
        const result = await apiRequest(`/calls/${args?.call_control_id}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_message": {
        const result = await apiRequest(`/messages/${args?.message_id}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_usage": {
        const params: Record<string, string> = {};
        if (args?.start_date) params["filter[start_date]"] = args.start_date as string;
        if (args?.end_date) params["filter[end_date]"] = args.end_date as string;
        const result = await apiRequest("/reports/ledger_billing_group_reports", "GET", undefined, params);
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
  console.error("Telnyx MCP server running on stdio");
}

main().catch(console.error);
