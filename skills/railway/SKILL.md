---
name: railway
description: Manage Railway infrastructure via GraphQL API. Deploy services, check deployments, view logs, manage environment variables. Triggers on requests involving Railway, deployments, hosting, or infrastructure management.
metadata: {"clawdbot":{"requires":{"env":["Railway_Token"]}}}
---

# Railway API

Manage Railway projects, services, deployments, and variables via the GraphQL API.

## Setup

```bash
# Required - Account or Team token from https://railway.com/account/tokens
export Railway_Token="your-api-token"
```

## Quick Commands

```bash
# Test connection
{baseDir}/scripts/railway.sh me

# List all projects
{baseDir}/scripts/railway.sh projects

# Get project details (services + environments)
{baseDir}/scripts/railway.sh project <project_id>

# List deployments for a service
{baseDir}/scripts/railway.sh deployments <project_id> <service_id> <environment_id>

# Get deployment status
{baseDir}/scripts/railway.sh deployment <deployment_id>

# Restart a deployment
{baseDir}/scripts/railway.sh restart <deployment_id>

# Redeploy latest (service in environment)
{baseDir}/scripts/railway.sh redeploy <project_id> <service_id> <environment_id>

# Get environment variables
{baseDir}/scripts/railway.sh variables <project_id> <service_id> <environment_id>

# Set environment variable
{baseDir}/scripts/railway.sh set-var <project_id> <service_id> <environment_id> <name> <value>

# View logs (via Railway CLI)
railway logs --service <service_name>
```

## Commands Reference

### me - Test authentication

```bash
{baseDir}/scripts/railway.sh me

# Returns: name, email, account info
```

### projects - List all projects in workspace

```bash
{baseDir}/scripts/railway.sh projects [workspace_id]

# Without workspace_id, lists projects accessible to your token
# Returns: project id, name, services, environments
```

### project - Get project details

```bash
{baseDir}/scripts/railway.sh project <project_id>

# Returns: full project info with services and environments
```

### deployments - List deployments

```bash
{baseDir}/scripts/railway.sh deployments <project_id> <service_id> <environment_id> [limit]

# Default limit: 5
# Returns: deployment id, status, staticUrl, createdAt
```

### deployment - Get single deployment

```bash
{baseDir}/scripts/railway.sh deployment <deployment_id>

# Returns: full deployment details including status
```

### restart - Restart existing deployment

```bash
{baseDir}/scripts/railway.sh restart <deployment_id>

# Restarts the specified deployment
```

### redeploy - Trigger new deployment

```bash
{baseDir}/scripts/railway.sh redeploy <project_id> <service_id> <environment_id>

# Creates a new deployment for the service
```

### variables - Get environment variables

```bash
{baseDir}/scripts/railway.sh variables <project_id> <service_id> <environment_id>

# Returns: key/value object of all variables
```

### set-var - Set/update environment variable

```bash
{baseDir}/scripts/railway.sh set-var <project_id> <service_id> <environment_id> <name> <value>

# Creates or updates a variable
```

## GraphQL API Reference

### Endpoint

```
https://backboard.railway.com/graphql/v2
```

### Authentication Headers

```bash
# Account/Team token
Authorization: Bearer <Railway_Token>

# Project token (scoped to environment)
Project-Access-Token: <PROJECT_TOKEN>

# Team token
Team-Access-Token: <TEAM_TOKEN>
```

### Common Queries

#### List Projects in Workspace

```graphql
query Projects {
  workspace(workspaceId: "<workspace_id>") {
    projects {
      edges {
        node {
          id
          name
          services {
            edges {
              node { id name }
            }
          }
          environments {
            edges {
              node { id name }
            }
          }
        }
      }
    }
  }
}
```

#### Get Deployments

```graphql
query Deployments {
  deployments(
    first: 5
    input: {
      projectId: "<project_id>"
      environmentId: "<environment_id>"
      serviceId: "<service_id>"
    }
  ) {
    edges {
      node {
        id
        status
        staticUrl
        createdAt
      }
    }
  }
}
```

#### Get Variables

```graphql
query Variables {
  variables(
    projectId: "<project_id>"
    environmentId: "<environment_id>"
    serviceId: "<service_id>"
  )
}
```

### Common Mutations

#### Restart Deployment

```graphql
mutation DeploymentRestart {
  deploymentRestart(id: "<deployment_id>")
}
```

#### Create Service

```graphql
mutation ServiceCreate {
  serviceCreate(
    input: {
      projectId: "<project_id>"
      source: { repo: "owner/repo" }
    }
  ) {
    id
  }
}
```

#### Upsert Variable

```graphql
mutation VariableUpsert {
  variableUpsert(
    input: {
      projectId: "<project_id>"
      environmentId: "<environment_id>"
      serviceId: "<service_id>"
      name: "VAR_NAME"
      value: "var_value"
    }
  )
}
```

#### Delete Project

```graphql
mutation ProjectDelete {
  projectDelete(id: "<project_id>")
}
```

## Raw cURL Examples

```bash
# Get current user
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $Railway_Token" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { me { name email } }"}'

# List deployments
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $Railway_Token" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { deployments(first: 5, input: {projectId: \"<pid>\", serviceId: \"<sid>\", environmentId: \"<eid>\"}) { edges { node { id status createdAt } } } }"}'

# Restart deployment
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $Railway_Token" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { deploymentRestart(id: \"<deployment_id>\") }"}'
```

## Railway CLI Alternative

For interactive use, the Railway CLI may be easier:

```bash
# Install CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# View status
railway status

# View logs
railway logs

# Deploy
railway up

# Open dashboard
railway open
```

## Rate Limits

| Plan | Requests/Hour | Requests/Second |
|------|---------------|-----------------|
| Free | 100 | - |
| Hobby | 1,000 | 10 |
| Pro | 10,000 | 50 |
| Enterprise | Custom | Custom |

Response headers for tracking:
- `X-RateLimit-Limit` - Max requests per day
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Window reset time
- `Retry-After` - Wait time when rate limited

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| Railway_Token | Yes | API token (Account, Team, or Project) |

## Known Project IDs

| Project | ID | Notes |
|---------|-----|-------|
| Agency OS | fef5af27-a022-4fb2-996b-cad099549af9 | Main backend |

## Tips

- Use `Cmd/Ctrl + K` in Railway dashboard to copy project/service/environment IDs
- Check Network tab in browser to see which queries the dashboard uses
- Use [GraphiQL playground](https://railway.com/graphiql) to explore schema
- Service logs require the Railway CLI (`railway logs`)
