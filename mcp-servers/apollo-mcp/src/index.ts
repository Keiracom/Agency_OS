#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

const API_KEY = process.env.APOLLO_API_KEY;
const BASE_URL = "https://api.apollo.io/v1";

if (!API_KEY) {
  console.error("APOLLO_API_KEY environment variable is required");
  process.exit(1);
}

async function apolloRequest(endpoint: string, method: string = "POST", body?: object) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache",
    },
    body: body ? JSON.stringify({ ...body, api_key: API_KEY }) : JSON.stringify({ api_key: API_KEY }),
  });

  if (!response.ok) {
    throw new Error(`Apollo API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

const server = new Server(
  { name: "apollo-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// Tool definitions
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search_people",
      description: "Search for people/contacts in Apollo database. Returns contact details, company info, and enrichment data.",
      inputSchema: {
        type: "object",
        properties: {
          q_keywords: { type: "string", description: "Keywords to search (job title, skills, etc.)" },
          person_titles: { type: "array", items: { type: "string" }, description: "Job titles to filter by" },
          person_locations: { type: "array", items: { type: "string" }, description: "Locations (city, state, country)" },
          organization_domains: { type: "array", items: { type: "string" }, description: "Company domains to search within" },
          organization_num_employees_ranges: { type: "array", items: { type: "string" }, description: "Employee count ranges, e.g. ['1,10', '11,50']" },
          page: { type: "number", description: "Page number (default 1)" },
          per_page: { type: "number", description: "Results per page (max 100)" },
        },
      },
    },
    {
      name: "search_companies",
      description: "Search for companies/organizations in Apollo database.",
      inputSchema: {
        type: "object",
        properties: {
          q_organization_keyword: { type: "string", description: "Company name or keyword" },
          organization_locations: { type: "array", items: { type: "string" }, description: "Company locations" },
          organization_num_employees_ranges: { type: "array", items: { type: "string" }, description: "Employee ranges" },
          organization_industry_tag_ids: { type: "array", items: { type: "string" }, description: "Industry IDs" },
          page: { type: "number", description: "Page number" },
          per_page: { type: "number", description: "Results per page" },
        },
      },
    },
    {
      name: "enrich_person",
      description: "Enrich a person's profile by email address. Returns full contact details and company info.",
      inputSchema: {
        type: "object",
        properties: {
          email: { type: "string", description: "Email address to enrich" },
        },
        required: ["email"],
      },
    },
    {
      name: "enrich_company",
      description: "Enrich a company's profile by domain. Returns company details, employee count, technologies, etc.",
      inputSchema: {
        type: "object",
        properties: {
          domain: { type: "string", description: "Company domain to enrich" },
        },
        required: ["domain"],
      },
    },
    {
      name: "get_credits",
      description: "Check Apollo API credit balance and usage.",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "bulk_enrich",
      description: "Bulk enrich multiple email addresses. More efficient than individual calls.",
      inputSchema: {
        type: "object",
        properties: {
          emails: { type: "array", items: { type: "string" }, description: "Array of email addresses to enrich" },
        },
        required: ["emails"],
      },
    },
  ],
}));

// Tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    let result;
    let creditsUsed = 0;

    switch (name) {
      case "search_people": {
        result = await apolloRequest("/mixed_people/search", "POST", {
          q_keywords: args?.q_keywords,
          person_titles: args?.person_titles,
          person_locations: args?.person_locations,
          organization_domains: args?.organization_domains,
          organization_num_employees_ranges: args?.organization_num_employees_ranges,
          page: args?.page || 1,
          per_page: args?.per_page || 25,
        });
        creditsUsed = result.people?.length || 0;
        break;
      }

      case "search_companies": {
        result = await apolloRequest("/mixed_companies/search", "POST", {
          q_organization_keyword: args?.q_organization_keyword,
          organization_locations: args?.organization_locations,
          organization_num_employees_ranges: args?.organization_num_employees_ranges,
          organization_industry_tag_ids: args?.organization_industry_tag_ids,
          page: args?.page || 1,
          per_page: args?.per_page || 25,
        });
        creditsUsed = result.organizations?.length || 0;
        break;
      }

      case "enrich_person": {
        result = await apolloRequest("/people/match", "POST", {
          email: args?.email,
          reveal_personal_emails: true,
          reveal_phone_number: true,
        });
        creditsUsed = result.person ? 1 : 0;
        break;
      }

      case "enrich_company": {
        result = await apolloRequest("/organizations/enrich", "POST", {
          domain: args?.domain,
        });
        creditsUsed = result.organization ? 1 : 0;
        break;
      }

      case "get_credits": {
        // Apollo doesn't have a direct credits endpoint, but we can check via account info
        result = await apolloRequest("/auth/health", "GET");
        break;
      }

      case "bulk_enrich": {
        const emails = args?.emails as string[];
        if (!emails || emails.length === 0) {
          throw new Error("emails array is required");
        }
        
        result = await apolloRequest("/people/bulk_match", "POST", {
          details: emails.map(email => ({ email })),
          reveal_personal_emails: true,
        });
        creditsUsed = result.matches?.length || 0;
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
  console.error("Apollo MCP server running on stdio");
}

main().catch(console.error);
