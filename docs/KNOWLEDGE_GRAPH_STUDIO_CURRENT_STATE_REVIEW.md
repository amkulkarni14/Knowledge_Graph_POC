# Knowledge Graph Studio — Current-State Verification

**Scope and evidence.** Compared docs/KNOWLEDGE_GRAPH_STUDIO_AUDIT.md with the current working tree, including existing untracked feature files. The open KNOWLEDGE_GRAPH_IMPLEMENTATION_AUDIT.md describes an older baseline and is historical. **S** means inspected in current source. **T** means prior executed test evidence. **R** means prior runtime observation. **U** means unverified in current live operation. This review did not make application requests, run tests, inspect secret values, query databases, restart services or change branches. Consequently, a source finding establishes implemented behavior, with actual persistence, security and performance outcomes bounded by available prior tests.

## Executive decision

Retain the 13-stage local authoring flow and the existing property graph stack. Prioritize durable workspace recovery, publishing readiness, and consistent data handling before enlarging the AI surface. The audit already described most of the features listed as new. Current source confirms they are present, but it does not show that the associated enterprise-readiness gaps have been closed. POC governance stages are intentionally hidden. Their retention in the governed policy is correct.

## Audit reconciliation

| Earlier concern or capability | Status today and evidence | Remaining decision |
|---|---|---|
| Approval steps in active workflow | **Resolved for POC; removal no longer applicable.** backend/app/services/workflow_policy.py active_stages excludes 6, 7 and 9. frontend/src/App.tsx ontologyStage guards direct links. T POC browser flow. | Keep hidden in POC; preserve governed path and historical records. |
| Old Build Plan naming and progress | **Resolved in active UI.** frontend/src/constants/stageNavigation.ts, frontend/src/features/build/BuildPage.tsx and StageStepper.tsx show Graph Build Manager. Stable internal ID 10. | Preserve routes and IDs; regression-test shared labels and ordinals. |
| Connector breadth and portability | **Partially resolved.** backend/app/services/provider_sources.py and source_connections.py provide concrete adapters and candidate confirmation. | Live acceptance of several provider stacks and resumable reads remain open. |
| Editable ontology naming | **Resolved within current artifact lifecycle.** backend/app/api/ontology.py save and services/workflow.py same_ontology_model preserve results on name-only edits. | Durable reopen of the entire workspace remains open. |
| Dashboard and Explorer duplication | **Partially resolved.** GraphCanvas and shared tables reused. BusinessInsightsPage and PublishedGraphsPage still represent distinct working versus published data. | Share presentation and provenance, not access boundaries. |
| Ollama offline/local path | **Partially resolved.** graph_questions.provider/availability and ollama_provider.check/complete support model tags, live inference and flagged fallback. R successful local query. | Cold-start misclassification, limited grammar and untested model breadth remain. |
| Missing session owner check or project memberships | **Resolved relative to the older implementation audit.** CurrentSession owner guard and graph_versions.authorize enforce boundaries. | Cross-tenant matrix and production role review remain open. |
| Snapshot integrity and Neo4j publication | **Partially resolved.** Workspace paths/checksums and registry-backed version coordination exist. | Full active workflow recovery, restore drills and deployment-specific publication acceptance remain open. |
| Restart resilience, privacy consistency, load and readiness | **Still open.** SessionRepository/BuildRunner remain local. Connector and graph projections still use differing privacy paths. Historical /graph-projects returned 503 while health returned 200. | Address before any shared deployment. |

## Frontend walkthrough

Routing evidence: frontend/src/App.tsx App, AuthGate and Workspace. Without a session, stage routes redirect to Home; published and insights routes remain available after sign-in. Unknown routes also go Home. Frontend navigation advises; server stage checks enforce. Paths below reference files under frontend/src.

