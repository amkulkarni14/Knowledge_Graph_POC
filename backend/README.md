# Knowledge Graph backend

FastAPI adapters for the existing 16-stage pipeline. Legacy Streamlit code and processing algorithms are unchanged.

## Install and run

From the Knowledge_Graph repository root, with the existing virtual environment activated:

~~~powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
~~~

- Interactive documentation: http://127.0.0.1:8000/docs
- OpenAPI contract: http://127.0.0.1:8000/openapi.json
- Health: http://127.0.0.1:8000/api/v1/health

Use one worker. Sessions, source connections, editor state and background-job status are process-local and expire after one hour of inactivity. A restart loses those handles. Saved artifacts remain on disk, but there is no session recovery API.

No authentication or authorization is implemented because the existing prototype has none. Bind to loopback for local development. Session UUIDs are not authenticated identities; author/reviewer names are workflow labels, not verified user identities. Add authentication/access control before shared deployment.

## Configuration

Set optional variables in the shell before starting the server. Existing environment files are unchanged.

| Variable | Default | Purpose |
|---|---|---|
| KG_API_STORAGE_DIR | repository storage/api_sessions | Session-specific artifacts |
| KG_API_CORS_ORIGINS | http://localhost:5173,http://127.0.0.1:5173 | Explicit comma-separated frontend origins |
| GROQ_API_KEY, GROQ_MODEL | Existing pipeline settings | Optional live suggestions |
| NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD | Unconfigured | Optional server-side Neo4j loading |
| KG_MAX_UPLOAD_FILES, KG_MAX_UPLOAD_MB, KG_MAX_UPLOAD_ROWS | Existing pipeline defaults | Source upload limits |

ApiSettings also controls the aggregate request limit (64 MiB), session TTL (3600 seconds), session capacity (100) and accepted background jobs (2). Pipeline calls serialize while temporarily selecting session-specific storage, restoring the original setting on success or failure. Distributed workers require durable session/job state and removal of the shared pipeline Settings dependency.

The aggregate request limit is independent of per-file limits. Only CSV/TSV/text uploads are supported. The framework may spool multipart files temporarily after the aggregate limit check; they are closed after parsing. The source connector holds parsed data in memory.

Passwords are accepted only for server-side source connections and excluded from API responses/errors. Groq and Neo4j credentials stay in the server environment. Never put credentials in VITE_ variables.

## Minimal sample workflow

~~~powershell
$base = "http://127.0.0.1:8000/api/v1"
$created = Invoke-RestMethod -Method Post -Uri "$base/sessions" -ContentType "application/json" -Body '{"name":"Retail demo"}'
$sid = $created.data.id
$p = "$base/sessions/$sid"

Invoke-RestMethod -Method Put -Uri "$p/scope" -ContentType "application/json" -Body '{"project":"Retail","business_questions":["How are customers connected to orders?"]}'
Invoke-RestMethod -Method Post -Uri "$p/sources/sample"
Invoke-RestMethod -Method Post -Uri "$p/metadata/extract"
Invoke-RestMethod -Method Post -Uri "$p/metadata/analyze"
Invoke-RestMethod -Method Post -Uri "$p/ontology/draft" -ContentType "application/json" -Body '{"mode":"template"}'
Invoke-RestMethod -Method Post -Uri "$p/ontology/draft/save"
Invoke-RestMethod -Method Post -Uri "$p/ontology/suggestions/skip"
Invoke-RestMethod -Method Post -Uri "$p/ontology/review" -ContentType "application/json" -Body '{"actor":"data.modeller"}'
Invoke-RestMethod -Method Post -Uri "$p/ontology/validate"
Invoke-RestMethod -Method Post -Uri "$p/ontology/approve" -ContentType "application/json" -Body '{"author":"data.modeller","reviewer":"reviewer.lead"}'
Invoke-RestMethod -Method Post -Uri "$p/builds" -ContentType "application/json" -Body '{}'
Invoke-RestMethod -Uri "$p/builds/status"

# Wait until status is completed before saving stage 16.
Invoke-RestMethod -Method Post -Uri "$p/graphs/snapshots" -ContentType "application/json" -Body '{}'
Invoke-RestMethod -Uri "$p/graphs/data?limit=300"
~~~

Poll build status until completed, blocked or failed. Blocking validation reports remain available through builds/stages/12 or builds/stages/15. Builds do not automatically approve ontologies.

For CSV data, replace sources/sample with multipart sources/upload, then use draft mode "schema". Skip AI for uploaded data unless the live provider is configured; the recorded offline fixture fits only the retail sample.

Snapshot payload {"load_neo4j":true} invokes the existing loader, which writes graph data and constraints. It runs only when explicitly requested and server-configured. Verification uses mocks and does not contact live databases.

## Tests

~~~powershell
python -m pip install -r backend/requirements-dev.txt
python -B -m pytest -p no:cacheprovider backend/tests -q
python -B -m pytest -p no:cacheprovider data_pipeline/tests -q
~~~

Tests use temporary storage, offline fixtures and mocked external connections. TestClient emits a third-party Starlette deprecation warning for httpx; tests still run.

See ../docs/api-integration.md for endpoint mapping, client patterns and limitations.
