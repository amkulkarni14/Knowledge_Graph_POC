# Frontend integration report

The React frontend is implemented inside the existing `frontend/` directory. It uses the existing FastAPI application and pipeline without changing their implementations. The prior staged backend/documentation changes remain intact. No commit or push was performed.

## Delivery inventory

| Category | Total | Implemented | Verified | Pending |
|---|---:|---:|---:|---|
| API operations | 58 | 58 | 57 successful real local HTTP operations | 1 live PostgreSQL connection |
| Workflow stages | 16 | 16 | 16 | 0 |
| Logical frontend screens | 18 | 18 | 18 browser route/workflow checks | 0 |
| Shared presentation components | 8 | 8 | 8 exercised in render/browser suites | 0 |
| Zustand stores | 3 | 3 | 3 through unit/browser behavior | 0 |
| API integrations | 58 | 58 | 57 local HTTP; PostgreSQL contract tested with backend mocks | Live PostgreSQL success |
| New frontend and integration tests | 22 | 22 | 22 passing | 0 |
| Existing backend/regression tests | 240 | 240 existing, unchanged | 240 passing | 0 |

Screen count is Overview + 16 stages + Graph Explorer. `/build` aliases the planning/build workspace and is not counted as an extra screen. The six parameterized build stages share one implementation. Shared component count covers PageHeader, StatusChip, Panel, Feedback, Report, DataTable, Confirm, and ErrorBoundary; application layout and domain components are separate. Verification means exercised behavior, not exhaustive branch coverage.

## Verification evidence

| Check | Result |
|---|---|
| Dependency resolution | `npm ls --depth=0` succeeds; lockfile generated |
| OpenAPI | Actual application produces OpenAPI 3.1, 49 paths, 58 operations |
| Generated types | Generated with openapi-typescript from the existing Python application |
| TypeScript | `npm run typecheck` passes in strict mode |
| ESLint | `npm run lint` passes without errors or warnings |
| Production build | `npm run build` passes |
| Unit/component/contract tests | 16 tests pass across four Vitest files |
| Browser and real HTTP integration | Six Playwright tests pass in Chromium |
| Existing backend/pipeline/CLI/Streamlit | 240 tests pass, unchanged |
| Accessibility | Axe WCAG 2 A/AA scan of the populated explorer reports zero violations |
| Retail sample | Real HTTP and full browser workflow pass |
| Customer 360 CSV | Real HTTP build and browser multi-file upload pass; 54 nodes, 64 edges |
| Offline AI | Actual recorded suggestions, review, validation, and approval pass in HTTP integration |
| Binary artifacts | All four artifacts verified over HTTP; browser graph.json.gz download verified |
| Saved graph | Snapshot creation, CURRENT promotion, saved-snapshot exploration verified |
| Session expiration | Server-side deletion clears client state and permits a fresh session |
| Preservation | `git diff --stat` has no tracked working-tree changes; additions are confined to frontend |

The 16 frontend tests check session epochs and stale responses, expiration, downstream cache reset, query serialization across sessions, repeated label parameters, multipart boundaries, binary downloads, request cancellation, safe error data, blocking validation, semantic tables, and store reset behavior. Browser suites cover initialization, route guarding, scope, upload, metadata, draft creation/save, skip/review/validation/approval, all build-stage routes, background execution, snapshot storage/promotion/download, graph inspection, nontrivial paths, metrics, accessibility, and session reset/expiration.

Mock-based tests are distinct from real integration tests: Vitest uses controlled mocks for API/client behavior. The HTTP sample/CSV suites and normal browser workflows call the real local FastAPI app. The browser capacity-error case deliberately intercepts an error response. Existing backend tests mock external connectors/providers. No live PostgreSQL, Groq, or Neo4j verification was attempted.

## Integration findings resolved in the frontend

- Most backend reads also use the nonblocking session lock. Axios serializes these requests per session, while allowing lock-free session/status/event polling and independent sessions.
- Snapshot downloads return binary responses despite generic OpenAPI response metadata.
- Metadata analysis POST and GET have different response shapes.
- OpenAPI lacks stage prerequisites and cleaning-kind enums; source-verified advisory mappings are documented.
- Stage 10 is grouped with construction in the React navigation while preserving backend identity.
- HTTP 200 validation failures remain visible and cannot mark a stage complete.
- Cytoscape layout and observer cleanup prevents callbacks against destroyed canvases.
- Scope form state survives authoritative server refresh after saving.

## Preserved files and generated output