| Page or surface | Current behavior and source evidence | Main limitation and finding |
|---|---|---|
| Sign-in at requested URL | features/auth/LoginPage.tsx LoginPage and app/authStore.ts; username/password, login, /me, sign-out via shell. | No independent settings/SSO surface. F05. |
| Home / and shell | features/overview/OverviewPage.tsx OverviewPage; create/open/reset workspace, progress, artifacts, build state. app/layout/AppShell.tsx and StageContinuation.tsx provide sidebar, activity, breadcrumbs, API status and Next/Back. | Active session list is not durable inventory. Back rendered in POC with predecessor. F01/F08. |
| Domains /domains | features/projects/DomainsPage.tsx DomainsPage; create/list templates reused by Scope. | No template edit/delete route found. F08. |
| Data Sources /sources | features/sources/SourcesPage.tsx, ConnectionFields.tsx and SourceAssets.tsx; connector/auth, test, discovery, preview, confirmation and disconnect. | Preview can precede sensitivity declarations. F03/F06. |
| Goal & Scope /scope | features/projects/ScopePage.tsx ScopePage; domain template, predefined/custom questions, exclusions and sensitivities. | Change invalidates derived stages; users need a clearer impact preview. F08. |
| Schema Extraction /metadata and Analysis /analysis | features/sources/MetadataPage.tsx; extract/catalog/field preview and analyze/classifications. | Distinct operations, overlapping screens. Heuristic classifications need confidence indicators. F08. |
| Ontology Studio /ontology | features/ontology/OntologyPage.tsx plus OntologyCanvas and AttributeEditor; initialize, edit name, classes, attributes, relationships, mappings, JSON, save/revert. | Keep stable IDs; model edits invalidate descendants. Add semantic diff and mapping confidence. F09. |
| Validation /validation | features/ontology/ReviewPages.tsx validation mode; run report and review issues without reviewer controls in POC. | Mapping-level validation; no SHACL engine identified. F09. |
| /suggestions, /review, /repository | ReviewPages.tsx governed modes; suggestion/skip, review/preview, approval, version and audit interfaces. | Intentionally hidden and route-guarded in POC. Caller-declared actor identities need independent principal checks in governed use. F05. |
| Graph Build Manager /build, /build/10 | features/build/BuildPage.tsx BuildPage; business rules, batch size, full/single run, status, events, cancellation. | Full build does not include snapshot save. F01/F08. |
| /build/11–15 | Same page in extraction, quality, cleaning and resolution, construction and validation modes. Reads paginated extraction/cleaning evidence and stage reports. | Repeated shell; preserve individual stage recovery while consolidating presentation. F07/F08. |
| Storage & Snapshots /storage | features/build/StoragePage.tsx StoragePage; save, publish option, choose ontology/build/artifact, history, promote and download. | Save, publish and complete workspace recovery are separate operations. F02/F04. |
| Graph Explorer /explorer | features/query/ExplorerPage.tsx and GraphCanvas.tsx; current/snapshot, search, node/edge inspector, neighborhood, labels and edge filters, grouped layouts and fit. | Edge filters apply to displayed edges; path may extend off canvas. F10. |
| Path Analysis and Metrics /explorer?view=path or metrics | ExplorerPage tabs; path endpoints/hops, highlighting, degree/component stats. | Merge duplicate menu entry affordances into tabs while retaining URLs. F10. |
| Ask Your Knowledge Graph | features/query/GraphQuestions.tsx; provider status, schema suggestions, one prior question, rerun history, results/evidence and executed plan. | Provider correctness assessed below. F11. |
| Business Insights /business-insights | features/query/BusinessInsightsPage.tsx and InsightsCharts.tsx; workspace/source/dataset/snapshot selection, measures, filters, charts, quality, exports. | Source and graph filter scopes differ and need prominent labels. F12. |
| Published Graphs /published-graphs | features/query/PublishedGraphsPage.tsx; root project/version selector with subviews explorer, query, analytics, schema, operations, intelligence and graphml. | Registry-dependent branch. F04/F10/F13. |
| Published Explorer and Query Workbench | PublishedGraphsPage controls for search/properties, paths, scenes, templates, compiled Cypher, query drafts and saved queries. | Distinct Neo4j access and versioning; reuse local Explorer widgets. F10. |
| Published Analytics and Schema | PublishedGraphsPage counts, distributions, rankings, communities, labels, directions, indexes. | Merge presentation selectively with Insights; preserve version semantics. F12. |
| Published Operations, Intelligence and GraphML | PublishedGraphsPage and GraphIntelligenceTools.tsx; membership, restore/current, export/delete/import, heuristic prediction and bounded RAG. | Capability-gate publish/admin paths; hide experimental scores from default navigation. F04/F13. |
| Stage Help | app/layout/StageHelp.tsx StageHelp, backend/app/services/stage_advice.py advise; read-only suggestions and checklist fallback. | Separate Groq implementation. Share provider policy while keeping stage advice separate from execution. F11. |

