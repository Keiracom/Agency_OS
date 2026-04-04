#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { config } from "dotenv";
import { resolve } from "path";
import { homedir } from "os";

config({ path: resolve(homedir(), ".config/agency-os/.env") });
const TOKEN = process.env.VERCEL_TOKEN || "";
const BASE = "https://api.vercel.com";
const headers = () => ({ "Authorization": `Bearer ${TOKEN}`, "Content-Type": "application/json" });

async function vercelGet(path: string) {
  const r = await fetch(`${BASE}${path}`, { headers: headers() });
  return r.ok ? r.json() : { error: true, status: r.status, text: await r.text() };
}

const server = new Server({ name: "vercel-mcp", version: "1.0.0" }, { capabilities: { tools: {} } });

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [
  { name: "list_projects", description: "List all Vercel projects", inputSchema: { type: "object", properties: { limit: { type: "number" } } } },
  { name: "get_project", description: "Get a specific Vercel project", inputSchema: { type: "object", properties: { project_id: { type: "string" } }, required: ["project_id"] } },
  { name: "list_deployments", description: "List deployments for a project", inputSchema: { type: "object", properties: { project_id: { type: "string" }, limit: { type: "number" } }, required: ["project_id"] } },
  { name: "get_deployment", description: "Get deployment details", inputSchema: { type: "object", properties: { deployment_id: { type: "string" } }, required: ["deployment_id"] } }
]}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;
  let result;
  if (name === "list_projects") result = await vercelGet(`/v9/projects?limit=${args?.limit || 20}`);
  else if (name === "get_project") result = await vercelGet(`/v9/projects/${args?.project_id}`);
  else if (name === "list_deployments") result = await vercelGet(`/v6/deployments?projectId=${args?.project_id}&limit=${args?.limit || 10}`);
  else if (name === "get_deployment") result = await vercelGet(`/v13/deployments/${args?.deployment_id}`);
  else result = { error: "Unknown tool" };
  return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
});

async function main() { const t = new StdioServerTransport(); await server.connect(t); }
main().catch(console.error);
