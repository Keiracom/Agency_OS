#!/bin/bash
# Railway API CLI wrapper
# Requires: Railway_Token environment variable

set -euo pipefail

RAILWAY_API="https://backboard.railway.com/graphql/v2"

# Check for token
if [ -z "${Railway_Token:-}" ]; then
    echo "Error: Railway_Token environment variable not set" >&2
    exit 1
fi

# GraphQL query helper
gql() {
    local query="$1"
    curl -s -X POST "$RAILWAY_API" \
        -H "Authorization: Bearer $Railway_Token" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}"
}

# Commands
cmd_me() {
    gql "query { me { id name email } }"
}

cmd_projects() {
    local workspace_id="${1:-}"
    if [ -n "$workspace_id" ]; then
        gql "query { workspace(workspaceId: \\\"$workspace_id\\\") { projects { edges { node { id name services { edges { node { id name } } } environments { edges { node { id name } } } } } } } }"
    else
        # Use me query to get projects
        gql "query { me { projects { edges { node { id name services { edges { node { id name } } } environments { edges { node { id name } } } } } } } }"
    fi
}

cmd_project() {
    local project_id="$1"
    gql "query { project(id: \\\"$project_id\\\") { id name description services { edges { node { id name } } } environments { edges { node { id name } } } } }"
}

cmd_deployments() {
    local project_id="$1"
    local service_id="$2"
    local environment_id="$3"
    local limit="${4:-5}"
    gql "query { deployments(first: $limit, input: { projectId: \\\"$project_id\\\", serviceId: \\\"$service_id\\\", environmentId: \\\"$environment_id\\\" }) { edges { node { id status staticUrl createdAt } } } }"
}

cmd_deployment() {
    local deployment_id="$1"
    gql "query { deployment(id: \\\"$deployment_id\\\") { id status staticUrl createdAt service { id name } environment { id name } } }"
}

cmd_restart() {
    local deployment_id="$1"
    gql "mutation { deploymentRestart(id: \\\"$deployment_id\\\") }"
}

cmd_redeploy() {
    local project_id="$1"
    local service_id="$2"
    local environment_id="$3"
    gql "mutation { serviceInstanceRedeploy(projectId: \\\"$project_id\\\", serviceId: \\\"$service_id\\\", environmentId: \\\"$environment_id\\\") }"
}

cmd_variables() {
    local project_id="$1"
    local service_id="$2"
    local environment_id="$3"
    gql "query { variables(projectId: \\\"$project_id\\\", serviceId: \\\"$service_id\\\", environmentId: \\\"$environment_id\\\") }"
}

cmd_set_var() {
    local project_id="$1"
    local service_id="$2"
    local environment_id="$3"
    local name="$4"
    local value="$5"
    gql "mutation { variableUpsert(input: { projectId: \\\"$project_id\\\", serviceId: \\\"$service_id\\\", environmentId: \\\"$environment_id\\\", name: \\\"$name\\\", value: \\\"$value\\\" }) }"
}

cmd_services() {
    local project_id="$1"
    gql "query { project(id: \\\"$project_id\\\") { services { edges { node { id name } } } } }"
}

cmd_environments() {
    local project_id="$1"
    gql "query { project(id: \\\"$project_id\\\") { environments { edges { node { id name } } } } }"
}

# Help
cmd_help() {
    cat <<EOF
Railway API CLI

Usage: railway.sh <command> [args]

Commands:
  me                                          Test authentication
  projects [workspace_id]                     List projects
  project <project_id>                        Get project details
  services <project_id>                       List services in project
  environments <project_id>                   List environments in project
  deployments <pid> <sid> <eid> [limit]       List deployments
  deployment <deployment_id>                  Get deployment details
  restart <deployment_id>                     Restart deployment
  redeploy <pid> <sid> <eid>                  Redeploy service
  variables <pid> <sid> <eid>                 Get environment variables
  set-var <pid> <sid> <eid> <name> <value>    Set environment variable
  help                                        Show this help

Examples:
  railway.sh me
  railway.sh projects
  railway.sh deployments abc123 def456 ghi789 10
  railway.sh restart xyz789
EOF
}

# Main
main() {
    local cmd="${1:-help}"
    shift || true

    case "$cmd" in
        me) cmd_me ;;
        projects) cmd_projects "$@" ;;
        project) cmd_project "$@" ;;
        services) cmd_services "$@" ;;
        environments) cmd_environments "$@" ;;
        deployments) cmd_deployments "$@" ;;
        deployment) cmd_deployment "$@" ;;
        restart) cmd_restart "$@" ;;
        redeploy) cmd_redeploy "$@" ;;
        variables) cmd_variables "$@" ;;
        set-var) cmd_set_var "$@" ;;
        help|--help|-h) cmd_help ;;
        *) echo "Unknown command: $cmd" >&2; cmd_help; exit 1 ;;
    esac
}

main "$@"