## Backend route inventory

All paths below are prefixed /api/v1. W means /sessions/{session_id}. P means /graph-projects/{project}; V means P/versions/{version}. Source of truth is the decorators in backend/app/api and router registration in backend/app/main.py. Use the generated contract for parameter-level details. Listing a route is not evidence of production operation.

| Module | Methods and route groups; relevant functions |
|---|---|
| main.py and api/auth.py | GET /health; POST /login, GET /me, POST /logout. create_app, login, me, logout. Liveness is independent of publication. |
| api/sessions.py | GET /stages; POST/GET /sessions; GET/DELETE W; PUT/GET W/scope; GET W/events; POST W/stage-advice/{stage}. create, read, close, scope, events, advice. |
| api/library.py | GET/POST /domains; GET /ontologies. domains, create_domain, ontologies. Account-owned artifact/domain records. |
| api/sources.py | GET /source-types; GET/DELETE W/sources; GET W/sources/health; POST legacy /postgres and /upload; POST /test, /locations, /connections, /connections/upload; GET /connections/candidate and /connections/{id}/assets; POST /connections/{id}/preview and /select; DELETE /connections/{id}. Subpaths rooted at W/sources. test_connection, connect, preview, select, disconnect. |
| api/metadata.py | W/metadata GET catalog, /tables, /columns, /preview, /analysis; POST /extract and /analyze. run_extract, catalog, preview, analyze. |
| api/ontology.py | Under W/ontology: GET/POST/PUT /draft; POST /draft/save and /draft/revert; POST /classes; PATCH/DELETE /classes/{class_name}; PUT /classes/{class_name}/attributes; POST/DELETE /relationships; GET/POST /suggestions, POST /suggestions/skip, /review/preview and /review; POST /validate and GET /validation; POST /approve, /use-approved, /versions/{version}/rollback; GET /versions, /versions/{version}, /audit. draft, save, replace_draft, validate, approve, rollback. |
| api/builds.py | Under W/builds: POST root; GET /status; POST /{job_id}/cancel; GET/POST /stages/{stage}; GET /extracted-rows, /cleaning/{kind}. start, status, cancel, stage, result, extracted, cleaning. |
| api/graphs.py | Under W/graphs: GET /data, /nodes, /node, /path, /metrics, /intelligence, /graphml/neighborhood; POST /graphml/preview and /graphml/publish; GET/POST /snapshots; POST /snapshots/{build_id}/current; GET /snapshots/{build_id}/download/{artifact}; GET /questions/provider and /questions/suggestions; POST /questions. select_graph through service, data, save_snapshot, promote, path, ask_graph. |
| api/insights.py | GET W/insights. insights uses session-local aggregate cache and typed filters. |
| api/graph_versions.py | GET /graph-projects, P/versions, P/health and P/members; PUT/DELETE P/members; PUT V/current and DELETE V; GET V/analytics, /communities/{index}, /export/{format_name}, /schema, /compare, /neighborhood, /intelligence, /graphml/neighborhood, /paths; GET/POST V/query; GET/PUT V/workspace-items; POST V/query-draft, /graph-rag and /investigate; POST W/builds/published. resolve, read_graph, authorize via registry; publication and membership require additional permissions. |
| backend/graph_mcp.py | Optional stdio tools issue authorized requests to published routes, including list/search/schema/neighborhood/path/rank/read-only query. No default Compose service. |

## Workflow and persistence verification

The guided sequence is source 2 → scope 1 → 3 → 4 → 5 → 8 → 10 → 11 → 12 → 13 → 14 → 15 → 16 in POC. Stage IDs remain distinct from display ordinals. Governed adds 6, 7 and 9. The server defaults to governed unless explicitly configured otherwise and rejects the validation-only policy for declared production. The last known live run used POC. Connect and scope have no mutual backend prerequisite, but schema extraction needs both. See backend/app/services/workflow_policy.py, workflow.py execute/clear_from/current_build_ontology, and frontend/src/constants/stages.constants.ts.

