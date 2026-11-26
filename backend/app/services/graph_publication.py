"""Build-time analytics and staged graph publication."""
import hashlib
import hmac
import os
from collections import Counter
from time import sleep

import networkx as nx
from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError

from backend.app.exceptions.handlers import ApiError
from backend.app.repositories import graph_versions as versions
from backend.app.services.graphs import hidden_properties
from backend.app.services.neo_graph import NeoGraphStore


def analyze(graph):
    simple = nx.Graph(graph)
    count, edges = graph.number_of_nodes(), graph.number_of_edges()
    components = sorted((len(group) for group in nx.connected_components(simple)), reverse=True)
    rankings = {"degree": nx.degree_centrality(simple)}
    communities = []
    unavailable = {}
    # Bound algorithms with superlinear time or dense working state.
    if 0 < count <= 2000 and edges <= 20000:
        try:
            rankings["pagerank"] = nx.pagerank(graph, max_iter=200)
        except ImportError:
            unavailable["pagerank"] = "SciPy is unavailable in the backend Python environment"
        except nx.PowerIterationFailedConvergence:
            unavailable["pagerank"] = "PageRank did not converge"
        rankings["betweenness"] = nx.betweenness_centrality(simple, k=64 if count > 64 else None, seed=42)
        rankings["closeness"] = nx.closeness_centrality(simple)
        if edges:
            groups = nx.community.louvain_communities(simple, seed=42)
            communities = [{"size": len(group), "members": sorted(group)[:100]}
                           for group in sorted(groups, key=len, reverse=True)[:100]]
    return {
        "nodes": count, "relationships": edges, "components": len(components),
        "node_labels": dict(Counter(props.get("label", "Entity") for _, props in graph.nodes(data=True))),
        "relationship_types": dict(Counter(props.get("type", "Relationship") for *_, props in graph.edges(data=True))),
        "largest_component": components[0] if components else 0,
        "strong_components": nx.number_strongly_connected_components(graph),
        "isolated_nodes": nx.number_of_isolates(simple), "density": nx.density(simple),
        "average_degree": sum(d for _, d in simple.degree()) / count if count else 0,
        "maximum_degree": max((d for _, d in simple.degree()), default=0),
        "average_path_length": (nx.average_shortest_path_length(simple)
                                if len(components) == 1 and count <= 500 else None),
        "rankings": {name: [{"node": node, "score": score}
                            for node, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:100]]
                     for name, scores in rankings.items()},
        "communities": communities,
        "unavailable_algorithms": unavailable,
    }


def private_identifiers(ctx):
    onto = ctx.build_ontology
    sensitive = set(ctx.scope.sensitive_columns if ctx.scope else ())
    for cls in onto.classes:
        if cls.mapping:
            sensitive.update(f"{cls.mapping.source_table}.{attr.source_column}"
                             for attr in cls.attributes if attr.pii and attr.source_column)
    for rel in onto.relationships:
        if rel.mapping:
            sensitive.update(f"{rel.mapping.table}.{prop.source_column}"
                             for prop in rel.properties if prop.pii and prop.source_column)

    labels = {cls.name for cls in onto.classes if cls.mapping and any(
        f"{cls.mapping.source_table}.{column}" in sensitive for column in cls.mapping.key_columns)}
    edge_types = set()
    for rel in onto.relationships:
        if rel.multi_edge and rel.mapping:
            table = ctx.catalog.table(rel.mapping.table)
            columns = table.primary_key or (rel.mapping.source_key_columns + rel.mapping.target_key_columns)
            if any(f"{rel.mapping.table}.{column}" in sensitive for column in columns):
                edge_types.add((rel.name, rel.mapping.table))
    secret = os.getenv("KG_GRAPH_ID_KEY")
    if (labels or edge_types) and not secret:
        raise ApiError(503, "graph_id_key_unconfigured", "Configure a graph identity key for sensitive source identifiers")

    def token(kind, value):
        return hmac.new(secret.encode(), f"{kind}:{value}".encode(), hashlib.sha256).hexdigest()

    node_ids = {node: f'{props["label"]}:private:{token("node", node)}'
                for node, props in ctx.graph.nodes(data=True) if props.get("label") in labels}

    def edge_key(key, props):
        kind = props.get("type")
        if ((kind, props.get("source_table")) in edge_types
                or ctx.graph.graph.get("import_origin") == "graphml"
                and any(relation_type == kind for relation_type, _ in edge_types)):
            return f'{kind}:private:{token("relationship", key)}'
        return str(key)

    return node_ids, edge_key


def persist(session, actor, version, report, commit, started_at=None, *, context=None):
    ctx = context if context is not None else session.ctx
    if not ctx.graph_report or not ctx.graph_report["ok"] or ctx.build_ontology is None:
        raise ApiError(409, "invalid_graph", "Graph and ontology must pass validation")
    report("analytics", 0)
    node_ids, edge_key = private_identifiers(ctx)
    analytics = analyze(nx.relabel_nodes(ctx.graph, node_ids) if node_ids else ctx.graph)
    build_stats = ctx.build_stats
    analytics["quality"] = {
        "merged_entities": sum(item.get("merged", 0) for item in build_stats.get("classes", {}).values()),
        "duplicate_relationships": sum(item.get("duplicates", 0) for item in build_stats.get("relationships", {}).values()),
        "dangling_references": sum(item.get("dangling", 0) for item in build_stats.get("relationships", {}).values()),
        "quarantine_by_stage": dict(Counter(item.get("stage", "unknown") for item in build_stats.get("quarantine", []))),
        "validation_warnings": len(ctx.graph_report["warnings"]),
    }
    hidden = {name.casefold() for name in hidden_properties(session)}
    sensitive = set(ctx.scope.sensitive_columns if ctx.scope else ())
    for relationship in ctx.build_ontology.relationships:
        mapping = relationship.mapping
        if mapping:
            hidden.update(prop.name.casefold() for prop in relationship.properties if prop.pii)
            hidden.update(prop.name.casefold() for prop in relationship.properties
                          if f"{mapping.table}.{prop.source_column}" in sensitive)
            hidden.update(column.casefold() for column in mapping.property_columns
                          if f"{mapping.table}.{column}" in sensitive)
    with versions.publication_guard(version):
        with versions.registry() as db:
            versions.register(db, session, actor, version, ctx, analytics, started_at)
        import_and_publish(session, actor, version, report, commit, hidden, node_ids, edge_key, ctx.graph)
    ctx.snapshot = {"build_id": version, "ontology_id": ctx.build_ontology.ontology_id,
                    "published": True, "storage": "neo4j"}
    ctx.mark_done(16)


def import_and_publish(session, actor, version, report, commit, hidden, node_ids, edge_key, graph):
    try:
        for attempt in range(3):
            totals = {"nodes": 0, "relationships": 0}

            def progress(stage, size):
                totals[stage] += size
                report(stage, totals[stage])

            try:
                with NeoGraphStore() as store:
                    store.import_graph(graph, session.id, version, hidden, progress,
                                       node_ids=node_ids, edge_key=edge_key)
                break
            except (TransientError, ServiceUnavailable, SessionExpired):
                if attempt == 2:
                    raise
                sleep(2 ** attempt)
        commit()
        with versions.registry() as db:
            versions.publish(db, session.id, version, actor)
    except Exception as error:
        with versions.registry() as db:
            versions.fail(db, session.id, version, actor)
        if isinstance(error, ApiError):
            raise
        raise ApiError(502, "publication_failed", "The staged graph could not be published") from None
