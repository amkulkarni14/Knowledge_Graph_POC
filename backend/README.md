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

The aggregate request limit is independent of per-file limits. Only CSV uploads are supported. The framework may spool multipart files temporarily after the aggregate limit check; they are closed after parsing. The source connector holds parsed data in memory.

Passwords are accepted only for server-side source connections and excluded from API responses/errors. Groq and Neo4j credentials stay in the server environment. Never put credentials in VITE_ variables.

`GET /domains` and `POST /domains` list and create reusable scope templates for the signed-in account. `GET /ontologies` lists saved working drafts and numbered ontology versions for account-owned workspaces. The ownership catalog and ontology artifacts live under `KG_API_STORAGE_DIR`. Session folders created before ownership tracking lack a recorded owner and are excluded from the library.

## Minimal CSV workflow

~~~powershell
$base = "http://127.0.0.1:8000/api/v1"
$token = (Invoke-RestMethod -Method Post -Uri "$base/login" -ContentType "application/json" -Body (@{username=$env:KG_API_USER;password=$env:KG_API_PASSWORD} | ConvertTo-Json)).access_token
$headers = @{Authorization="Bearer $token"}
$created = Invoke-RestMethod -Headers $headers -Method Post -Uri "$base/sessions" -ContentType "application/json" -Body '{"name":"Customer workspace"}'
$sid = $created.data.id
$p = "$base/sessions/$sid"

curl.exe --fail-with-body -H "Authorization: Bearer $token" -F "files=@customers.csv" -F "files=@accounts.csv" "$p/sources/upload"
Invoke-RestMethod -Headers $headers -Method Put -Uri "$p/scope" -ContentType "application/json" -Body '{"project":"Customer workspace","business_questions":["How are customers connected to accounts?"]}'
Invoke-RestMethod -Headers $headers -Method Post -Uri "$p/metadata/extract"
Invoke-RestMethod -Headers $headers -Method Post -Uri "$p/metadata/analyze"
Invoke-RestMethod -Headers $headers -Method Post -Uri "$p/ontology/draft" -ContentType "application/json" -Body '{"mode":"schema"}'
Invoke-RestMethod -Headers $headers -Method Post -Uri "$p/ontology/draft/save"
Invoke-RestMethod -Headers $headers -Method Post -Uri "$p/ontology/suggestions/skip"
Invoke-RestMethod -Headers $headers -Method Post -Uri "$p/ontology/review" -ContentType "application/json" -Body '{"actor":"data.modeller"}'
Invoke-RestMethod -Headers $headers -Method Post -Uri "$p/ontology/validate"
Invoke-RestMethod -Headers $headers -Method Post -Uri "$p/ontology/approve" -ContentType "application/json" -Body '{"author":"data.modeller","reviewer":"reviewer.lead"}'
Invoke-RestMethod -Headers $headers -Method Post -Uri "$p/builds" -ContentType "application/json" -Body '{}'
Invoke-RestMethod -Headers $headers -Uri "$p/builds/status"

# Wait until status is completed before saving stage 16.
Invoke-RestMethod -Headers $headers -Method Post -Uri "$p/graphs/snapshots" -ContentType "application/json" -Body '{}'
Invoke-RestMethod -Headers $headers -Uri "$p/graphs/data?limit=300"
~~~

Poll build status until completed, blocked or failed. Blocking validation reports remain available through builds/stages/12 or builds/stages/15. Builds do not automatically approve ontologies.

For PostgreSQL, send a connection request to `POST /sources/postgres` in place of the CSV upload. To generate suggestions, configure Groq and call `POST /ontology/suggestions`.

Snapshot payload {"load_neo4j":true} queues staged Neo4j publication and returns a job with HTTP 202. Poll the build status endpoint. See [Published graph platform](../docs/PUBLISHED_GRAPH_PLATFORM.md) for migration, database setup and operation.

## Tests

~~~powershell
python -m pip install -r backend/requirements-dev.txt
python -B -m pytest -p no:cacheprovider backend/tests -q
python -B -m pytest -p no:cacheprovider data_pipeline/tests -q
~~~

