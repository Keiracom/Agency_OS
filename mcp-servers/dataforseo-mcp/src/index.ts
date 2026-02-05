#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const LOGIN = process.env.DATAFORSEO_LOGIN;
const PASSWORD = process.env.DATAFORSEO_PASSWORD;
const BASE_URL = "https://api.dataforseo.com/v3";

if (!LOGIN || !PASSWORD) {
  console.error("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD environment variables are required");
  process.exit(1);
}

const AUTH_HEADER = "Basic " + Buffer.from(`${LOGIN}:${PASSWORD}`).toString("base64");

async function dataForSeoRequest(endpoint: string, body: object[]) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method: "POST",
    headers: {
      "Authorization": AUTH_HEADER,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`DataForSEO API error: ${response.status} ${response.statusText}`);
  }

  const result = await response.json();
  
  if (result.status_code !== 20000) {
    throw new Error(`DataForSEO error: ${result.status_message}`);
  }

  return result;
}

const server = new Server(
  { name: "dataforseo-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "serp_google",
      description: "Get Google SERP results for a keyword. Returns organic results, featured snippets, and SERP features.",
      inputSchema: {
        type: "object",
        properties: {
          keyword: { type: "string", description: "Search keyword or phrase" },
          location_name: { type: "string", description: "Location (e.g., 'Sydney,New South Wales,Australia' or 'United States')" },
          language_code: { type: "string", description: "Language code (e.g., 'en')" },
          device: { type: "string", enum: ["desktop", "mobile"], description: "Device type" },
          depth: { type: "number", description: "Number of results to return (default 10, max 100)" },
        },
        required: ["keyword"],
      },
    },
    {
      name: "keyword_data",
      description: "Get keyword metrics: search volume, CPC, competition, and trends.",
      inputSchema: {
        type: "object",
        properties: {
          keywords: { type: "array", items: { type: "string" }, description: "Array of keywords to analyze" },
          location_name: { type: "string", description: "Location for metrics" },
          language_code: { type: "string", description: "Language code" },
        },
        required: ["keywords"],
      },
    },
    {
      name: "domain_analytics",
      description: "Get SEO metrics for a domain: organic traffic, keywords, top pages.",
      inputSchema: {
        type: "object",
        properties: {
          domain: { type: "string", description: "Domain to analyze" },
          location_name: { type: "string", description: "Location for data" },
          language_code: { type: "string", description: "Language code" },
        },
        required: ["domain"],
      },
    },
    {
      name: "backlinks",
      description: "Get backlink profile for a domain: referring domains, anchors, link types.",
      inputSchema: {
        type: "object",
        properties: {
          domain: { type: "string", description: "Domain to analyze" },
          limit: { type: "number", description: "Number of backlinks to return" },
          filters: { type: "array", items: { type: "string" }, description: "Filters array" },
        },
        required: ["domain"],
      },
    },
    {
      name: "competitors",
      description: "Find organic search competitors for a domain.",
      inputSchema: {
        type: "object",
        properties: {
          domain: { type: "string", description: "Domain to find competitors for" },
          location_name: { type: "string", description: "Location" },
          language_code: { type: "string", description: "Language" },
          limit: { type: "number", description: "Number of competitors to return" },
        },
        required: ["domain"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    let result;
    let cost = 0;
    
    // DataForSEO pricing (approximate per request)
    const costEstimates: Record<string, number> = {
      serp_google: 0.002,
      keyword_data: 0.05, // per keyword
      domain_analytics: 0.01,
      backlinks: 0.02,
      competitors: 0.01,
    };

    switch (name) {
      case "serp_google": {
        result = await dataForSeoRequest("/serp/google/organic/live/regular", [{
          keyword: args?.keyword,
          location_name: args?.location_name || "United States",
          language_code: args?.language_code || "en",
          device: args?.device || "desktop",
          depth: args?.depth || 10,
        }]);
        cost = costEstimates.serp_google;
        break;
      }

      case "keyword_data": {
        const keywords = args?.keywords as string[];
        result = await dataForSeoRequest("/keywords_data/google_ads/search_volume/live", [{
          keywords: keywords,
          location_name: args?.location_name || "United States",
          language_code: args?.language_code || "en",
        }]);
        cost = costEstimates.keyword_data * keywords.length;
        break;
      }

      case "domain_analytics": {
        result = await dataForSeoRequest("/dataforseo_labs/google/domain_metrics_by_categories/live", [{
          target: args?.domain,
          location_name: args?.location_name || "United States",
          language_code: args?.language_code || "en",
        }]);
        cost = costEstimates.domain_analytics;
        break;
      }

      case "backlinks": {
        result = await dataForSeoRequest("/backlinks/summary/live", [{
          target: args?.domain,
          limit: args?.limit || 100,
          filters: args?.filters,
        }]);
        cost = costEstimates.backlinks;
        break;
      }

      case "competitors": {
        result = await dataForSeoRequest("/dataforseo_labs/google/competitors_domain/live", [{
          target: args?.domain,
          location_name: args?.location_name || "United States",
          language_code: args?.language_code || "en",
          limit: args?.limit || 10,
        }]);
        cost = costEstimates.competitors;
        break;
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    // Extract relevant data from nested response
    const tasks = result.tasks?.[0];
    const data = tasks?.result || tasks;

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: true,
            data: data,
            metadata: {
              estimatedCostUSD: cost,
              estimatedCostAUD: (cost * 1.55).toFixed(4), // Approximate USD→AUD
              timestamp: new Date().toISOString(),
              statusCode: result.status_code,
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
  console.error("DataForSEO MCP server running on stdio");
}

main().catch(console.error);
