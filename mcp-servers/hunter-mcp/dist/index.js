#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema, } from "@modelcontextprotocol/sdk/types.js";
const API_KEY = process.env.HUNTER_API_KEY;
const BASE_URL = "https://api.hunter.io/v2";
if (!API_KEY) {
    console.error("HUNTER_API_KEY environment variable is required");
    process.exit(1);
}
async function hunterRequest(endpoint, params = {}) {
    const url = new URL(`${BASE_URL}${endpoint}`);
    url.searchParams.set("api_key", API_KEY);
    for (const [key, value] of Object.entries(params)) {
        if (value)
            url.searchParams.set(key, value);
    }
    const response = await fetch(url.toString());
    if (!response.ok) {
        const error = await response.json();
        throw new Error(`Hunter API error: ${error.errors?.[0]?.details || response.statusText}`);
    }
    return response.json();
}
const server = new Server({ name: "hunter-mcp", version: "1.0.0" }, { capabilities: { tools: {} } });
server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [
        {
            name: "domain_search",
            description: "Find all email addresses associated with a domain. Returns emails, names, positions, and confidence scores.",
            inputSchema: {
                type: "object",
                properties: {
                    domain: { type: "string", description: "Domain to search (e.g., company.com)" },
                    type: { type: "string", enum: ["personal", "generic"], description: "Filter by email type" },
                    seniority: { type: "string", description: "Filter by seniority (junior, senior, executive)" },
                    department: { type: "string", description: "Filter by department (executive, it, finance, management, sales, legal, support, hr, marketing, communication, education, design, health, operations)" },
                    limit: { type: "number", description: "Number of results (default 10, max 100)" },
                    offset: { type: "number", description: "Offset for pagination" },
                },
                required: ["domain"],
            },
        },
        {
            name: "email_finder",
            description: "Find the most likely email address of a person using their name and company domain.",
            inputSchema: {
                type: "object",
                properties: {
                    domain: { type: "string", description: "Company domain" },
                    first_name: { type: "string", description: "Person's first name" },
                    last_name: { type: "string", description: "Person's last name" },
                },
                required: ["domain", "first_name", "last_name"],
            },
        },
        {
            name: "email_verifier",
            description: "Verify if an email address is valid, deliverable, and not risky.",
            inputSchema: {
                type: "object",
                properties: {
                    email: { type: "string", description: "Email address to verify" },
                },
                required: ["email"],
            },
        },
        {
            name: "get_account",
            description: "Get Hunter.io account information including credit balance and usage.",
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
        const creditCosts = {
            domain_search: 1, // per request
            email_finder: 1,
            email_verifier: 1,
            get_account: 0,
        };
        switch (name) {
            case "domain_search": {
                result = await hunterRequest("/domain-search", {
                    domain: args?.domain,
                    type: args?.type,
                    seniority: args?.seniority,
                    department: args?.department,
                    limit: String(args?.limit || 10),
                    offset: String(args?.offset || 0),
                });
                creditsUsed = creditCosts.domain_search;
                break;
            }
            case "email_finder": {
                result = await hunterRequest("/email-finder", {
                    domain: args?.domain,
                    first_name: args?.first_name,
                    last_name: args?.last_name,
                });
                creditsUsed = result.data?.email ? creditCosts.email_finder : 0;
                break;
            }
            case "email_verifier": {
                result = await hunterRequest("/email-verifier", {
                    email: args?.email,
                });
                creditsUsed = creditCosts.email_verifier;
                break;
            }
            case "get_account": {
                result = await hunterRequest("/account");
                // Include credit summary in response
                if (result.data) {
                    result.summary = {
                        plan: result.data.plan_name,
                        searches_left: result.data.requests?.searches?.available - result.data.requests?.searches?.used,
                        verifications_left: result.data.requests?.verifications?.available - result.data.requests?.verifications?.used,
                    };
                }
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
                        data: result.data,
                        meta: result.meta,
                        metadata: {
                            creditsUsed,
                            creditCost: creditCosts[name] || 0,
                            timestamp: new Date().toISOString(),
                        },
                    }, null, 2),
                },
            ],
        };
    }
    catch (error) {
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
    console.error("Hunter MCP server running on stdio");
}
main().catch(console.error);
