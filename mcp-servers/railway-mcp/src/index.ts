#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { config } from "dotenv";
import { resolve } from "path";
import { homedir } from "os";

config({ path: resolve(homedir(), ".config/agency-os/.env") });

const RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2";
const RAILWAY_TOKEN = process.env.RAILWAY_TOKEN || process.env.Railway_Token || "";
const RAILWAY_PROJECT_TOKEN = process.env.RAILWAY_PROJECT_TOKEN || "";

// Detect if the token is a project token (UUID format) vs account token (longer alphanumeric)
function isProjectToken(token: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(token);
}

async function graphqlRequest(query: string, variables?: Record<string, unknown>, useProjectToken = false) {
  const token = useProjectToken && RAILWAY_PROJECT_TOKEN ? RAILWAY_PROJECT_TOKEN : RAILWAY_TOKEN;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  
  // Use different auth header for project tokens
  if (isProjectToken(token)) {
    headers["Project-Access-Token"] = token;
  } else {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(RAILWAY_API_URL, {
    method: "POST",
    headers,
    body: JSON.stringify({ query, variables }),
  });

  if (!response.ok) {
    const text = await response.text();
    return { error: true, status_code: response.status, message: text };
  }

  const result = await response.json();
  if (result.errors) {
    return { error: true, errors: result.errors };
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
      description: "List all Railway projects you have access to",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "get_project",
      description: "Get details of a specific Railway project including services",
      inputSchema: {
        type: "object",
        properties: {
          project_id: { type: "string", description: "Railway project ID" },
        },
        required: ["project_id"],
      },
    },
    {
      name: "get_deployments",
      description: "List deployments for a service in an environment",
      inputSchema: {
        type: "object",
        properties: {
          project_id: { type: "string", description: "Railway project ID" },
          service_id: { type: "string", description: "Railway service ID" },
          environment_id: { type: "string", description: "Railway environment ID" },
          limit: { type: "number", description: "Max number of deployments to return (default 10)" },
        },
        required: ["project_id", "service_id", "environment_id"],
      },
    },
    {
      name: "get_service_status",
      description: "Get the current status of a service (latest deployment info)",
      inputSchema: {
        type: "object",
        properties: {
          service_id: { type: "string", description: "Railway service ID" },
          environment_id: { type: "string", description: "Railway environment ID" },
        },
        required: ["service_id", "environment_id"],
      },
    },
    {
      name: "restart_service",
      description: "Restart a service by redeploying the latest deployment",
      inputSchema: {
        type: "object",
        properties: {
          deployment_id: { type: "string", description: "Deployment ID to redeploy" },
        },
        required: ["deployment_id"],
      },
    },
    {
      name: "deploy_service",
      description: "Trigger a new deployment for a service",
      inputSchema: {
        type: "object",
        properties: {
          service_id: { type: "string", description: "Railway service ID" },
          environment_id: { type: "string", description: "Railway environment ID" },
        },
        required: ["service_id", "environment_id"],
      },
    },
    {
      name: "get_logs",
      description: "Get build or runtime logs for a deployment",
      inputSchema: {
        type: "object",
        properties: {
          deployment_id: { type: "string", description: "Deployment ID" },
          log_type: { type: "string", enum: ["build", "deploy"], description: "Type of logs to fetch (default: deploy)" },
          limit: { type: "number", description: "Max number of log lines (default 100)" },
        },
        required: ["deployment_id"],
      },
    },
    {
      name: "stop_deployment",
      description: "Stop a running deployment",
      inputSchema: {
        type: "object",
        properties: {
          deployment_id: { type: "string", description: "Deployment ID to stop" },
        },
        required: ["deployment_id"],
      },
    },
    {
      name: "list_environments",
      description: "List all environments for a project",
      inputSchema: {
        type: "object",
        properties: {
          project_id: { type: "string", description: "Railway project ID" },
        },
        required: ["project_id"],
      },
    },
    {
      name: "get_variables",
      description: "Get environment variables for a service",
      inputSchema: {
        type: "object",
        properties: {
          project_id: { type: "string", description: "Railway project ID" },
          environment_id: { type: "string", description: "Railway environment ID" },
          service_id: { type: "string", description: "Railway service ID" },
        },
        required: ["project_id", "environment_id", "service_id"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "list_projects": {
        // If using project token, we can only get info about that specific project
        if (isProjectToken(RAILWAY_TOKEN)) {
          const query = `
            query {
              projectToken {
                projectId
                environmentId
                project {
                  id
                  name
                  description
                  services {
                    edges {
                      node {
                        id
                        name
                      }
                    }
                  }
                }
              }
            }
          `;
          const result = await graphqlRequest(query);
          return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
        } else {
          // Account token: list all projects
          const query = `
            query {
              projects {
                edges {
                  node {
                    id
                    name
                    description
                    createdAt
                    updatedAt
                    services {
                      edges {
                        node {
                          id
                          name
                        }
                      }
                    }
                    environments {
                      edges {
                        node {
                          id
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
          `;
          const result = await graphqlRequest(query);
          return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
        }
      }

      case "get_project": {
        const query = `
          query getProject($projectId: String!) {
            project(id: $projectId) {
              id
              name
              description
              createdAt
              updatedAt
              environments {
                edges {
                  node {
                    id
                    name
                  }
                }
              }
              services {
                edges {
                  node {
                    id
                    name
                    icon
                    createdAt
                  }
                }
              }
            }
          }
        `;
        const result = await graphqlRequest(query, { projectId: args?.project_id });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_deployments": {
        const limit = (args?.limit as number) || 10;
        const query = `
          query getDeployments($input: DeploymentListInput!) {
            deployments(input: $input) {
              edges {
                node {
                  id
                  status
                  createdAt
                  updatedAt
                  staticUrl
                  meta
                }
              }
            }
          }
        `;
        const result = await graphqlRequest(query, {
          input: {
            projectId: args?.project_id,
            serviceId: args?.service_id,
            environmentId: args?.environment_id,
            first: limit,
          },
        });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_service_status": {
        const query = `
          query getServiceInstance($serviceId: String!, $environmentId: String!) {
            serviceInstance(serviceId: $serviceId, environmentId: $environmentId) {
              id
              serviceId
              serviceName
              startCommand
              healthcheckPath
              latestDeployment {
                id
                status
                createdAt
                staticUrl
                meta
              }
            }
          }
        `;
        const result = await graphqlRequest(query, {
          serviceId: args?.service_id,
          environmentId: args?.environment_id,
        });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "restart_service": {
        const query = `
          mutation deploymentRedeploy($id: String!) {
            deploymentRedeploy(id: $id) {
              id
              status
            }
          }
        `;
        const result = await graphqlRequest(query, { id: args?.deployment_id });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "deploy_service": {
        const query = `
          mutation serviceInstanceDeploy($serviceId: String!, $environmentId: String!) {
            serviceInstanceDeploy(serviceId: $serviceId, environmentId: $environmentId)
          }
        `;
        const result = await graphqlRequest(query, {
          serviceId: args?.service_id,
          environmentId: args?.environment_id,
        });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_logs": {
        const logType = (args?.log_type as string) || "deploy";
        const limit = (args?.limit as number) || 100;
        
        if (logType === "build") {
          const query = `
            query getBuildLogs($deploymentId: String!, $limit: Int) {
              buildLogs(deploymentId: $deploymentId, limit: $limit)
            }
          `;
          const result = await graphqlRequest(query, {
            deploymentId: args?.deployment_id,
            limit,
          });
          return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
        } else {
          const query = `
            query getDeployLogs($deploymentId: String!, $limit: Int) {
              deploymentLogs(deploymentId: $deploymentId, limit: $limit)
            }
          `;
          const result = await graphqlRequest(query, {
            deploymentId: args?.deployment_id,
            limit,
          });
          return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
        }
      }

      case "stop_deployment": {
        const query = `
          mutation deploymentStop($id: String!) {
            deploymentStop(id: $id)
          }
        `;
        const result = await graphqlRequest(query, { id: args?.deployment_id });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_environments": {
        const query = `
          query getEnvironments($projectId: String!) {
            environments(projectId: $projectId) {
              edges {
                node {
                  id
                  name
                  createdAt
                  isEphemeral
                }
              }
            }
          }
        `;
        const result = await graphqlRequest(query, { projectId: args?.project_id });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_variables": {
        const query = `
          query getVariables($projectId: String!, $environmentId: String!, $serviceId: String!) {
            variables(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId)
          }
        `;
        const result = await graphqlRequest(query, {
          projectId: args?.project_id,
          environmentId: args?.environment_id,
          serviceId: args?.service_id,
        });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
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
