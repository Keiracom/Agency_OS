#!/usr/bin/env python3
"""
Infrastructure Master Tool - Workflow and deployment management.

Consolidates: prefect, railway

Usage:
    python3 tools/infra_master.py <action> <target> [options]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# Load env
def load_env():
    env_file = Path.home() / ".config/agency-os/.env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    value = value.strip().strip('"').strip("'")
                    os.environ[key.strip()] = value

load_env()

PREFECT_API_URL = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
RAILWAY_TOKEN = os.getenv("Railway_Token")

# ============================================
# PREFECT
# ============================================

def prefect_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make Prefect API request."""
    
    url = f"{PREFECT_API_URL}/{endpoint}"
    
    req = Request(url, method=method,
                  headers={"Content-Type": "application/json"})
    
    if data:
        req.data = json.dumps(data).encode()
    
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        return {"error": f"Prefect API error: {e.code}"}


def prefect_health() -> dict:
    """Check Prefect server health."""
    try:
        req = Request(f"{PREFECT_API_URL}/health")
        with urlopen(req, timeout=10) as response:
            return {"status": "healthy", "response": response.read().decode()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def prefect_flows(limit: int = 20) -> list[dict]:
    """List flows."""
    result = prefect_request("POST", "flows/filter", {"limit": limit})
    if isinstance(result, list):
        return [{"name": f.get("name"), "id": f.get("id")} for f in result]
    return [result]


def prefect_runs(limit: int = 20, state: str = None) -> list[dict]:
    """List flow runs."""
    data = {"limit": limit, "sort": "START_TIME_DESC"}
    if state:
        data["flow_runs"] = {"state": {"type": {"any_": [state.upper()]}}}
    
    result = prefect_request("POST", "flow_runs/filter", data)
    if isinstance(result, list):
        return [{
            "name": r.get("name"),
            "state": r.get("state_type"),
            "started": r.get("start_time"),
            "id": r.get("id"),
        } for r in result]
    return [result]


def prefect_trigger(deployment_id: str, params: dict = None) -> dict:
    """Trigger a deployment run."""
    data = {}
    if params:
        data["parameters"] = params
    
    return prefect_request("POST", f"deployments/{deployment_id}/create_flow_run", data)


# ============================================
# RAILWAY
# ============================================

def railway_request(query: str, variables: dict = None) -> dict:
    """Make Railway GraphQL request."""
    
    if not RAILWAY_TOKEN:
        return {"error": "Railway_Token not set"}
    
    url = "https://backboard.railway.app/graphql/v2"
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    req = Request(url, method="POST",
                  data=json.dumps(payload).encode(),
                  headers={
                      "Content-Type": "application/json",
                      "Authorization": f"Bearer {RAILWAY_TOKEN}",
                  })
    
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        return {"error": f"Railway API error: {e.code}"}


def railway_projects() -> list[dict]:
    """List Railway projects."""
    query = """
        query {
            projects {
                edges {
                    node {
                        id
                        name
                        createdAt
                    }
                }
            }
        }
    """
    result = railway_request(query)
    if "data" in result:
        return [edge["node"] for edge in result["data"]["projects"]["edges"]]
    return [result]


def railway_deployments(project_id: str = None) -> list[dict]:
    """List recent deployments."""
    query = """
        query($projectId: String) {
            deployments(first: 10, input: {projectId: $projectId}) {
                edges {
                    node {
                        id
                        status
                        createdAt
                        service {
                            name
                        }
                    }
                }
            }
        }
    """
    result = railway_request(query, {"projectId": project_id})
    if "data" in result:
        return [{
            "id": edge["node"]["id"],
            "status": edge["node"]["status"],
            "service": edge["node"].get("service", {}).get("name"),
            "created": edge["node"]["createdAt"],
        } for edge in result["data"]["deployments"]["edges"]]
    return [result]


# ============================================
# ROUTER
# ============================================

def route(action: str, target: str, **kwargs) -> list[dict] | dict:
    """Route to appropriate infra handler."""
    
    limit = kwargs.get("limit", 20)
    state = kwargs.get("state")
    deployment_id = kwargs.get("deployment_id")
    project_id = kwargs.get("project_id")
    
    if target == "prefect":
        if action == "health":
            return [prefect_health()]
        elif action == "flows":
            return prefect_flows(limit)
        elif action == "runs":
            return prefect_runs(limit, state)
        elif action == "trigger":
            if not deployment_id:
                return [{"error": "deployment_id required"}]
            return [prefect_trigger(deployment_id)]
        else:
            return [{"error": f"Unknown action for prefect: {action}"}]
    
    elif target == "railway":
        if action == "projects":
            return railway_projects()
        elif action == "deployments":
            return railway_deployments(project_id)
        else:
            return [{"error": f"Unknown action for railway: {action}"}]
    
    else:
        return [{"error": f"Unknown target: {target}"}]


def format_results(results: list, action: str) -> str:
    """Format results for display."""
    
    if not results:
        return "No results."
    
    if "error" in results[0]:
        return f"❌ Error: {results[0]['error']}"
    
    output = [f"🔧 {action.upper()} Results", "=" * 50]
    
    for i, item in enumerate(results[:20], 1):
        if action == "runs":
            output.append(f"[{i}] {item.get('name', '?')}")
            output.append(f"    State: {item.get('state')} | Started: {item.get('started', '')[:19]}")
        elif action == "flows":
            output.append(f"[{i}] {item.get('name')}")
            output.append(f"    ID: {item.get('id')}")
        elif action == "projects":
            output.append(f"[{i}] {item.get('name')}")
            output.append(f"    ID: {item.get('id')}")
        elif action == "deployments":
            output.append(f"[{i}] {item.get('service', '?')}")
            output.append(f"    Status: {item.get('status')} | {item.get('created', '')[:19]}")
        else:
            output.append(json.dumps(item, indent=2))
        output.append("")
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Infrastructure Master Tool")
    parser.add_argument("action", choices=["health", "flows", "runs", "trigger", "projects", "deployments"])
    parser.add_argument("target", choices=["prefect", "railway"])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--state", help="Filter by state (prefect)")
    parser.add_argument("--deployment-id", help="Deployment ID to trigger")
    parser.add_argument("--project-id", help="Railway project ID")
    parser.add_argument("--json", action="store_true")
    
    args = parser.parse_args()
    
    results = route(
        action=args.action,
        target=args.target,
        limit=args.limit,
        state=args.state,
        deployment_id=args.deployment_id,
        project_id=args.project_id,
    )
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_results(results, args.action))


if __name__ == "__main__":
    main()
