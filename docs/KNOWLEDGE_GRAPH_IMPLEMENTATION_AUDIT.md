# Knowledge Graph implementation audit

This audit records the repository baseline before implementation. The supplied architecture HTML describes the pipeline stages and an earlier UI. The current application uses React.

## Existing architecture

React 19, Vite, TypeScript, React Router, Material UI, TanStack Query and Zustand support a signed-in workflow. The API client uses bearer tokens and a common response envelope. The shell, workflow stepper, feedback components, storage page and Cytoscape explorer are reusable. Cytoscape already supports interactive bounded views, layouts, node and edge selection, and label colors. The ontology editor covers manual mapping, suggestions, review, validation and repository operations.

FastAPI exposes versioned session, source, schema, ontology, build and graph APIs. Services wrap pipeline stages and isolate transient state by session UUID. JWT authentication uses one configured account and a process-local logout list. Session access initially has no owner check or project roles. Workflow events and the latest build status are available through polling. The bounded in-process executor runs stages 10–15. Pipeline calls share a process-wide lock while switching storage paths.

PostgreSQL serves as a source through a read-only connector. The metadata bootstrap DDL defines ontology, ontology versions, AI request and suggestion records, ontology audit, graph builds and quarantine. The application uses filesystem ontology versions and in-memory workflow/job state. There are no durable project memberships, connection references, active graph registry, query or scene history, or managed metadata migrations.

The PostgreSQL connector populates a schema catalog and key relationships. Manual mappings and optional Groq suggestions feed human review and ontology validation. The approved ontology builds an extraction plan. Keyset batches populate an in-memory staged source. Profiling and rules precede normalization, entity resolution and quarantine. Construction creates a directed NetworkX multigraph, then validates it against the ontology and source. Step 16 saves JSON gzip, GraphML, quarantine and a checksum manifest under the session graph directory. It publishes the filesystem CURRENT pointer before attempting the optional Neo4j load.

Neo4j is configured server-side and has an optional Docker profile. Its driver is initialized per load. The existing loader merges node IDs globally by label, matches relationship endpoints by bare ID, creates per-label constraints and counts submitted rows. Graph APIs read NetworkX or files. Live connectivity, contents, edition, indexes and constraints were unavailable for verification. Docker Desktop's Linux engine pipe was absent.

## Step status

Statuses reflect repository inspection. No step is credited with live end-to-end verification.

| Step | Status | Evidence |
|---|---|---|
| 1 Scope | Partially implemented | Scope sheet and workspace UI |
| 2 Connection | Partially implemented | PostgreSQL, CSV and sample connectors |
| 3 Discovery | Partially implemented | Catalog from source metadata |
| 4 Interpretation | Partially implemented | Table classification and relationship candidates |
| 5 Manual ontology | Partially implemented | React editor and mapped draft |
| 6 AI suggestions | Partially implemented | Groq service and recorded fixture |
| 7 Review | Requires improvement | Decisions exist, reviewer is a workflow label |
| 8 Ontology validation | Partially implemented | Structural and source mapping checks |
| 9 Ontology registry | Requires improvement | Filesystem repository |
| 10 Build planning | Partially implemented | Mapped columns and source tables |
| 11 Extraction | Requires improvement | Full in-memory staging and watermarks |
| 12 Data quality | Partially implemented | Profiling, rules and blocking thresholds |
| 13 Cleaning and resolution | Partially implemented | Normalization, canonical keys and quarantine |
| 14 Graph construction | Partially implemented | Directed NetworkX property multigraph |
| 15 Graph validation | Partially implemented | Ontology and source checks |
| 16 Persistence | Requires improvement | Local artifacts and unscoped optional Neo4j import |
| 17 Analytics | Partially implemented | Degree, components and one path |
| 18 Exploration | Partially implemented | React Cytoscape, bounded views and inspector |
| 19 Operations | Partially implemented | Pollable process-local build execution |

## Gaps and implementation sequence

The principal security gaps are project authorization, unscoped imports, raw artifact downloads and dependence on mutable ontology state for masking historical graphs. The checked-in environment file should be treated as potentially sensitive. Its contents were omitted from this report. Large builds retain extracted rows, cleaned entities and graph structures simultaneously. Repeated snapshot loads, synchronous import, global pipeline serialization and request-time analytics increase latency.

1. Extend the existing PostgreSQL graph build registry with a project owner, staged versions, an atomic current pointer and lifecycle timestamps. Add a server-side Neo4j storage adapter with a composite node identity, bounded writes, validated counts and scoped recovery. Preserve local snapshots for existing callers.
2. Add version-keyed analytics with explicit algorithm budgets and background execution.
3. Extend the existing Cytoscape explorer and add schema and query views in the React shell. Use server-owned query templates until database isolation and a dedicated restricted identity support a free-form workbench.
4. Reuse the build runner for progress and staged publication. Use full source reconciliation to detect deletions until the source supplies CDC or tombstones.
5. Verify against isolated PostgreSQL and Neo4j instances, including isolation, restore, failed imports and refresh.

Expected touchpoints include the existing graph and build routes, workflow session dependencies, PostgreSQL metadata schema, configuration, React routing, storage and explorer pages. New modules should house the version registry and Neo4j storage, with separate integration tests and deployment documentation. Reuse Cytoscape because it is already integrated and covers interactive layout and bounded expansion. Sigma would add a second graph stack. React Flow remains suited to the ontology editor.

## Baseline verification

The default Python installation lacks pytest and the registered Python 3.12 interpreter is missing. The initial React test invocation reached Vitest, where Windows denied worker process creation. The Docker client could not reach its engine. The audit used static inspection and did not mutate database state.