Paths in this table are relative to data_pipeline/src/kg_pipeline unless otherwise marked.

| ID | Gate | Implementation, output and recovery |
|---|---|---|
| 2 | None | preprocessing/s02_connect.py plus backend/app/api/sources.py select. Confirm active source selection; cancel/disconnect available. Handle in memory. |
| 1 | None | core/s01_scope.py run. Typed project scope; save retains eligible connection and invalidates downstream results. |
| 3 | 1, 2 | metadata_extractor/s03_schema_extraction.py run. Catalog and provenance; retry connector failures. |
| 4 | 3 | metadata_extractor/s04_schema_analysis.py run. Classification and inferred candidate relationships; rerun with changed schema. |
| 5 | 3, 4 | ontology_compiler/s05_manual_ontology.py run and API save. Mapped working draft, stable identity and independent display name. Correct mappings or revert. |
| 6 | 5 | ontology_compiler/s06_ai_suggestions.py run/skip. Governed suggestion or explicit skip. |
| 7 | 5, 6 | ontology_compiler/s07_review_approval.py run. Governed merged reviewed draft. Preview and revise. |
| 8 | 5 POC; 7 governed | ontology_compiler/s08_ontology_validation.py run. Pass completes stage. POC stores validated snapshot/digest. Fix failed checks and rerun. |
| 9 | 8 | ontology_compiler/s09_ontology_repository.py run/use_existing. Governed approved version and audit. |
| 10 | 3, 8 POC; 3, 9 governed | graph_builder/s10_build_plan.py run. Validate eligible ontology, produce entity/relation projections. |
| 11 | 10 | preprocessing/s11_extraction.py run. Staged projected reads and watermark observations; no durable resume after failure. |
| 12 | 11 | preprocessing/s12_data_quality.py run/profile. Key, null, type, reference and business rules; blocking findings prevent completion. Some defaults are retail-specific. |
| 13 | 12 | preprocessing/s13_cleaning_er.py run. Normalize, resolve deterministically and quarantine. Result is transient. |
| 14 | 13 | graph_builder/s14_graph_builder.py run. Directed NetworkX multigraph with mapped identity and provenance. Correct inputs and rebuild. |
| 15 | 14 | graph_builder/s15_graph_validation.py run. Successful realized-graph checks enable snapshot. |
| 16 | 14, 15 | graph_builder/loaders/s16_graph_persistence.py run and API save_snapshot. Checksummed durable artifact or optional publication. Not part of full-build 10–15. |

**Persistence boundaries.** backend/app/repositories/sessions.py SessionRepository.create/get/list_owned/cleanup owns process-local active sessions, source connections, results, progress and locks. Reopening from Home and browser reload works while the backend session still exists. Backend restart or expiry removes active session access. backend/app/repositories/library.py catalog/register_workspace/save_working_draft/list_ontologies maintains SQLite inventory and saved working files, but does not rehydrate PipelineContext. Prior restart verified retained file checksums and ended active sessions. A readable artifact and a resumable workspace are different capabilities.

**Graph and snapshot isolation.** backend/app/core/dependencies.py get_session resolves an authenticated owner. backend/app/services/graphs.py checked_path limits files to the session snapshot root, load verifies manifest hashes and selects the requested or CURRENT version, and select_graph uses the current in-memory graph or requested disk snapshot. api/graphs.py promote and download are owner-scoped operations. Earlier tests cover version selection/download and snapshot integrity. No fresh restore drill was run, and the reviewed APIs still require an active session for session-scoped snapshot recovery. See F01–F02.

**Auth and authorization.** backend/app/api/auth.py login/me/logout and backend/app/core/security.py authenticate bcrypt credentials from configured account or registry-backed users and sign expiring JWTs. RevokedTokens is process-local. backend/app/core/dependencies.py get_current_user validates claims/revocation; get_session passes owner. Frontend sessionStorage persists auth across reload, not a selected workspace. The published registry additionally checks owner or membership and management roles. Governed reviewer name checks do not independently authenticate reviewers. Prior tests exercised invalid tokens, ownership and publication authorizations; fresh multi-tenant or database credential tests were outside this review.

## Database, connector and Docker integration

