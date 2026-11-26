# KNOWLEDGE GRAPH STUDIO — COMPLETE APPLICATION ARCHITECTURE, FUNCTIONAL AUDIT & ENHANCEMENT ROADMAP

**Audit scope.** Current working tree, including existing untracked feature files. **S** means verified in source, **T** means previously executed tests with available results, **R** means a prior runtime observation in this workspace, and **U** means real operation unverified. Test definitions alone are coverage evidence. No new tests, builds, deployments, service changes, or runtime requests were performed. The report is the sole repository change.

## 1. Executive Summary

Knowledge Graph Studio is an end-to-end single-node POC with a proven CSV-to-graph path, two explicit workflow policies, and local graph queries backed by deterministic execution. Its strongest demonstrated workflow connects Customer360 CSV, extracts metadata, validates an ontology, constructs a property graph, and supports manual and Ollama-assisted exploration. The principal release risks are process-local workspace and job state, publishing prerequisites that can fail separately from application health, and in-memory scaling limits. Connector source implementations extend well beyond the live-tested matrix. GraphRAG, predictions and recommendations are experimental. Auth guards, schema validation, snapshot integrity, and scoped query compilation are useful production building blocks. No complete subsystem has production acceptance evidence.

## 2. Application Purpose and Business Value

| Audience | Problem and current benefit |
|---|---|
| Data engineer | Connect heterogeneous sources, inspect keys and lineage, profile and transform data into graph-ready rows. |
| Ontology steward | Model, validate and optionally govern entities, identifiers, source mappings and relationships. |
| Analyst | Explore identity, connectivity and paths, inspect scoped indicators and ask bounded graph questions. |
| Platform operator | Store reproducible snapshots and manage published versions, access, exports and audit events. |

The shared capability is traceable cross-record discovery. Domain-specific KPIs and causal conclusions still need curated business definitions and independent validation.

## 3. Technology Stack

| Layer | Declared stack |
|---|---|
| Frontend | React 19, TypeScript 5.9, Vite 8, React Router 7, Zustand, TanStack Query, Axios, Zod, React Hook Form, Tailwind 4, MUI, HeroUI, Emotion, Lucide. |
| Visuals | React Flow ontology canvas, Cytoscape graph canvas, HTML/CSS/Canvas dashboard graphics and shared MUI tables. |
| Backend and pipeline | Python 3.12 image, FastAPI, Uvicorn, Pydantic, PyJWT, bcrypt, multipart, python-dotenv, NetworkX, SciPy. |
| Data | psycopg, pyodbc with optional Driver 18, Oracle Thin, boto3, Azure identity/storage, Google Cloud Storage and BigQuery SDKs. |
| Persistence | SQLite account-owned library, filesystem workspace artifacts, optional PostgreSQL registry and Neo4j published graph. |
| AI | Groq SDK, Ollama HTTP API, deterministic rules, optional FastMCP stdio entry. |
| QA/deployment | pytest, Vitest, Testing Library, Playwright, axe, ESLint, generated OpenAPI TypeScript, Nginx, Docker Compose. |