| File category | Changes made by this implementation |
|---|---:|
| New frontend source/configuration/documentation files | 55 |
| Existing frontend files modified | 0; initial folders contained no files |
| Existing backend files modified | 0 |
| Existing pipeline files modified | 0 |
| Legacy Streamlit files modified | 0 |
| Datasets, ontology definitions, database schemas modified | 0 |
| Existing root configurations modified | 0 |
| Files deleted | 0 |
| `.gitkeep` files created | 0 |

Dependencies, production assets, downloaded Chromium binaries, test traces/screenshots, isolated session artifacts, and test temporary directories are local generated output excluded by `frontend/.gitignore`.

## Remaining limitations

- Live PostgreSQL, Neo4j, and Groq verification requires separately authorized, configured services. PostgreSQL is the only API operation without a successful real connector call in this run; Neo4j/Groq options share otherwise verified endpoints.
- Authentication, RBAC, persistent projects, session recovery, arbitrary Cypher, graph editing, natural-language querying, Excel ingestion, and server-side cancellation remain unsupported by the backend and are not presented as implemented.
- Reloading the frontend loses its in-memory session handle. Expired/deleted sessions cannot be restored.
- Broad backend reports are inspectable structured data; not every variable report field has a dedicated chart. Advanced ontology fields remain editable through the full JSON editor alongside structured class/relationship/attribute controls.
- Metadata relationship candidates are returned only by the analyze POST. Re-run analysis to regenerate them after leaving that page.
- Accessibility was scanned on a representative populated explorer. This is not a certification or exhaustive assistive-technology audit.
- The production bundler reports a third-party `react-compiler-runtime` "use no memo" directive warning. The build and browser tests pass. The unchanged Python suite emits one Starlette/httpx deprecation warning.
- This is a local frontend integration, not a hosted deployment. No production security claim is made for the unauthenticated backend.

Setup and reproduction commands are in [README](../README.md). Architecture, migration mapping, exact endpoint inventory, and the generated OpenAPI snapshot are included alongside this report.

## New files

The following list includes source, configuration, generated contracts, and documentation; ignored runtime output is excluded.

```text
frontend/.env.example
frontend/.gitignore
frontend/README.md
frontend/docs/api-inventory.md
frontend/docs/architecture.md
frontend/docs/integration-report.md
frontend/docs/migration-map.md
frontend/docs/openapi.json
frontend/e2e/api-workflow.spec.ts
frontend/e2e/browser-failures.spec.ts
frontend/e2e/sample-workflow.spec.ts
frontend/e2e/session-expiration.spec.ts
frontend/eslint.config.mjs
frontend/index.html
frontend/package-lock.json
frontend/package.json
frontend/playwright.config.ts
frontend/scripts/generate-api-types.mjs
frontend/src/App.tsx
frontend/src/api/client.ts
frontend/src/api/sessionsApi.ts
frontend/src/api/workflowApi.ts
frontend/src/app/layout/AppShell.tsx
frontend/src/app/layout/StageStepper.tsx
frontend/src/app/providers.tsx
frontend/src/app/store.ts
frontend/src/constants/stages.constants.ts
frontend/src/features/build/BuildPage.tsx
frontend/src/features/build/StoragePage.tsx
frontend/src/features/ontology/AttributeEditor.tsx
frontend/src/features/ontology/OntologyCanvas.tsx
frontend/src/features/ontology/OntologyPage.tsx
frontend/src/features/ontology/ReviewPages.tsx
frontend/src/features/overview/OverviewPage.tsx
frontend/src/features/projects/ScopePage.tsx
frontend/src/features/query/ExplorerPage.tsx
frontend/src/features/query/GraphCanvas.tsx
frontend/src/features/sources/MetadataPage.tsx
frontend/src/features/sources/SourcesPage.tsx
frontend/src/main.tsx
frontend/src/shared/hooks/useWorkspace.ts
frontend/src/shared/ui/WorkspaceUi.tsx
frontend/src/styles/global.css
frontend/src/styles/theme.ts
frontend/src/test/api-contract.test.ts
frontend/src/test/feedback.test.tsx
frontend/src/test/session-lifecycle.test.tsx
frontend/src/test/setup.ts
frontend/src/test/stores.test.ts
frontend/src/types/common.types.ts
frontend/src/types/generated/openapi.ts
frontend/tsconfig.app.json
frontend/tsconfig.json
frontend/tsconfig.node.json
frontend/vite.config.ts
```
