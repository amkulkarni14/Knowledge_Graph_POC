# Knowledge Graph React workspace

React and strict TypeScript frontend for the existing FastAPI application. All 16 workflow stages use backend session state. No backend, pipeline, ontology definition, dataset, or Streamlit changes are required.

## Run locally

From `Knowledge_Graph`, start the existing backend in a terminal:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. The default API URL is `http://127.0.0.1:8000/api/v1`. To change it, copy `.env.example` to `.env` and set `VITE_API_BASE_URL`. Only public configuration belongs in Vite environment variables.

Node must satisfy Vite's engine requirement (`20.19+` or `22.12+`); this workspace was checked using Node 26.13.0. Dependencies are locked in `package-lock.json`.

## Guided sample workflow

1. Create a workspace and save scope with a project name and at least one question.
2. Connect the retail sample, extract metadata, and analyze it.
3. Create a retail template draft and save it.
4. Generate offline suggestions or explicitly skip AI.
5. Review suggestions and apply review. Invalid suggestions require editing before acceptance. Configure cycle/watermark rules when appropriate.
6. Validate the ontology. Enter its reviewed author and a different reviewer, then explicitly approve it.
7. Run stages individually or confirm a complete build (stages 10–15). Monitor real status and events.
8. Save the validated graph in Stage 16. Neo4j loading is optional and requires explicit selection and server configuration.
9. Explore the current graph or a saved snapshot, inspect properties, find undirected paths, review metrics, and download artifacts.
10. Reset the workspace to delete its session.

For Customer 360, upload the CSV files in `../data/samples/customer360` together, choose a schema-derived ontology, and skip AI unless a live provider is explicitly desired. The offline AI fixture fits the retail source only. No live service connection was exercised during development.

## Contracts and checks

```powershell
npm run generate:api
npm run typecheck
npm run lint
npm test
npm run build
```

`generate:api` imports the existing Python app with bytecode writing disabled and emits `src/types/generated/openapi.ts` and `docs/openapi.json`. It does not run a pipeline or contact providers. Set `KG_PYTHON` to override the interpreter, or `KG_OPENAPI_URL=http://127.0.0.1:8000/openapi.json` to generate from HTTP instead.

Browser and real HTTP integration tests:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PWD '.local/browsers'
npx playwright install chromium
npm run test:e2e
```

Playwright starts Vite and the existing FastAPI app if those URLs are not already running. Its isolated backend uses `.local/e2e-sessions`. Tests never initiate live PostgreSQL, Groq, or Neo4j connections. Unit/component tests use controlled mocks; `e2e/api-workflow.spec.ts` and browser workflows use real local API responses. Browser failure tests explicitly intercept only their failure responses.

The Python backend and regression suites can be run unchanged from the repository root:

```powershell
New-Item -ItemType Directory -Force frontend/.local | Out-Null
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider backend/tests data_pipeline/tests -q --basetemp=frontend/.local/pytest-check
```

Use a new `--basetemp` directory for each run when preserving previous test output matters.

## Behavior and boundaries

- TanStack Query owns server state; Zustand stores only the active session and UI selections/preferences. Nothing sensitive is persisted in browser storage.
- Sessions expire after backend-configured inactivity and do not survive backend restarts. Refreshing the frontend loses its in-memory session handle. No recovery is promised.
- Mutations refresh session completion and clear derived caches. Outgoing reads support cancellation. Late mutation results cannot overwrite another workspace.
- Build polling stops at terminal status or unmount. Leaving the page stops monitoring; it does not cancel server processing.
- Graph exploration is bounded and read-only. Pathfinding ignores relationship direction.
- Arbitrary JSON fields in broad backend reports are displayed as inspectable details. Advanced ontology fields remain available through the full ontology editor.
- Metadata analysis POST includes relationship candidates; the GET endpoint contains only table classifications. Re-run analysis to regenerate candidates after navigation/reload.
- Exports and detailed cleaning/audit reports can contain source data despite masked graph responses.
- No authentication, RBAC, persistent project catalog, arbitrary Cypher, natural-language querying, direct graph editing, Excel ingestion, or build-cancellation capability is represented.
- This local frontend is not a deployment of an authenticated enterprise service. Existing backend limitations still apply.

See [architecture](docs/architecture.md), [API inventory](docs/api-inventory.md), [migration mapping](docs/migration-map.md), and [verification report](docs/integration-report.md).
