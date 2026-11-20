# MCP server

The optional integration uses the official Python MCP SDK with stdio. It proxies typed graph tools through the authenticated FastAPI service. Every request keeps the application's project and graph-version checks. Database credentials stay with FastAPI. The MCP participant receives only an application bearer token. Tools cover projects, versions, schema, node search and detail, neighborhoods, shortest paths, cached analytics, structural candidate ranking, and compiled read-only Cypher.

Install `backend/requirements-mcp.txt` in the client-side Python environment and start the server from the repository root. Set `KG_MCP_API_URL` to the HTTPS API URL or local HTTP endpoint. Set `KG_MCP_ACCESS_TOKEN` through the client secret mechanism to a valid token from the existing application login. The token inherits its user's roles and expiration. Configure the MCP client's stdio command as follows.

```json
{
  "command": "<python-executable>",
  "args": ["-m", "backend.graph_mcp"],
  "env": {
    "KG_MCP_API_URL": "<graph-platform-api-base-url>",
    "KG_MCP_ACCESS_TOKEN": "<injected-application-bearer-token>"
  }
}
```

The integration logs tool names to stderr. HTTP service rejection becomes an MCP tool error. There is no remote MCP listener or client management UI in this milestone. The SDK is optional because the React and FastAPI deployment do not require an MCP client. [Official MCP Python SDK](https://py.sdk.modelcontextprotocol.io/)
