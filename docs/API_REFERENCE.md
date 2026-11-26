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

## Entity exploration

Both endpoints are available under `/sessions/{id}/graphs` and under `/graph-projects/{project}/versions/{version}`. Workspace requests accept `ontology_id` and `build_id` to select a saved snapshot.

| Method | Suffix | Purpose |
|---|---|---|
| GET | `/entities` | List graph entity types when `q` is omitted. With `q`, find exact identifiers or up to 20 prefix suggestions when `prefix=true`. Optional `label` filters results. |
| GET | `/entity-neighborhood` | Retrieve an entity by its graph `node_id`, its incoming and outgoing counts, and the bounded graph reached in `hops` (0–3). Zero hops returns the entity for inspection. |

IDs follow the graph builder’s case-sensitive key format and preserve leading zeros. Enter composite key parts in mapping order, separated by `|`. Traversal returns at most 100 nodes and 300 relationships. The response indicates truncation and reports whole-version totals separately. Graphs created before versioned ontology context was captured still resolve stored entity IDs and may return an empty ontology context.
