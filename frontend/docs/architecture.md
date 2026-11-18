# Frontend architecture

The existing `frontend/src` hierarchy is reused. React Router lazy-loads feature pages; the shared shell owns navigation, workspace identity, and activity. `App.tsx` protects workflow routes when no session exists. Backend stages supply titles and completion; the source-verified prerequisite mapping in `constants/stages.constants.ts` only advises action disabling. HTTP 409 remains authoritative.

## Responsibilities

| Layer | Responsibility |
|---|---|
| `app` | Providers, session/UI/graph Zustand stores, shell and routing |
| `api` | One Axios instance, safe errors, generated contract usage, all endpoint adapters |
| `features/projects` | Scope form, React Hook Form and Zod validation |
| `features/sources` | Sample/PostgreSQL/CSV connections, schema and analysis |
| `features/ontology` | React Flow canvas, model editor, review, validation, versions |
| `features/build` | Build configuration, quality rules, status/events, stage results, storage |
| `features/query` | Cytoscape canvas, bounded search/neighborhood, paths, metrics |
| `shared` | Presentation components, session-scoped queries/mutations |
| `types/generated` | OpenAPI-generated types; no handwritten duplication of DTOs |

Feature modules share presentation and API adapters rather than introducing duplicate API/store layers for each page. The initial proposed file plan was consolidated where colocated code has a single owner: API adapters share `workflowApi.ts`, feedback components share `WorkspaceUi.tsx`, and review-related routes share `ReviewPages.tsx`. Existing empty folders are preserved, including `auth`; no unsupported login was created.

## State and request lifecycle

Server responses are keyed by `['workspace', sessionId, feature, ...parameters]`. Credentials are never query keys. Active session changes increment an epoch. Each mutation captures its session and epoch; success and failure callbacks ignore obsolete sessions. Concurrent workspace mutations are rejected locally and backend conflicts are displayed without retrying mutations. A per-session Axios queue serializes locked reads and short mutations, because backend operation() rejects overlapping reads too. Lock-free session/status/event reads bypass this queue. Different sessions can read concurrently.

After a successful state-changing operation, pending reads are cancelled, the session is refreshed, and derived queries reset. This prevents old ontology, validation, graph, or extraction data remaining visible after upstream changes. Graph instances and resize observers are destroyed on unmount. Session deletion cancels queries and clears session cache and graph selections. Expiration clears the session and gives a new-workspace notice.

Build status polls every 1.5 seconds while queued/running; build events poll every 2 seconds while monitoring an active job. Terminal states stop both timers. TanStack Query supplies AbortSignals to reads. A status transition refreshes session completion immediately. Event pages use offset/limit; they do not fabricate streaming events or progress percentages.

## Design system

`styles/global.css` defines shared surfaces, borders, accent, muted text, focus treatment, layout, and responsive behavior; `styles/theme.ts` supplies the corresponding MUI theme. Tailwind handles layout and responsiveness. MUI owns structured forms, tables, confirmation dialogs, and report controls. HeroUI owns compact status chips. CSS layer order places MUI before component and utility overrides. HeroUI v3 uses its v3 style package; v2 providers and v2 component APIs are not mixed into the app.

The sidebar separates data, ontology, construction, and exploration. Stage 10 is presented with construction while keeping its backend identity. The ontology canvas has a model editor and accessible data representation. The graph canvas has an inspector, legend, entity table, neighborhood controls, path analysis, and metrics. On narrow viewports the sidebar contracts and multi-column panels stack.

## Contract gaps handled without backend changes

- Broad object responses use `Record<string, unknown>` and inspectable report rendering.
- Generated OpenAPI types preserve strongly typed DTOs, ontology entities, catalog, and graph view.
- Multipart file boundaries are set by the browser; uploads use repeated `files` fields.
- Binary snapshot responses override the generic download OpenAPI declaration.
- Successful HTTP validation with `ok:false` remains a blocking report, not workflow completion.
- `merges`, `changes`, `quarantine`, and `records` are the source-verified cleaning kinds.
- Metadata analysis POST and GET have distinct response types.

No backend implementation or contract files outside the frontend are changed.
