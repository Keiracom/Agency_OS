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

const RESEND_API_URL = process.env.RESEND_API_URL || "https://api.resend.com";
const RESEND_API_KEY = process.env.RESEND_API_KEY || "";

async function apiRequest(endpoint: string, method = "GET", body?: object) {
  const response = await fetch(`${RESEND_API_URL}${endpoint}`, {
    method,
    headers: {
      Authorization: `Bearer ${RESEND_API_KEY}`,
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
  { name: "resend-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "send_email",
      description: "Send an email via Resend",
      inputSchema: {
        type: "object",
        properties: {
          from_address: { type: "string", description: "Sender email (must be verified domain)" },
          to: { type: "array", items: { type: "string" }, description: "Recipient email(s)" },
          subject: { type: "string", description: "Email subject" },
          html: { type: "string", description: "HTML body content" },
          text: { type: "string", description: "Plain text body (alternative to HTML)" },
          reply_to: { type: "string", description: "Reply-to address" },
          cc: { type: "array", items: { type: "string" }, description: "CC recipients" },
          bcc: { type: "array", items: { type: "string" }, description: "BCC recipients" },
          tags: { type: "array", items: { type: "object" }, description: "Tags for tracking [{name, value}]" },
        },
        required: ["from_address", "to", "subject"],
      },
    },
    {
      name: "list_emails",
      description: "List sent emails from Resend",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "get_email",
      description: "Get details and status of a sent email",
      inputSchema: {
        type: "object",
        properties: {
          email_id: { type: "string", description: "Email ID from send_email" },
        },
        required: ["email_id"],
      },
    },
    {
      name: "send_batch",
      description: "Send multiple emails in a batch",
      inputSchema: {
        type: "object",
        properties: {
          emails: {
            type: "array",
            items: { type: "object" },
            description: "List of email objects (from, to, subject, html/text)",
          },
        },
        required: ["emails"],
      },
    },
    {
      name: "list_domains",
      description: "List all configured sending domains",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "get_domain",
      description: "Get details of a specific domain",
      inputSchema: {
        type: "object",
        properties: {
          domain_id: { type: "string", description: "Domain ID" },
        },
        required: ["domain_id"],
      },
    },
    {
      name: "add_domain",
      description: "Add a new sending domain",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "Domain name (e.g., mail.example.com)" },
          region: { type: "string", description: "AWS region for delivery (default us-east-1)" },
        },
        required: ["name"],
      },
    },
    {
      name: "verify_domain",
      description: "Trigger verification check for a domain",
      inputSchema: {
        type: "object",
        properties: {
          domain_id: { type: "string", description: "Domain ID to verify" },
        },
        required: ["domain_id"],
      },
    },
    {
      name: "delete_domain",
      description: "Delete a sending domain",
      inputSchema: {
        type: "object",
        properties: {
          domain_id: { type: "string", description: "Domain ID to delete" },
        },
        required: ["domain_id"],
      },
    },
    {
      name: "list_api_keys",
      description: "List API keys for the account",
      inputSchema: { type: "object", properties: {} },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "send_email": {
        const payload: Record<string, unknown> = {
          from: args?.from_address,
          to: Array.isArray(args?.to) ? args.to : [args?.to],
          subject: args?.subject,
        };
        if (args?.html) payload.html = args.html;
        if (args?.text) payload.text = args.text;
        if (args?.reply_to) payload.reply_to = args.reply_to;
        if (args?.cc) payload.cc = args.cc;
        if (args?.bcc) payload.bcc = args.bcc;
        if (args?.tags) payload.tags = args.tags;
        const result = await apiRequest("/emails", "POST", payload);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_emails": {
        const result = await apiRequest("/emails");
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_email": {
        const result = await apiRequest(`/emails/${args?.email_id}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "send_batch": {
        const result = await apiRequest("/emails/batch", "POST", args?.emails as object);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_domains": {
        const result = await apiRequest("/domains");
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_domain": {
        const result = await apiRequest(`/domains/${args?.domain_id}`);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "add_domain": {
        const result = await apiRequest("/domains", "POST", {
          name: args?.name,
          region: (args?.region as string) || "us-east-1",
        });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "verify_domain": {
        const result = await apiRequest(`/domains/${args?.domain_id}/verify`, "POST");
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "delete_domain": {
        const result = await apiRequest(`/domains/${args?.domain_id}`, "DELETE");
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_api_keys": {
        const result = await apiRequest("/api-keys");
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
  console.error("Resend MCP server running on stdio");
}

main().catch(console.error);
