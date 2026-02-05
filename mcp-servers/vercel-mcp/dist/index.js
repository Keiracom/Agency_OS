#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema, } from "@modelcontextprotocol/sdk/types.js";
const VERCEL_TOKEN = process.env.VERCEL_TOKEN;
const VERCEL_API = "https://api.vercel.com";
async function vercelRequest(endpoint, method = "GET", body) {
    if (!VERCEL_TOKEN) {
        throw new Error("VERCEL_TOKEN environment variable required");
    }
    const response = await fetch(`${VERCEL_API}${endpoint}`, {
        method,
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${VERCEL_TOKEN}`,
        },
        body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
        const text = await response.text();
        throw new Error(`Vercel API error: ${response.status} - ${text}`);
    }
    // Some endpoints return no content
    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
        return response.json();
    }
    return { success: true };
}
const server = new Server({ name: "vercel-mcp", version: "1.0.0" }, { capabilities: { tools: {} } });
server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [
        {
            name: "list_projects",
            description: "List all Vercel projects",
            inputSchema: { type: "object", properties: {} },
        },
        {
            name: "list_deployments",
            description: "List deployments for a project",
            inputSchema: {
                type: "object",
                properties: {
                    project_id: { type: "string", description: "Project ID or name" },
                    limit: { type: "number", description: "Max results (default 20)", default: 20 },
                },
                required: ["project_id"],
            },
        },
        {
            name: "get_deployment",
            description: "Get deployment details",
            inputSchema: {
                type: "object",
                properties: {
                    deployment_id: { type: "string", description: "Deployment ID or URL" },
                },
                required: ["deployment_id"],
            },
        },
        {
            name: "get_logs",
            description: "Get build logs for a deployment",
            inputSchema: {
                type: "object",
                properties: {
                    deployment_id: { type: "string", description: "Deployment ID" },
                },
                required: ["deployment_id"],
            },
        },
        {
            name: "list_env_vars",
            description: "List environment variables for a project",
            inputSchema: {
                type: "object",
                properties: {
                    project_id: { type: "string", description: "Project ID or name" },
                },
                required: ["project_id"],
            },
        },
        {
            name: "create_deployment",
            description: "Trigger a new deployment (requires git integration or files)",
            inputSchema: {
                type: "object",
                properties: {
                    project_id: { type: "string", description: "Project ID or name" },
                    ref: { type: "string", description: "Git ref to deploy (branch/commit)" },
                },
                required: ["project_id"],
            },
        },
        {
            name: "promote_to_production",
            description: "Promote a preview deployment to production",
            inputSchema: {
                type: "object",
                properties: {
                    deployment_id: { type: "string", description: "Deployment ID to promote" },
                },
                required: ["deployment_id"],
            },
        },
    ],
}));
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
        switch (name) {
            case "list_projects": {
                const data = await vercelRequest("/v9/projects");
                const projects = data.projects.map((p) => ({
                    id: p.id,
                    name: p.name,
                    framework: p.framework,
                    createdAt: p.createdAt,
                    latestDeployments: p.latestDeployments,
                }));
                return {
                    content: [{ type: "text", text: JSON.stringify(projects, null, 2) }],
                };
            }
            case "list_deployments": {
                const projectId = args?.project_id;
                const limit = args?.limit || 20;
                const data = await vercelRequest(`/v6/deployments?projectId=${encodeURIComponent(projectId)}&limit=${limit}`);
                const deployments = data.deployments.map((d) => ({
                    id: d.uid,
                    name: d.name,
                    url: d.url,
                    state: d.state,
                    target: d.target,
                    createdAt: d.createdAt,
                    ready: d.ready,
                }));
                return {
                    content: [{ type: "text", text: JSON.stringify(deployments, null, 2) }],
                };
            }
            case "get_deployment": {
                const deploymentId = args?.deployment_id;
                const data = await vercelRequest(`/v13/deployments/${encodeURIComponent(deploymentId)}`);
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                id: data.id,
                                name: data.name,
                                url: data.url,
                                state: data.readyState,
                                target: data.target,
                                createdAt: data.createdAt,
                                buildingAt: data.buildingAt,
                                ready: data.ready,
                                meta: data.meta,
                            }, null, 2),
                        },
                    ],
                };
            }
            case "get_logs": {
                const deploymentId = args?.deployment_id;
                // Get build logs (events)
                const data = await vercelRequest(`/v2/deployments/${encodeURIComponent(deploymentId)}/events`);
                return {
                    content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
                };
            }
            case "list_env_vars": {
                const projectId = args?.project_id;
                const data = await vercelRequest(`/v9/projects/${encodeURIComponent(projectId)}/env`);
                const envVars = data.envs.map((e) => ({
                    key: e.key,
                    target: e.target,
                    type: e.type,
                    // Value is often encrypted, so we just show metadata
                    id: e.id,
                    createdAt: e.createdAt,
                }));
                return {
                    content: [{ type: "text", text: JSON.stringify(envVars, null, 2) }],
                };
            }
            case "create_deployment": {
                const projectId = args?.project_id;
                const ref = args?.ref;
                // Get project details first to find the repo
                const project = await vercelRequest(`/v9/projects/${encodeURIComponent(projectId)}`);
                if (!project.link) {
                    return {
                        content: [
                            {
                                type: "text",
                                text: "Project has no linked Git repository. Manual deployment requires file upload which is not supported in this tool.",
                            },
                        ],
                        isError: true,
                    };
                }
                // Trigger deployment via the Vercel API
                const deployment = await vercelRequest("/v13/deployments", "POST", {
                    name: project.name,
                    project: projectId,
                    target: "preview",
                    gitSource: ref
                        ? {
                            type: project.link.type,
                            ref,
                            repoId: project.link.repoId,
                        }
                        : undefined,
                });
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                id: deployment.id,
                                url: deployment.url,
                                state: deployment.readyState,
                                target: deployment.target,
                            }, null, 2),
                        },
                    ],
                };
            }
            case "promote_to_production": {
                const deploymentId = args?.deployment_id;
                // Get deployment to find project
                const deployment = await vercelRequest(`/v13/deployments/${encodeURIComponent(deploymentId)}`);
                // Promote by setting alias
                const result = await vercelRequest(`/v10/projects/${deployment.projectId}/promote/${deploymentId}`, "POST");
                return {
                    content: [
                        {
                            type: "text",
                            text: `Deployment ${deploymentId} promoted to production`,
                        },
                    ],
                };
            }
            default:
                throw new Error(`Unknown tool: ${name}`);
        }
    }
    catch (error) {
        return {
            content: [
                {
                    type: "text",
                    text: `Error: ${error instanceof Error ? error.message : String(error)}`,
                },
            ],
            isError: true,
        };
    }
});
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Vercel MCP server running on stdio");
}
main().catch(console.error);
