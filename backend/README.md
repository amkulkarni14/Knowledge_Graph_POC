# Knowledge Graph backend

FastAPI adapters for the 16-stage pipeline. See the [Docker guide](../docker/README.md) to run the backend alongside the React frontend and local databases.

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

## Authentication (JWT)

Every route except `GET /api/v1/health` and `POST /api/v1/login` requires `Authorization: Bearer <token>`; a missing, invalid, expired or logged-out token returns `401`.

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/login` | `{"username","password"}` returns `{"access_token","token_type":"bearer","user":{"username"}}`, or `401` |
| `GET /api/v1/me` | Validates the current token (used by the frontend on page refresh) |
| `POST /api/v1/logout` | Revokes the token (process-local deny-list, like sessions) |

The default account is configured in `.env` (`AUTH_DEFAULT_USERNAME`, `AUTH_DEFAULT_PASSWORD_HASH` as a bcrypt hash). For local development it is `admin` / `admin`; change it before any shared use. Authentication is in `backend/app/core/security.py` (`authenticate()` is the single place to replace with a users-table lookup). If `JWT_SECRET_KEY` is empty a random key is generated per start, so tokens do not survive a restart.

Workflow sessions are owned by the authenticated user. Published graph projects support owner and viewer permissions through the PostgreSQL metadata registry. Ontology author and reviewer fields remain workflow labels. Bind to loopback for local development and serve over HTTPS if shared.

## Configuration

Set optional variables in the shell before starting the server. Existing environment files are unchanged.

| Variable | Default | Purpose |
|---|---|---|
| KG_API_STORAGE_DIR | repository storage/api_sessions | Session-specific artifacts |
| KG_API_CORS_ORIGINS | http://localhost:5173,http://127.0.0.1:5173 | Explicit comma-separated frontend origins |
| JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES | Random key per start, HS256, 60 | Token signing and lifetime |
| AUTH_DEFAULT_USERNAME, AUTH_DEFAULT_PASSWORD_HASH | admin, unset (login disabled) | Default account (bcrypt hash) |
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

Snapshot payload {"load_neo4j":true} queues staged Neo4j publication and returns a job with HTTP 202. Poll the build status endpoint. See [Published graph platform](../docs/PUBLISHED_GRAPH_PLATFORM.md) for migration, database setup and operation.

## Tests

~~~powershell
python -m pip install -r backend/requirements-dev.txt
python -B -m pytest -p no:cacheprovider backend/tests -q
python -B -m pytest -p no:cacheprovider data_pipeline/tests -q
~~~

Tests use temporary storage, offline fixtures and mocked external connections. TestClient emits a third-party Starlette deprecation warning for httpx; tests still run.

See ../docs/api-integration.md for endpoint mapping, client patterns and limitations.