Tests use temporary storage, offline fixtures and mocked external connections. TestClient emits a third-party Starlette deprecation warning for httpx; tests still run.

See ../docs/api-integration.md for endpoint mapping, client patterns and limitations.

## Ontology workflow policy

The backend defaults to `KG_WORKFLOW_POLICY=governed`. For a local POC, set
`KG_WORKFLOW_POLICY=poc_validation_only` before starting the backend. For Docker
Compose, put the setting in `docker/.env` and rebuild and recreate the app
services. Set `KG_DEPLOYMENT_ENV=production` in production. The backend rejects
validation-only mode when the deployment environment is marked production.

Validation-only mode hides AI Suggestions, Review & Approval, and Ontology
Versioning. Save the ontology in Ontology Studio and run Ontology Validation.
Only the successfully validated revision can feed the build. Editing or
replacing that draft invalidates validation and downstream results. The policy
does not approve the ontology or create an approval record. Workflow events and
new graph artifacts retain the validation digest for lineage.

Set the policy back to `governed` or unset it and restart the backend to restore
the approval workflow. A backend restart ends process-local workspace sessions.
Existing stored ontology versions, approval records, and published graphs remain
on their existing storage.

## Guided data connectors

Stage 2 uses a candidate connection. Test connection checks access and closes
its temporary handle. Connect opens a session-owned candidate for discovery and
preview. Confirm selection publishes the selected asset set as the active source.
Cancel closes the candidate. Disconnect clears the active connection and its
dependent stages. Existing CSV upload and PostgreSQL endpoints still activate
sources directly for API clients.

The connector manifest is at GET /api/v1/source-types. Under the existing
session sources route the guided operations are POST /test, POST /locations,
POST /connections, and multipart POST /connections/upload. Candidate operations
use GET /connections/candidate and GET /connections/{id}/assets,
POST /connections/{id}/preview or /select, and DELETE /connections/{id}.
DELETE /sources disconnects the active source. Full extraction uses stage 11.

| Setting | Purpose |
|---|---|
| KG_SOURCE_ENDPOINTS | Comma-separated exact host:port pairs approved for database and custom S3 connections. |
| KG_SOURCE_DEV_ENDPOINTS | Explicit non-production hostname and port exceptions for local services. Compose defaults to postgres:5432. |
| KG_SOURCE_S3_ENDPOINTS | Comma-separated exact custom S3 origins. Supply endpoint-specific credentials. |
| KG_SOURCE_MAX_ROWS / KG_SOURCE_MAX_BYTES | Guided staging limits, default 100,000 rows and 128 MiB of estimated row data. |
| KG_SOURCE_ORACLE_WALLET_DIR / KG_SOURCE_ORACLE_WALLET_PASSWORD | Optional deployment-managed Oracle TLS wallet. |
| INSTALL_SQL_SERVER_DRIVER | Optional Docker build flag. Set true when accepting the Microsoft ODBC Driver 18 license and installing that driver in the Linux image. |

Use read-only source identities and restrict connector egress to permitted
network destinations, especially for SDKs and drivers that resolve names
internally. The Axios client submits credentials only for an explicit
operation. The API keeps connection handles in session memory and returns
sanitized status and errors. Configure platform trust or PGSSLROOTCERT for
verified TLS.

The source selector advertises CSV for local files and supported cloud objects.
Object paths are listed through SDK pagination and indexed up to 1,000 entries
in the chosen prefix. Use a narrower prefix for larger buckets. Preview reads
a bounded range, and selected objects remain subject to existing file limits.
For a partially sampled object, configure an explicit ontology key mapping.
Excel, TSV, JSON, and Parquet remain outside the supported formats.

Oracle uses Thin mode and TCPS. SQL Server uses ODBC Driver 18 with certificate
validation and SQL authentication. S3 accepts default or temporary credentials
and explicit keys, Azure accepts default identity, service principal, key or
SAS, and Google sources use Application Default Credentials. BigQuery applies
a dry run and caps generated query scans at 64 MiB. Cloud credential chains and
trust material are configured in the deployment environment.

## Business Insights

