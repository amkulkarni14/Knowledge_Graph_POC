# Neo4j integration

Publish a validated session graph from **Storage & Snapshots** or import GraphML from the **GraphML Import** sidebar. GraphML reuses the existing bounded build worker and creates an immutable version under the active workflow project. The worker validates GraphML again with that project's approved ontology. The Neo4j adapter scopes imports and reads by project and version. A composite node constraint prevents duplicate identities. PostgreSQL publishes only after Neo4j validates the staged counts and relationship endpoints.

Failed imports preserve the current pointer. The source pipeline and ontology context stay available in the active workflow. GraphML publication records a content digest as its source reference.

See [platform setup](PUBLISHED_GRAPH_PLATFORM.md) for indexes, retention, DB identities and lifecycle procedures. For Aura, use verified TLS and provide an approved CA bundle through `SSL_CERT_FILE` if necessary. Production Aura publication requires a deployment smoke test. The disposable integration fixture exercises Neo4j Community without GDS.
