# API integration inventory

Generated from the actual backend OpenAPI 3.1 contract and checked against controllers. All paths below are complete. JSON success types include the `Result` envelope. Binary downloads and 204 are handled separately.

All 58 operations have frontend adapters and UI consumers. 57 are exercised with successful real local HTTP responses across the sample/CSV integration tests and browser lifecycle. PostgreSQL has typed request/response handling and existing backend tests with mocked dependencies; no live PostgreSQL credentials or connection were used.

| Method | Endpoint | Request body | Parameters | Response | Adapter / UI | Status |
|---|---|---|---|---|---|---|
| GET | /api/v1/health | None | None | 200: unknown | sessionsApi / AppShell / OverviewPage / BuildPage | Implemented; real local HTTP exercised |
| GET | /api/v1/stages | None | None | 200: Result_list_dict__ | sessionsApi / AppShell / OverviewPage / BuildPage | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions | application/json: SessionCreate | None | 201: Result_SessionView_ | sessionsApi / AppShell / OverviewPage / BuildPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id} | None | path: session_id (required) | 200: Result_SessionView_ | sessionsApi / AppShell / OverviewPage / BuildPage | Implemented; real local HTTP exercised |
| DELETE | /api/v1/sessions/{session_id} | None | path: session_id (required) | 204: no body | sessionsApi / AppShell / OverviewPage / BuildPage | Implemented; real local HTTP exercised |
| PUT | /api/v1/sessions/{session_id}/scope | application/json: ScopeRequest | path: session_id (required) | 200: Result_dict_ | scopeApi / ScopePage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/scope | None | path: session_id (required) | 200: Result_Union_dict__NoneType__ | scopeApi / ScopePage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/events | None | path: session_id (required); query: offset [minimum=0, default=0]; query: limit [minimum=1, maximum=500, default=100] | 200: Result_Page_dict__ | sessionsApi / AppShell / OverviewPage / BuildPage | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/sources/sample | None | path: session_id (required) | 200: Result_dict_ | sourcesApi / SourcesPage | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/sources/postgres | application/json: PostgresRequest | path: session_id (required) | 200: Result_dict_ | sourcesApi / SourcesPage | Implemented; mocked connector tests; live unverified |
| POST | /api/v1/sessions/{session_id}/sources/upload | multipart/form-data: repeated files (binary) | path: session_id (required) | 200: Result_dict_ | sourcesApi / SourcesPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/sources | None | path: session_id (required) | 200: Result_dict_ | sourcesApi / SourcesPage | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/metadata/extract | None | path: session_id (required) | 200: Result_SchemaCatalog_ | metadataApi / MetadataPage / OntologyPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/metadata | None | path: session_id (required) | 200: Result_SchemaCatalog_ | metadataApi / MetadataPage / OntologyPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/metadata/tables | None | path: session_id (required); query: offset [minimum=0, default=0]; query: limit [minimum=1, maximum=200, default=50] | 200: Result_Page_dict__ | metadataApi / MetadataPage / OntologyPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/metadata/columns | None | path: session_id (required); query: table (required) | 200: Result_list_dict__ | metadataApi / MetadataPage / OntologyPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/metadata/preview | None | path: session_id (required); query: table (required); query: limit [minimum=1, maximum=100, default=20] | 200: Result_list_dict__ | metadataApi / MetadataPage / OntologyPage | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/metadata/analyze | None | path: session_id (required) | 200: Result_dict_ | metadataApi / MetadataPage / OntologyPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/metadata/analysis | None | path: session_id (required) | 200: Result_list_dict__ | metadataApi / MetadataPage / OntologyPage | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/draft | application/json: DraftRequest | path: session_id (required) | 200: Result_dict_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/ontology/draft | None | path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| PUT | /api/v1/sessions/{session_id}/ontology/draft | application/json: OntologyRequest | path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/draft/revert | None | path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/draft/save | None | path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/classes | application/json: ClassRequest | path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| PUT | /api/v1/sessions/{session_id}/ontology/classes/{class_name}/attributes | application/json: AttributesRequest | path: class_name (required); path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| PATCH | /api/v1/sessions/{session_id}/ontology/classes/{class_name} | application/json: RenameRequest | path: class_name (required); path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| DELETE | /api/v1/sessions/{session_id}/ontology/classes/{class_name} | None | path: class_name (required); path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/relationships | application/json: RelationshipRequest | path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| DELETE | /api/v1/sessions/{session_id}/ontology/relationships | None | path: session_id (required); query: key (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/suggestions | application/json: AIRequest | path: session_id (required) | 200: Result_list_ReviewItem__ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/ontology/suggestions | None | path: session_id (required) | 200: Result_dict_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/suggestions/skip | None | path: session_id (required) | 200: Result_dict_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/review/preview | application/json: ReviewRequest | path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/review | application/json: ReviewRequest | path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/validate | None | path: session_id (required) | 200: Result_dict_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/ontology/validation | None | path: session_id (required) | 200: Result_dict_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/approve | application/json: ApprovalRequest | path: session_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/ontology/versions | None | path: session_id (required); query: ontology_id (required) | 200: Result_list_dict__ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/ontology/versions/{version} | None | path: version (required); path: session_id (required); query: ontology_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/versions/{version}/rollback | application/json: ActorRequest | path: version (required); path: session_id (required); query: ontology_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/ontology/use-approved | None | path: session_id (required); query: ontology_id (required) | 200: Result_Ontology_ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/ontology/audit | None | path: session_id (required); query: ontology_id (required); query: offset [minimum=0, default=0]; query: limit [minimum=1, maximum=500, default=100] | 200: Result_Page_dict__ | ontologyApi / OntologyPage / AttributeEditor / ReviewPages | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/builds | application/json: BuildRequest | path: session_id (required) | 202: Result_dict_ | buildsApi / BuildPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/builds/status | None | path: session_id (required) | 200: Result_Union_dict__NoneType__ | buildsApi / BuildPage | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/builds/stages/{stage} | application/json: BuildRequest | path: stage (required); path: session_id (required) | 200: Result_dict_ | buildsApi / BuildPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/builds/stages/{stage} | None | path: stage (required); path: session_id (required) | 200: Result_dict_ | buildsApi / BuildPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/builds/extracted-rows | None | path: session_id (required); query: table (required); query: offset [minimum=0, default=0]; query: limit [minimum=1, maximum=200, default=50] | 200: Result_Page_dict__ | buildsApi / BuildPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/builds/cleaning/{kind} | None | path: kind (required); path: session_id (required); query: offset [minimum=0, default=0]; query: limit [minimum=1, maximum=200, default=50] | 200: Result_Page_dict__ | buildsApi / BuildPage | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/graphs/snapshots | application/json: SnapshotRequest | path: session_id (required) | 200: Result_dict_ | snapshotsApi / StoragePage / ExplorerPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/graphs/snapshots | None | path: session_id (required); query: ontology_id (required) | 200: Result_list_dict__ | snapshotsApi / StoragePage / ExplorerPage | Implemented; real local HTTP exercised |
| POST | /api/v1/sessions/{session_id}/graphs/snapshots/{build_id}/current | None | path: build_id (required); path: session_id (required); query: ontology_id (required) | 200: Result_dict_ | snapshotsApi / StoragePage / ExplorerPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/graphs/snapshots/{build_id}/download/{artifact} | None | path: build_id (required); path: artifact (required) [enum=['graph.json.gz', 'graph.graphml', 'manifest.json', 'quarantine.json']]; path: session_id (required); query: ontology_id (required) | 200: binary FileResponse (controller overrides generic OpenAPI metadata) | snapshotsApi / StoragePage / ExplorerPage | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/graphs/data | None | path: session_id (required); query: ontology_id; query: build_id; query: limit [minimum=1, maximum=500, default=300]; query: edge_limit [minimum=1, maximum=2000, default=1000]; query: labels; query: focus; query: hops [minimum=1, maximum=3, default=1] | 200: Result_GraphView_ | graphsApi / ExplorerPage / GraphCanvas | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/graphs/nodes | None | path: session_id (required); query: ontology_id; query: build_id; query: search [default=]; query: label; query: offset [minimum=0, default=0]; query: limit [minimum=1, maximum=200, default=50] | 200: Result_Page_dict__ | graphsApi / ExplorerPage / GraphCanvas | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/graphs/node | None | path: session_id (required); query: node_id (required); query: ontology_id; query: build_id; query: limit [minimum=1, maximum=500, default=100] | 200: Result_dict_ | graphsApi / ExplorerPage / GraphCanvas | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/graphs/path | None | path: session_id (required); query: source (required); query: target (required); query: ontology_id; query: build_id; query: max_hops [minimum=1, maximum=100, default=20] | 200: Result_dict_ | graphsApi / ExplorerPage / GraphCanvas | Implemented; real local HTTP exercised |
| GET | /api/v1/sessions/{session_id}/graphs/metrics | None | path: session_id (required); query: ontology_id; query: build_id; query: limit [minimum=1, maximum=100, default=15] | 200: Result_dict_ | graphsApi / ExplorerPage / GraphCanvas | Implemented; real local HTTP exercised |

Total: **58 operations**, including health and the stage registry. Parameterized stage GET/POST routes each count once.

## Controller-only constraints

- Build stage path values: 10 through 15.
- Cleaning kind values: merges, changes, quarantine, records.
- Relationship deletion uses a full key query parameter, not a relationship path ID.
- Approval compares author/reviewer case-insensitively and checks the reviewed draft author.
- Snapshot integrity and validation are checked before CURRENT promotion.
- Source/scope/editor mutations invalidate downstream results.
- Validation can return 200 with ok:false; frontend completion comes from session state.
- Graph source is in-memory unless ontology_id is supplied. build_id requires ontology_id.
- Graph path direction is ignored.
- Stages registry lacks prerequisites; the advisory frontend mapping is source-verified.

## Backend contract differences

POST metadata/analyze returns tables plus relationship candidates; GET metadata/analysis returns only table classifications. Downloads have a generic JSON OpenAPI declaration but return bytes. Broad dictionary schemas are rendered through unknown-valued report components. No backend contract was changed to hide these limitations.

Concurrency clarification: operation() locks most reads as well as mutations. The frontend serializes these per session; session views, build status, and events remain available for polling.
