# Graph intelligence API

All routes are under `/api/v1`. Normal bearer authentication applies. Published graph routes require access to the project and a ready version. Session routes require ownership.

| Method | Relative path | Purpose |
|---|---|---|
| GET | `/sessions/{id}/graphs/intelligence` | Structural rankings for an anchor in workflow memory |
| GET | `/sessions/{id}/graphs/graphml/neighborhood` | Export a scoped neighborhood |
| POST | `/sessions/{id}/graphs/graphml/preview` | Preview multipart GraphML against approved ontology |
| POST | `/sessions/{id}/graphs/graphml/publish` | Queue validated GraphML staging |
| GET | `/graph-projects/{project}/versions/{version}/intelligence` | Rank a published neighborhood, with optional target label |
| GET | `/graph-projects/{project}/versions/{version}/graphml/neighborhood` | Export a published sample |
| POST | `/graph-projects/{project}/versions/{version}/query-draft` | Draft and validate Cypher without execution |
| POST | `/graph-projects/{project}/versions/{version}/graph-rag` | Retrieve graph facts and return a cited answer |
| POST | `/graph-projects/{project}/versions/{version}/investigate` | Run a bounded investigation with trace |

GraphML form fields are `file`, `label_key` and `relationship_key`. The operations API exposes the queued job. Structural queries require `node_id` and accept `target_label`. Drafting accepts `question`; GraphRAG and investigation accept `node_id` and `question`. Use the existing `POST .../query` endpoint to execute reviewed Cypher. See [generated OpenAPI](../frontend/docs/openapi.json) for the complete contract.