| Integration | Current verified design and evidence | Qualification |
|---|---|---|
| SQLite library and files | backend/app/repositories/library.py catalog and working draft save; data_pipeline/src/kg_pipeline/graph_builder/loaders/s16_graph_persistence.py snapshot artifacts and manifest. | Durable on backend volume, no complete workflow restore. |
| PostgreSQL sources | data_pipeline/src/kg_pipeline/preprocessing/connectors/postgres_source.py iter_batches, provider credentials/TLS, catalog, keyset or cursor fallback. backend/app/core/source_network.py endpoint controls. | Prior isolated guided source run. Watermark support at reader level only. |
| SQL Server / Oracle | backend/app/services/provider_sources.py mssql/oracle and connectors/relational_source.py iter_batches. ODBC Driver 18 read-only connection; Oracle TCPS/wallet and connection bounds. | Concrete code, live enterprise endpoints U. |
| CSV/sample | connectors/csv_source.py and sample_source.py. Bounded upload, inferred mappings, fixture or parsed CSV data. | Strongest T/R coverage; validate inference for keyless and messy data. |
| AWS, Azure, GCS | provider_sources.py s3/azure/gcs and connectors/object_source.py. Provider-specific auth and bounded list/range/read. | S3-compatible SDK fixture T; live AWS/Azure/GCS U. CSV object support, no durable increments. |
| BigQuery | provider_sources.py bigquery and connectors/bigquery_source.py iter_batches; ADC, projected read, dry run and maximum bytes. | Mocked cap coverage T; real dataset U. |
| PostgreSQL metadata registry | database/postgres/init/02_kg_meta_schema.sql and 04_graph_versions.sql plus backend/app/repositories/graph_versions.py registry/authorize/register/publish/recover_interrupted. Versions, owner/member roles, events and saved scenes/queries. | Initialization SQL is not a managed upgrade strategy for existing volumes. Prior registry 503 when unconfigured. |
| NetworkX | graph_builder/s14_graph_builder.py run; graph readers/services and snapshot load. Local authoring graph and bounded analytics. | No independent service or persistent NetworkX session; main memory cost remains. |
| Neo4j publication | backend/app/services/graph_publication.py persist/import_and_publish, neo_graph.py NeoGraphStore.import_graph/records and registry publication guard. Batched writes and scoped project/version identity; metadata and graph counts checked. | Two stores, recoverable lifecycle rather than atomic distributed commit. Current live end-to-end publication U. |
| Published queries | backend/app/api/graph_versions.py resolve/read_graph and services/cypher_subset.py compile_query. Registry read/management authorization, scoped parameterized templates and compiled subset. | Test-level behavior, no new live isolation or least-privilege exercise. |

| Docker service / path | Responsibility and current gap |
|---|---|
| frontend, docker/frontend.Dockerfile and nginx.conf | Node build, Nginx static SPA/API proxy, loopback port 8080 by default, starts after backend health. Prior live app usage; no new check. |
| backend, docker/backend.Dockerfile and compose.yaml | Non-root Python container, one Uvicorn worker, named backend-data mount and API health check. Optional ODBC build option. Readiness lacks explicit per-capability summary. |
| postgres profile | PostgreSQL source/bootstrap and optional publishing registry. Named postgres-data and pg_isready. Bootstrap only applies when appropriate for new data directories. |
| neo4j profile | Optional published graph server, named neo4j-data. Separate database readiness and role configuration matter. |
| Ollama host | External Windows process via host.docker.internal. No application Compose Ollama service. Previous verified loopback listener was accessible from container. |
| Deployment | Existing examples point to Compose runtime variables and native .env. No secret values read. Earlier clean staged build handled Windows context issues. Rebuildability and restart recovery need distinct tests. |

## Ollama and question capability matrix

backend/app/services/ollama_provider.py check reads installed tags; complete sends non-streaming JSON and bounded output to configured local Ollama. backend/app/services/graph_questions.py plan_question validates model output against typed DTO and selected graph; execute evaluates read-only operations and explain lets a model select verified statements. Availability is model-tag readiness, not proof of inference speed. The prior live Browser/API run returned nine Account entities, provider ollama and explanation_source ai_evidence_selection. Another initial request fell back while loading. The observed sequence supports investigating timeout handling; it does not establish a conclusive root cause. Current container/model status was not rechecked.