The read-only `GET /api/v1/sessions/{session_id}/insights` endpoint uses the
active connector and workspace schema. Dataset, date, category, and numeric
filters apply within the selected profile. The API reports the observed row
count and whether it reached the profile limit. Graph filters apply to the
selected validated graph or workspace snapshot. Data quality findings come
from the latest pipeline report for the dataset and are independent of row
filters.

The service caches the latest selection per workspace for up to 60 seconds.
Use `refresh=true` to bypass the cache. `KG_INSIGHTS_ROWS` defaults to 5,000
(maximum 25,000). Graph analytics default to a maximum of 100,000 nodes and
300,000 edges, configurable through `KG_INSIGHTS_GRAPH_NODES` and
`KG_INSIGHTS_GRAPH_EDGES`. The interactive preview shows up to 60 masked
entities and 160 relationships. Pass these optional variables into the backend
container environment if overriding the defaults.

Field discovery excludes declared keys, sensitive scope fields, and ontology
attributes marked as PII. Category and trend groups with fewer than three
observations are omitted. Use scope and ontology sensitivity settings to
classify fields that contain sensitive data. The dashboard provides aggregate
CSV, trend PNG, and browser print-to-PDF.

## Ask Your Knowledge Graph

In Graph Explorer, select the current workspace graph or a saved snapshot and
open **Ask Your Knowledge Graph**. In the backend environment set
`KG_GRAPH_AI_ENABLED=true`, `KG_GRAPH_AI_MODEL` to the configured provider model,
and `GROQ_API_KEY` to its server-side credential. Compose reads these settings
from `docker/.env`. Suggestions and manual exploration work with AI disabled.

Set `KG_GRAPH_AI_PROVIDER=groq` (the default) to keep the existing provider.
Choose `rules` for offline predefined questions or `ollama` for a local model.
Both use the same schema validation and execution path. Ollama connection or
model failures fall back to predefined entity and relationship questions,
counts, graph summaries, and paths between quoted node IDs. The UI shows the
provider that answered and asks for clarification on unsupported questions.
The status endpoint checks Ollama's installed model tags. For Groq it checks
configuration presence, and the first query checks live connectivity.

For Windows Docker Desktop, install and start Ollama for Windows, then run
`ollama pull qwen2.5:7b` and `ollama list`. Set `KG_GRAPH_AI_ENABLED=true`,
`KG_GRAPH_AI_PROVIDER=ollama`, `KG_GRAPH_AI_MODEL=qwen2.5:7b`, and
`OLLAMA_BASE_URL=http://host.docker.internal:11434` in `docker/.env`.
Use `http://127.0.0.1:11434` when running the backend directly on Windows.
If Docker cannot reach the default listener, bind Ollama to a host interface
reachable by Docker Desktop and limit port 11434 to trusted local access.
Recreate the backend to apply runtime settings. The setting affects Ask Your
Knowledge Graph. Stage Help and the published Neo4j workbench retain Groq.

The workspace endpoints are `GET /api/v1/sessions/{id}/graphs/questions/suggestions`
and `POST /api/v1/sessions/{id}/graphs/questions`. The model chooses a typed plan
for a node label or a directed relationship pattern. Supported plans list or
count matches, optionally filtering a supported property by a literal substring.
Workspace plans run against the existing NetworkX graph or checked snapshot.
Historical snapshots support labels and relationships. The existing published
Neo4j Query Workbench continues to draft and validate its read-only Cypher
subset separately.

The provider receives the question, one previous question, and bounded schema
identifiers. The explanation request contains calculated counts. Graph property
values, record IDs, and connection credentials are excluded from the model
context. The model orders verified statements, and the application assembles the
explanation and links it to the result table and visual evidence.

Queries have a maximum of 100,000 nodes and 250,000 relationships, a three-second
execution deadline, two concurrent requests, and up to 40 displayed matches.
Provider calls use the existing 20-second timeout. The query plan and returned
evidence are inspectable. Workspace question history is kept in browser memory.

For future stage assistants, reuse the provider interface and stage-help panel.
Give each stage a bounded fact collector and a typed response contract. Keep
schema, ontology, validation, build, and quality facts read-only. For Path
Analysis and Business Insights, supply existing path evidence and aggregate
definitions with source references. Keep operations behind each stage's
existing explicit controls.
