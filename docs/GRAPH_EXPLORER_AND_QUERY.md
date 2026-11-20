# Graph explorer, query and GraphML

Use **Graph Explorer** for the active NetworkX graph or a local snapshot. Use **Published Graph Explorer** for a Neo4j version. Search by ID or name, filter, select or expand an entity, and investigate a path in the relevant view. Published **Query Workbench** supports graph, table and JSON results for templates and the compiled Cypher subset.

Use **Graph Versions** for a full GraphML export. In **Graph Intelligence**, enter an entity ID and use **Export neighborhood GraphML**. The export retrieves a bounded two-hop sample from the selected published graph or active session. This action exports the neighborhood of the specified node. Canvas layout and hidden-element state are outside GraphML serialization.

To bring GraphML into a project, activate that project's workflow and approve its ontology. Open **GraphML Import**, select a file, provide the GraphML attribute names that carry labels and relationship types, then validate and preview. Review the destination and counts. **Stage and publish a new version** queues a worker, and **Graph Operations** shows the result. Uploads accept one directed UTF-8 graph up to 4 MiB, 10,000 nodes, and 30,000 relationships. DTDs, duplicate identifiers, dangling relationships, invalid ontology types, and cardinality or cycle violations are rejected.

The exporter stores each node or edge as a JSON record under a GraphML data key. The importer also accepts attribute-based GraphML. It maps declared attributes through ontology types and ignores unknown or reserved fields. XML identifiers or exported JSON identifiers are preserved. A published export can omit sensitive fields. When an approved ontology requires one of those fields, validate against an authorized complete file or an ontology that permits the field to be absent. The import does not recreate Neo4j constraints, layout settings or raw source-record provenance. Test the local-snapshot-to-Neo4j round-trip with the opt-in live test.

New local snapshots use unique XML edge IDs and retain original multigraph edge keys in an attribute. Older local GraphML files containing repeated XML edge identifiers require a new export before import.