| Question type | Supported result |
|---|---|
| “How many Account entities are there?” | Exact, bounded count for an existing label; schema suggestions support this. Demonstrated with live Ollama. |
| “Show Account entities” or “Show relationship type X from A to B” | Approved label or directed pattern, bounded evidence, rows and inspected plan. Schema-specific names matter. |
| “How many X relationships go from A to B?” | Count one valid directed edge pattern. Not an arbitrary join. |
| “Find the shortest path from exact quoted ID A to exact quoted ID B” | Up to eight hops, direction ignored, explicit missing-node/no-path behavior, test coverage. |
| “Summarize graph insights” | Structural counts and label totals, not a business forecast or causality claim. |
| Filter a property by text | Whitelisted current-graph source field and literal substring grounded in question context; historical schemas lack this guarantee. |
| “What about those?” | One prior question passed as prompt context. Anaphora and chained reasoning are not guaranteed, and the rules engine does not infer the prior intent. |
| Numeric ranges, arbitrary aggregates, trends, ranking across entities, arbitrary multi-hop joins, predictive or causal questions | Outside workspace query-plan grammar. Business Insights and published analytics are distinct features. |

graph_questions.py caps graph size at 100k nodes/250k edges, uses bounded execution and 40 result matches, and caps concurrent planning. Ollama outage fallback is visible and uses predefined phrases. Provider selection affects workspace Ask; other AI surfaces use separate Groq code. Recommendation: benchmark against varied labeled graphs, add typed predicates/aggregates incrementally, separate transport/timeout/model errors, and retain reproducible evidence. Prompts can still contain user-entered sensitive text.

## Is Business Insights generic?

**Generic profiling and structural analytics, partial business semantics.** backend/app/services/insights.py discover/profile/dashboard derive fields from types, category-name heuristics, mapped privacy metadata and keys, rather than hardcoded Customer360 dashboard KPIs. Filters operate within the selected source profile. Numeric totals, averages, categories, period buckets, small-group suppression and mixed-currency checks are generic within their supported field shapes. graph_summary computes topology and connectivity for a validated current graph or selected snapshot. quality_rows uses latest pipeline quality results independent of row filters. CSV, chart PNG and browser PDF print are present in frontend/src/features/query/InsightsCharts.tsx and BusinessInsightsPage.tsx.

The 5,000-row default profile (25,000 maximum) can be nonrepresentative, and field heuristics cannot infer corporate metric definitions. Warehouse pushdown is connector-specific and dashboard aggregation is generally bounded backend computation. Prior tests used Customer360, supply-chain and generic/no-date schemas, mixed currency, export and snapshot use. Cloud provider coverage remains distinct from generic algorithm coverage. Do not assume that filtering graph labels filters source charts, or that a chart describes an entire large dataset.

## Findings and prioritized enhancement roadmap

P0 blocks an intended production capability, P1 core reliability, P2 usability/value, P3 optional. Complexity is delivery complexity, not operational risk.

