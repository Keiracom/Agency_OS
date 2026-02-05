#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const API_KEY = process.env.PROSPEO_API_KEY;
const BASE_URL = "https://api.prospeo.io";

if (!API_KEY) {
  console.error("PROSPEO_API_KEY environment variable is required");
  process.exit(1);
}

async function prospeoRequest(endpoint: string, body: object) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-KEY": API_KEY!,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Prospeo API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

const server = new Server(
  { name: "prospeo-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "find_email",
      description: "Find a professional email address given first name, last name, and company domain.",
      inputSchema: {
        type: "object",
        properties: {
          first_name: { type: "string", description: "Person's first name" },
          last_name: { type: "string", description: "Person's last name" },
          domain: { type: "string", description: "Company domain (e.g., company.com)" },
        },
        required: ["first_name", "last_name", "domain"],
      },
    },
    {
      name: "verify_email",
      description: "Verify if an email address is valid and deliverable.",
      inputSchema: {
        type: "object",
        properties: {
          email: { type: "string", description: "Email address to verify" },
        },
        required: ["email"],
      },
    },
    {
      name: "domain_search",
      description: "Find all email addresses associated with a domain.",
      inputSchema: {
        type: "object",
        properties: {
          domain: { type: "string", description: "Domain to search (e.g., company.com)" },
        },
        required: ["domain"],
      },
    },
    {
      name: "linkedin_to_email",
      description: "Extract email address from a LinkedIn profile URL.",
      inputSchema: {
        type: "object",
        properties: {
          linkedin_url: { type: "string", description: "LinkedIn profile URL" },
        },
        required: ["linkedin_url"],
      },
    },
    {
      name: "get_credits",
      description: "Check Prospeo API credit balance.",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    let result;
    let creditsUsed = 0;
    const creditCosts: Record<string, number> = {
      find_email: 1,
      verify_email: 1,
      domain_search: 10,
      linkedin_to_email: 3,
      get_credits: 0,
    };

    switch (name) {
      case "find_email": {
        result = await prospeoRequest("/email-finder", {
          first_name: args?.first_name,
          last_name: args?.last_name,
          company: args?.domain,
        });
        creditsUsed = result.email ? creditCosts.find_email : 0;
        break;
      }

      case "verify_email": {
        result = await prospeoRequest("/email-verifier", {
          email: args?.email,
        });
        creditsUsed = creditCosts.verify_email;
        break;
      }

      case "domain_search": {
        result = await prospeoRequest("/domain-search", {
          company: args?.domain,
        });
        creditsUsed = creditCosts.domain_search;
        break;
      }

      case "linkedin_to_email": {
        result = await prospeoRequest("/linkedin-email-finder", {
          url: args?.linkedin_url,
        });
        creditsUsed = result.email ? creditCosts.linkedin_to_email : 0;
        break;
      }

      case "get_credits": {
        const response = await fetch(`${BASE_URL}/credits`, {
          method: "GET",
          headers: { "X-KEY": API_KEY! },
        });
        result = await response.json();
        break;
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: true,
            data: result,
            metadata: {
              creditsUsed,
              creditCost: creditCosts[name] || 0,
              timestamp: new Date().toISOString(),
            },
          }, null, 2),
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error",
          }, null, 2),
        },
      ],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Prospeo MCP server running on stdio");
}

main().catch(console.error);
