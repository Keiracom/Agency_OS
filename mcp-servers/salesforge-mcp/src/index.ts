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

// Load env
config({ path: resolve(homedir(), ".config/agency-os/.env") });

const SALESFORGE_API_URL = process.env.SALESFORGE_API_URL || "https://api.salesforge.ai/public/v2";
const SALESFORGE_API_KEY = process.env.SALESFORGE_API_KEY || "";
const WARMFORGE_API_URL = process.env.WARMFORGE_API_URL || "https://api.warmforge.ai/public/v1";
const WARMFORGE_API_KEY = process.env.WARMFORGE_API_KEY || "";
const INFRAFORGE_API_URL = process.env.INFRAFORGE_API_URL || "https://api.infraforge.ai/public";
const INFRAFORGE_API_KEY = process.env.INFRAFORGE_API_KEY || "";

async function apiRequest(
  url: string,
  method = "GET",
  headers: Record<string, string>,
  body?: object
) {
  const response = await fetch(url, {
    method,
    headers: { ...headers, "Content-Type": "application/json" },
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

const salesforgeHeaders = () => ({ Authorization: `Bearer ${SALESFORGE_API_KEY}` });
const warmforgeHeaders = () => ({ Authorization: `Bearer ${WARMFORGE_API_KEY}` });
const infraforgeHeaders = () => ({ Authorization: `Bearer ${INFRAFORGE_API_KEY}` });

const server = new Server(
  { name: "salesforge-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "list_campaigns",
      description: "List all Salesforge campaigns with IDs, names, status, and basic metrics",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "create_campaign",
      description: "Create a new Salesforge campaign",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "Campaign name" },
          config: { type: "object", description: "Campaign configuration (steps, settings, tracking)" },
        },
        required: ["name", "config"],
      },
    },
    {
      name: "get_campaign_stats",
      description: "Get campaign statistics and metrics (sent, delivered, opened, clicked, replied, bounced)",
      inputSchema: {
        type: "object",
        properties: {
          campaign_id: { type: "string", description: "Campaign/sequence ID" },
        },
        required: ["campaign_id"],
      },
    },
    {
      name: "add_leads",
      description: "Add leads to a Salesforge campaign",
      inputSchema: {
        type: "object",
        properties: {
          campaign_id: { type: "string", description: "Campaign/sequence ID" },
          leads: {
            type: "array",
            items: { type: "object" },
            description: "Lead objects with email (required), firstName, lastName, company, customFields",
          },
        },
        required: ["campaign_id", "leads"],
      },
    },
    {
      name: "pause_campaign",
      description: "Pause a running campaign",
      inputSchema: {
        type: "object",
        properties: {
          campaign_id: { type: "string", description: "Campaign/sequence ID to pause" },
        },
        required: ["campaign_id"],
      },
    },
    {
      name: "resume_campaign",
      description: "Resume a paused campaign",
      inputSchema: {
        type: "object",
        properties: {
          campaign_id: { type: "string", description: "Campaign/sequence ID to resume" },
        },
        required: ["campaign_id"],
      },
    },
    {
      name: "get_warmup_status",
      description: "Get WarmForge email warmup status for all mailboxes (progress, reputation, daily limits)",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "list_domains",
      description: "List all InfraForge domains with DNS status and mailbox counts",
      inputSchema: { type: "object", properties: {} },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "list_campaigns": {
        const result = await apiRequest(
          `${SALESFORGE_API_URL}/sequences`,
          "GET",
          salesforgeHeaders()
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "create_campaign": {
        const payload = { name: args?.name, ...(args?.config as object || {}) };
        const result = await apiRequest(
          `${SALESFORGE_API_URL}/sequences`,
          "POST",
          salesforgeHeaders(),
          payload
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_campaign_stats": {
        const campaignId = args?.campaign_id as string;
        const result = await apiRequest(
          `${SALESFORGE_API_URL}/sequences/${campaignId}/stats`,
          "GET",
          salesforgeHeaders()
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "add_leads": {
        const campaignId = args?.campaign_id as string;
        const leads = args?.leads as object[];
        const result = await apiRequest(
          `${SALESFORGE_API_URL}/sequences/${campaignId}/leads`,
          "POST",
          salesforgeHeaders(),
          { leads }
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "pause_campaign": {
        const campaignId = args?.campaign_id as string;
        const result = await apiRequest(
          `${SALESFORGE_API_URL}/sequences/${campaignId}/pause`,
          "POST",
          salesforgeHeaders()
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "resume_campaign": {
        const campaignId = args?.campaign_id as string;
        const result = await apiRequest(
          `${SALESFORGE_API_URL}/sequences/${campaignId}/resume`,
          "POST",
          salesforgeHeaders()
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_warmup_status": {
        const result = await apiRequest(
          `${WARMFORGE_API_URL}/mailboxes`,
          "GET",
          warmforgeHeaders()
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_domains": {
        const result = await apiRequest(
          `${INFRAFORGE_API_URL}/domains`,
          "GET",
          infraforgeHeaders()
        );
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
  console.error("Salesforge MCP server running on stdio");
}

main().catch(console.error);
