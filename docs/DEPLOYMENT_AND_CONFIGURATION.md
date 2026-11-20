# Deployment and configuration

Use the existing backend, React build and PostgreSQL metadata migrations. This upgrade adds no database DDL. GraphML writes use the existing staged import and Neo4j constraint. Restart both components after updating source. For Docker deployments, rebuild and recreate the affected services.

Runtime variable names are `KG_META_DSN`, `NEO4J_URI`, `NEO4J_DATABASE`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_READ_USER`, `NEO4J_READ_PASSWORD`, and `KG_GRAPH_ID_KEY` when sensitive identifiers require pseudonymization. Use `SSL_CERT_FILE` for a trusted custom CA bundle if required. For AI set `KG_GRAPH_AI_ENABLED`, `KG_GRAPH_AI_MODEL` and `GROQ_API_KEY`. Enable graph AI only when sharing bounded graph facts and question text with the selected provider is approved. MCP uses `KG_MCP_API_URL` and `KG_MCP_ACCESS_TOKEN` in the external client process.

Use process secrets or an approved secret store. The root environment file is tracked. Keep TLS verification enabled and use distinct database read/write identities where the deployment supports it. Verify authentication, a published read, and staged import in the target environment before rollout.

Run the Python offline suites with the backend test dependencies, then the disposable live integration with isolated PostgreSQL and Neo4j. Install the optional MCP dependencies for the transport tests. Run React unit tests and build checks from `frontend`. Real provider and production-scale load tests require approved environments and representative data.

```text
python -m pip install -r backend/requirements-dev.txt -r backend/requirements-mcp.txt
python -m pytest backend/tests data_pipeline/tests
cd frontend
npm run build
npm run lint
npm test -- --pool=threads
```

Enable the disposable database test with that fixture's `KG_TEST_SOURCE`, metadata DSN and Neo4j credentials. See the [published platform guide](PUBLISHED_GRAPH_PLATFORM.md) for fixture setup.
