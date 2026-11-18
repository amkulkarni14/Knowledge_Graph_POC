# Streamlit-to-React migration

| Existing Streamlit page/component | React implementation | Existing API usage |
|---|---|---|
| app, bootstrap, layout | AppShell, OverviewPage, session store | sessions, stages, events |
| home | OverviewPage | guided sample entry; explicit review/approval |
| s01_scope | ScopePage | scope read/save |
| s02_connect | SourcesPage | sample, PostgreSQL, multipart upload, source status |
| s03_schema | MetadataPage | extraction, catalog, tables, columns, preview |
| s04_analysis | MetadataPage analysis route | analyze, analysis results |
| s05_manual | OntologyPage, OntologyCanvas, AttributeEditor | draft and class/relationship editing, save/revert |
| s06_ai | ReviewPages suggestions route | offline/live suggestions, metadata, skip |
| s07_review | ReviewPages review route | decisions, preview, apply, cycle/watermark rules |
| s08_validate | ReviewPages validation route | validation report, blocking findings |
| s09_repo | ReviewPages repository route | explicit approval, versions, audit, rollback, reuse |
| s10_plan | BuildPage stage 10 | plan execution/result |
| s11_extract | BuildPage stage 11 | extraction, watermarks, rows, progress |
| s12_quality | BuildPage stage 12 | quality report, supported business rules |
| s13_clean | BuildPage stage 13 | summaries, merges, changes, quarantine, records |
| s14_build | BuildPage stage 14, ExplorerPage | graph construction and graph data |
| s15_gvalidate | BuildPage stage 15 | reconciliation/conformance/validation reports |
| s16_store | StoragePage | snapshots, optional Neo4j, CURRENT, artifacts |
| explorer, graph_view, viz | ExplorerPage, GraphCanvas | current/saved graph, search, inspector, paths, metrics |

The Streamlit automatic demo policy is not an approval bypass in React. Every workflow explicitly reviews and approves. The legacy Customer 360 server-files shortcut has no API equivalent; users upload those existing CSVs with the implemented upload endpoint. No backend environment credentials are prefilled in browser forms.