| ID / module | Status and source evidence | Limitation → improvement | Priority / dependency / complexity | Regression risk |
|---|---|---|---|---|
| F01 Workspace persistence | Open. backend/app/repositories/sessions.py SessionRepository and services/builds.py BuildRunner. | Durable files coexist with transient context, source handles and jobs. Create durable run checkpoints, reopen workflow and queue recovery with secret references. | P0; storage schema, auth scope, migration; High | Replaying stale source or validation, duplicate jobs, loss of old artifacts. |
| F02 Snapshot recovery | Partial. backend/app/services/graphs.py load/checked_path and api/graphs.py promote/download. | Current file checks and version selection are sound boundaries; session loss blocks access through session-only APIs. Add account-scoped durable restoration and verified backup restore. | P1; F01, artifact lineage; Medium | Cross-workspace artifact access, incorrect CURRENT pointer or metadata mismatch. |
| F03 Privacy and outbound scope | Open. backend/app/api/sources.py preview, api/metadata.py preview, services/graphs.py hidden_properties, services/graph_publication.py private_identifiers and services/graph_questions.py graph_schema. | Distributed sensitivity and export filters, with source preview preceding scope. Central policy for previews, builds, snapshots, exports and provider egress. | P0; classification schema and roles; High | Breaking legitimate previews, leaking restricted identities via compatibility paths. |
| F04 Publication and readiness | Partial. backend/app/repositories/graph_versions.py registry/publish/recover_interrupted, services/graph_publication.py persist, docker/compose.yaml health. | Old /graph-projects 503 under unconfigured registry, two-store partial failure possible. Capability preflight and transactional state/restore drills. | P0 for published release; DB migration and credentials roles; Medium | Local workspace access gated incorrectly, incomplete Neo4j version reported current. |
| F05 Authentication, authorization and approval | Owner isolation resolved relative to historical audit; governed identity partial. backend/app/core/dependencies.py get_session, api/auth.py logout, api/ontology.py approve and repositories/graph_versions.py authorize. | Process-local revocations; caller-declared reviewer can undermine separation of duties. Add authenticated reviewer roles and shared revocation and quotas before enterprise. | P1; identity contracts and registry; High | Lockouts, replayed or misattributed approval, privileges broadened. |
| F06 Connector lifecycle | Partial. backend/app/services/provider_sources.py and source_connections.py SelectedSource; connectors implementations above. | Mixed fixture and live evidence, limited shape formats and no durable increment. Acceptance matrix seeded by highest-demand integrations, schema drift and safe credential handling. | P1; disposable environments and provider contracts; Medium | Legacy CSV/PG behavior or TLS restrictions regress. |
| F07 Larger graphs and load | Open. backend/app/core/middleware.py BodyLimitMiddleware, services/workflow.py storage/PIPELINE_LOCK, preprocessing/s11_extraction.py run and services/graphs.py load. | Buffered uploads, process-wide storage lock, in-memory stages and repeated hash/deserialize. Measure peak memory and p95, then add disk-backed staging/capped immutable snapshot cache and durable jobs. | P1; F01/checkpoint contracts; High | Memory spikes on cold load, stale graph version, unsafe cancellation. |
| F08 Workflow and screen simplification | Partial. frontend/src/App.tsx Workspace, app/layout/StageContinuation.tsx and features/build/BuildPage.tsx. | Repeated stage panels and source-first navigation create context switches. Merge metadata/analysis presentation and build detail views while retaining stage IDs/recovery. | P2; stable workflow policy/state; Medium | Broken deep links and inaccurate progress in either policy. |
| F09 Ontology modeling and lineage | Naming resolved; modeling partial. backend/app/api/ontology.py save, services/workflow.py current_build_ontology and data_pipeline/src/kg_pipeline/ontology_compiler/s08_ontology_validation.py. | Inferred mappings and deterministic validation need confidence/diffs and stronger source-version linkage. Add explicit semantic diffs; evaluate OWL/SHACL only if required. | P1; reproducible catalog and ontology IDs; Medium | Renames invalidate legitimate results or structural changes mistakenly preserve them. |
| F10 Graph exploration overlap | Partial. frontend/src/features/query/ExplorerPage.tsx, GraphCanvas.tsx and PublishedGraphsPage.tsx. | Similar controls and different query stores. Reuse data-source selector, inspector and path evidence; keep published authorization separate. | P2; adapter contract and version routing; Medium | Snapshot/published semantics confused, out-of-scope edge display. |
| F11 NLQ provider and query scope | Partial. backend/app/services/graph_questions.py plan_question/run_plan, ollama_provider.py check/complete, frontend/src/features/query/GraphQuestions.tsx. | Validated narrow plans, cold-start fallback and provider label inconsistencies across modules. Add separate timeout status, benchmark and typed extensions. | P1; evidence grammar and egress policy; Medium | Free-form model output accepted, incorrect arithmetic, fallback hidden. |
| F12 Insight semantics and duplication | Partial. backend/app/services/insights.py discover/profile/graph_summary, frontend/src/features/query/BusinessInsightsPage.tsx and PublishedGraphsPage.tsx. | Generic profiles but no governed metrics catalog. Show denominator/freshness, exact/sample state, connector pushdowns and reuse visual primitives. | P2; lineage, quotas and metric definitions; High | Mixed currencies or misleading scope, privacy via differencing. |
| F13 Experimental graph intelligence | Incomplete for production. backend/app/services/graph_intelligence.py structural_insights/grounded_answer and api/graph_versions.py investigate. | Heuristic vectors and bounded facts are not predictive or semantic search quality evidence. Hide advanced nav by default, evaluate with access-aware evidence corpus. | P3; curated benchmark and provider governance; High | Unsupported claims and leakage of source evidence. |
| F14 Release and test coverage | Partial. backend/tests/test_graph_live.py test_source_to_published_versions, frontend/e2e/published-graphs.spec.ts, Docker init and logs cited below. | Live suites depend on fixtures. Add repeatable acceptance, restart drill, role and migration matrix, and diagnostic health with structured traces. | P1; disposable integrations and fixture tooling; Medium | Side effects in shared environments, false acceptance from mocks or skips. |

