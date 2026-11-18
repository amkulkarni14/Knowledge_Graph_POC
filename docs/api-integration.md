# Frontend to backend integration

## Architecture and scope

React -> typed API client -> backend/app/api -> backend/app/services -> existing kg_pipeline -> source connections and session-specific artifacts.

No frontend implementation existed when this API was added. This change provides backend integration endpoints; it does not claim a completed React migration. Existing pipeline, Streamlit, datasets, schemas and configuration files are preserved.

## Frontend client

Use a public VITE_API_BASE_URL such as http://127.0.0.1:8000/api/v1. Create one Axios instance and generate request/response TypeScript types from /openapi.json.

~~~typescript
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
});
const created = await api.post("/sessions", { name: "Workspace" });
const sessionId = created.data.data.id;
const controller = new AbortController();
const graph = await api.get("/sessions/" + sessionId + "/graphs/data", {
  params: { limit: 300 },
  signal: controller.signal,
});
const form = new FormData();
selectedFiles.forEach((file) => form.append("files", file));
await api.post("/sessions/" + sessionId + "/sources/upload", form);
~~~

Let the browser set the multipart boundary. Client cancellation stops waiting; it does not cancel server work. There is no job-cancellation endpoint. Keep UI preferences/selections in Zustand, while source connections, pipeline contexts and approval state remain on the server. Do not persist credentials in browser state.

## Contracts

Successful JSON responses use {"data":...}. Paginated data contains items, total, offset and limit. Downloads return bytes. Session deletion returns 204 with no body.

Errors use {"error":{"code":"validation_error","message":"Request validation failed","details":[{"location":["body","port"],"type":"less_than_equal"}]}}. Submitted values and provider exception text are excluded.

| Status | Meaning |
|---|---|
| 400 | Malformed HTTP/multipart |
| 404 | Missing/expired session, version, table, node or snapshot |
| 409 | Prerequisite, concurrent mutation, state conflict or integrity failure |
| 413 | Request/file size limit |
| 422 | Invalid input, domain mapping, upload or review |
| 502 | Source/provider/storage failure with sanitized details |
| 503 | Session/build capacity |
| 500 | Unexpected failure with sanitized details |

A validation operation can return HTTP 200 with ok:false and actual findings. Such a stage is not marked complete and blocks downstream processing.

## Complete feature mapping

No API existed before this change. Routes below are relative to /api/v1/sessions/{session_id}, except the session/stage registry routes.

