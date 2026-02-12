#!/usr/bin/env node
/**
 * MCP Bridge - Connects Clawdbot to MCP servers
 * 
 * Commands:
 *   servers              List available MCP servers
 *   tools <server>       List tools from a specific server
 *   call <server> <tool> [args_json]  Call an MCP tool
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { spawn } from "child_process";
import { config } from "dotenv";
import { resolve } from "path";
import { existsSync } from "fs";

// Load env vars from Agency OS config
const envPath = resolve(process.env.HOME || "~", ".config/agency-os/.env");
if (existsSync(envPath)) {
  config({ path: envPath });
}

// MCP Server Registry
interface MCPServerConfig {
  path?: string;           // Local path to dist/index.js
  npx?: string;            // NPM package to run via npx
  args?: string[];         // Additional args for npx
  env?: Record<string, string>;
  description: string;
}

const MCP_SERVERS: Record<string, MCPServerConfig> = {
  // === CORE DATA LAYER ===
  supabase: {
    npx: "@supabase/mcp-server-supabase",
    args: ["--access-token", process.env.SUPABASE_ACCESS_TOKEN || ""],
    env: { 
      SUPABASE_URL: process.env.SUPABASE_URL || "",
    },
    description: "Supabase database - queries, tables, auth, storage (CRITICAL)",
  },
  redis: {
    npx: "@upstash/mcp-server",
    env: { 
      UPSTASH_REDIS_REST_URL: process.env.UPSTASH_REDIS_REST_URL || "",
      UPSTASH_REDIS_REST_TOKEN: process.env.UPSTASH_REDIS_REST_TOKEN || "",
    },
    description: "Redis/Upstash cache - get, set, lists, pub/sub",
  },
  // === INFRASTRUCTURE ===
  prefect: {
    path: "/home/elliotbot/clawd/mcp-servers/prefect-mcp/dist/index.js",
    env: { PREFECT_API_URL: process.env.PREFECT_API_URL || "" },
    description: "Prefect workflow orchestration - flows, runs, deployments",
  },
  railway: {
    path: "/home/elliotbot/clawd/mcp-servers/railway-mcp/dist/index.js",
    env: { RAILWAY_TOKEN: process.env.Railway_Token || "" },
    description: "Railway deployment platform - projects, services, logs",
  },
  apollo: {
    path: "/home/elliotbot/clawd/mcp-servers/apollo-mcp/dist/index.js",
    env: { APOLLO_API_KEY: process.env.APOLLO_API_KEY || "" },
    description: "Apollo.io enrichment - people search, company data",
  },
  prospeo: {
    path: "/home/elliotbot/clawd/mcp-servers/prospeo-mcp/dist/index.js",
    env: { PROSPEO_API_KEY: process.env.PROSPEO_API_KEY || "" },
    description: "Prospeo email finder - email lookup, verification",
  },
  hunter: {
    path: "/home/elliotbot/clawd/mcp-servers/hunter-mcp/dist/index.js",
    env: { HUNTER_API_KEY: process.env.HUNTER_API_KEY || "" },
    description: "Hunter.io - domain search, email verification",
  },
  dataforseo: {
    path: "/home/elliotbot/clawd/mcp-servers/dataforseo-mcp/dist/index.js",
    env: {
      DATAFORSEO_LOGIN: process.env.DATAFORSEO_LOGIN || "",
      DATAFORSEO_PASSWORD: process.env.DATAFORSEO_PASSWORD || "",
    },
    description: "DataForSEO - SERP, keywords, backlinks",
  },
  vercel: {
    path: "/home/elliotbot/clawd/mcp-servers/vercel-mcp/dist/index.js",
    env: { VERCEL_TOKEN: process.env.VERCEL_TOKEN || "" },
    description: "Vercel deployments - projects, domains, deployments",
  },
  salesforge: {
    path: "/home/elliotbot/clawd/mcp-servers/salesforge-mcp/dist/index.js",
    env: { SALESFORGE_API_KEY: process.env.SALESFORGE_API_KEY || "" },
    description: "Salesforge outreach - campaigns, sequences, leads",
  },
  vapi: {
    path: "/home/elliotbot/clawd/mcp-servers/vapi-mcp/dist/index.js",
    env: { VAPI_API_KEY: process.env.VAPI_API_KEY || "" },
    description: "Vapi voice AI - assistants, calls, transcripts",
  },
  telnyx: {
    path: "/home/elliotbot/clawd/mcp-servers/telnyx-mcp/dist/index.js",
    env: { TELNYX_API_KEY: process.env.TELNYX_API_KEY || "" },
    description: "Telnyx communications - SMS, voice, numbers",
  },
  unipile: {
    path: "/home/elliotbot/clawd/mcp-servers/unipile-mcp/dist/index.js",
    env: { UNIPILE_API_KEY: process.env.UNIPILE_API_KEY || "" },
    description: "Unipile LinkedIn - profiles, connections, messages",
  },
  resend: {
    path: "/home/elliotbot/clawd/mcp-servers/resend-mcp/dist/index.js",
    env: { RESEND_API_KEY: process.env.RESEND_API_KEY || "" },
    description: "Resend email API - transactional email, domains",
  },
  memory: {
    path: "/home/elliotbot/clawd/mcp-servers/memory-mcp/dist/index.js",
    env: {
      SUPABASE_URL: process.env.SUPABASE_URL || "",
      SUPABASE_SERVICE_KEY: process.env.SUPABASE_SERVICE_KEY || "",
    },
    description: "Semantic memory - search, save, embeddings",
  },
};

// Active client connections (lazy-loaded)
const activeClients: Map<string, Client> = new Map();
const activeTransports: Map<string, StdioClientTransport> = new Map();

async function connectToServer(serverName: string): Promise<Client> {
  // Return existing connection if available
  const existing = activeClients.get(serverName);
  if (existing) {
    return existing;
  }

  const serverConfig = MCP_SERVERS[serverName];
  if (!serverConfig) {
    throw new Error(`Unknown MCP server: ${serverName}. Available: ${Object.keys(MCP_SERVERS).join(", ")}`);
  }

  // Determine command and args based on config type
  let command: string;
  let args: string[];

  if (serverConfig.npx) {
    // NPM package - run via npx
    command = "npx";
    args = ["-y", serverConfig.npx, ...(serverConfig.args || [])];
  } else if (serverConfig.path) {
    // Local path - run via node
    if (!existsSync(serverConfig.path)) {
      throw new Error(`Server not built: ${serverConfig.path}. Run 'npm run build' in the MCP server directory.`);
    }
    command = "node";
    args = [serverConfig.path];
  } else {
    throw new Error(`Server ${serverName} has no path or npx package configured.`);
  }

  // Merge process env with server-specific env
  const env = { ...process.env, ...serverConfig.env };

  const transport = new StdioClientTransport({
    command,
    args,
    env: env as Record<string, string>,
  });

  const client = new Client(
    { name: "mcp-bridge", version: "1.0.0" },
    { capabilities: {} }
  );

  await client.connect(transport);

  // Cache the connection
  activeClients.set(serverName, client);
  activeTransports.set(serverName, transport);

  return client;
}

async function disconnectServer(serverName: string): Promise<void> {
  const client = activeClients.get(serverName);
  const transport = activeTransports.get(serverName);

  if (client) {
    await client.close();
    activeClients.delete(serverName);
  }

  if (transport) {
    await transport.close();
    activeTransports.delete(serverName);
  }
}

async function disconnectAll(): Promise<void> {
  for (const serverName of activeClients.keys()) {
    await disconnectServer(serverName);
  }
}

// Command: List servers
async function listServers(): Promise<void> {
  console.log("# Available MCP Servers\n");

  for (const [name, config] of Object.entries(MCP_SERVERS)) {
    let status: string;
    let location: string;

    if (config.npx) {
      status = "✓ (npm)";
      location = `Package: ${config.npx}`;
    } else if (config.path) {
      const exists = existsSync(config.path);
      status = exists ? "✓" : "✗ (not built)";
      location = `Path: ${config.path}`;
    } else {
      status = "✗ (no config)";
      location = "N/A";
    }

    console.log(`## ${name} ${status}`);
    console.log(`   ${config.description}`);
    console.log(`   ${location}\n`);
  }

  console.log(`\nTotal: ${Object.keys(MCP_SERVERS).length} servers`);
}

// Command: List tools from a server
async function listTools(serverName: string): Promise<void> {
  try {
    const client = await connectToServer(serverName);
    const result = await client.listTools();

    console.log(`# Tools from ${serverName}\n`);

    if (result.tools.length === 0) {
      console.log("No tools available.");
      return;
    }

    for (const tool of result.tools) {
      console.log(`## ${tool.name}`);
      console.log(`   ${tool.description || "No description"}`);

      if (tool.inputSchema && typeof tool.inputSchema === "object") {
        const schema = tool.inputSchema as { properties?: Record<string, unknown>; required?: string[] };
        if (schema.properties) {
          const props = Object.keys(schema.properties);
          const required = schema.required || [];
          if (props.length > 0) {
            console.log(`   Parameters: ${props.map(p => required.includes(p) ? `${p}*` : p).join(", ")}`);
          }
        }
      }
      console.log("");
    }

    console.log(`\nTotal: ${result.tools.length} tools`);
  } catch (error) {
    console.error(`Error: ${error instanceof Error ? error.message : String(error)}`);
    process.exit(1);
  }
}

// Command: Call a tool
async function callTool(serverName: string, toolName: string, argsJson?: string): Promise<void> {
  try {
    const client = await connectToServer(serverName);

    let args: Record<string, unknown> = {};
    if (argsJson) {
      try {
        args = JSON.parse(argsJson);
      } catch {
        throw new Error(`Invalid JSON arguments: ${argsJson}`);
      }
    }

    const result = await client.callTool({ name: toolName, arguments: args });

    // Output the result
    if (result.content && Array.isArray(result.content)) {
      for (const item of result.content) {
        if (item.type === "text") {
          console.log(item.text);
        } else {
          console.log(JSON.stringify(item, null, 2));
        }
      }
    } else {
      console.log(JSON.stringify(result, null, 2));
    }

    if (result.isError) {
      process.exit(1);
    }
  } catch (error) {
    console.error(`Error: ${error instanceof Error ? error.message : String(error)}`);
    process.exit(1);
  }
}

// Main
async function main(): Promise<void> {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log(`MCP Bridge - Connect Clawdbot to MCP servers

Usage:
  mcp-bridge servers              List available MCP servers
  mcp-bridge tools <server>       List tools from a specific server
  mcp-bridge call <server> <tool> [args_json]  Call an MCP tool

Examples:
  mcp-bridge servers
  mcp-bridge tools prefect
  mcp-bridge call prefect list_flows
  mcp-bridge call prefect get_flow_runs '{"limit": 5}'
`);
    process.exit(0);
  }

  const command = args[0];

  try {
    switch (command) {
      case "servers":
        await listServers();
        break;

      case "tools":
        if (!args[1]) {
          console.error("Usage: mcp-bridge tools <server>");
          process.exit(1);
        }
        await listTools(args[1]);
        break;

      case "call":
        if (!args[1] || !args[2]) {
          console.error("Usage: mcp-bridge call <server> <tool> [args_json]");
          process.exit(1);
        }
        await callTool(args[1], args[2], args[3]);
        break;

      default:
        console.error(`Unknown command: ${command}`);
        process.exit(1);
    }
  } finally {
    await disconnectAll();
  }
}

main().catch((error) => {
  console.error(`Fatal error: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
