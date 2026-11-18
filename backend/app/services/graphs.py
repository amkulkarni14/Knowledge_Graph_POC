"""Safe snapshot access and bounded graph responses for frontend canvases."""
import re
import json
from itertools import islice
from pathlib import Path
import networkx as nx
from fastapi.encoders import jsonable_encoder
from kg_pipeline.graph_builder.loaders import s16_graph_persistence as persistence
from backend.app.exceptions.handlers import ApiError
from backend.app.services.workflow import require

ARTIFACTS = {"graph.json.gz": "application/gzip", "graph.graphml": "application/graphml+xml",
             "manifest.json": "application/json", "quarantine.json": "application/json"}


def snapshot_root(session):
    return session.root / "graphs"


def checked_path(session, ontology_id, build_id=None, artifact=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,62}", ontology_id):
        raise ApiError(422, "invalid_identifier", "Invalid ontology identifier")
    if build_id is not None and not re.fullmatch(r"[0-9]{8}T[0-9]{12}Z", build_id):
        raise ApiError(422, "invalid_identifier", "Invalid snapshot identifier")
    if artifact is not None and artifact not in ARTIFACTS:
        raise ApiError(404, "artifact_not_found", "Artifact is not available")
    root = snapshot_root(session).resolve()
    target = root / ontology_id
    if build_id:
        target /= build_id
    if artifact:
        target /= artifact
    target = target.resolve()
    if not target.is_relative_to(root):
        raise ApiError(422, "invalid_path", "Invalid snapshot path")
    return target


def load(session, ontology_id, build_id=None):
    if build_id is None:
        current = checked_path(session, ontology_id) / "CURRENT"
        if not current.is_file() or not current.resolve().is_relative_to(snapshot_root(session).resolve()):
            raise ApiError(404, "snapshot_not_found", "No current snapshot exists")
        build_id = current.read_text(encoding="utf-8").strip()
    folder = checked_path(session, ontology_id, build_id)
    if not folder.is_dir():
        raise ApiError(404, "snapshot_not_found", "Snapshot does not exist")
    for name in ARTIFACTS:
        if not checked_path(session, ontology_id, build_id, name).is_file():
            raise ApiError(409, "incomplete_snapshot", "Snapshot is incomplete")
    try:
        manifest = json.loads(checked_path(session, ontology_id, build_id, "manifest.json").read_text(encoding="utf-8"))
        for name in ("graph.json.gz", "graph.graphml", "quarantine.json"):
            expected = manifest["files"][name]
            if persistence._sha256(checked_path(session, ontology_id, build_id, name)) != expected:
                raise ValueError("Artifact checksum mismatch")
        return persistence.load_graph(ontology_id, build_id, root=snapshot_root(session))
    except (ValueError, KeyError, OSError):
        raise ApiError(409, "snapshot_integrity", "Snapshot integrity verification failed") from None


def select_graph(session, ontology_id=None, build_id=None):
    if ontology_id is not None:
        return load(session, ontology_id, build_id)
    if build_id is not None:
        raise ApiError(422, "missing_ontology", "Snapshot selection requires an ontology identifier")
    require(session, 14)
    return session.ctx.graph


def hidden_properties(session):
    hidden = {"password", "token", "secret", "api_key"}
    onto = session.ctx.approved_ontology or session.ctx.manual_ontology
    if onto:
        hidden |= {a.name for cls in onto.classes for a in cls.attributes if a.pii}
        if session.ctx.scope:
            sensitive = set(session.ctx.scope.sensitive_columns)
            hidden |= {a.name for cls in onto.classes if cls.mapping for a in cls.attributes
                       if f"{cls.mapping.source_table}.{a.source_column}" in sensitive}
    return hidden


def node_properties(session, data):
    hide = hidden_properties(session)
    return jsonable_encoder({k: v for k, v in data.items() if k.lower() not in hide})


def graph_view(session, graph, limit=300, edge_limit=1000, labels=None, focus=None, hops=1):
    selected = graph
    if focus is not None:
        if focus not in graph:
            raise ApiError(404, "node_not_found", "Node does not exist")
        # Bounded breadth-first search avoids materializing an unbounded ego graph.
        seen, frontier = {focus}, [focus]
        for _ in range(hops):
            next_frontier = []
            for node in frontier:
                for neighbor in graph.to_undirected(as_view=True).neighbors(node):
                    if neighbor not in seen:
                        seen.add(neighbor)
                        next_frontier.append(neighbor)
                        if len(seen) >= limit:
                            break
                if len(seen) >= limit:
                    break
            frontier = next_frontier
            if not frontier or len(seen) >= limit:
                break
        selected = graph.subgraph(seen)
    candidates = (node for node, props in selected.nodes(data=True)
                  if not labels or props.get("label") in labels)
    nodes = list(islice(candidates, limit))
    subgraph = selected.subgraph(nodes)
    edges = list(islice(subgraph.edges(keys=True, data=True), edge_limit))
    return {"nodes": [{"id": str(n), "properties": node_properties(session, graph.nodes[n])} for n in nodes],
            "edges": [{"source": str(u), "target": str(v), "key": str(k),
                       "properties": node_properties(session, props)} for u, v, k, props in edges],
            "total_nodes": graph.number_of_nodes(), "total_edges": graph.number_of_edges(),
            "truncated": len(nodes) < graph.number_of_nodes() or len(edges) < subgraph.number_of_edges()}
