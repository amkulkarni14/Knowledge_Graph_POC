"""Local MCP server using the existing authenticated Graph Platform API."""
import logging
import os
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from mcp.server.fastmcp import FastMCP

server = FastMCP("Knowledge Graph Platform")
log = logging.getLogger("kg.mcp")


def call(path, *, params=None, body=None):
    base = os.getenv("KG_MCP_API_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
    token = os.getenv("KG_MCP_ACCESS_TOKEN")
    url = urlsplit(base)
    loopback = url.hostname in {"localhost", "127.0.0.1", "::1"}
    if (not token or url.username or url.password or url.query or url.fragment
            or not (url.scheme == "https" or (loopback and url.scheme == "http"))):
        raise ValueError("Configure a bearer token and an HTTPS or local Graph Platform API URL")
    try:
        with httpx.Client(timeout=20, headers={"Authorization": "Bearer " + token}) as client:
            response = client.request("GET" if body is None else "POST", base + path, params=params, json=body)
            if not response.is_success:
                raise ValueError(f"Graph API rejected the request (HTTP {response.status_code})")
            return response.json()["data"]
    except httpx.HTTPError:
        raise ValueError("Graph API connection failed") from None


def scope(project: UUID, version: UUID):
    return f"/graph-projects/{project}/versions/{version}"


@server.tool()
def list_graph_projects() -> list[dict]:
    """List graph projects visible to the authenticated user."""
    log.info("list_graph_projects")
    return call("/graph-projects")


@server.tool()
def list_graph_versions(project: UUID) -> dict:
    """List versions visible to the authenticated user."""
    log.info("list_graph_versions")
    return call(f"/graph-projects/{project}/versions")


@server.tool()
def get_graph_schema(project: UUID, version: UUID) -> dict:
    """Inspect schema of an authorized published version."""
    log.info("get_graph_schema")
    return call(scope(project, version) + "/schema")


@server.tool()
def search_nodes(project: UUID, version: UUID, search: str, label: str = "") -> dict:
    """Search up to 20 nodes by ID or name, optionally restricted by label."""
    log.info("search_nodes")
    return call(scope(project, version) + "/query",
                params={"template": "entities", "search": search, "label": label, "limit": 20})


@server.tool()
def get_node_details(project: UUID, version: UUID, node_id: str) -> dict:
    """Get one node and its immediate relationships from a published graph."""
    log.info("get_node_details")
    graph = call(scope(project, version) + "/neighborhood", params={"node_id": node_id, "limit": 20})
    return {"node": next((node for node in graph["nodes"] if node["id"] == node_id), None),
            "relationships": graph["edges"], "truncated": graph["truncated"]}


@server.tool()
def explore_neighborhood(project: UUID, version: UUID, node_id: str, hops: int = 1) -> dict:
    """Load a bounded one- or two-hop graph around an entity."""
    log.info("explore_neighborhood")
    return call(scope(project, version) + "/neighborhood", params={"node_id": node_id, "hops": hops, "limit": 20})


@server.tool()
def find_shortest_path(project: UUID, version: UUID, source: str, target: str) -> dict:
    """Find a shortest path up to 12 hops in one graph version."""
    log.info("find_shortest_path")
    return call(scope(project, version) + "/paths", params={"source": source, "target": target})


@server.tool()
def get_graph_analytics(project: UUID, version: UUID) -> dict:
    """Return cached statistics and ranking results for the selected version."""
    log.info("get_graph_analytics")
    return call(scope(project, version) + "/analytics")


@server.tool()
def rank_graph_candidates(project: UUID, version: UUID, node_id: str, target_label: str = "") -> dict:
    """Rank bounded two-hop links and similar entities, with supporting node IDs."""
    log.info("rank_graph_candidates")
    return call(scope(project, version) + "/intelligence", params={"node_id": node_id, "target_label": target_label})


@server.tool()
def execute_readonly_graph_query(project: UUID, version: UUID, cypher: str) -> dict:
    """Execute the platform's validated Cypher subset on one published version."""
    log.info("execute_readonly_graph_query")
    return call(scope(project, version) + "/query", body={"cypher": cypher})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    server.run(transport="stdio")
