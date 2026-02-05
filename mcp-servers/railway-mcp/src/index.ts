#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const RAILWAY_TOKEN = process.env.RAILWAY_TOKEN;
const RAILWAY_API = "https://backboard.railway.app/graphql/v2";

async function railwayQuery(query: string, variables: Record<string, unknown> = {}) {
  if (!RAILWAY_TOKEN) {
    throw new Error("RAILWAY_TOKEN environment variable required");
  }

  const response = await fetch(RAILWAY_API, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${RAILWAY_TOKEN}`,
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Railway API error: ${response.status} - ${text}`);
  }

  const result = await response.json();
  if (result.errors) {
    throw new Error(`GraphQL error: ${JSON.stringify(result.errors)}`);
  }
  return result.data;
}

const server = new Server(
  { name: "railway-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "list_projects",
      description: "List all Railway projects",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "list_services",
      description: "List services in a project",
      inputSchema: {
        type: "object",
        properties: {
          project_id: { type: "string", description: "Project ID" },
        },
        required: ["project_id"],
      },
    },
    {
      name: "get_deployment_status",
      description: "Get current deployment status for a service",
      inputSchema: {
        type: "object",
        properties: {
          service_id: { type: "string", description: "Service ID" },
        },
        required: ["service_id"],
      },
    },
    {
      name: "get_logs",
      description: "Get recent logs for a service",
      inputSchema: {
        type: "object",
        properties: {
          service_id: { type: "string", description: "Service ID" },
          lines: { type: "number", description: "Number of lines (default 100)", default: 100 },
        },
        required: ["service_id"],
      },
    },
    {
      name: "list_variables",
      description: "List environment variables for a service",
      inputSchema: {
        type: "object",
        properties: {
          service_id: { type: "string", description: "Service ID" },
        },
        required: ["service_id"],
      },
    },
    {
      name: "set_variable",
      description: "Set an environment variable for a service",
      inputSchema: {
        type: "object",
        properties: {
          service_id: { type: "string", description: "Service ID" },
          key: { type: "string", description: "Variable name" },
          value: { type: "string", description: "Variable value" },
        },
        required: ["service_id", "key", "value"],
      },
    },
    {
      name: "redeploy",
      description: "Trigger a redeploy for a service",
      inputSchema: {
        type: "object",
        properties: {
          service_id: { type: "string", description: "Service ID" },
        },
        required: ["service_id"],
      },
    },
    {
      name: "rollback",
      description: "Rollback to a previous deployment",
      inputSchema: {
        type: "object",
        properties: {
          service_id: { type: "string", description: "Service ID" },
          deployment_id: { type: "string", description: "Target deployment ID" },
        },
        required: ["service_id", "deployment_id"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "list_projects": {
        const data = await railwayQuery(`
          query {
            me {
              projects {
                edges {
                  node {
                    id
                    name
                    description
                    createdAt
                    updatedAt
                  }
                }
              }
            }
          }
        `);
        const projects = data.me.projects.edges.map((e: { node: unknown }) => e.node);
        return {
          content: [{ type: "text", text: JSON.stringify(projects, null, 2) }],
        };
      }

      case "list_services": {
        const projectId = args?.project_id as string;
        const data = await railwayQuery(
          `
          query($projectId: String!) {
            project(id: $projectId) {
              services {
                edges {
                  node {
                    id
                    name
                    createdAt
                  }
                }
              }
            }
          }
        `,
          { projectId }
        );
        const services = data.project.services.edges.map((e: { node: unknown }) => e.node);
        return {
          content: [{ type: "text", text: JSON.stringify(services, null, 2) }],
        };
      }

      case "get_deployment_status": {
        const serviceId = args?.service_id as string;
        const data = await railwayQuery(
          `
          query($serviceId: String!) {
            service(id: $serviceId) {
              id
              name
              deployments(first: 1) {
                edges {
                  node {
                    id
                    status
                    createdAt
                    staticUrl
                  }
                }
              }
            }
          }
        `,
          { serviceId }
        );
        const deployment = data.service.deployments.edges[0]?.node || null;
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                { service: data.service.name, latestDeployment: deployment },
                null,
                2
              ),
            },
          ],
        };
      }

      case "get_logs": {
        const serviceId = args?.service_id as string;
        const lines = (args?.lines as number) || 100;
        const data = await railwayQuery(
          `
          query($serviceId: String!, $limit: Int!) {
            service(id: $serviceId) {
              deployments(first: 1) {
                edges {
                  node {
                    id
                  }
                }
              }
            }
            deploymentLogs(deploymentId: $deploymentId, limit: $limit) {
              message
              timestamp
              severity
            }
          }
        `,
          { serviceId, limit: lines }
        );
        // Note: Railway's log API structure may vary - this is best effort
        return {
          content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
        };
      }

      case "list_variables": {
        const serviceId = args?.service_id as string;
        const data = await railwayQuery(
          `
          query($serviceId: String!) {
            service(id: $serviceId) {
              serviceInstances {
                edges {
                  node {
                    variables
                  }
                }
              }
            }
          }
        `,
          { serviceId }
        );
        const variables = data.service.serviceInstances.edges[0]?.node?.variables || {};
        return {
          content: [{ type: "text", text: JSON.stringify(variables, null, 2) }],
        };
      }

      case "set_variable": {
        const serviceId = args?.service_id as string;
        const key = args?.key as string;
        const value = args?.value as string;
        const data = await railwayQuery(
          `
          mutation($serviceId: String!, $name: String!, $value: String!) {
            variableUpsert(input: { serviceId: $serviceId, name: $name, value: $value }) {
              id
            }
          }
        `,
          { serviceId, name: key, value }
        );
        return {
          content: [{ type: "text", text: `Variable ${key} set successfully` }],
        };
      }

      case "redeploy": {
        const serviceId = args?.service_id as string;
        const data = await railwayQuery(
          `
          mutation($serviceId: String!) {
            serviceInstanceRedeploy(serviceId: $serviceId) {
              id
            }
          }
        `,
          { serviceId }
        );
        return {
          content: [{ type: "text", text: `Redeploy triggered for service ${serviceId}` }],
        };
      }

      case "rollback": {
        const serviceId = args?.service_id as string;
        const deploymentId = args?.deployment_id as string;
        const data = await railwayQuery(
          `
          mutation($deploymentId: String!) {
            deploymentRollback(id: $deploymentId) {
              id
            }
          }
        `,
          { deploymentId }
        );
        return {
          content: [{ type: "text", text: `Rollback to deployment ${deploymentId} triggered` }],
        };
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
  console.error("Railway MCP server running on stdio");
}

main().catch(console.error);