| Legacy source | Existing feature | Implemented API | Frontend feature |
|---|---|---|---|
| app.py, components/layout.py | Navigation, stage registry, completion | GET /api/v1/stages; GET session | Application shell/workflow |
| components/bootstrap.py | Session context/reset | POST /api/v1/sessions; GET/DELETE session | Session lifecycle |
| pages/home.py | Sample pipeline demonstration | Individual stage APIs plus POST /builds after explicit review/approval | Overview |
| pages/s01_scope.py | Scope/questions/tables/sensitive columns | GET/PUT /scope | Projects/scope |
| pages/s02_connect.py | Sample source | POST /sources/sample | Sources |
| pages/s02_connect.py | Read-only PostgreSQL connection | POST /sources/postgres | Sources |
| pages/s02_connect.py | CSV files, inferred keys/links, warnings | POST /sources/upload; GET /sources | Upload/source reports |
| pages/s03_schema.py | Catalog, columns, keys, metadata | POST /metadata/extract; GET /metadata, /metadata/tables, /metadata/columns, /metadata/preview | Schema |
| pages/s04_analysis.py | Table classification and relationship candidates | POST /metadata/analyze; GET /metadata/analysis | Analysis |
| pages/s05_manual.py | Empty/template/schema draft and notes | POST/GET/PUT /ontology/draft | Ontology studio |
| pages/s05_manual.py | Classes and attribute editor | POST /ontology/classes; PATCH/DELETE class; PUT class attributes | Class editor |
| pages/s05_manual.py | Relationships, mappings and properties | POST/DELETE /ontology/relationships | Relationship editor |
| pages/s05_manual.py | Save/revert editor | POST /ontology/draft/save, /ontology/draft/revert | Editor actions |
| pages/s06_ai.py | Offline/live AI, masking, allowlist, skip | POST/GET /ontology/suggestions; POST /ontology/suggestions/skip | AI suggestions |
| pages/s07_review.py | Approve/edit/reject, cycle/watermark rules | POST /ontology/review/preview, /ontology/review | Review |
| pages/s08_validate.py | Structural/semantic validation | POST /ontology/validate; GET /ontology/validation | Validation |
| pages/s09_repo.py | Save/approve with distinct author/reviewer | POST /ontology/approve | Approval |
| pages/s09_repo.py | Versions, audit, rollback, reuse approved | GET /ontology/versions, version, /ontology/audit; POST rollback, /ontology/use-approved | Version history |
| pages/s10_plan.py | Approved source-to-graph mappings | POST/GET /builds/stages/10 | Build plan |
| pages/s11_extract.py | Batches/checkpoints/watermarks/staged rows | POST/GET stage 11; GET /builds/extracted-rows | Extraction |
| pages/s12_quality.py | Rules/null/type/duplicate/orphan checks | POST/GET stage 12 | Data quality |
| pages/s13_clean.py | Canonical records, merges, changes, quarantine | POST/GET stage 13; GET /builds/cleaning/{kind} | Cleaning |
| pages/s14_build.py | Graph generation and build statistics | POST/GET stage 14; GET /graphs/data, /graphs/nodes, /graphs/node | Construction |
| pages/s15_gvalidate.py | Reconciliation, conformance and metrics | POST/GET stage 15 | Graph validation |
| pages/s16_store.py | Snapshots and optional Neo4j loading | POST /graphs/snapshots | Persistence |
| pages/s16_store.py | Exports, history and CURRENT promotion | GET /graphs/snapshots; GET artifact download; POST current | Snapshots |
| pages/explorer.py | Saved graph, neighborhood, path, degree rankings | GET /graphs/data, /graphs/nodes, /graphs/node, /graphs/path, /graphs/metrics | Exploration |
| components/layout.py | Activity and run feedback | GET /events; GET /builds/status | Progress/errors |
| components/graph_view.py, components/viz.py | Graph rendering, legends and layouts | Structured node/edge responses | Future React graph canvas |

The home page's automatic demo review is not an API approval bypass. API clients explicitly review and approve before starting a graph build. No UI features are claimed migrated in this backend-only change.

## Endpoint usage and safeguards