Sequence P0 work first. F01 supplies resilience for F02 and F07, while F03 must precede wider export and AI rollout. F04 can progress independently for an organization that needs publication. Then qualify connectors, approvals, capacity and provider timeouts at P1. Merge navigation and metric presentation after the evidence contracts are stable. Leave predictive GraphRAG evaluation to P3.

## Test and runtime evidence

| Evidence | What it establishes | Boundary |
|---|---|---|
| Prior full suite 272 passed, 2 skipped and 29 frontend unit tests passed | Prior controlled execution, including auth, session/graph tests, snapshots, insights, provider plan/fallback and component contracts. | Not executed again in this audit. Counts apply to the previously tested checkout. |
| backend/tests/test_api.py test_sessions_are_isolated_and_close, test_workspace_list_only_shows_active_sessions_owned_by_the_user, test_saved_ontologies_include_versions_after_workspace_closes, test_snapshot_path_and_artifact_validation | Tests explicitly target owner boundaries, inventory/active-session distinction and artifact integrity. | Does not prove active workspace restart recovery or all production attack surfaces. |
| test_validation_only_workflow_builds_without_approval and frontend/e2e/validation-only-workflow.spec.ts | Prerequisites, current validation, hidden direct routes, navigation and naming. Local build-manager-poc-retry.log records pass after earlier failure. | Prior browser check not a fresh execution. |
| backend/tests/test_api.py test_s3_sdk_selection_through_graph_validation and test_bigquery_preview_checks_scan_budget | Compatible service fixture and mocked BigQuery scan boundary. | No live tenant proof. |
| Business Insights API tests and frontend/e2e/business-insights.spec.ts | Diverse CSV shapes, filters, currency, no graph, workspace isolation, deterministic results and exports. Local business-insights-final-e2e.log reports three passes. | Browser and test fixtures, not warehouse-scale quality. |
| Graph question/provider tests and frontend/src/test/graph-questions.test.tsx | Typed plan/schema guards, provider responses, explicit fallback and read-only behavior. graph-questions-retry.log records browser pass; initial workflow timed out. | Live Ollama demonstrated separately; live Groq U. |
| backend/tests/test_graph_publication.py and test_graph_live.py; frontend/e2e/published-graphs.spec.ts | Failure and lifecycle fixture coverage, conditional live fixture paths. | No verified current deployed publish/access, restore or live Neo4j tenant isolation from this review. |
| Prior Docker/API/browser checks | Source-to-graph app path, workspace file preservation across rebuild, Ollama live answer; separately observed registry unavailable when unconfigured. | Historical R only. Current deployment state deliberately not probed. |

## Final functionality classification

| Disposition | Functionality | Decision |
|---|---|---|
| Keep | Sign-in, owner isolation, workspace Home, source/scope, ontology authoring and validation, graph building/validation, local snapshots and Explorer | Preserve the verified core and improve recovery without changing stage IDs. |
| Enhance | Workspace reopening, connectors, data quality and lineage, Neo4j publishing, Business Insights and Ask Your Knowledge Graph | Improve evidence, readiness, scope and operational durability within existing service boundaries. |
| Merge | Schema Extraction/Analysis UI, repeated Build Manager subpages, local/published canvas and inspector primitives, Path/Metrics navigation, dashboard cards | Merge presentation. Preserve stable URLs, distinct authorization and processing stages. |
| Hide | AI Suggestions, Review & Approval and Ontology Versioning in POC; unavailable publishing actions; experimental standalone intelligence by default | Preserve governed behavior, published links with appropriate access, and historical artifacts. |
| Remove | None established | Current source references active services and compatibility APIs. Require dependency and usage evidence before deletion. |
