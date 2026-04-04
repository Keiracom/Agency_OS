#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { config } from "dotenv";
import { resolve } from "path";
import { homedir } from "os";

config({ path: resolve(homedir(), ".config/agency-os/.env") });
const API_KEY = process.env.PROSPEO_API_KEY || "";
const BASE = "https://api.prospeo.io";
const headers = () => ({ "X-KEY": API_KEY, "Content-Type": "application/json" });

async function prospeoPost(path: string, body: object) {
  const r = await fetch(`${BASE}${path}`, { method: "POST", headers: headers(), body: JSON.stringify(body) });
  return r.ok ? r.json() : { error: true, status: r.status, text: await r.text() };
}

const server = new Server({ name: "prospeo-mcp", version: "1.0.0" }, { capabilities: { tools: {} } });

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [
  { name: "find_email", description: "Find email for a person by full name and company domain", inputSchema: { type: "object", properties: { full_name: { type: "string" }, domain: { type: "string" } }, required: ["full_name", "domain"] } },
  { name: "verify_email", description: "Verify if an email address is valid and deliverable", inputSchema: { type: "object", properties: { email: { type: "string" } }, required: ["email"] } },
  { name: "domain_search", description: "Find all emails associated with a domain", inputSchema: { type: "object", properties: { domain: { type: "string" }, limit: { type: "number" } }, required: ["domain"] } }
]}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;
  let result;
  if (name === "find_email") result = await prospeoPost("/email-finder", { full_name: args?.full_name, domain: args?.domain });
  else if (name === "verify_email") result = await prospeoPost("/email-verifier", { email: args?.email });
  else if (name === "domain_search") result = await prospeoPost("/domain-search", { domain: args?.domain, limit: args?.limit || 10 });
  else result = { error: "Unknown tool" };
  return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
});

async function main() { const t = new StdioServerTransport(); await server.connect(t); }
main().catch(console.error);