- Session creation accepts name and returns its UUID, stage completion and expiration.
- Scope requires project and at least one business question.
- PostgreSQL accepts host, port, dbname, user, password, sslmode and schemas, reusing the existing read-only connector.
- Upload accepts repeated multipart fields named files. All files validate before source replacement. Excel is unsupported.
- Metadata columns/preview require a qualified catalog table. Preview limit is 100.
- Draft creation takes mode new/template/schema with optional ontology_id, namespace, name and author. Template mode requires the sample source.
- Draft replacement takes {"ontology":{...}}. Class/relationship creation takes {"definition":{...}}. Unknown nested fields are rejected.
- Relationship deletion takes the full key as a query parameter, for example Customer-[PLACED]->Order.
- Suggestions take actor, use_groq, include_samples and allowed_tables. An explicit empty table allowlist is rejected.
- Review decisions are indexed by returned suggestion IDs. Invalid suggestions require an edited payload before acceptance; duplicate suggestions are informational.
- Review preview validates decisions without committing state; applied review supports cycle and watermark rules.
- Approval requires author to match the reviewed draft and reviewer to differ case-insensitively.
- Version/audit endpoints use ontology_id query parameters. Rollback creates a new draft and does not rewrite the old approved definition.
- POST /builds accepts batch_size (1..100000) and optional business_rules; returns 202 and runs stages 10..15. It does not save snapshots automatically.
- Individual build stages can be run with POST /builds/stages/{stage}. GET retrieves completed results or blocking validation reports.
- Business rules are qualified-table maps of column/rule pairs. Only non_negative and allowed_values with a nonempty values list are accepted. Arbitrary expressions/code are not accepted.
- Poll /builds/status until completed/blocked/failed. Stage 11 supplies per-table progress. Poll /events with offset/limit for completed-stage logs.
- Stage 16 takes optional load_neo4j; credentials come exclusively from server environment variables.
- Snapshot queries require ontology_id and use returned build_id timestamp identifiers. Only valid, checksum-verified snapshots can become CURRENT.
- Download path: /graphs/snapshots/{build_id}/download/{artifact}?ontology_id=...
- Artifacts are restricted to graph.json.gz, graph.graphml, quarantine.json and manifest.json. The three data artifacts are checksum-verified before serving.
- /graphs/data uses the current in-memory graph, or selects a saved snapshot with ontology_id and optional build_id. It supports node limit<=500, edge_limit<=2000, repeated labels, focus and hops 1..3.
- /graphs/nodes supports ID search, label filtering and pagination. /graphs/node returns bounded relationships.
- /graphs/path takes source/target and max_hops<=100; direction is ignored to match the legacy explorer.
- /graphs/metrics returns counts, components and a bounded degree-centrality ranking.
- Scope/source/editor changes invalidate downstream completion and derived results. Editor revert uses a separate last-saved draft; source changes discard it.
- Concurrent mutations return 409. Sessions are isolated; source connections close when sessions expire/delete.

## Limitations

No authentication, RBAC, persistent project catalog or session recovery is implemented. CORS is not authorization. Session artifacts are isolated under storage/api_sessions/{session_uuid}; existing legacy artifacts are not moved or exposed through these routes. Closing/expiring a session preserves disk artifacts; retention/recovery needs future design.

Graph JSON hides ontology-marked PII and scope-mapped sensitive properties; previews hide configured sensitive columns. Raw exports and detailed cleaning/audit reports can contain source data. These filters are not authorization or a full data-governance policy.

NetworkX processing remains in memory. Browser payloads and request sizes are bounded, but the original pipeline's memory characteristics remain. No arbitrary Cypher, graph editing, natural-language querying, Excel support or new analytics engine is implemented.

No React routes, Zustand stores, Axios implementation or production frontend build are included. No live PostgreSQL, Neo4j or Groq verification was performed. OpenAPI strongly types requests, ontology/catalog entities and graph responses; variable stage reports use JSON object schemas.

## Verification

The backend suite covers validation/redaction, sessions/expiration, concurrency rejection, workflow invalidation, failed-upload preservation, CSV/sample builds, offline AI parity, version rollback, upload limits, CORS, polling, storage restoration, downloads and corrupt exports.

The unchanged pipeline/CLI/Streamlit regression suite is tested separately. Offline tests do not establish live-service or React parity.


## Verified implementation results

- 58 API operations; OpenAPI 3.1 generation succeeds, including multipart upload schema.
- 40 backend API tests pass.
- All 200 pre-existing pipeline, CLI and Streamlit tests pass.
- Localhost Uvicorn startup, health and OpenAPI HTTP smoke test passes; the test server was stopped afterward.
- SHA-256 checks confirm all 93 pre-existing project/runtime files are unchanged.
- 22 new files added under backend/ and docs/; no existing project files modified or deleted and no .gitkeep files created.
- Backend/test dependencies installed into the existing project virtual environment.
- One third-party TestClient deprecation warning remains; it does not affect the passing tests.
- Live PostgreSQL/Neo4j/Groq behavior and React integration remain unverified.
