"""MCP SDK transport integration against a temporary authenticated HTTP fixture."""
import json
import importlib.util
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

if importlib.util.find_spec("mcp") is None:
    pytest.skip("Install the optional MCP SDK to exercise its transport", allow_module_level=True)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT = "d133c995-08cd-4a8f-9c01-cc11b800be49"


class ScopedApi(BaseHTTPRequestHandler):
    def do_GET(self):
        valid = self.headers.get("Authorization") == "Bearer stdio-test-token"
        permitted = self.path == f"/api/v1/graph-projects/{PROJECT}/versions"
        self.send_response(200 if valid and permitted else 404 if valid else 401)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"data": {"versions": []}}).encode())

    def log_message(self, *_):
        pass


def test_mcp_requires_token_and_retains_api_scope():
    import anyio

    async def exercise():
        with ThreadingHTTPServer(("127.0.0.1", 0), ScopedApi) as http:
            worker = Thread(target=http.serve_forever, daemon=True)
            worker.start()
            try:
                for token, expected_error in (("stdio-test-token", None), ("invalid-token", "HTTP 401")):
                    env = {**os.environ, "KG_MCP_API_URL": f"http://127.0.0.1:{http.server_port}/api/v1",
                           "KG_MCP_ACCESS_TOKEN": token}
                    params = StdioServerParameters(command=sys.executable, args=["-B", "-m", "backend.graph_mcp"], env=env)
                    async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
                        await client.initialize()
                        tools = await client.list_tools()
                        assert any(tool.name == "list_graph_versions" for tool in tools.tools)
                        result = await client.call_tool("list_graph_versions", {"project": PROJECT})
                        assert result.isError == bool(expected_error)
                        if expected_error:
                            assert expected_error in result.content[0].text
                        else:
                            denied = await client.call_tool("list_graph_versions", {"project": "00000000-0000-0000-0000-000000000000"})
                            assert denied.isError and "HTTP 404" in denied.content[0].text
            finally:
                http.shutdown()
                worker.join()

    anyio.run(exercise)
