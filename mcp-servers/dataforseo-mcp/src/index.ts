#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { config } from "dotenv";
import { resolve } from "path";
import { homedir } from "os";

config({ path: resolve(homedir(), ".config/agency-os/.env") });
const LOGIN = process.env.DATAFORSEO_LOGIN || "";
const PASSWORD = process.env.DATAFORSEO_PASSWORD || "";
const BASE = "https://api.dataforseo.com/v3";
const headers = () => ({ "Authorization": "Basic " + Buffer.from(`${LOGIN}:${PASSWORD}`).toString("base64"), "Content-Type": "application/json" });

async function dfsPost(path: string, body: object) {
  const r = await fetch(`${BASE}${path}`, { method: "POST", headers: headers(), body: JSON.stringify(body) });
  return r.ok ? r.json() : { error: true, status: r.status, text: await r.text() };
}

const server = new Server({ name: "dataforseo-mcp", version: "1.0.0" }, { capabilities: { tools: {} } });

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [
  { name: "serp_search", description: "Search Google SERP via DataForSEO", inputSchema: { type: "object", properties: { keyword: { type: "string" }, location_code: { type: "number" }, language_code: { type: "string" } }, required: ["keyword"] } },
  { name: "keyword_ideas", description: "Get keyword ideas for a seed keyword", inputSchema: { type: "object", properties: { keyword: { type: "string" }, location_code: { type: "number" } }, required: ["keyword"] } },
  { name: "get_backlinks", description: "Get backlinks for a domain", inputSchema: { type: "object", properties: { target: { type: "string" }, limit: { type: "number" } }, required: ["target"] } }
]}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;
  let result;
  if (name === "serp_search") result = await dfsPost("/serp/google/organic/live/advanced", [{ keyword: args?.keyword, location_code: args?.location_code || 2840, language_code: args?.language_code || "en", depth: 10 }]);
  else if (name === "keyword_ideas") result = await dfsPost("/dataforseo_labs/google/keyword_ideas/live", [{ keyword: args?.keyword, location_code: args?.location_code || 2840, language_code: "en" }]);
  else if (name === "get_backlinks") result = await dfsPost("/backlinks/summary/live", [{ target: args?.target, limit: args?.limit || 10 }]);
  else result = { error: "Unknown tool" };
  return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
});

async function main() { const t = new StdioServerTransport(); await server.connect(t); }
main().catch(console.error);