Evidence: frontend/package.json, requirements.txt, backend/requirements*.txt, docker/*.Dockerfile. These are declaration and image versions.

## 4. Architecture Diagram

~~~mermaid
flowchart LR
  U[Browser] --> N[Nginx SPA and API proxy]
  N --> F[FastAPI and bearer auth]
  F --> W[Process-local owner-scoped workspace and jobs]
  W --> P[Ontology and graph pipeline]
  P --> C[CSV sample relational and cloud connectors]
  P --> G[NetworkX workspace graph]
  W --> S[(SQLite and filesystem)]
  G --> S
  G --> Pub[Publish version]
  Pub --> PG[(PostgreSQL registry and audit)]
  Pub --> Neo[(Neo4j scoped graph versions)]
  F --> PG
  F --> Neo
  F --> Q[Validated read-only question planner]
  Q --> G
  Q --> S
  Q --> O[Ollama on Windows]
  Q --> A[Groq]
  Q --> R[Rules]
  M[MCP stdio adapter] --> F
~~~

Browser requests terminate at the API. Neo4j and PostgreSQL have separate publication responsibilities. Publication coordinates two stores with state and recovery, so failure handling needs explicit consistency checks.

## 5. Repository Structure

| Path | Responsibility |
|---|---|
| Root README.md, .env.example, requirements files | Usage, native configuration template, dependencies. |
| frontend/src/main.tsx, App.tsx | SPA entry, providers, auth gate, lazy routes and workspace routing. |
| frontend/src/app, constants, shared, styles | Shell, state stores, workflow labels, hooks, forms and UI theme. |
| frontend/src/features | auth, overview, projects, sources, ontology, build and query features. |
| frontend/src/api, types; frontend/docs, scripts | API clients, shared schema definitions, OpenAPI snapshot and generation. |
| frontend/src/test, frontend/e2e | Component, client, auth and browser workflow tests. |
| backend/app/main.py, api, core, dto, exceptions | API entry/lifespan, scoped routers, settings/auth/middleware, validation and errors. |
| backend/app/services, repositories | Workflow, connectors, queues, graph readers/publishing, questions, analytics, workspace and registry storage. |
| backend/graph_mcp.py, backend/tests | MCP entry and backend regression/optional integration suites. |
| data_pipeline/src/kg_pipeline | CLI pipeline, core models, preprocessing/connectors, metadata extraction, ontology compilation, graph build and loaders. |
| scripts/run_pipeline.py, data_pipeline/tests, data | CLI entry, pipeline tests, CSV/JSON fixtures and ontology samples. |
| database/postgres/init, docker | Bootstrap schema/indexes, Compose, Nginx, Dockerfiles, reader provisioning. |
| docs | Existing architecture and capability notes. Source takes precedence where documentation describes a target. |

See Appendix A for the repository file inventory. Generated dependency trees and caches are excluded.

## 6. Complete Page and Module Inventory

API paths in section 6 are relative to /api/v1. Workspace routes use /sessions/{id}. Authentication errors clear frontend auth on 401. Queries and mutations surface errors in shared Feedback or feature alerts. Server prerequisites are authoritative. Direct links remain discoverable for enabled stages, while Next gates on completion, downstream prerequisites, pending edits and jobs.

| Page / route / source | Controls and direct behavior | State, prerequisites, gaps and importance |
|---|---|---|
| Login gate / any requested route, LoginPage.tsx | Username/password and Sign in call POST /login, followed by GET /me; logout posts /logout. Pending/invalid login feedback. | sessionStorage token. Successful login lands on Home. No separate login/settings route, SSO, MFA or recovery UI identified. Essential. |
| Home /, OverviewPage.tsx | Create/open workspace, active list, overview, progress, graph/build status and saved artifacts. /sessions, /stages, /ontologies, /graph-projects. | Zustand selection, server-local session registry, separate durable artifact index. Essential. Surface workspace expiry and publishing readiness clearly. |
| Domains /domains, DomainsPage.tsx | Create/list domain templates with project, questions, notes/scope. POST/GET /domains; selected later in Scope. | SQLite account-owned library. No edit/delete API found. Valuable, optional. |
| Global AppShell, StageStepper, StageContinuation, StageHelp | Sidebar/group collapse, breadcrumbs, activity events, API connection/help, logout/reset, stage help with checklist fallback. | No standalone settings route. Next respects server stage catalog, pending candidates, dirty scope, active work. Back renders under POC policy. Consolidate gate messaging. |
| Data Sources /sources, SourcesPage.tsx | Source/provider/auth fields, tests, discovery, CSV upload, paginated assets, bounded preview, confirm/cancel, disconnect; /source-types and /sources routes. | Confirm activates workspace connection. Failed candidate preserves active source. Secrets in process memory. Essential, add privilege and sensitivity preflight. |
| Goal & Scope /scope, ScopePage.tsx | Domain picker, project name, predefined/custom questions, exclusions/sensitivity and notes; GET/PUT /scope. | Project and questions validated, edits invalidate descendants and retain valid source. Essential. Sensitivity can be set after source preview. |
| Schema Extraction /metadata, MetadataPage.tsx | Extract, source tables, qualified-table columns and preview; /metadata/extract, /tables, /columns, /preview. | Scope and source required. Bounded preview uses sensitive-field declarations. Essential. Add drift/estimated size cues. |
| Schema Analysis /analysis, MetadataPage.tsx | Analyze, classifications and inferred relationship candidates; /metadata/analyze and /analysis. | Catalog required. Heuristics are advisory. Valuable processing, merge UI with extraction. |
| Ontology Studio /ontology, OntologyPage.tsx | Schema/empty draft, ID/name/author, visual model, class/attribute/relationship mappings, JSON, save/revert. /ontology/draft, /draft/save, /draft/revert and model edits. | Requires metadata/analysis. IDs and display names are separate. Names validated and saved by ID. Name-only save preserves downstream evidence. Structural changes invalidate it. Essential. |
| AI Suggestions /suggestions, ReviewPages.tsx | Actor, sample and table controls, Generate, Skip; /ontology/suggestions and /skip. | Governed only. Skip completes stage. Suggestions require review and controlled provider egress. Optional enhancement. |
| Review & Approval /review, ReviewPages.tsx | Preview and apply reviewed suggestion edits, decisions and build rules; /review/preview and /review. | Governed only. Produces a hybrid draft. Review stage and explicit approval in repository are separate. Valuable governance. |
| Ontology Validation /validation, ReviewPages.tsx | Validate, view report/issues; POST /ontology/validate, GET /validation. | POC requires saved draft; governed requires reviewed draft. Failed report blocks progress. Essential. |
| Ontology Versioning /repository, ReviewPages.tsx | Approve/reject, author and reviewer inputs, version/audit, rollback/use-approved; /approve, /versions and /audit. | Governed only; filed versions retained. Four-eyes checks need independently authenticated reviewer identity for enterprise. Valuable, hide for POC. |
| Graph Build Manager /build, /build/10, BuildPage.tsx | Batch size, business rules and values, Run stage or full build, status/cancel, events. /builds, /builds/status, /builds/stages/10, /events. | Requires eligible ontology and catalog. Rules validated against catalog. Essential. |
| Data Extraction /build/11 | Staged result and paginated selected rows, /builds/stages/11 and /builds/extracted-rows. | Requires plan. Memory-backed. Essential processing, optional standalone screen. |
| Data Quality /build/12 | Check results and configured business rules, /builds/stages/12. | Requires extraction. Blocking defects prevent completion. Essential control. |
| Cleaning & Entity Resolution /build/13 | Inspect merges/quarantine and page through details, /builds/stages/13 and /builds/cleaning/{kind}. | Quality prerequisite. Deterministic matching. Consolidate UI while retaining processing and audit. |
| Graph Construction /build/14 | Stage execution and graph build report, /builds/stages/14. | Requires cleaned data. Creates NetworkX graph. Essential processing. |
| Graph Validation /build/15 | Run integrity checks and inspect report, /builds/stages/15. | Graph prerequisite. Successful report required for snapshots. Essential control. |
| Storage & Snapshots /storage, StoragePage.tsx | Save, optional Publish to Neo4j, ontology/build/artifact selectors, history, make current, download. /graphs/snapshots and versioned /current, /download. | Requires stages 14 and 15. Durable artifacts. Optional external publication. |
| Graph Explorer /explorer, ExplorerPage.tsx | Current/snapshot selector, label/type filters, search, layouts, limits, neighborhood hops, zoom/fit/reset and property inspector. /graphs/data, /nodes, /node and /snapshots. | Active workspace required, manual current graph starts at stage 14. Relationship-type filter operates on visible edges. Essential outcome. |
| Path Analysis and Graph Metrics /explorer?view=path or metrics | Source/target/hops and visible path highlight, counts/components and connected-node rankings; /graphs/path and /metrics. | Bounded undirected path semantics. Highlight may omit off-canvas entities. Valuable as tabs rather than more stages. |
| Ask Your Knowledge Graph, GraphQuestions.tsx | Collapsible prompt, suggested questions, readiness, follow-up/rerun, results, executed plan and graph evidence. /graphs/questions, /provider, /suggestions. | Current graph or checked snapshot. Memory-only history. Unsupported prompts clarify. Valuable. |
| Business Insights /business-insights | Workspace, active source, dataset, graph/snapshot and configurable filters, refresh, metrics/charts/network, exports; /insights and workspace/snapshot APIs. | Available outside stage gating. Source widgets need source; current graph widgets need validated stage 15. Valuable, bounded. |

### Published Graphs

Shared route /published-graphs with query parameters for view and selection. The source files are PublishedGraphsPage.tsx, GraphIntelligenceTools.tsx and backend/app/api/graph_versions.py. To avoid repetition, version routes below are under /graph-projects/{project}/versions/{version}. Features depend on registry, access and Neo4j readiness. None completes a workflow stage by viewing it.

| View | Inputs, controls and APIs | Assessment |
|---|---|---|
| Root selector | Lists projects and versions, project/version dropdowns, unavailable/error states. GET /graph-projects and /versions. | Visible even if registry unconfigured. Published feature area should display readiness. |
| explorer | Name/ID, labels, relation/property filters, selection, scene save/restore, path, neighborhood and layout. /query, /neighborhood, /paths, /workspace-items. | Overlaps local Explorer UX but has distinct published access/storage. Valuable where publishing is enabled. |
| query | Templates and Cypher input, drafting, execute, result modes and saved queries. /query, /query-draft and /workspace-items. | Compiled subset and explicit execution. Optional for analysts using templates. |
| analytics | Counts, distributions, ranking algorithm, community drill-in. /analytics and /communities/{index}. | Version artifact analytics. Useful with provenance and sample/algorithm definitions. |
| schema | Labels, direction triples, indexes and constraints; /schema. | Useful to query authors and operators. Fold into query or operations where appropriate. |
| operations | Members/roles, build and publish, version comparison and history, export, make current, retention-gated deletion. Project /members, /health and version /compare, /export, /current and DELETE routes. | Privileged operations. Requires publishing preflight and explicit access. |
| intelligence | Published or current workspace structural analysis, predictions, scores, neighborhood export, published fact retrieval and investigation. /intelligence, /graphml/neighborhood, /graph-rag and /investigate. | Experimental. Treat similarity as heuristic evidence. Merge duplicative navigation with Ask and analytics. |
| graphml | Upload, mapping keys, preview and publish. Workspace /graphs/graphml/preview and /publish, with job status. | Optional interoperability, bounded upload and validation. Keep behind capability gating. |

## 7. End-to-End Workflow

The UI guides users through source stage 2 before scope stage 1. Neither requires the other on the server. The governed sequence is 2 → 1 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16. Explicit POC policy excludes 6, 7, and 9, yielding 13 stages. Graph Build Manager stays ID 10 and appears seventh in that UI. See stages.constants.ts, workflow_policy.py, StageContinuation.tsx and workflow.py.

| Stage | Prerequisite | Operation, completion and recovery |
|---|---|---|
| 2 | none | Candidate confirm activates source. Preview/cancel/reconnect available. Connection process-local; replacement discards downstream state. |
| 1 | none | Save scope and questions. Scope edit keeps eligible connection, invalidates derived work. |
| 3 | 1, 2 | Introspect selected source into catalog. Retry connector/schema failures. |
| 4 | 3 | Classify tables and infer candidates. Rebuild after catalog change. |
| 5 | 3, 4 | Save mapped ontology with at least one class. Correct mappings or revert. Durable working file. |
| 6 | 5 | Suggest or explicitly skip. Governed only. Retry provider or skip. |
| 7 | 5, 6 | Apply decisions into hybrid draft. Governed only. Review preview supports correction. |
| 8 | 5 POC; 7 governed | Validate. Only pass completes. POC binds build eligibility to validated structure and digest. Revise and rerun. |
| 9 | 8 | Approve/use an eligible version. Governed only. Repository and audit retained. |
| 10 | 3, 8 POC; 3, 9 governed | Construct projected build plan using eligible ontology. Fix mappings/eligibility and retry. |
| 11 | 10 | Staging batches and watermark observations. Process memory. Retry source reads after correction. |
| 12 | 11 | Key, type, null, relationship and business rules. Blocking violations prevent completion. Adjust source or rules. |
| 13 | 12 | Normalize, quarantine and resolve. Review matching and audit rows. State remains in memory. |
| 14 | 13 | Build directed property graph and counts. Rerun from eligible clean state. |
| 15 | 14 | Validate graph. Invalid report blocks validated snapshot. Repair mapping/data and rebuild. |
| 16 | 14, 15 | Save durable checksummed artifacts. Optional registry/Neo4j publication. Recovery and retry depend on artifact/version state. |

Login, workspace selection and optional domain templates precede stages. Explore, Ask, Insights and published queries are independent outcomes. One-click build runs 10–15; manually resolving source onboarding, inferred keys, semantic mapping and governance is still needed for many real schemas. There is no demonstrated restart/resume of an incomplete run from stage artifacts. CLI pipeline.py has separate defaults and should be documented as a separate execution profile.

## 8. Data Source and Pipeline Assessment

Evidence: api/sources.py, dto/sources.py, services/source_connections.py, provider_sources.py, core/source_network.py and data_pipeline/src/kg_pipeline/preprocessing/connectors. Guided connection validates input, optionally lists locations, creates a candidate, discovers and paginates assets, previews projected rows and confirms selection as the workspace’s single active source. Failures expose sanitized errors. Provider-specific account privilege remains operational configuration.

| Connector / implementation | Auth, schema, preview and ingestion | Incremental / evidence |
|---|---|---|
| CSV / csv_source.py | Bounded multipart, CSV parsing and inferred schema/keys, multi-file asset selection, bounded sample and staged cursor. | No CDC. Customer360 and messy fixture coverage. S/T/R. |
| Sample / sample_source.py | No external auth. Fixture catalog and in-memory rows use shared read interface. | No durable increment. S/T. |
| PostgreSQL / postgres_source.py | Credentials/TLS, allowlisted host, resolved address, schema/table/view and keys, bounded read-only data access, keyset or server cursor. | Reader supports watermark/resume parameters. No durable end-to-end CDC. Isolated local PostgreSQL pipeline run previously verified. S/R. |
| SQL Server / relational_source.py | ODBC Driver 18, SQL auth, read-only, certificate checks, declared keys and fetchmany/limited preview. Optional image driver. | Incremental workflow absent. S/U live. |
| Oracle / relational_source.py | Oracle Thin TCPS, service/SID, wallet options, declared keys, limited projected selection and fetchmany. | No durable increment. S/U live. Egress controls relevant to driver DNS resolution. |
| S3/S3-compatible / object_source.py | Default/temporary or explicit SDK auth, bucket and prefix discovery, bounded CSV range reads. Custom origins allowlisted. | No object change tracking. Real compatible HTTP fixture through graph validation; native AWS tenant unverified. S/T. |
| Azure Blob / ADLS / object_source.py | Account-derived endpoint, default identity, service principal/key/SAS where supported, container/filesystem and prefix listing, bounded CSV reads. | No durable incremental. S/U live. |
| GCS / object_source.py | ADC, bucket/prefix discovery, bounded CSV range/full reads. | No durable incremental. S/U live. |
| BigQuery / bigquery_source.py | ADC, project/dataset, catalog projection, dry run and billed-byte caps, paginated results. | No durable incremental. Mocked dry-run checks, live project unverified. S/T. |

Object index discovery is bounded, currently 1,000 entries per prefix. Partial inference can need explicit key mapping. CSV is the implemented file format. Guided staging defaults to 100,000 rows and 128 MiB estimated row data, not a peak-memory guarantee. Legacy paths need independent load qualification. Schema provenance is represented across selected assets and catalog metadata, validated mappings and artifacts. Quality checks include nulls, duplicates, referential integrity, type conversion, business rules and quarantine. Stage 12 has retail defaults when rules are omitted and matching tables exist. Deterministic resolution uses normalized mapped keys. For medallion-style processing, add immutable stage manifests, durable partitioned Silver staging, safe replays and checkpointed incremental Gold publication. Data source preview, full reads and aggregation merit connector-specific test fixtures and explicit cost/latency budgets.

## 9. Ontology and Graph Architecture

Pydantic core/ontology_models.py represents classes, attributes, relationships, identifier mappings, cardinality, lineage, origin, normalization and required flags. Schema drafts derive mapping candidates from tables and inferred or declared keys. Users can refine candidates with manual editors. Multiple domains fit the model, while the sample/default rule paths carry retail assumptions. s08_ontology_validation.py performs rule-based schema, mapping, type and relationship checks. No executable SHACL engine, OWL reasoner or RDF backend was identified. GraphML is property-graph interchange.

Ontology IDs and editable display names are separate. api/ontology.py writes working drafts by stable ID. Renaming updates the working copy while preserving validation evidence for unchanged structure. Structural edits invalidate descendants. The governed repository stores authored and reviewed versions plus audit entries. In POC mode, workflow.current_build_ontology enforces the validated structural version and the build records its digest.

s13_cleaning_er.py resolves candidates deterministically via normalized groups and mapped identifiers, with quarantine reports. s14_graph_builder.py maps clean rows to directed NetworkX MultiDiGraph entities and relationships with stable keys/provenance. s15_graph_validation.py checks the realized graph. s16_graph_persistence.py writes compressed JSON, GraphML, manifest/checksums and quarantine artifacts. services/graphs.py checks paths and verifies artifact hashes before loading. Rebuilds replace derived memory; artifacts live independently. Optional publication uses the PostgreSQL registry for version and permission metadata and Neo4j for scoped graph data. Database and filesystem graph copies need explicit retention, restore and cross-store reconciliation.

Major gaps are temporal modeling and incremental merges, extraction/input version hashes throughout the chain, reusable data contracts, and measurement of peak memory and query latency at representative sizes.

## 10. AI and Natural Language Query Capabilities

Evidence: dto/graph_questions.py, services/graph_questions.py, ollama_provider.py, graph_intelligence.py, stage_advice.py, cypher_subset.py, api/graphs.py and GraphQuestions.tsx.

| Capability | Actual behavior and limitation |
|---|---|
| Provider selection | KG_GRAPH_AI_ENABLED, KG_GRAPH_AI_PROVIDER, KG_GRAPH_AI_MODEL, GROQ_API_KEY and OLLAMA_BASE_URL. Status checks Ollama installed tags, while Groq checks configuration presence. Rule provider needs no model. Ollama service errors may fall back; show the provider that actually answered. |
| Typed query generation | Sends question, previous question and bounded identifiers from the selected graph. Response must match Pydantic plan and schema. Paths verify quoted IDs, property filters require allowed schema fields and literal grounding. No generated Python or arbitrary workspace Cypher executes. Scope is owner-checked. |
| Entity and relationship asks | List/count one entity label or one typed directed relationship pattern. Rule parser matches predefined templates. General cross-entity joins are unsupported. |
| Property filtering | Current graph can apply approved source-node property literal substring. No real numeric comparisons, inequalities, date filters or numeric aggregates in local NLQ. Historical snapshot suggestions use labels/types. |
| Traversal and paths | Shortest undirected path between exact supplied IDs, up to eight hops for NLQ. No arbitrary multi-hop pattern, dependency semantics, or business-impact computation. Manual path limits differ. |
| Aggregation, rankings and trends | Counts and structural summary, including isolated entities and label counts. No generic sum, average, top-N, time-series, cohort or inferred business metric in NLQ. Separate analytics tools calculate some of these. |
| Evidence and grounding | Deterministic computation produces actual rows and graph evidence. Provider orders a bounded set of verified statements. It does not author workspace arithmetic. Explanation fallback can be calculated even when planning used an LLM. History keeps one prior question as context, with small browser-memory rerun list. |
| Limits | 100k nodes, 250k edges, three-second bounded execution checks, two concurrent requests and 40 displayed matches. Provider timeouts are separate. Cold startup can lead to fallback. |
| Other AI surfaces | Stage Help, governed ontology suggestions, published Cypher drafts and neighborhood GraphRAG remain separate Groq paths. Published Cypher uses a compiled read-only subset. Published RAG provides facts and checks citation IDs; valid IDs cannot prove a generated sentence. |
| Prediction / embeddings | 16-dimensional hashed label-neighborhood structural features and common-neighbor heuristics. No trained predictive model, text/vector index or generic autonomous agent found. |

Prior live browser verification saw qwen2.5:7b, provider ollama, nine Account entities and verified-evidence text. An earlier first request fell back while the model was loading. That timing is consistent with inference latency, not sufficient to establish root cause. Live Groq verification is absent. Build a labeled, domain-diverse NLQ benchmark before adding capabilities, then extend the typed plan with predicates, aggregates, explicit traversal direction and execution budgets. Keep unsupported answers explicit. Untrusted prompt strings, source identifiers and published evidence require provider egress policy and quote preservation.

## 11. Business Insights and Analytics

The dashboard derives category/date/measure candidates from workspace catalogs and ontology metadata. It excludes selected keys/sensitive properties and uses small-group suppression. Category vocabulary is heuristic. A matching currency column can suppress mixed-currency totals. Default numeric totals do not establish a metric's business meaning. Stage 12 quality defaults can embed retail assumptions, but the dashboard computes metrics from the available data rather than hardcoding Customer360 dashboard values.

| Surface | Implemented behavior | Caveat |
|---|---|---|
| KPIs and performance | Record/profile counts, missingness and completeness, eligible sums/means, percent change across available periods, ranked visible category totals. | Counts may describe a bounded profile; no meaningful arbitrary composite quality score or full enterprise metric catalog. |
| Distributions and trends | Horizontal bars, donut for manageable categories, Canvas line/area trend and aggregation table. Date interval and range, measure, numeric range, category and chart click filters. | Key-ordered prefixes and partial periods may bias interpretation. Ranking is among visible categories. |
| Graph and quality | Bounded validated current graph or snapshot, entity/relationship distribution, connectivity, isolated nodes, weak components, relationship density, masked network, latest quality findings and dependency summaries. | Graph filters scope graph results. Source filters scope source aggregates. Quality comes from the latest pipeline report, independent of row filters. |
| Export and state | Aggregate CSV with definitions and freshness, trend PNG, browser print-to-PDF, persisted preferences keyed by workspace/source. | No scheduled reporting, verified pixel-perfect PDF or shared/curated dashboard catalog. |

Defaults: 5,000 profile rows, maximum 25,000, 60-second latest-selection cache, graph caps and bounded preview. Processing is backend-side with connector reads, rather than full data delivery to the browser. Add profile-scope labels, denominator definitions, externally curated metric semantics, pushed-down compatible aggregates, and anti-differencing safeguards for sensitive deployments. See api/insights.py, services/insights.py, frontend/src/features/query/{BusinessInsightsPage,InsightsCharts}.tsx.

## 12. Backend, API, Database and Security

| Severity | Finding, evidence and impact |
|---|---|
| High | **Restart and scaling.** SessionRepository, RevokedTokens and BuildRunner are process-local. Default active workspace TTL is 3,600 seconds, repository max 100, local thread pool two. Multiworker lacks shared state, revocation and coordinated queue. Global PIPELINE_LOCK serializes storage-sensitive pipeline calls across workspaces. |
| High | **Identity governance.** Published membership is registry-authorized and query scoping is compiled. Workflow author/reviewer fields can be caller-declared; four-eyes text separation does not prove a distinct principal signed. Add authenticated role-based approval and immutable decision audit. |
| High | **Sensitive data policy fragmentation.** Candidate preview can happen before scope. Metadata, extracted rows, graph display/export, insights and AI use separate filters. Consistent classification and export policies are not evidenced. Local artifacts can include identity/provenance/quarantine information. Limit ACLs and design central redaction. |
| High | **Resource pressure.** Upload caps, row/page limits and timeouts exist, but staging, graph construction and some analytics materialize memory. Snapshot reload and hashing can amplify work. No general API rate limiter or durable job queue identified. |
| High | **Publication dependencies.** PostgreSQL registry, permissions, Neo4j access and initialization are necessary. Prior runtime saw registry_unconfigured / HTTP 503 on /graph-projects, with healthy core app. |
| Medium | **API contracts.** Typed models at important boundaries coexist with Result[dict] and free-form reports. REST naming differs across workspace and published APIs. OpenAPI TS generation helps but cannot certify arbitrary dictionary shapes. |
| Medium | **Auth and secrets.** Bearer HS JWT, bcrypt, owner-scoped sessions, configured CORS and revocation checks. Tokens reside in sessionStorage and may be exposed by XSS. No enterprise IdP/SSO/MFA, shared revocation, per-user traffic quota or durable secret vault identified. Default local bootstrap needs explicit deployment hardening. |
| Medium | **SQL/Cypher handling.** Catalog keys, identifier quoting, parameterized queries and allowlists reduce risk. Cypher parser compiles a narrow pattern into project/version-scoped statements with limited rows. Database role and tenant isolation must be confirmed in real environments. Oracle/custom object routing needs egress controls. |
| Medium | **Observability and storage.** Structured API error codes, trace logs, workflow events and publication audit exist. Cross-component trace IDs, centralized metrics, redaction assurance, continuous retention policies across all artifact classes and restore drills are missing. |

Database transactions and version advisory/row locks are visible in repositories/graph_versions.py. Publishing coordinates registry and Neo4j, recovering interrupted jobs where implemented. Bootstrap SQL under database/postgres/init includes project membership, version/event/workspace-item tables and version lookup indexes. Verify those indexes and Neo4j uniqueness constraints on populated databases before publishing at scale. SQLite is the lightweight domain and working-draft catalog. It is not a shared workflow state store. Error envelopes hide provider internals, but stable machine-readable codes should distinguish unavailable, unconfigured, timed out, and unsupported conditions more consistently.

## 13. Docker and Infrastructure

Compose starts frontend and backend, with PostgreSQL and Neo4j available via profiles. Frontend is built with Node and delivered by Nginx. Nginx proxies /api/v1 to backend:8000, serves SPA routes, and publishes loopback port 8080 by default. Python image uses a non-root user and one Uvicorn worker. Docker build context filters keep local files/dependencies out; prior Windows context issues were avoided with a clean build context. Backend liveness checks /api/v1/health. PostgreSQL uses pg_isready, and frontend waits on backend dependency condition. Neo4j is not independently proven ready by API liveness. Named volumes retain backend files, PostgreSQL and Neo4j storage; recreation still loses process-local sessions. PostgreSQL init scripts apply when the database volume is first initialized, so existing volumes need explicit migration if schema changes.

Config surfaces: docker/compose.yaml, docker/.env.example, root .env.example, docker/nginx.conf, backend/app/core/config.py and data_pipeline/src/kg_pipeline/config.py. No secret-bearing values included. Ollama is host-managed, using host.docker.internal:11434 for Docker Desktop. Prior read and live inference worked through the Windows loopback listener in this setup. Keep internal connectivity distinct from public exposure. TLS ingress, production secret mounts, publication preflight, reproducible lockfiles, migration tooling and restore rehearsals are deployment priorities.

## 14. Code Quality and Testing

- Clear router, DTO, repository and pipeline boundaries. Shared React Query and UI components, a centralized workflow policy, and centralized stage display configuration are strengths.
- PublishedGraphsPage.tsx and OntologyPage.tsx combine many responsibilities; split by existing domain responsibilities when touching them. BuildPage repeats shell structure across stages intentionally but could use progressive disclosure. Multiple stage catalogs (pipeline registry, frontend order, labels and routes) are coordinated but merit parity tests. Unused dependency/dead-code deletion requires a separate usage/build audit; this read-only inspection does not certify specific packages removable.
- Existing evidence: previously executed backend/pipeline suite had 272 passed, 2 skipped. Frontend Vitest had 29 passed. Local business-insights-final-e2e.log records 3 passed. graph-questions-e2e.log records one timeout and one pass; graph-questions-retry.log records the successful workflow retry. Build logs record successful Vite builds. These are prior observations and not fresh audit runs.
- backend/tests/test_graph_live.py requires disposable live database fixtures and can skip. Source, validation-only, auth, temporal snapshots, governance, browser failures, publication and insights coverage exists. Mocked provider/transport tests are not equivalent to live cloud acceptance.
- Coverage gaps are production-size memory/load, concurrent mutation and restart/resume, publish backup/restore, provider timeout/connector matrix, browser accessibility beyond selected checks, and cross-surface PII/export regression. Prior bundle-size warnings, Data Sources MUI label/key console warnings in dev, and repository-wide lint false positive in an E2E file merit reproducible checks.

## 15. Current Bugs and Technical Debt

| Finding | Evidence and correction direction |
|---|---|
| Published graph route can open with registry API unavailable | R: /graph-projects 503 when registry DSN unset. S: registry precondition. Add published readiness and explicit UI disablement for unconfigured stacks. |
| Active workflow cannot resume after restart | S: process-local repository/state and queue. R: restart ended active sessions while saved file checksums matched. Add durable checkpoint model with recovery API and no credential serialization. |
| Cold Ollama inference can look like a network failure | R: fallback first, validated live retry succeeded. S: transport maps timeout/network into broad reachability error. Distinguish timeout, refusal, model missing and malformed inference; disclose cause and provider. |
| Node/path result visibility differs from execution result | S: local path highlight decorates visible graph rather than necessarily rendering whole shortest path. Offer a bounded result subgraph. |
| Workflow presentation is source-first although scope is needed at extraction | S: stage order and prerequisites; sensitive preview may precede declarations. Add preflight classification or revise display order deliberately. |
| Data Sources MUI warnings and artifact portability | Prior dev logs show picker label/key warnings. Windows direct Compose context issues previously observed. Add stable identifiers and reproducible source packaging. |
| Evidence plane fragmentation | S: local and published routing, snapshot integrity, analytics and AI code paths. Similar UI concepts obscure store, version, scope and freshness. Reuse presentation and normalized evidence definitions. |

## 16. Necessary, Optional, Redundant and Incomplete Features

A essential, B valuable, C optional, D overlapping/redundant presentation, E incomplete, F candidate for removal from default navigation. Multiple labels distinguish pipeline necessity from UI placement. These are design recommendations, and no removals were made.

| Module | Class | Rationale, consequences and recommended treatment |
|---|---|---|
| Authentication, workspace, Home, stage routing | A/E | Removing jeopardizes isolation and workflow. Keep and add durable resume. |
| Source connection, scope, catalog | A | Removing breaks activation and mapping. Keep key/sensitivity clues early. |
| Schema Analysis page | B/D | Analyzer feeds ontology prerequisites. Merge presentation into Metadata but keep its execution and evidence. |
| Domain templates | B/C | Accelerate common setup but scope can be entered directly. Hide or consolidate in Scope if adoption is low. |
| Ontology Studio and validation | A | Removing breaks all eligible graph building. Keep stable IDs, name editing, validation gate and reports. |
| AI Suggestions and governed review/repository | B/C/E | POC already hides them. Governed depends on suggestion-or-skip, review and approval. Preserve code and historical records. Improve authenticated sign-off before enterprise rollout. |
| Build Manager, extraction, quality, cleaning, construction and graph checks | A/D | Steps have distinct state and recovery, but separate repeated screens can be consolidated into Build Manager with links. Removing controls would lose reproducibility and quality evidence. |
| Local storage and snapshots | A | Removing loses durable graph restoration/export. Separate save snapshot from publish. |
| Explorer, Path Analysis and Metrics | A/B/D | Keep core manual exploration. Sidebar aliases can funnel into tabs. Preserve URL links for bookmarks. |
| Ask Your Knowledge Graph and global Stage Help | B/C/E | Different intent, shared provider/evidence policy. Hide optional AI affordances for environments that disallow model use. Keep manual graph controls. |
| Business Insights and Published Analytics | B/D/E | Similar visual presentation, different source/profile versus published-version semantics. Share components and definitions. Hiding one loses its specific data context. |
| Published project/access/lifecycle | B/E | Optional for local POC, required for managed published data. Gate by capability and improve operational readiness. Deleting would affect registry, Neo4j, authorizations and MCP. |
| Published Explorer, Query Workbench, Schema | B/C/D | Share graph components and selectors with local explorer where possible. Query/admin use cases differ. Keep distinct execution and access guards. |
| GraphML import/export, MCP adapter | C | Useful interoperability. Hide where no operational owner exists. Removing breaks existing import/export integrations and optional tooling. |
| Link prediction, structural embeddings, standalone experimental Intelligence labels | C/E/F | Low verified business value as standalone surface today. Hide by default and retain existing APIs while validating heuristic utility. RAG shares evidence and could live under Ask with clear scope. |
| Duplicate navigation-only entries into the same tabs | D/F | Safe consolidation when existing URLs and direct links keep their semantics. No service behavior needs removal. |

## 17. Missing Capabilities

Release gates include durable reopen/recovery and queueing, deployment readiness and migration controls, independent approvals and identity integration, unified data redaction/export policy, tested non-CSV connector lifecycle and scale gates. Product gaps include consistent lineage and drift, incremental refresh, semantic KPI definitions, optional standards-based ontology export/validation, incident monitoring, and measurable graph query performance. Advanced gaps include general typed NLQ predicates/aggregations, directed semantic traversal, evaluated multilingual or ambiguous queries, reliable cross-document GraphRAG, and privacy-protected publication at scale. These should be attempted after core controls rather than becoming default scope.

## 18. Prioritized Enhancement Recommendations

Effort is an indicative range for one engineer in working days, excluding organization-wide reviews and external vendor provisioning. Risk describes delivery/change risk. P0 blocks a targeted release use case; P1 core milestone, P2 planned value, P3 optional. Rows identify value, current gap/solution, dependencies, complexity, effort, risk and target.

| Enhancement and value | Current gap and recommended solution | Dependencies | Priority, complexity, effort, risk, target |
|---|---|---|---|
| Published readiness | Unset registry yields visible failures. Run dependency/schema/role preflight and expose per-feature readiness. | Compose, registry, Neo4j | P0, Low, 2–4d, low, POC/publish |
| Durable reopen | Process restart loses workflow. Persist stage inputs/results/checkpoints and immutable artifact references. | Storage contract, auth owner, migrations | P0, High, 15–30d, high, MVP |
| Consistent privacy | Context-dependent redaction. Centralize classification and projection policy across previews, charts, exports and providers. | Catalog/ontology and role model | P0, High, 12–25d, high, MVP |
| Connector qualification | Several concrete SDK adapters have limited acceptance. Build provider matrix with no routable secrets in CI, schema drift and edge-case fixtures. | Disposable provider fixtures, egress policy | P1, Medium, 6–15d, medium, MVP |
| Durable staging and incrementality | Full memory staging and no resumable changes. Use partitioned staged artifacts, checkpoints and replay contracts. | Durable workspace/run store | P1, High, 20–45d, high, enterprise |
| Guided workflow and remediation | Repeated pages and failure steps force context switches. Use a unified build timeline, first-error actions and sensitivity preflight. | Stable state transitions, UX tests | P1, Medium, 5–12d, medium, POC/MVP |
| Stewardship and graph integrity | Inferred keys and opaque changes alter output. Add mapping confidence, semantic diffs, lineage and review of merge decisions. | Reproducible source/run identity | P1, Medium, 8–18d, medium, MVP |
| Signed approval and enterprise identity | Text actor names and local identity. Bind approvals to authenticated roles and add external IdP and durable revocation. | Registry, role model, IdP | P1, High, 12–30d, high, enterprise |
| Graph workspace consolidation | Two explorers duplicate UX. Share graph panels, queries scoped via adapters and result-subgraph paths. | Workspace/published adapter contracts | P2, Medium, 8–18d, medium, MVP |
| Typed NLQ plus benchmark | Narrow grammar and unmeasured correctness. Add test corpus, typed numeric/date predicates and verified aggregates/traversals. | Query limits, evidence and permissions | P1, Medium, 10–22d, medium, MVP |
| Provider reliability | Timeout and refusal treated similarly. Distinguish readiness, model load/inference time, fallback causes and calculate-first mode. | Provider diagnostics and telemetry | P1, Low, 3–7d, low, POC/MVP |
| Business metric semantics | Heuristic measures based on profiles. Introduce governed metric definitions, explicit denominators and supported pushdown/export provenance. | Catalog contracts and data permissions | P2, High, 10–25d, high, enterprise |
| Operational controls | No unified observability/SLOs or documented recovery at scale. Add traces, quota budgets, migrations, backups and restore exercises. | Deployment and job architecture | P1, High, 12–25d, medium, enterprise |
| Standards and analytics | Scope for optional SHACL/RDF interchange and graph algorithms with clear semantics. Start data-contract use case before new store. | Ontology versioning and benchmark | P2, High, 10–25d, medium, enterprise |
| Evaluated GraphRAG/prediction | Structural heuristics and bounded facts lack business evaluation. Build evidence corpus, retrieval quality gates and offline baselines. | Egress policy, evidence/access parity | P3, High, 15–40d, high, optional enterprise |

## 19. Implementation Roadmap

**Phase A — Immediate fixes.** Add readiness and feature gating for publishing. Separate provider cold-timeout and connection errors. Reduce observable picker warnings and verify local reproducible builds. Publish a supported-connector matrix and default privacy guidance. These make the existing POC understandable without expanding scope.

**Phase B — Core application.** Persist workspace and job checkpoints without persisting raw secrets. Enable restart drills, recovery and quality remediation. Separate durable workspace identity from short-lived connection handles. Consolidate stage presentation and publish clear stage artifacts. Qualify CSV and PostgreSQL first, then prioritize additional connectors based on customer demand.

**Phase C — Graph intelligence.** Share explorer and evidence UI across adapters, add evidence subgraph for paths, and introduce typed NLQ coverage and evaluated extensions. Govern dashboard definitions and disclose sampling before offering additional metrics. Keep deterministic answers for core questions.

**Phase D — Enterprise readiness.** Enforce authenticated approvals, define RBAC/export classification, run migration/restore and load tests, and add durable staging, list/query quotas, operational traces and secrets handling. Establish publication consistency and SLOs before enabling shared clusters.

**Phase E — Advanced capabilities.** Add domain-qualified semantic retrieval, GraphRAG and predictions only after objective quality, privacy and business-value gates. Avoid new graph engines without a workload or interoperability requirement.

## 20. Final Architectural Recommendations

Treat workspace authoring, artifact storage, and published query serving as distinct lifecycle boundaries. Keep one underlying workflow model and consolidate its presentation. Retain NetworkX for bounded authoring and testing. Use an adapter boundary and capacity measurements before offloading workloads to an engine. Keep publication optional for local use, with its own readiness and operational baseline. Keep typed deterministic graph execution authoritative and make the AI provider replaceable within the same access and evidence policy.

### Appendix A — Repository file inventory

The inventory includes tracked files and non-ignored working-tree files present during discovery. It excludes generated dependency and cache folders, local secret files, and the audit itself.

~~~text
.env.example
.gitignore
backend/app/api/auth.py
backend/app/api/builds.py
backend/app/api/graph_versions.py
backend/app/api/graphs.py
backend/app/api/insights.py
backend/app/api/library.py
backend/app/api/metadata.py
backend/app/api/ontology.py
backend/app/api/sessions.py
backend/app/api/sources.py
backend/app/core/config.py
backend/app/core/dependencies.py
backend/app/core/middleware.py
backend/app/core/security.py
backend/app/core/source_network.py
backend/app/dto/graph_questions.py
backend/app/dto/insights.py
backend/app/dto/models.py
backend/app/dto/sources.py
backend/app/exceptions/handlers.py
backend/app/main.py
backend/app/repositories/graph_versions.py
backend/app/repositories/library.py
backend/app/repositories/sessions.py
backend/app/services/builds.py
backend/app/services/cypher_subset.py
backend/app/services/graph_exports.py
backend/app/services/graph_intelligence.py
backend/app/services/graph_publication.py
backend/app/services/graph_questions.py
backend/app/services/graphml_import.py
backend/app/services/graphs.py
backend/app/services/insights.py
backend/app/services/neo_graph.py
backend/app/services/ollama_provider.py
backend/app/services/ontology.py
backend/app/services/provider_sources.py
backend/app/services/source_connections.py
backend/app/services/stage_advice.py
backend/app/services/workflow.py
backend/app/services/workflow_policy.py
backend/graph_mcp.py
backend/README.md
backend/requirements.txt
backend/requirements-dev.txt
backend/requirements-mcp.txt
backend/tests/helpers.py
backend/tests/test_api.py
backend/tests/test_auth.py
backend/tests/test_graph_intelligence.py
backend/tests/test_graph_live.py
backend/tests/test_graph_mcp.py
backend/tests/test_graph_publication.py
data/fixtures/groq_offline_fixture.json
data/ontologies/retail_manual_draft.json
data/samples/customer360/accounts.csv
data/samples/customer360/banks.csv
data/samples/customer360/credit_enquiry.csv
data/samples/customer360/credit_score.csv
data/samples/customer360/customers.csv
data/samples/customer360/loans.csv
data/samples/customer360/payments.csv
data/samples/customer360_messy/customers.csv
data/samples/customer360_messy/loans.csv
data/samples/README.md
data_pipeline/src/kg_pipeline/__init__.py
data_pipeline/src/kg_pipeline/config.py
data_pipeline/src/kg_pipeline/core/__init__.py
data_pipeline/src/kg_pipeline/core/context.py
data_pipeline/src/kg_pipeline/core/naming.py
data_pipeline/src/kg_pipeline/core/ontology_models.py
data_pipeline/src/kg_pipeline/core/s01_scope.py
data_pipeline/src/kg_pipeline/core/schema_models.py
data_pipeline/src/kg_pipeline/graph_builder/__init__.py
data_pipeline/src/kg_pipeline/graph_builder/loaders/s16_graph_persistence.py
data_pipeline/src/kg_pipeline/graph_builder/s10_build_plan.py
data_pipeline/src/kg_pipeline/graph_builder/s14_graph_builder.py
data_pipeline/src/kg_pipeline/graph_builder/s15_graph_validation.py
data_pipeline/src/kg_pipeline/metadata_extractor/s03_schema_extraction.py
data_pipeline/src/kg_pipeline/metadata_extractor/s04_schema_analysis.py
data_pipeline/src/kg_pipeline/ontology_compiler/ontology_draft.py
data_pipeline/src/kg_pipeline/ontology_compiler/s05_manual_ontology.py
data_pipeline/src/kg_pipeline/ontology_compiler/s06_ai_suggestions.py
data_pipeline/src/kg_pipeline/ontology_compiler/s07_review_approval.py
data_pipeline/src/kg_pipeline/ontology_compiler/s08_ontology_validation.py
data_pipeline/src/kg_pipeline/ontology_compiler/s09_ontology_repository.py
data_pipeline/src/kg_pipeline/pipeline.py
data_pipeline/src/kg_pipeline/preprocessing/connectors/__init__.py
data_pipeline/src/kg_pipeline/preprocessing/connectors/base.py
data_pipeline/src/kg_pipeline/preprocessing/connectors/bigquery_source.py
data_pipeline/src/kg_pipeline/preprocessing/connectors/csv_source.py
data_pipeline/src/kg_pipeline/preprocessing/connectors/object_source.py
data_pipeline/src/kg_pipeline/preprocessing/connectors/postgres_source.py
data_pipeline/src/kg_pipeline/preprocessing/connectors/relational_source.py
data_pipeline/src/kg_pipeline/preprocessing/connectors/sample_data.py
data_pipeline/src/kg_pipeline/preprocessing/connectors/sample_source.py
data_pipeline/src/kg_pipeline/preprocessing/s02_connect.py
data_pipeline/src/kg_pipeline/preprocessing/s11_extraction.py
data_pipeline/src/kg_pipeline/preprocessing/s12_data_quality.py
data_pipeline/src/kg_pipeline/preprocessing/s13_cleaning_er.py
data_pipeline/src/kg_pipeline/preprocessing/transform.py
data_pipeline/tests/conftest.py
data_pipeline/tests/test_csv_source.py
data_pipeline/tests/test_naming.py
data_pipeline/tests/test_ontology_draft.py
data_pipeline/tests/test_pipeline_csv.py
database/postgres/init/01_source_schema.sql
database/postgres/init/02_kg_meta_schema.sql
database/postgres/init/04_graph_versions.sql
docker/.env.example
docker/backend.Dockerfile
docker/backend.Dockerfile.dockerignore
docker/compose.yaml
docker/frontend.Dockerfile
docker/frontend.Dockerfile.dockerignore
docker/nginx.conf
docker/postgres-reader.sql
docker/README.md
docs/AGENTIC_WORKFLOWS.md
docs/API_REFERENCE.md
docs/api-integration.md
docs/DEPLOYMENT_AND_CONFIGURATION.md
docs/GRAPH_ANALYTICS.md
docs/GRAPH_EXPLORER_AND_QUERY.md
docs/GRAPHRAG_AND_EMBEDDINGS.md
docs/KNOWLEDGE_GRAPH_IMPLEMENTATION_AUDIT.md
docs/KNOWLEDGE_GRAPH_IMPLEMENTATION_REPORT.md
docs/KNOWLEDGE_GRAPH_PLATFORM_AUDIT.md
docs/KNOWLEDGE_GRAPH_TARGET_ARCHITECTURE.md
docs/KNOWLEDGE_GRAPH_UPGRADE_REPORT.md
docs/LINK_PREDICTION_AND_RECOMMENDATIONS.md
docs/MCP_SERVER.md
docs/NATURAL_LANGUAGE_GRAPH_QUERY.md
docs/NEO4J_INTEGRATION.md
docs/PUBLISHED_GRAPH_PLATFORM.md
frontend/.env.example
frontend/.gitignore
frontend/docs/api-inventory.md
frontend/docs/architecture.md
frontend/docs/integration-report.md
frontend/docs/migration-map.md
frontend/docs/openapi.json
frontend/e2e/api-workflow.spec.ts
frontend/e2e/browser-failures.spec.ts
frontend/e2e/business-insights.spec.ts
frontend/e2e/published-graphs.spec.ts
frontend/e2e/sample-workflow.spec.ts
frontend/e2e/session-expiration.spec.ts
frontend/e2e/validation-only-workflow.spec.ts
frontend/e2e/workflow-fixtures.ts
frontend/eslint.config.mjs
frontend/index.html
frontend/npm22.cmd
frontend/package.json
frontend/package-lock.json
frontend/playwright.config.ts
frontend/README.md
frontend/scripts/generate-api-types.mjs
frontend/src/api/authApi.ts
frontend/src/api/client.ts
frontend/src/api/libraryApi.ts
frontend/src/api/sessionsApi.ts
frontend/src/api/workflowApi.ts
frontend/src/App.tsx
frontend/src/app/authStore.ts
frontend/src/app/layout/AppShell.tsx
frontend/src/app/layout/StageContinuation.tsx
frontend/src/app/layout/StageHelp.tsx
frontend/src/app/layout/StageStepper.tsx
frontend/src/app/providers.tsx
frontend/src/app/store.ts
frontend/src/constants/branding.ts
frontend/src/constants/businessQuestions.ts
frontend/src/constants/stageNavigation.ts
frontend/src/constants/stages.constants.ts
frontend/src/features/auth/LoginPage.tsx
frontend/src/features/build/BuildPage.tsx
frontend/src/features/build/StoragePage.tsx
frontend/src/features/ontology/AttributeEditor.tsx
frontend/src/features/ontology/OntologyCanvas.tsx
frontend/src/features/ontology/OntologyPage.tsx
frontend/src/features/ontology/ReviewPages.tsx
frontend/src/features/overview/OverviewPage.tsx
frontend/src/features/projects/BusinessQuestionsField.tsx
frontend/src/features/projects/DomainsPage.tsx
frontend/src/features/projects/ScopeFields.tsx
frontend/src/features/projects/ScopePage.tsx
frontend/src/features/query/BusinessInsightsPage.tsx
frontend/src/features/query/ExplorerPage.tsx
frontend/src/features/query/GraphCanvas.tsx
frontend/src/features/query/GraphIntelligenceTools.tsx
frontend/src/features/query/GraphQuestions.tsx
frontend/src/features/query/InsightsCharts.tsx
frontend/src/features/query/PublishedGraphsPage.tsx
frontend/src/features/sources/ConnectionFields.tsx
frontend/src/features/sources/guidedSources.ts
frontend/src/features/sources/MetadataPage.tsx
frontend/src/features/sources/SourceAssets.tsx
frontend/src/features/sources/SourcesPage.tsx
frontend/src/main.tsx
frontend/src/shared/hooks/useWorkflowStages.ts
frontend/src/shared/hooks/useWorkspace.ts
frontend/src/shared/ui/WorkspaceUi.tsx
frontend/src/styles/global.css
frontend/src/styles/theme.ts
frontend/src/test/api-contract.test.ts
frontend/src/test/auth.test.ts
frontend/src/test/feedback.test.tsx
frontend/src/test/graph-intelligence.test.tsx
frontend/src/test/graph-questions.test.tsx
frontend/src/test/published-graphs.test.tsx
frontend/src/test/session-lifecycle.test.tsx
frontend/src/test/setup.ts
frontend/src/test/stores.test.ts
frontend/src/types/common.types.ts
frontend/src/types/generated/openapi.ts
frontend/tsconfig.app.json
frontend/tsconfig.json
frontend/tsconfig.node.json
frontend/vite.config.ts
README.md
requirements.txt
requirements-dev.txt
scripts/run_pipeline.py
~~~


### Appendix B — Operational boundaries and evidence pointers

| Boundary | Code and audit implication |
|---|---|
| HTTP ingress | backend/app/core/middleware.py BodyLimitMiddleware accumulates request messages before parsing. The request limit mitigates oversized individual bodies but leaves aggregate peak allocation dependent on concurrency. Stream uploads behind bounded spooling and per-account quotas before exposing the service widely. |
| Secrets and role scope | backend/app/core/security.py, dependencies.py, repositories/graph_versions.py authorize session owner or published project access. Registry grants explicitly include viewer access, while management is owner-scoped. Confirm separation between warehouse, graph reader and publisher roles at deployment. |
| API expansion | backend/app/api/graph_versions.py BASE and TOOLS resolve project and version UUIDs. It also exposes a published build operation under an active session and project health. API reference is generated from actual registrations. The browser router has no URL registry for all server endpoints. |
| Snapshot safety | services/graphs.py checks canonical paths and artifact hashes. Test integrity and portability independently from durable restore of workflow sessions. |
| MCP | backend/graph_mcp.py wraps existing authenticated published endpoints over stdio. It can list projects/versions, inspect schemas and neighborhoods, query and rank. It needs its own token and authorized API URL and is not a default web route or Compose service. |
| Runtime evidence boundaries | POC 13-stage UI, local rebuild health, source/snapshot analytics, Ollama count and fallback came from previous controlled checks. Published Graphs 503 was specific to an unset registry, not proof of an implementation defect in all deployments. No release-wide current live acceptance was performed. |

### Ten highest-priority improvements

1. Make publication dependency status visible and gate publishing until the registry, schema and Neo4j roles are ready.
2. Persist workspace identity, draft references and workflow checkpoints so users can resume after restart.
3. Apply a shared classification and redaction policy at source preview, read, export and AI boundaries.
4. Build a connector acceptance matrix starting with CSV and PostgreSQL, then the highest-demand enterprise adapters.
5. Replace large in-memory stage results with durable, partitioned artifacts and resumable execution.
6. Bind approval and role grants to independently authenticated principals with a durable audit trail.
7. Consolidate workflow progress and remediation into the Build Manager while keeping stage-level evidence.
8. Add data contracts, drift detection, input fingerprints and end-to-end lineage.
9. Distinguish model availability from inference readiness and benchmark the bounded NLQ grammar across domains.
10. Define operational quotas, metrics, migrations, backup and restore tests before enabling shared production access.

### Ten most important architectural risks

1. Process-local workflow sessions and jobs disappear after restart and cannot safely scale across workers.
2. Partial publication across PostgreSQL and Neo4j can require reconciliation and explicit recovery.
3. Privacy decisions vary across preview, build results, artifacts, analytics and AI pathways.
4. Caller-declared workflow reviewer names can undermine meaningful separation of duties.
5. Memory-bound staging, graph algorithms, upload buffering and snapshot loading can exhaust host capacity.
6. A healthy API can hide unavailable publishing, provider or connector capabilities.
7. Unqualified connector/TLS/credential configurations can fail or expose excessive outbound permissions.
8. Inferred mappings, retail defaults and bounded profiles can produce plausible output with wrong business semantics.
9. Provider drift, broad timeout errors and incomplete citation verification can weaken confidence in AI answers.
10. Existing local and published feature overlap can obscure data scope, freshness, permissions and ownership.
